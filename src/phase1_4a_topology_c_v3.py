"""Phase 1.4a Topology C_v3 — Parallel Fusion with temporal alignment.

Builds on Phase 1.3 Topology C: identical BirdNET config
(``target_min_conf=None``) and identical audio preprocessing, plus the
Phase 1.4a frame_extractor per-frame YOLO trace used to construct a
2-second ``timeline`` and a ``sync_summary``.

The LLM receives:
  * ``overall``       — Phase 1.3 C-style YOLO aggregate (full-video).
  * ``audio_overall`` — Phase 1.3 C-style BirdNET species-level summary.
  * ``timeline``      — per-window visual + audio features (sampled if
    the clip is long enough to exceed ``max_llm_windows``).
  * ``sync_summary``  — the four disjoint window sets + sync_rate.

Fallback mirrors Phase 1.4a C_v2: if both modalities are silent at the
overall level, skip the LLM and emit ``{sparrow: 0, bulbul: 0}``.
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_3_common.birdnet_analyzer import BirdNetAnalyzer
from phase1_3_common.extended_sources import load_extended_videos
from phase1_3_common.extended_summary import (
    per_fold_row,
    per_fold_table_header,
    render_breakdown,
)
from phase1_3_common.llm_client import LlmClient, ModelMissing, OllamaUnavailable
from phase1_3_common.loocv_runner import ensure_utf8_streams, run_loocv_over
from phase1_3_common.video_processor import (
    DEFAULT_FPS,
    DEFAULT_SR,
    extract_audio,
    extract_frames,
    probe_duration,
)
from phase1_3_common.yolo_detector import YoloDetector
from phase1_3_topology_c import format_audio_for_llm
from phase1_4a_common.frame_extractor import (
    aggregate_selected,
    extract_bird_frames,
    run_yolo_per_frame,
)
from phase1_4a_common.temporal_sampler import (
    DEFAULT_WINDOW_SEC,
    build_timeline,
)
from phase1_4a_common.timeline_compact import compact_timeline_for_llm

TOPOLOGY = "C_v3"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v3"
SUMMARY_PATH = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v3_summary.md"

MAX_LLM_WINDOWS = 40
LLM_TIMEOUT_SEC = 360

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

temporal_sync ヒント (2 秒ごとに視覚・音声の同期状況を集計):
- both_present: 同じ窓で鳥 bbox と対象種音声が両方検出された窓数
- visual_only: 鳥 bbox のみ検出された窓数
- audio_only:  対象種音声のみ検出された窓数
- neither:     両方なしの窓数
- sync_rate = both_present / (total - neither): 両モダリティ一致率

判断の重み付け:
- both_present が 1 以上あるとき、その窓の存在は強い肯定シグナル
- sync_rate が高いほど判定の確信度は高い
- sync_rate = 0 でも audio_only か visual_only が多ければ片側から判定

入力:
{
  "visual": {
    "num_frames_analyzed": N, "frames_with_bird": K,
    "max_bbox_size_relative": 0.XX, "avg_bbox_size_relative": 0.XX,
    "std_bbox_size": 0.XX, "avg_detection_confidence": 0.XX,
    "detection_counts_per_frame": [...]
  },
  "audio": {
    "all_detections": [{"species_code": "...", "scientific_name": "...",
                         "confidence": 0.XX, "num_detections": N}, ...],
    "target_species_found": true/false, "total_detections": N,
    "note": "音声品質低い..."
  },
  "temporal_sync": {
    "window_duration_sec": 2.0, "total_windows": N,
    "both_present": X, "visual_only": Y, "audio_only": Z, "neither": W,
    "sync_rate": 0.XX
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
1. visual.frames_with_bird = 0 AND audio.target_species_found = false
   -> {sparrow: 0, bulbul: 0}, fallback_used=true
2. visual.frames_with_bird > 0 -> bbox サイズで判定、音声で補強
3. audio のみ対象種あり -> 音声に基づき判定
4. 音声に他種検出があるが対象種なし -> 視覚情報優先
5. temporal_sync.both_present >= 1 -> 両モダリティを同等に重視"""


