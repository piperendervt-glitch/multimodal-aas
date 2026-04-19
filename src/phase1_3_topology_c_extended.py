"""Phase 1.3 — Topology C extended run (self + YouTube, 43 folds)."""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

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
from phase1_3_common.yolo_detector import YoloDetector
from phase1_3_topology_c import SYSTEM_PROMPT, make_fold_fn  # noqa: F401

TOPOLOGY = "C"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_c"
SUMMARY_PATH = (
    REPO_ROOT / "results" / "phase1_3_extended" / "topology_c_extended_summary.md"
)


def _modality(row: dict) -> str:
    return ((row.get("llm_output") or {}).get("parsed") or {}).get("modality_used", "-")


def render_summary(rows, skipped, total_time: float) -> str:
    modality_counts: Counter[str] = Counter()
    for r in rows:
        if "error" in r:
            modality_counts["error"] += 1
            continue
        modality_counts[_modality(r)] += 1

    lines = [
        "# Phase 1.3 Topology C extended summary (self + YouTube)",
        "",
        "Pipeline: ffmpeg (audio 16 kHz + frames @ 1 fps CFR) -> "
        "BirdNET + YOLOv8n -> `qwen2.5:7b` fusion "
        "(BirdNET target_threshold=None, all detections forwarded to LLM)",
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

    lines.append(render_breakdown(rows))
    lines.append("## Per-fold results")
    lines.append("")
    lines.extend(per_fold_table_header(["modality"]))
    for r in rows:
        if "error" in r:
            lines.append(per_fold_row(r, ["-"]))
            continue
        lines.append(per_fold_row(r, [_modality(r)]))
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
