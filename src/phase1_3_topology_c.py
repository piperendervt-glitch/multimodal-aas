"""Phase 1.3 — Topology C: Parallel Fusion (YOLOv8n + BirdNET -> LLM).

Both the visual and audio pipelines run independently per fold; the LLM
receives a combined prompt and makes the final multi-label decision.

Design choices, based on Phase 1.3 root-cause analysis:

  * BirdNET is invoked with ``target_min_conf=None`` so *every*
    detection above ``min_conf=0.1`` is forwarded to the LLM. This is a
    deliberate workaround for the balcony webcam audio quality
    limitation — the 0.3 species threshold used by Topology A silenced
    the audio node on 10/11 folds, so here we trust the LLM to weight
    audio evidence itself.
  * Fallback fires only when *both* modalities are silent
    (``frames_with_bird=0`` and ``target_species_found=false``). A
    single-modality signal is always forwarded to the LLM.
  * ``elapsed_sec`` is broken out per stage (audio extract, frame
    extract, birdnet, yolo, llm, total) so Phase 1.3+ can see where
    wall time is spent.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_3_common.birdnet_analyzer import (
    BULBUL_COMMON,
    BULBUL_SCI,
    BirdNetAnalyzer,
    SPARROW_COMMON,
    SPARROW_SCI,
)
from phase1_3_common.llm_client import LlmClient, ModelMissing, OllamaUnavailable
from phase1_3_common.loocv_runner import (
    compute_metrics,
    ensure_utf8_streams,
    run_loocv,
)
from phase1_3_common.video_processor import (
    DEFAULT_FPS,
    DEFAULT_SR,
    extract_audio,
    extract_frames,
    probe_duration,
)
from phase1_3_common.yolo_detector import YoloDetector

TOPOLOGY = "C"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_3" / "topology_c"
SUMMARY_PATH = REPO_ROOT / "results" / "phase1_3" / "topology_c_summary.md"

SYSTEM_PROMPT = """あなたは日本の野鳥観察を支援するアシスタントです。
ベランダに設置したバードケーキに来る鳥を観察しています。
撮影環境にはスズメとヒヨドリのみが飛来します。

YOLOv8n による視覚的鳥検出結果と、BirdNET による音声種識別結果の
両方から、動画に映っている鳥の種を判定してください。

重要な判定材料:
- スズメ (sparrow) は小型: 画面に対する bbox サイズは通常 0.08 未満
- ヒヨドリ (bulbul) は中型: 画面に対する bbox サイズは通常 0.13 以上
- 中間サイズ (0.08-0.13) の場合は、検出数や分布、音声情報から判断
- 動画の音声品質は低い (Web カメラマイク) ため、BirdNET の検出が
  少なくても視覚情報を優先してよい

入力:
{
  "visual": {
    "num_frames_analyzed": 15,
    "frames_with_bird": 12,
    "max_bbox_size_relative": 0.08,
    "avg_bbox_size_relative": 0.06,
    "std_bbox_size": 0.02,
    "avg_detection_confidence": 0.76,
    "detection_counts_per_frame": [1, 2, 2, 1, 0, ...]
  },
  "audio": {
    "all_detections": [
      {"species_code": "...", "scientific_name": "...", "confidence": 0.XX, "num_detections": X}
    ],
    "target_species_found": true/false,
    "total_detections": 0 or N,
    "note": "optional descriptive note"
  }
}

以下のJSON形式で応答してください:
{
  "predictions": {"sparrow": 0 または 1, "bulbul": 0 または 1},
  "confidence": {"sparrow": 0.0-1.0, "bulbul": 0.0-1.0},
  "reasoning": "判定理由 (50字以内)",
  "modality_used": "visual" または "audio" または "both" または "none",
  "fallback_used": false
}

