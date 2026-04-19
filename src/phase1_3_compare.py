"""Phase 1.3 — Topology A vs B side-by-side comparison.

Reads every fold JSON under results/phase1_3/topology_a/ and
results/phase1_3/topology_b/, matches by ``video_id``, and writes
results/phase1_3/a_vs_b_comparison.md. Records simple agreement counts
for later Mirror-Effect analysis; no interpretation here.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
A_DIR = REPO_ROOT / "results" / "phase1_3" / "topology_a"
B_DIR = REPO_ROOT / "results" / "phase1_3" / "topology_b"
OUT_PATH = REPO_ROOT / "results" / "phase1_3" / "a_vs_b_comparison.md"


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def load_folds(base: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not base.is_dir():
        return out
    for fold_dir in sorted(base.glob("fold_*")):
        for p in sorted(fold_dir.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            out[data["video_id"]] = data
    return out


def pred_cell(row: dict[str, Any] | None) -> str:
    if row is None:
        return "(no row)"
    if "error" in row:
        return "ERR"
    p = row.get("final_prediction")
    if p is None:
        return "NONE"
    return f"{p['sparrow']}/{p['bulbul']}"


def main() -> int:
    ensure_utf8_streams()
    a = load_folds(A_DIR)
    b = load_folds(B_DIR)
    ids = sorted(set(a) | set(b))

    lines = [
        "# Phase 1.3 Topology A vs B",
        "",
        "- Topology A = Audio-Only (BirdNET -> LLM)",
        "- Topology B = Visual-Only (YOLOv8n -> LLM)",
        "",
        f"- Folds with A result: {len(a)}",
        f"- Folds with B result: {len(b)}",
        f"- Common folds: {len(set(a) & set(b))}",
        "",
        "## Per-video comparison",
        "",
        "| fold | video_id | GT (S/B) | A pred | B pred | S match A=B | B match A=B | A fb | B fb | A t | B t |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    agree_both = 0
    agree_sparrow = 0
    agree_bulbul = 0
    comparable = 0
    both_correct = 0
    only_a_correct = 0
    only_b_correct = 0
    both_wrong = 0
    gt_pattern: Counter[str] = Counter()

    for vid in ids:
        ar = a.get(vid)
        br = b.get(vid)
        gt = (ar or br).get("ground_truth", {"sparrow": "-", "bulbul": "-"})
        fold = (ar or br).get("fold", "-")

        a_cell = pred_cell(ar)
        b_cell = pred_cell(br)
        s_match = b_match = "-"
        a_fb = "Y" if (ar and ar.get("fallback_triggered")) else "-"
        b_fb = "Y" if (br and br.get("fallback_triggered")) else "-"
        a_t = ar.get("elapsed_sec", {}).get("total", 0.0) if ar and "error" not in ar else 0.0
        b_t = br.get("elapsed_sec", {}).get("total", 0.0) if br and "error" not in br else 0.0

        if ar and br and "error" not in ar and "error" not in br:
            ap = ar["final_prediction"]
            bp = br["final_prediction"]
            comparable += 1
            s_match = "OK" if ap["sparrow"] == bp["sparrow"] else "X"
            b_match = "OK" if ap["bulbul"] == bp["bulbul"] else "X"
            if s_match == "OK":
                agree_sparrow += 1
            if b_match == "OK":
                agree_bulbul += 1
            if s_match == "OK" and b_match == "OK":
                agree_both += 1

            a_ok = (ap["sparrow"] == gt["sparrow"]) and (ap["bulbul"] == gt["bulbul"])
            b_ok = (bp["sparrow"] == gt["sparrow"]) and (bp["bulbul"] == gt["bulbul"])
            if a_ok and b_ok:
                both_correct += 1
            elif a_ok:
                only_a_correct += 1
            elif b_ok:
                only_b_correct += 1
            else:
                both_wrong += 1
            gt_pattern[f"{gt['sparrow']}/{gt['bulbul']}"] += 1

        fold_str = f"{fold:02d}" if isinstance(fold, int) else str(fold)
        lines.append(
            f"| {fold_str} | {vid} | {gt.get('sparrow','-')}/{gt.get('bulbul','-')} "
            f"| {a_cell} | {b_cell} | {s_match} | {b_match} | {a_fb} | {b_fb} "
            f"| {a_t:.2f}s | {b_t:.2f}s |"
        )

    lines.append("")
    lines.append("## Agreement (folds comparable on both sides)")
    lines.append("")
    if comparable == 0:
        lines.append("_No folds had comparable predictions on both sides._")
    else:
        lines.append(f"- Comparable folds: {comparable}")
        lines.append(f"- Agree on sparrow:  {agree_sparrow} / {comparable}")
        lines.append(f"- Agree on bulbul:   {agree_bulbul} / {comparable}")
        lines.append(f"- Agree on both labels (full match): {agree_both} / {comparable}")
    lines.append("")

    lines.append("## Correctness split (diagnostic for Mirror Effect candidate A)")
    lines.append("")
    if comparable == 0:
        lines.append("_No comparable folds._")
    else:
        lines.append(f"- Both correct:      {both_correct} / {comparable}")
        lines.append(f"- Only A correct:    {only_a_correct} / {comparable}")
        lines.append(f"- Only B correct:    {only_b_correct} / {comparable}")
        lines.append(f"- Both wrong:        {both_wrong} / {comparable}")
        lines.append("")
        lines.append("Ground-truth pattern distribution (comparable folds):")
        for pattern, cnt in gt_pattern.most_common():
            lines.append(f"- `{pattern}`: {cnt}")
    lines.append("")
    lines.append(
        "Phase 1.2 only ran end-to-end smoke tests; these counts are retained for "
        "Phase 1.3+ analysis and should not be interpreted as a Mirror Effect result."
    )
    lines.append("")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
