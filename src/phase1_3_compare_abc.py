"""Phase 1.3 — Topology A vs B vs C side-by-side comparison.

Reads per-fold JSON under ``results/phase1_3/topology_{a,b,c}/``, builds
a unified per-video comparison table, and records pairwise agreement /
correctness-pattern counts for Mirror-Effect inspection. No
interpretation; the output is bookkeeping for Phase 1.3+.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE = REPO_ROOT / "results" / "phase1_3"
OUT_PATH = BASE / "abc_comparison.md"


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
    p = row.get("final_prediction") or {}
    return f"{p.get('sparrow','?')}/{p.get('bulbul','?')}"


def both_correct(row: dict[str, Any] | None) -> bool:
    if row is None or "error" in row:
        return False
    ok = row.get("is_correct") or {}
    return bool(ok.get("sparrow")) and bool(ok.get("bulbul"))


def class_correct(row: dict[str, Any] | None, cls: str) -> bool | None:
    if row is None or "error" in row:
        return None
    return bool((row.get("is_correct") or {}).get(cls))


def metrics_for(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute F1 / accuracy / fallback stats from raw rows."""
    matrix = {
        "sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }
    fallback = 0
    elapsed = 0.0
    counted = 0
    for r in rows:
        if "error" in r:
            continue
        if r.get("fallback_triggered"):
            fallback += 1
        pred = r.get("final_prediction") or {}
        gt = r.get("ground_truth") or {}
        for cls in ("sparrow", "bulbul"):
            if pred.get(cls) not in (0, 1) or gt.get(cls) not in (0, 1):
                continue
            p = pred[cls]; g = gt[cls]
            if p == 1 and g == 1:
                matrix[cls]["tp"] += 1
            elif p == 1 and g == 0:
                matrix[cls]["fp"] += 1
            elif p == 0 and g == 1:
                matrix[cls]["fn"] += 1
            else:
                matrix[cls]["tn"] += 1
        t = (r.get("elapsed_sec") or {}).get("total")
        if t is not None:
            elapsed += float(t)
            counted += 1

    def f1_of(m: dict[str, int]) -> float:
        tp, fp, fn = m["tp"], m["fp"], m["fn"]
        if tp == 0:
            return 0.0
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    f1 = {k: f1_of(matrix[k]) for k in matrix}
    return {
        "sparrow_f1": f1["sparrow"],
        "bulbul_f1":  f1["bulbul"],
        "macro_f1":   (f1["sparrow"] + f1["bulbul"]) / 2.0,
        "fallback":   fallback,
        "mean_total_sec": elapsed / counted if counted else 0.0,
        "folds":      len(rows),
    }


def pair_agreement(
    rows_x: dict[str, dict[str, Any]],
    rows_y: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    s_match = b_match = both_match = comparable = 0
    for vid in set(rows_x) & set(rows_y):
        rx, ry = rows_x[vid], rows_y[vid]
        if "error" in rx or "error" in ry:
            continue
        px = rx.get("final_prediction") or {}
        py = ry.get("final_prediction") or {}
        if px.get("sparrow") not in (0, 1) or py.get("sparrow") not in (0, 1):
            continue
        if px.get("bulbul") not in (0, 1) or py.get("bulbul") not in (0, 1):
            continue
        comparable += 1
        sm = px["sparrow"] == py["sparrow"]
        bm = px["bulbul"] == py["bulbul"]
        s_match += int(sm)
        b_match += int(bm)
        both_match += int(sm and bm)
    return {
        "comparable": comparable,
        "sparrow_agree": s_match,
        "bulbul_agree": b_match,
        "both_agree": both_match,
    }


def main() -> int:
    ensure_utf8_streams()
    a = load_folds(BASE / "topology_a")
    b = load_folds(BASE / "topology_b")
    c = load_folds(BASE / "topology_c")
    ids = sorted(set(a) | set(b) | set(c))

    ma = metrics_for(list(a.values()))
    mb = metrics_for(list(b.values()))
    mc = metrics_for(list(c.values()))

    ag_ab = pair_agreement(a, b)
    ag_ac = pair_agreement(a, c)
    ag_bc = pair_agreement(b, c)

    lines = [
        "# Phase 1.3 Topology A vs B vs C",
        "",
        "- A = Audio-Only (BirdNET -> LLM)",
        "- B = Visual-Only (YOLOv8n -> LLM)",
        "- C = Parallel Fusion (BirdNET + YOLOv8n -> LLM, no BirdNET target threshold)",
        "",
        f"- Folds with A result: {len(a)} | B: {len(b)} | C: {len(c)}",
        "",
        "## Overall metrics",
        "",
        "| topology | macro F1 | sparrow F1 | bulbul F1 | fallback | mean total (s) |",
        "|---|---:|---:|---:|---:|---:|",
        f"| A | {ma['macro_f1']:.3f} | {ma['sparrow_f1']:.3f} | {ma['bulbul_f1']:.3f} "
        f"| {ma['fallback']} / {ma['folds']} | {ma['mean_total_sec']:.2f} |",
        f"| B | {mb['macro_f1']:.3f} | {mb['sparrow_f1']:.3f} | {mb['bulbul_f1']:.3f} "
        f"| {mb['fallback']} / {mb['folds']} | {mb['mean_total_sec']:.2f} |",
        f"| C | {mc['macro_f1']:.3f} | {mc['sparrow_f1']:.3f} | {mc['bulbul_f1']:.3f} "
        f"| {mc['fallback']} / {mc['folds']} | {mc['mean_total_sec']:.2f} |",
        "",
        "## Per-video comparison",
        "",
        "| fold | video_id | GT S/B | A pred | B pred | C pred | A full-ok | B full-ok | C full-ok |",
        "|---:|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|",
    ]

    for vid in ids:
        ar = a.get(vid); br = b.get(vid); cr = c.get(vid)
        gt = ((ar or br or cr) or {}).get("ground_truth", {"sparrow": "-", "bulbul": "-"})
        fold = ((ar or br or cr) or {}).get("fold", "-")
        fold_str = f"{fold:02d}" if isinstance(fold, int) else str(fold)
        lines.append(
            f"| {fold_str} | {vid} "
            f"| {gt.get('sparrow','-')}/{gt.get('bulbul','-')} "
            f"| {pred_cell(ar)} | {pred_cell(br)} | {pred_cell(cr)} "
            f"| {'OK' if both_correct(ar) else 'X'} "
            f"| {'OK' if both_correct(br) else 'X'} "
            f"| {'OK' if both_correct(cr) else 'X'} |"
        )
    lines.append("")

    lines.append("## Pairwise agreement (both sides comparable)")
    lines.append("")
    lines.append("| pair | comparable | sparrow agree | bulbul agree | full match |")
    lines.append("|---|---:|---:|---:|---:|")
    for label, ag in (("A vs B", ag_ab), ("A vs C", ag_ac), ("B vs C", ag_bc)):
        if ag["comparable"] == 0:
            lines.append(f"| {label} | 0 | - | - | - |")
        else:
            lines.append(
                f"| {label} | {ag['comparable']} "
                f"| {ag['sparrow_agree']}/{ag['comparable']} "
                f"| {ag['bulbul_agree']}/{ag['comparable']} "
                f"| {ag['both_agree']}/{ag['comparable']} |"
            )
    lines.append("")

    # Correctness-pattern breakdown B vs C (the most informative comparison).
    bc_both_ok = bc_only_b = bc_only_c = bc_both_wrong = 0
    for vid in set(b) & set(c):
        br, cr = b[vid], c[vid]
        if "error" in br or "error" in cr:
            continue
        b_ok = both_correct(br)
        c_ok = both_correct(cr)
        if b_ok and c_ok:
            bc_both_ok += 1
        elif b_ok:
            bc_only_b += 1
        elif c_ok:
            bc_only_c += 1
        else:
            bc_both_wrong += 1

    lines.append("## Correctness split (B vs C)")
    lines.append("")
    lines.append(f"- Both correct: {bc_both_ok}")
    lines.append(f"- Only B correct: {bc_only_b}")
    lines.append(f"- Only C correct: {bc_only_c}")
    lines.append(f"- Both wrong: {bc_both_wrong}")
    lines.append("")

    lines.append("## Mirror Effect candidate A (pairwise agreement interpretation)")
    lines.append("")
    lines.append(
        "Pairwise agreement is the direct observable for Phase 1.3+ Mirror-Effect "
        "analysis. A pipeline that 'mirrors' another will show high agreement even "
        "when accuracy differs; a genuinely independent pipeline will show agreement "
        "bounded by the bird-distribution prior."
    )
    lines.append("")
    lines.append(
        "Phase 1.2 / 1.3 runs so far have not been large enough to declare Mirror "
        "Effect presence or absence — these counts are recorded as the baseline."
    )
    lines.append("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