判定ルール:
1. 視覚で frames_with_bird = 0 and 音声で対象種検出あり -> 音声に基づき判定
2. 視覚で frames_with_bird > 0 -> bbox サイズで判定、音声で補強
3. 両方とも対象種検出なし -> {sparrow: 0, bulbul: 0}, fallback_used=true
4. 音声に他種検出があるが対象種なし -> 視覚情報優先"""


def _species_code(scientific_name: str, common_name: str) -> str:
    if SPARROW_SCI in scientific_name or SPARROW_COMMON in common_name:
        return "sparrow"
    if BULBUL_SCI in scientific_name or BULBUL_COMMON in common_name:
        return "bulbul"
    return "other"


def format_audio_for_llm(all_detections: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate BirdNET per-window detections into one row per species.

    The LLM gets a concise species-level view with max confidence and
    total windows, plus a boolean hint about whether either target
    species appeared at all.
    """
    by_species: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for d in all_detections:
        key = (d["scientific_name"], d.get("species", ""))
        by_species.setdefault(key, []).append(d)

    target_species_found = any(
        SPARROW_SCI in sci or SPARROW_COMMON in com
        or BULBUL_SCI in sci or BULBUL_COMMON in com
        for (sci, com) in by_species
    )

    formatted: list[dict[str, Any]] = []
    items = list(by_species.items())
    items.sort(key=lambda kv: -max(d["confidence"] for d in kv[1]))
    for (sci, com), hits in items:
        confs = [d["confidence"] for d in hits]
        formatted.append({
            "species_code": _species_code(sci, com),
            "scientific_name": sci,
            "common_name": com,
            "confidence": round(max(confs), 4),
            "avg_confidence": round(sum(confs) / len(confs), 4),
            "num_detections": len(hits),
        })

    return {
        "all_detections": formatted,
        "target_species_found": target_species_found,
        "total_detections": len(all_detections),
        "note": (
            "音声品質は低い (Web カメラマイク)。"
            "対象種が検出されなくても視覚情報を優先可能。"
        ),
    }


