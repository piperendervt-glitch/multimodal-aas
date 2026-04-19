"""Phase 1.2 cross-modal comparison.

Reads every JSON under results/phase1_2/visual/ and results/phase1_2/audio/,
matches by video_id, and writes results/phase1_2/comparison_summary.md.

This is bookkeeping for Phase 1.3 (Mirror Effect analysis); Phase 1.2
itself only needs to confirm that both pipelines ran end-to-end. The
agreement statistics are logged but not interpreted here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
VISUAL_DIR = REPO_ROOT / "results" / "phase1_2" / "visual"
AUDIO_DIR = REPO_ROOT / "results" / "phase1_2" / "audio"
OUT_PATH = REPO_ROOT / "results" / "phase1_2" / "comparison_summary.md"


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def load_results(d: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        out[data["video_id"]] = data
    return out


def main() -> int:
    ensure_utf8_streams()
    visual = load_results(VISUAL_DIR)
    audio = load_results(AUDIO_DIR)
    all_ids = sorted(set(visual) | set(audio))

    lines = [
        "# Phase 1.2 Cross-Modal Comparison",
        "",
        "Side-by-side record of the visual (YOLOv8n) and audio (BirdNET) pipelines.",
        "Phase 1.2 only confirms both pipelines run; Mirror Effect analysis is deferred to Phase 1.3.",
        "",
        f"- Visual JSONs: {len(visual)}",
        f"- Audio JSONs:  {len(audio)}",
        f"- Videos in both: {len(set(visual) & set(audio))}",
        "",
        "## Per-video comparison",
        "",
        "| video_id | GT (S/B) | V pred (S/B) | A pred (S/B) | S match V=A | B match V=A | V elapsed | A elapsed |",
        "|---|---|---|---|---|---|---|---|",
    ]

    agree_both = 0
    agree_sparrow = 0
    agree_bulbul = 0
    both_have_preds = 0
    v_elapsed_sum = 0.0
    a_elapsed_sum = 0.0

    for vid in all_ids:
        v = visual.get(vid)
        a = audio.get(vid)
        gt = (v or a).get("ground_truth", {"sparrow": "-", "bulbul": "-"})

        def pred_cell(row: dict[str, Any] | None) -> str:
            if row is None:
                return "(no row)"
            r = row.get("llm_response")
            if r is None:
                return "PARSE_FAIL"
            p = r["predictions"]
            return f"{p['sparrow']}/{p['bulbul']}"

        v_cell = pred_cell(v)
        a_cell = pred_cell(a)

        s_match = b_match = "-"
        if (v and v.get("llm_response")) and (a and a.get("llm_response")):
            both_have_preds += 1
            vp = v["llm_response"]["predictions"]
            ap = a["llm_response"]["predictions"]
            s_match = "OK" if vp["sparrow"] == ap["sparrow"] else "X"
            b_match = "OK" if vp["bulbul"] == ap["bulbul"] else "X"
            if s_match == "OK":
                agree_sparrow += 1
            if b_match == "OK":
                agree_bulbul += 1
            if s_match == "OK" and b_match == "OK":
                agree_both += 1

        v_t = v["elapsed_sec"] if v else 0.0
        a_t = a["elapsed_sec"] if a else 0.0
        v_elapsed_sum += v_t
        a_elapsed_sum += a_t

        gt_cell = f"{gt.get('sparrow','-')}/{gt.get('bulbul','-')}"
        lines.append(
            f"| {vid} | {gt_cell} | {v_cell} | {a_cell} | {s_match} | {b_match} "
            f"| {v_t:.2f}s | {a_t:.2f}s |"
        )

    lines.append("")
    lines.append("## Agreement (both modalities parsed a response)")
    lines.append("")
    if both_have_preds == 0:
        lines.append("_No videos had a parsed response on both sides._")
    else:
        lines.append(f"- Videos with predictions on both sides: {both_have_preds}")
        lines.append(f"- Agree on sparrow: {agree_sparrow} / {both_have_preds}")
        lines.append(f"- Agree on bulbul:  {agree_bulbul} / {both_have_preds}")
        lines.append(f"- Agree on both labels: {agree_both} / {both_have_preds}")
    lines.append("")

    lines.append("## Processing time totals")
    lines.append("")
    lines.append(f"- Visual total elapsed: {v_elapsed_sum:.1f} s over {len(visual)} videos")
    lines.append(f"- Audio total elapsed:  {a_elapsed_sum:.1f} s over {len(audio)} videos")
    lines.append("")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
