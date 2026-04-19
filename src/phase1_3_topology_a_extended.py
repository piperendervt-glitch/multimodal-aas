"""Phase 1.3 — Topology A extended run (self + YouTube, 43 folds)."""

from __future__ import annotations

import sys
import time
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
from phase1_3_topology_a import SYSTEM_PROMPT, make_fold_fn  # noqa: F401 — reused

TOPOLOGY = "A"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_a"
SUMMARY_PATH = (
    REPO_ROOT / "results" / "phase1_3_extended" / "topology_a_extended_summary.md"
)


def render_summary(rows, skipped, total_time: float) -> str:
    lines = [
        "# Phase 1.3 Topology A extended summary (self + YouTube)",
        "",
        "Pipeline: ffmpeg (16 kHz mono) -> BirdNET (birdnetlib) -> `qwen2.5:7b`",
        "",
        f"- Total folds executed: {len(rows)}",
        f"- Skipped YouTube entries (download failed / missing): {len(skipped)}",
        f"- Total wall time: {total_time:.1f} s",
        "",
        render_breakdown(rows),
        "## Per-fold results",
        "",
    ]
    lines.extend(per_fold_table_header())
    for r in rows:
        lines.append(per_fold_row(r))
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
    videos, skipped = load_extended_videos()
    print(f"Videos: {len(videos)} (self={sum(1 for v in videos if v['source']=='self')}, "
          f"youtube={sum(1 for v in videos if v['source']!='self')}); skipped={len(skipped)}")

    run_start = time.perf_counter()
    rows = run_loocv_over(TOPOLOGY, make_fold_fn(bn, llm), RESULTS_BASE, videos)
    total_time = time.perf_counter() - run_start

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(render_summary(rows, skipped, total_time), encoding="utf-8")
    print(f"Summary: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