def make_fold_fn(bn: BirdNetAnalyzer, det: YoloDetector, llm: LlmClient):
    def fold_fn(fold: int, video: dict[str, Any], gt: dict[str, int]) -> dict[str, Any]:
        t0 = time.perf_counter()
        audio_path = extract_audio(video["video_path"], video["video_id"], sr=DEFAULT_SR)
        t_audio_ext = time.perf_counter() - t0
        duration = probe_duration(audio_path)

        t0 = time.perf_counter()
        frame_paths = extract_frames(
            video["video_path"], video["video_id"], fps=DEFAULT_FPS
        )
        t_frame_ext = time.perf_counter() - t0

        t0 = time.perf_counter()
        bn_out = bn.analyze(audio_path, target_min_conf=None)
        t_bn = time.perf_counter() - t0

        t0 = time.perf_counter()
        yolo_out = det.aggregate(frame_paths)
        t_yolo = time.perf_counter() - t0

        audio_input = format_audio_for_llm(bn_out["all_detections"])
        visual_input = {
            "num_frames_analyzed": yolo_out["num_frames_analyzed"],
            "frames_with_bird": yolo_out["frames_with_bird"],
            "max_bbox_size_relative": yolo_out["max_bbox_size_relative"],
            "avg_bbox_size_relative": yolo_out["avg_bbox_size_relative"],
            "std_bbox_size": yolo_out["std_bbox_size"],
            "avg_detection_confidence": yolo_out["avg_detection_confidence"],
            "detection_counts_per_frame": yolo_out["detection_counts_per_frame"],
        }
        llm_input = {"visual": visual_input, "audio": audio_input}

        t_llm = 0.0
        fallback = False
        llm_output: dict[str, Any] | None = None

        both_silent = (
            yolo_out["frames_with_bird"] == 0 and not audio_input["target_species_found"]
        )

        if both_silent:
            fallback = True
            llm_output = {
                "raw": None,
                "parsed": {
                    "predictions": {"sparrow": 0, "bulbul": 0},
                    "confidence": {"sparrow": 0.0, "bulbul": 0.0},
                    "reasoning": "視覚で鳥なし、音声でも対象種なし (LLM スキップ)",
                    "modality_used": "none",
                    "fallback_used": True,
                },
                "elapsed_sec": 0.0,
            }
            final_pred = {
                "sparrow": 0,
                "bulbul": 0,
                "confidence": {"sparrow": 0.0, "bulbul": 0.0},
            }
        else:
            llm_output = llm.generate(SYSTEM_PROMPT, llm_input)
            t_llm = llm_output["elapsed_sec"]
            parsed = llm_output["parsed"]
            if parsed is None:
                fallback = True
                final_pred = {
                    "sparrow": 0,
                    "bulbul": 0,
                    "confidence": {"sparrow": 0.0, "bulbul": 0.0},
                }
            else:
                p = parsed["predictions"]
                c = parsed.get("confidence") or {}
                final_pred = {
                    "sparrow": int(p["sparrow"]),
                    "bulbul": int(p["bulbul"]),
                    "confidence": {
                        "sparrow": float(c.get("sparrow", 0.0)),
                        "bulbul": float(c.get("bulbul", 0.0)),
                    },
                }

        is_correct = {
            "sparrow": final_pred["sparrow"] == gt["sparrow"],
            "bulbul":  final_pred["bulbul"]  == gt["bulbul"],
        }

        return {
            "video_id": video["video_id"],
            "audio_extraction": {
                "audio_path": str(audio_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "duration_sec": round(duration, 3),
                "sample_rate": DEFAULT_SR,
            },
            "frame_extraction": {
                "num_frames": len(frame_paths),
                "fps_sampling": float(DEFAULT_FPS),
            },
            "birdnet_output": bn_out,
            "yolo_output": yolo_out,
            "fallback_triggered": fallback,
            "llm_input": llm_input,
            "llm_output": llm_output,
            "final_prediction": final_pred,
            "ground_truth": gt,
            "is_correct": is_correct,
            "elapsed_sec": {
                "audio_extraction": round(t_audio_ext, 3),
                "frame_extraction": round(t_frame_ext, 3),
                "birdnet": round(t_bn, 3),
                "yolo": round(t_yolo, 3),
                "llm": round(t_llm, 3),
                "total": round(
                    t_audio_ext + t_frame_ext + t_bn + t_yolo + t_llm, 3
                ),
            },
        }

    return fold_fn


def _modality_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"visual": 0, "audio": 0, "both": 0, "none": 0, "unparsed": 0}
    for r in rows:
        if "error" in r:
            counts["unparsed"] += 1
            continue
        parsed = (r.get("llm_output") or {}).get("parsed") or {}
        mod = parsed.get("modality_used")
        if mod in counts:
            counts[mod] += 1
        else:
            counts["unparsed"] += 1
    return counts


