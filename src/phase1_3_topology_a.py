"""Phase 1.3 — Topology A: Audio-Only (BirdNET -> LLM).

Pipeline per fold:
    mp4 -> wav (16 kHz mono, cached) -> birdnetlib -> target filter
        -> qwen2.5:7b (format=json)

Fallback: when BirdNET returns zero target-species detections at
confidence >= 0.3, the LLM call is skipped and the prediction is set to
``{sparrow: 0, bulbul: 0, fallback_used: true}``. The BirdNET raw output
and ``other_birds`` list are still persisted so that Phase 1.3+ can
revisit these cases.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_3_common.birdnet_analyzer import BirdNetAnalyzer, DEFAULT_TARGET_MIN_CONF
from phase1_3_common.llm_client import LlmClient, ModelMissing, OllamaUnavailable
from phase1_3_common.loocv_runner import (
    compute_metrics,
    ensure_utf8_streams,
    run_loocv,
)
from phase1_3_common.video_processor import DEFAULT_SR, extract_audio, probe_duration

TOPOLOGY = "A"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_3" / "topology_a"
SUMMARY_PATH = REPO_ROOT / "results" / "phase1_3" / "topology_a_summary.md"

SYSTEM_PROMPT = """あなたは日本の野鳥観察を支援するアシスタントです。
ベランダに設置したバードケーキに来る鳥を観察しています。
撮影環境にはスズメとヒヨドリのみが飛来します。

BirdNET による音声種識別結果のみから、動画に映っている鳥の種を判定してください。
視覚情報はありません。音声のみで判断します。

入力:
{
  "detections": [
    {"species_code": "sparrow", "scientific_name": "Passer montanus", "confidence": 0.85, "num_detections": 3},
    {"species_code": "bulbul", "scientific_name": "Hypsipetes amaurotis", "confidence": 0.62, "num_detections": 1},
    ...
  ],
  "other_birds_detected": ["Rock Pigeon", "Sparrow sp."],
  "total_audio_duration_sec": 45.2
}

以下のJSON形式で応答してください:
{
  "predictions": {"sparrow": 0 または 1, "bulbul": 0 または 1},
  "confidence": {"sparrow": 0.0-1.0, "bulbul": 0.0-1.0},
  "reasoning": "判定理由 (50字以内)",
  "fallback_used": false
}

