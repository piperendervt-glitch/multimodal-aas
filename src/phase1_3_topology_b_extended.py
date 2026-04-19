"""Phase 1.3 — Topology B extended run (self + YouTube, 43 folds)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_3_common.extended_sources import load_extended_videos
from phase1_3_common.extended_summary import (
    per_fold_row,
    per_fold_table_header,
    render_breakdown,
)
from phase1_3_common.llm_client import LlmClient, ModelMissing, OllamaUnavailable
from phase1_3_common.loocv_runner import ensure_utf8_streams, run_loocv_over
from phase1_3_common.yolo_detector import YoloDetector
from phase1_3_topology_b import SYSTEM_PROMPT, make_fold_fn  # noqa: F401

TOPOLOGY = "B"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_b"
SUMMARY_PATH = (
    REPO_ROOT / "results" / "phase1_3_extended" / "topology_b_extended_summary.md"
)


def render_summary(rows, skipped, total_time: float) -> str:
    lines = [
        "# Phase 1.3 Topology B extended summary (self + YouTube)",
        "",
        "Pipeline: ffmpeg @ 1 fps (CFR) -> YOLOv8n (bird class) -> `qwen2.5:7b`",
        "",
        f"- Total folds executed: {len(rows)}",
        f"- Skipped YouTube entries: {len(skipped)}",
        f"- Total wall time: {total_time:.1f} s",
        "",
        render_breakdown(rows),
        "## Per-fold results",
        "",
    ]
    lines.extend(per_fold_table_header(["max_rel", "with_bird"]))
    for r in rows:
        if "error" in r:
            lines.append(per_fold_row(r, ["-", "-"]))
            continue
        y = r.get("yolo_output", {}) or {}
        lines.append(per_fold_row(r, [
            f"{y.get('max_bbox_size_relative', 0.0):.3f}",
            str(y.get('frames_with_bird', '-')),
        ]))
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

    det = YoloDetector()
    videos, skipped = load_extended_videos()
    print(f"Videos: {len(videos)} (skipped={len(skipped)})")

    run_start = time.perf_counter()
    rows = run_loocv_over(TOPOLOGY, make_fold_fn(det, llm), RESULTS_BASE, videos)
    total_time = time.perf_counter() - run_start

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(render_summary(rows, skipped, total_time), encoding="utf-8")
    print(f"Summary: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