def _overall_visual(per_frame_yolo: list[dict[str, Any]]) -> dict[str, Any]:
    """Phase 1.3-C-style visual aggregate computed over all sampled frames."""
    import math as _math

    bbox_rels: list[float] = []
    confs: list[float] = []
    counts: list[int] = []
    frames_with_bird = 0
    for f in per_frame_yolo:
        counts.append(f["num_detections"])
        if f["num_detections"] > 0:
            frames_with_bird += 1
        for d in f["detections"]:
            bbox_rels.append(float(d["bbox_rel"]))
            confs.append(float(d["confidence"]))
    max_rel = max(bbox_rels) if bbox_rels else 0.0
    avg_rel = sum(bbox_rels) / len(bbox_rels) if bbox_rels else 0.0
    if len(bbox_rels) > 1:
        mean = sum(bbox_rels) / len(bbox_rels)
        var = sum((x - mean) ** 2 for x in bbox_rels) / (len(bbox_rels) - 1)
        std_rel = _math.sqrt(var)
    else:
        std_rel = 0.0
    max_conf = max(confs) if confs else 0.0
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    return {
        "num_frames_analyzed": len(per_frame_yolo),
        "frames_with_bird": frames_with_bird,
        "max_bbox_size_relative": round(max_rel, 4),
        "avg_bbox_size_relative": round(avg_rel, 4),
        "std_bbox_size": round(std_rel, 4),
        "max_detection_confidence": round(max_conf, 4),
        "avg_detection_confidence": round(avg_conf, 4),
        "detection_counts_per_frame": counts,
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
        per_frame = run_yolo_per_frame(det, frame_paths, fps_sampling=float(DEFAULT_FPS))
        t_yolo = time.perf_counter() - t0

        overall_visual = _overall_visual(per_frame)
        audio_overall = format_audio_for_llm(bn_out["all_detections"])

        timeline = build_timeline(
            per_frame_yolo=per_frame,
            birdnet_detections=bn_out["all_detections"],
            video_duration_sec=duration,
            window_sec=DEFAULT_WINDOW_SEC,
        )
        timeline_for_llm = compact_timeline_for_llm(timeline, max_windows=MAX_LLM_WINDOWS)

        sync = timeline["sync_summary"]
        temporal_sync = {
            "window_duration_sec": timeline["window_duration_sec"],
            "total_windows": timeline["num_windows"],
            "both_present": len(sync["both_present_windows"]),
            "visual_only": len(sync["visual_only_windows"]),
            "audio_only": len(sync["audio_only_windows"]),
            "neither": len(sync["neither_windows"]),
            "sync_rate": sync["sync_rate"],
        }

        llm_input = {
            "visual": {
                "num_frames_analyzed": overall_visual["num_frames_analyzed"],
                "frames_with_bird": overall_visual["frames_with_bird"],
                "max_bbox_size_relative": overall_visual["max_bbox_size_relative"],
                "avg_bbox_size_relative": overall_visual["avg_bbox_size_relative"],
                "std_bbox_size": overall_visual["std_bbox_size"],
                "avg_detection_confidence": overall_visual["avg_detection_confidence"],
                "detection_counts_per_frame": overall_visual["detection_counts_per_frame"],
            },
            "audio": audio_overall,
            "temporal_sync": temporal_sync,
        }

        t_llm = 0.0
        fallback = False
        llm_output: dict[str, Any] | None = None

        both_silent = (
            overall_visual["frames_with_bird"] == 0
            and not audio_overall["target_species_found"]
        )

        if both_silent:
            fallback = True
            llm_output = {
                "raw": None,
                "parsed": {
                    "predictions": {"sparrow": 0, "bulbul": 0},
                    "confidence": {"sparrow": 0.0, "bulbul": 0.0},
                    "reasoning": "視覚で鳥検出なし、音声でも対象種なし (LLM スキップ)",
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

        # frame_extractor-style selected aggregate (for parity with C_v2 logging)
        fe_out = {
            "total_frames_sampled": len(per_frame),
            "frames_with_bird": sum(1 for f in per_frame if f["num_detections"] > 0),
            "frame_selection_rate": round(
                sum(1 for f in per_frame if f["num_detections"] > 0) / len(per_frame), 4
            ) if per_frame else 0.0,
            "fps_sampling": float(DEFAULT_FPS),
            "selected_frames": [f for f in per_frame if f["num_detections"] > 0],
            "all_frames_yolo_output": per_frame,
        }
        yolo_selected = aggregate_selected(fe_out)

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
            "frame_extractor": {
                "total_frames_sampled": fe_out["total_frames_sampled"],
                "frames_with_bird": fe_out["frames_with_bird"],
                "frame_selection_rate": fe_out["frame_selection_rate"],
                "fps_sampling": fe_out["fps_sampling"],
                "all_frames_yolo_output": fe_out["all_frames_yolo_output"],
            },
            "yolo_output_overall": overall_visual,
            "yolo_output_selected_only": yolo_selected,
            "birdnet_output": bn_out,
            "timeline": timeline,
            "sync_summary": timeline["sync_summary"],
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


def _modality(row: dict[str, Any]) -> str:
    return ((row.get("llm_output") or {}).get("parsed") or {}).get("modality_used", "-")


def render_summary(rows: list[dict[str, Any]], skipped, total_time: float) -> str:
    modality_counts: Counter[str] = Counter()
    sync_rates: list[float] = []
    for r in rows:
        if "error" in r:
            modality_counts["error"] += 1
            continue
        modality_counts[_modality(r)] += 1
        sync = r.get("sync_summary") or {}
        sync_rates.append(float(sync.get("sync_rate", 0.0)))

    lines = [
        "# Phase 1.4a Topology C_v3 extended summary (self + YouTube)",
        "",
        "Pipeline: ffmpeg -> per-frame YOLOv8n + BirdNET (target_threshold=None) "
        "-> temporal_sampler (2s windows, sync_summary) -> `qwen2.5:7b` fusion",
        "",
        f"- Total folds executed: {len(rows)}",
        f"- Skipped YouTube entries: {len(skipped)}",
        f"- Total wall time: {total_time:.1f} s",
        "",
        "## Modality used (from LLM response)",
        "",
        "| modality | count |",
        "|---|---:|",
    ]
    for mod, cnt in sorted(modality_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {mod} | {cnt} |")
    lines.append("")

    if sync_rates:
        mean = sum(sync_rates) / len(sync_rates)
        zeros = sum(1 for r in sync_rates if r == 0.0)
        lines.append("## sync_rate distribution")
        lines.append("")
        lines.append(f"- mean: {mean:.3f}")
        lines.append(f"- min:  {min(sync_rates):.3f}")
        lines.append(f"- max:  {max(sync_rates):.3f}")
        lines.append(f"- folds with sync_rate = 0: {zeros}")
        lines.append("")

    # Correlation: sync_rate vs per-fold correctness
    correct_rates: list[float] = []
    wrong_rates: list[float] = []
    for r in rows:
        if "error" in r:
            continue
        ok = r.get("is_correct") or {}
        sync = (r.get("sync_summary") or {}).get("sync_rate", 0.0)
        if ok.get("sparrow") and ok.get("bulbul"):
            correct_rates.append(float(sync))
        else:
            wrong_rates.append(float(sync))
    if correct_rates or wrong_rates:
        def mean_or_dash(xs: list[float]) -> str:
            return f"{sum(xs)/len(xs):.3f}" if xs else "-"
        lines.append("## sync_rate vs correctness")
        lines.append("")
        lines.append("| subset | n | mean sync_rate |")
        lines.append("|---|---:|---:|")
        lines.append(f"| fully correct | {len(correct_rates)} | {mean_or_dash(correct_rates)} |")
        lines.append(f"| at least one class wrong | {len(wrong_rates)} | {mean_or_dash(wrong_rates)} |")
        lines.append("")

    lines.append(render_breakdown(rows))
    lines.append("## Per-fold results")
    lines.append("")
    lines.extend(per_fold_table_header(["modality", "sync_rate", "num_windows"]))
    for r in rows:
        if "error" in r:
            lines.append(per_fold_row(r, ["-", "-", "-"]))
            continue
        sync = (r.get("sync_summary") or {}).get("sync_rate", 0.0)
        nw = (r.get("timeline") or {}).get("num_windows", "-")
        lines.append(per_fold_row(r, [_modality(r), f"{sync:.3f}", str(nw)]))
    lines.append("")

    if skipped:
        lines.append("## Skipped YouTube entries")
        lines.append("")
        lines.append("| video_id | category | source | status | error |")
        lines.append("|---|---|---|---|---|")
        for s in skipped:
            lines.append(
                f"| {s.get('video_id','-')} | {s.get('category','-')} "
                f"| {s.get('source','-')} | {s.get('download_status') or s.get('reason','-')} "
                f"| {(s.get('download_error') or '')[:80]} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()
    llm = LlmClient(timeout=LLM_TIMEOUT_SEC)
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
    videos, skipped = load_extended_videos()
    print(f"Videos: {len(videos)} (skipped={len(skipped)})")

    run_start = time.perf_counter()
    rows = run_loocv_over(TOPOLOGY, make_fold_fn(bn, det, llm), RESULTS_BASE, videos)
    total_time = time.perf_counter() - run_start

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(render_summary(rows, skipped, total_time), encoding="utf-8")
    print(f"Summary: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