判定ルール:
- BirdNET が sparrow を confidence >= 0.3 で検出 -> sparrow = 1
- BirdNET が bulbul を confidence >= 0.3 で検出 -> bulbul = 1
- detections が空（対象種検出なし）-> {sparrow: 0, bulbul: 0}, reasoning に理由明記"""


def make_fold_fn(bn: BirdNetAnalyzer, llm: LlmClient):
    def fold_fn(fold: int, video: dict[str, Any], gt: dict[str, int]) -> dict[str, Any]:
        t0 = time.perf_counter()
        audio_path = extract_audio(video["video_path"], video["video_id"], sr=DEFAULT_SR)
        t_extract = time.perf_counter() - t0
        duration = probe_duration(audio_path)

        t0 = time.perf_counter()
        bn_out = bn.analyze(audio_path, target_min_conf=DEFAULT_TARGET_MIN_CONF)
        t_bn = time.perf_counter() - t0

        llm_input = {
            "detections": bn_out["filtered_target_species"],
            "other_birds_detected": bn_out["other_birds"],
            "total_audio_duration_sec": round(duration, 2),
        }

        t_llm = 0.0
        fallback = False
        llm_output: dict[str, Any] | None = None

        if not bn_out["filtered_target_species"]:
            fallback = True
            llm_output = {
                "raw": None,
                "parsed": {
                    "predictions": {"sparrow": 0, "bulbul": 0},
                    "confidence": {"sparrow": 0.0, "bulbul": 0.0},
                    "reasoning": "対象種の検出なし (LLM スキップ)",
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
            "birdnet_output": bn_out,
            "fallback_triggered": fallback,
            "llm_input": llm_input,
            "llm_output": llm_output,
            "final_prediction": final_pred,
            "ground_truth": gt,
            "is_correct": is_correct,
            "elapsed_sec": {
                "audio_extract": round(t_extract, 3),
                "birdnet": round(t_bn, 3),
                "llm": round(t_llm, 3),
                "total": round(t_extract + t_bn + t_llm, 3),
            },
        }
    return fold_fn


def format_summary(rows: list[dict[str, Any]], metrics: dict[str, Any], total_time: float) -> str:
    n = len(rows)
    lines = [
        "# Phase 1.3 Topology A (Audio-Only) Summary",
        "",
        "- Pipeline: ffmpeg (16 kHz mono) -> BirdNET (birdnetlib) -> `qwen2.5:7b`",
        f"- Folds:   {n}",
        f"- Scored:  {metrics['n_scored']}",
        f"- Fallback triggered: {metrics['fallback_triggered']} / {n}",
        f"- LLM parse failures (non-fallback): {metrics['parse_fail']} / {n}",
        f"- Errors:  {metrics['errors']} / {n}",
        f"- Macro F1: {metrics['macro_f1']:.3f}",
        f"- Sparrow F1: {metrics['f1']['sparrow']:.3f} | Bulbul F1: {metrics['f1']['bulbul']:.3f}",
        f"- Sparrow accuracy: {metrics['accuracy']['sparrow']:.3f} | "
        f"Bulbul accuracy: {metrics['accuracy']['bulbul']:.3f}",
        f"- Total wall time: {total_time:.1f} s",
        "",
        "## Per-fold results",
        "",
        "| fold | video_id | dur (s) | targets | other | pred (S/B) | GT (S/B) | S OK | B OK | fallback | t_audio | t_birdnet | t_llm |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['fold']:02d} | {r['video_id']} | - | - | - | ERR | {r['ground_truth']['sparrow']}/{r['ground_truth']['bulbul']} | - | - | - | - | - | - |")
            continue
        bn = r["birdnet_output"]
        targets = ",".join(d["species_code"] for d in bn["filtered_target_species"]) or "-"
        other = len(bn["other_birds"])
        pred = r["final_prediction"]
        gt = r["ground_truth"]
        ok = r["is_correct"]
        ok_s = "OK" if ok["sparrow"] else "X"
        ok_b = "OK" if ok["bulbul"] else "X"
        fb = "Y" if r["fallback_triggered"] else "-"
        t = r["elapsed_sec"]
        lines.append(
            f"| {r['fold']:02d} | {r['video_id']} "
            f"| {r['audio_extraction']['duration_sec']:.1f} "
            f"| {targets} | {other} "
            f"| {pred['sparrow']}/{pred['bulbul']} "
            f"| {gt['sparrow']}/{gt['bulbul']} "
            f"| {ok_s} | {ok_b} | {fb} "
            f"| {t['audio_extract']:.2f} "
            f"| {t['birdnet']:.2f} "
            f"| {t['llm']:.2f} |"
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

    lines.append("## Mean stage times (across all folds)")
    lines.append("")
    n_all = sum(1 for r in rows if "error" not in r) or 1
    mean_extract = sum(r["elapsed_sec"]["audio_extract"] for r in rows if "error" not in r) / n_all
    mean_bn = sum(r["elapsed_sec"]["birdnet"] for r in rows if "error" not in r) / n_all
    mean_llm = sum(r["elapsed_sec"]["llm"] for r in rows if "error" not in r) / n_all
    lines.append(f"- Audio extraction:    {mean_extract:.2f} s")
    lines.append(f"- BirdNET inference:   {mean_bn:.2f} s")
    lines.append(f"- LLM call (non-fallback avg): {mean_llm:.2f} s")
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

    run_start = time.perf_counter()
    rows = run_loocv(TOPOLOGY, make_fold_fn(bn, llm), RESULTS_BASE)
    total_time = time.perf_counter() - run_start

    metrics = compute_metrics(rows)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(format_summary(rows, metrics, total_time), encoding="utf-8")

    print()
    print(f"Folds scored     : {metrics['n_scored']} / {len(rows)}")
    print(f"Fallback          : {metrics['fallback_triggered']}")
    print(f"LLM parse failures: {metrics['parse_fail']}")
    print(f"Errors            : {metrics['errors']}")
    print(f"Macro F1          : {metrics['macro_f1']:.3f}")
    print(f"Summary           : {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
