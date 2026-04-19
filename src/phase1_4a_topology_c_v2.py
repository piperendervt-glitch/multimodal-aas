"""Phase 1.4a Topology C_v2 — Parallel Fusion with frame pre-filter.

Identical to Phase 1.3 Topology C (same BirdNET config with
``target_min_conf=None``, same LLM prompt) except the YOLO aggregate fed
to the LLM is computed over bird-detected frames only. The hypothesis
is that removing no-bird frames from the statistics improves LLM
decision quality (objective B: accuracy).

Fallback policy:
    * selected_frames == 0 AND audio target-species not found -> fallback
    * Otherwise LLM is called exactly as in Phase 1.3 Topology C.

The per-fold JSON preserves both the selected aggregate and the full
per-frame YOLO trace so Phase 1.4a+ can revisit decisions.
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
from phase1_3_topology_c import SYSTEM_PROMPT, format_audio_for_llm
from phase1_4a_common.frame_extractor import aggregate_selected, extract_bird_frames

TOPOLOGY = "C_v2"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v2"
SUMMARY_PATH = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v2_summary.md"


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
        fe_out = extract_bird_frames(det, frame_paths, fps_sampling=DEFAULT_FPS)
        t_yolo = time.perf_counter() - t0

        yolo_selected = aggregate_selected(fe_out)

        audio_input = format_audio_for_llm(bn_out["all_detections"])
        visual_input = {
            "num_frames_analyzed": yolo_selected["num_frames_analyzed"],
            "frames_with_bird": yolo_selected["frames_with_bird"],
            "max_bbox_size_relative": yolo_selected["max_bbox_size_relative"],
            "avg_bbox_size_relative": yolo_selected["avg_bbox_size_relative"],
            "std_bbox_size": yolo_selected["std_bbox_size"],
            "avg_detection_confidence": yolo_selected["avg_detection_confidence"],
            "detection_counts_per_frame": yolo_selected["detection_counts_per_frame"],
        }
        llm_input = {"visual": visual_input, "audio": audio_input}

        t_llm = 0.0
        fallback = False
        llm_output: dict[str, Any] | None = None

        both_silent = (
            fe_out["frames_with_bird"] == 0 and not audio_input["target_species_found"]
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
                "selected_frames": fe_out["selected_frames"],
                "all_frames_yolo_output": fe_out["all_frames_yolo_output"],
            },
            "yolo_output_selected_only": yolo_selected,
            "birdnet_output": bn_out,
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
    selection_rates: list[float] = []
    for r in rows:
        if "error" in r:
            modality_counts["error"] += 1
            continue
        modality_counts[_modality(r)] += 1
        fe = r.get("frame_extractor") or {}
        if fe:
            selection_rates.append(float(fe.get("frame_selection_rate", 0.0)))

    lines = [
        "# Phase 1.4a Topology C_v2 extended summary (self + YouTube)",
        "",
        "Pipeline: ffmpeg (audio 16 kHz + frames @ 1 fps CFR) -> "
        "frame_extractor (YOLOv8n bird pre-filter) -> BirdNET (target_threshold=None) "
        "-> `qwen2.5:7b` fusion",
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

    if selection_rates:
        mean = sum(selection_rates) / len(selection_rates)
        min_r = min(selection_rates)
        max_r = max(selection_rates)
        zeros = sum(1 for r in selection_rates if r == 0.0)
        lines.append("## Frame selection rate (bird-detected frames / total sampled)")
        lines.append("")
        lines.append(f"- mean: {mean:.3f}")
        lines.append(f"- min:  {min_r:.3f}")
        lines.append(f"- max:  {max_r:.3f}")
        lines.append(f"- folds with 0% selection (all no-bird): {zeros}")
        lines.append("")

    lines.append(render_breakdown(rows))
    lines.append("## Per-fold results")
    lines.append("")
    lines.extend(per_fold_table_header(["modality", "sel_rate"]))
    for r in rows:
        if "error" in r:
            lines.append(per_fold_row(r, ["-", "-"]))
            continue
        sel = (r.get("frame_extractor") or {}).get("frame_selection_rate", 0.0)
        lines.append(per_fold_row(r, [_modality(r), f"{sel:.3f}"]))
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