def format_summary(
    rows: list[dict[str, Any]],
    metrics: dict[str, Any],
    total_time: float,
) -> str:
    n = len(rows)
    modality_counts = _modality_counts(rows)
    lines = [
        "# Phase 1.3 Topology C (Parallel Fusion) Summary",
        "",
        "- Pipeline: ffmpeg (audio 16 kHz + frames @ 1 fps CFR) "
        "-> BirdNET + YOLOv8n -> `qwen2.5:7b` fusion",
        f"- Folds:   {n}",
        f"- Scored:  {metrics['n_scored']}",
        f"- Fallback triggered: {metrics['fallback_triggered']} / {n}",
        f"- LLM parse failures (non-fallback): {metrics['parse_fail']} / {n}",
        f"- Errors:  {metrics['errors']} / {n}",
        f"- Macro F1: {metrics['macro_f1']:.3f}",
        f"- Sparrow F1: {metrics['f1']['sparrow']:.3f} | "
        f"Bulbul F1: {metrics['f1']['bulbul']:.3f}",
        f"- Sparrow accuracy: {metrics['accuracy']['sparrow']:.3f} | "
        f"Bulbul accuracy: {metrics['accuracy']['bulbul']:.3f}",
        f"- Total wall time: {total_time:.1f} s",
        "",
        "## Modality used (from LLM response)",
        "",
        "| modality | count |",
        "|---|---:|",
        f"| visual    | {modality_counts['visual']} |",
        f"| audio     | {modality_counts['audio']} |",
        f"| both      | {modality_counts['both']} |",
        f"| none      | {modality_counts['none']} |",
        f"| unparsed  | {modality_counts['unparsed']} |",
        "",
        "## Per-fold results",
        "",
        "| fold | video_id | frames_with_bird | max_rel | audio_det | target_audio | modality | pred (S/B) | GT (S/B) | S OK | B OK | fallback | t_total |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        if "error" in r:
            lines.append(
                f"| {r['fold']:02d} | {r['video_id']} | - | - | - | - | - | ERR "
                f"| {r['ground_truth']['sparrow']}/{r['ground_truth']['bulbul']} "
                "| - | - | - | - |"
            )
            continue
        y = r["yolo_output"]
        a = r["llm_input"]["audio"]
        pred = r["final_prediction"]
        gt = r["ground_truth"]
        ok = r["is_correct"]
        ok_s = "OK" if ok["sparrow"] else "X"
        ok_b = "OK" if ok["bulbul"] else "X"
        fb = "Y" if r["fallback_triggered"] else "-"
        t_total = r["elapsed_sec"]["total"]
        modality = ((r.get("llm_output") or {}).get("parsed") or {}).get("modality_used", "-")
        lines.append(
            f"| {r['fold']:02d} | {r['video_id']} "
            f"| {y['frames_with_bird']} "
            f"| {y['max_bbox_size_relative']:.3f} "
            f"| {a['total_detections']} "
            f"| {'Y' if a['target_species_found'] else '-'} "
            f"| {modality} "
            f"| {pred['sparrow']}/{pred['bulbul']} "
            f"| {gt['sparrow']}/{gt['bulbul']} "
            f"| {ok_s} | {ok_b} | {fb} | {t_total:.2f} |"
        )
    lines.append("")

    lines.append("## Confusion matrices")
    lines.append("")
    for species in ("sparrow", "bulbul"):
        m = metrics["confusion_matrix"][species]
        lines.append(f"### {species}")
        lines.append("")
        lines.append("| | pred=1 | pred=0 |")
        lines.append("|---|---|---|")
        lines.append(f"| gt=1 | TP={m['tp']} | FN={m['fn']} |")
        lines.append(f"| gt=0 | FP={m['fp']} | TN={m['tn']} |")
        lines.append("")

    lines.append("## Model reasoning")
    lines.append("")
    for r in rows:
        if "error" in r:
            lines.append(f"- **fold_{r['fold']:02d} {r['video_id']}**: [error] {r['error']}")
            continue
        parsed = (r.get("llm_output") or {}).get("parsed") or {}
        reasoning = parsed.get("reasoning") or "(none)"
        lines.append(f"- **fold_{r['fold']:02d} {r['video_id']}**: {reasoning}")
    lines.append("")

    lines.append("## Mean stage times (non-error folds)")
    lines.append("")
    good = [r for r in rows if "error" not in r]
    n_all = len(good) or 1
    stages = ("audio_extraction", "frame_extraction", "birdnet", "yolo", "llm", "total")
    for stage in stages:
        mean = sum(r["elapsed_sec"][stage] for r in good) / n_all
        lines.append(f"- {stage:18s}: {mean:.2f} s")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()

    llm = LlmClient()
    try:
        llm.check_ready()
    except OllamaUnavailable as e:
        print(str(e), file=sys.stderr)
        return 2
    except ModelMissing as e:
        print(str(e), file=sys.stderr)
        return 3

    bn = BirdNetAnalyzer()
    det = YoloDetector()

    run_start = time.perf_counter()
    rows = run_loocv(TOPOLOGY, make_fold_fn(bn, det, llm), RESULTS_BASE)
    total_time = time.perf_counter() - run_start

    metrics = compute_metrics(rows)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        format_summary(rows, metrics, total_time), encoding="utf-8"
    )

    print()
    print(f"Folds scored     : {metrics['n_scored']} / {len(rows)}")
    print(f"Fallback          : {metrics['fallback_triggered']}")
    print(f"LLM parse failures: {metrics['parse_fail']}")
    print(f"Errors            : {metrics['errors']}")
    print(f"Macro F1          : {metrics['macro_f1']:.3f}")
    print(f"Modality counts   : {_modality_counts(rows)}")
    print(f"Summary           : {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
