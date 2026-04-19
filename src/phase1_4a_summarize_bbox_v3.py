"""Phase 1.4a bbox prompt v3 summary and Go judgment.

Compares:
    * Phase 1.3 extended Topology B  (baseline)
    * Phase 1.4a Topology B_v3       (bbox prompt v3)
    * Phase 1.3 extended Topology C  (baseline)
    * Phase 1.4a Topology C_v4       (bbox prompt v3, same fusion topology)

Go criteria (either one is sufficient):
    * B_v3 YouTube macro F1 >= 0.642 (Phase 1.3 B YouTube 0.542 + 0.10)
    * C_v4 YouTube macro F1 >= 0.894 (Phase 1.3 C YouTube 0.874 + 0.02)
    * C_v4 full  macro F1 >= 0.860  (Phase 1.3 C full 0.840 + 0.02)
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
PH13_B_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_b"
PH13_C_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_c"
B_V3_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_b_v3"
C_V4_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v4"
OUT_PATH = REPO_ROOT / "results" / "phase1_4a" / "bbox_prompt_v3_summary.md"

PH13_B_YT_F1 = 0.542
PH13_C_YT_F1 = 0.874
PH13_C_FULL_F1 = 0.840
GO_B_YT_THRESHOLD = PH13_B_YT_F1 + 0.10
GO_C_YT_THRESHOLD = PH13_C_YT_F1 + 0.02
GO_C_FULL_THRESHOLD = PH13_C_FULL_F1 + 0.02


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


def metrics_for(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = {
        "sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }
    scored = fallback = err = 0
    for r in rows:
        if "error" in r:
            err += 1
            continue
        if r.get("fallback_triggered"):
            fallback += 1
        pred = r.get("final_prediction") or {}
        gt = r.get("ground_truth") or {}
        if pred.get("sparrow") not in (0, 1) or pred.get("bulbul") not in (0, 1):
            continue
        scored += 1
        for cls in ("sparrow", "bulbul"):
            p, g = pred[cls], gt[cls]
            if p == 1 and g == 1:
                matrix[cls]["tp"] += 1
            elif p == 1 and g == 0:
                matrix[cls]["fp"] += 1
            elif p == 0 and g == 1:
                matrix[cls]["fn"] += 1
            else:
                matrix[cls]["tn"] += 1

    def f1_of(m: dict[str, int]) -> float:
        tp, fp, fn = m["tp"], m["fp"], m["fn"]
        if tp == 0:
            return 0.0
        pr = tp / (tp + fp) if (tp + fp) else 0.0
        rc = tp / (tp + fn) if (tp + fn) else 0.0
        if pr + rc == 0:
            return 0.0
        return 2 * pr * rc / (pr + rc)

    f1 = {k: f1_of(matrix[k]) for k in matrix}
    return {
        "n": len(rows),
        "scored": scored,
        "fallback": fallback,
        "errors": err,
        "sparrow_f1": f1["sparrow"],
        "bulbul_f1": f1["bulbul"],
        "macro_f1": (f1["sparrow"] + f1["bulbul"]) / 2.0,
    }


def filter_rows(rows: list[dict[str, Any]], pred: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
    return [r for r in rows if pred(r)]


def pred_cell(row: dict[str, Any] | None) -> str:
    if row is None:
        return "-"
    if "error" in row:
        return "ERR"
    p = row.get("final_prediction") or {}
    return f"{p.get('sparrow','?')}/{p.get('bulbul','?')}"


def full_ok(row: dict[str, Any] | None) -> bool | None:
    if row is None or "error" in row:
        return None
    ok = row.get("is_correct") or {}
    return bool(ok.get("sparrow") and ok.get("bulbul"))


def dominant_breakdown(rows: list[dict[str, Any]]) -> dict[str, Counter[str]]:
    buckets: dict[str, Counter[str]] = {
        "sparrow": Counter(), "bulbul": Counter(), "mixed": Counter(), "both": Counter(),
    }
    for r in rows:
        if "error" in r:
            continue
        cat = r.get("category", "other")
        if cat not in buckets:
            continue
        bd = (r.get("bbox_distribution") or {}).get("bbox_size_distribution") or {}
        dom = bd.get("dominant_range", "-")
        buckets[cat][dom] += 1
    return buckets


def variation_breakdown(rows: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for r in rows:
        if "error" in r:
            continue
        v = (r.get("bbox_distribution") or {}).get("size_variation_type", "-")
        counts[v] += 1
    return counts


def render_scope(b: dict[str, Any], b_v3: dict[str, Any], c: dict[str, Any], c_v4: dict[str, Any], title: str) -> list[str]:
    return [
        f"### {title}",
        "",
        "| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| macro F1 | {b['macro_f1']:.3f} | {b_v3['macro_f1']:.3f} | {b_v3['macro_f1']-b['macro_f1']:+.3f} "
        f"| {c['macro_f1']:.3f} | {c_v4['macro_f1']:.3f} | {c_v4['macro_f1']-c['macro_f1']:+.3f} |",
        f"| sparrow F1 | {b['sparrow_f1']:.3f} | {b_v3['sparrow_f1']:.3f} | {b_v3['sparrow_f1']-b['sparrow_f1']:+.3f} "
        f"| {c['sparrow_f1']:.3f} | {c_v4['sparrow_f1']:.3f} | {c_v4['sparrow_f1']-c['sparrow_f1']:+.3f} |",
        f"| bulbul F1 | {b['bulbul_f1']:.3f} | {b_v3['bulbul_f1']:.3f} | {b_v3['bulbul_f1']-b['bulbul_f1']:+.3f} "
        f"| {c['bulbul_f1']:.3f} | {c_v4['bulbul_f1']:.3f} | {c_v4['bulbul_f1']-c['bulbul_f1']:+.3f} |",
        f"| fallback | {b['fallback']} | {b_v3['fallback']} | {b_v3['fallback']-b['fallback']:+d} "
        f"| {c['fallback']} | {c_v4['fallback']} | {c_v4['fallback']-c['fallback']:+d} |",
        f"| scored | {b['scored']}/{b['n']} | {b_v3['scored']}/{b_v3['n']} | "
        f"| {c['scored']}/{c['n']} | {c_v4['scored']}/{c_v4['n']} | |",
        "",
    ]


def main() -> int:
    ensure_utf8_streams()
    b = load_folds(PH13_B_BASE)
    b_v3 = load_folds(B_V3_BASE)
    c = load_folds(PH13_C_BASE)
    c_v4 = load_folds(C_V4_BASE)

    b_list = list(b.values()); b_v3_list = list(b_v3.values())
    c_list = list(c.values()); c_v4_list = list(c_v4.values())

    scopes: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("Full (self + YouTube)", lambda r: True),
        ("Self-recorded only", lambda r: r.get("source") == "self"),
        ("YouTube only", lambda r: (r.get("source") or "").startswith("youtube")),
        ("YouTube-grok", lambda r: r.get("source") == "youtube-grok"),
        ("YouTube-claude", lambda r: r.get("source") == "youtube-claude"),
    ]
    categories = sorted({r.get("category") for r in (c_v4_list + b_v3_list) if r.get("category")})

    lines: list[str] = [
        "# Phase 1.4a bbox prompt v3 summary (B_v3, C_v4)",
        "",
        "Replaces Phase 1.3 Topology B/C absolute bbox thresholds (sparrow < 0.08, ",
        "bulbul >= 0.13) with relative distribution features (dominant_range, ",
        "size_variation_type).",
        "",
        "- B_v3: Visual-Only with prompt v3.",
        "- C_v4: Parallel Fusion with prompt v3 (no temporal_sync, no frame pre-filter).",
        "",
        "## Metric deltas (B / B_v3, C / C_v4)",
        "",
    ]
    for title, pred in scopes:
        lines.extend(render_scope(
            metrics_for(filter_rows(b_list, pred)),
            metrics_for(filter_rows(b_v3_list, pred)),
            metrics_for(filter_rows(c_list, pred)),
            metrics_for(filter_rows(c_v4_list, pred)),
            title,
        ))
    for cat in categories:
        def pred(r: dict[str, Any], cat_: str = cat) -> bool:
            return r.get("category") == cat_
        lines.extend(render_scope(
            metrics_for(filter_rows(b_list, pred)),
            metrics_for(filter_rows(b_v3_list, pred)),
            metrics_for(filter_rows(c_list, pred)),
            metrics_for(filter_rows(c_v4_list, pred)),
            f"Category = {cat}",
        ))

    # dominant_range distribution by GT category (C_v4 side)
    lines.append("## dominant_range distribution by ground-truth category (C_v4)")
    lines.append("")
    buckets = dominant_breakdown(c_v4_list)
    lines.append("| category | small | medium | large | none |")
    lines.append("|---|---:|---:|---:|---:|")
    for cat in ("sparrow", "bulbul", "mixed", "both"):
        c_counts = buckets[cat]
        if sum(c_counts.values()) == 0:
            continue
        lines.append(
            f"| {cat} | {c_counts.get('small', 0)} | {c_counts.get('medium', 0)} "
            f"| {c_counts.get('large', 0)} | {c_counts.get('none', 0)} |"
        )
    lines.append("")

    var_counts = variation_breakdown(c_v4_list)
    lines.append("## size_variation_type distribution (C_v4)")
    lines.append("")
    lines.append("| variation_type | count |")
    lines.append("|---|---:|")
    for key in ("uniform", "mixed", "none"):
        lines.append(f"| {key} | {var_counts.get(key, 0)} |")
    lines.append("")

    # Per-fold flip tables vs Phase 1.3 B and C.
    ids = sorted(set(b) | set(b_v3) | set(c) | set(c_v4),
                 key=lambda v: (c_v4.get(v) or c.get(v) or b_v3.get(v) or b.get(v) or {}).get("fold", 999))

    lines.append("## Per-fold side-by-side")
    lines.append("")
    lines.append("| fold | video_id | source | category | GT S/B | B | B_v3 | C | C_v4 | dom | var |")
    lines.append("|---:|---|---|---|:-:|:-:|:-:|:-:|:-:|---|---|")
    for vid in ids:
        rB = b.get(vid); rB3 = b_v3.get(vid); rC = c.get(vid); rC4 = c_v4.get(vid)
        base = rC4 or rC or rB3 or rB or {}
        fold = base.get("fold", "-")
        fold_str = f"{fold:02d}" if isinstance(fold, int) else str(fold)
        gt = base.get("ground_truth", {"sparrow": "-", "bulbul": "-"})
        bd = (rC4 or rB3 or {}).get("bbox_distribution") or {}
        dom = bd.get("bbox_size_distribution", {}).get("dominant_range", "-")
        var = bd.get("size_variation_type", "-")
        lines.append(
            f"| {fold_str} | {vid} | {base.get('source','-')} | {base.get('category','-')} "
            f"| {gt.get('sparrow','-')}/{gt.get('bulbul','-')} "
            f"| {pred_cell(rB)} | {pred_cell(rB3)} | {pred_cell(rC)} | {pred_cell(rC4)} "
            f"| {dom} | {var} |"
        )
    lines.append("")

    # Flip counts: B vs B_v3, C vs C_v4
    def flip_counts(base_rows: dict[str, dict[str, Any]], new_rows: dict[str, dict[str, Any]]) -> tuple[int, int, int, int]:
        both_ok = wins = regress = both_wrong = 0
        for vid in set(base_rows) & set(new_rows):
            ok_b = full_ok(base_rows[vid]); ok_n = full_ok(new_rows[vid])
            if ok_b is None or ok_n is None:
                continue
            if ok_b and ok_n:
                both_ok += 1
            elif ok_n and not ok_b:
                wins += 1
            elif ok_b and not ok_n:
                regress += 1
            else:
                both_wrong += 1
        return both_ok, wins, regress, both_wrong

    b_ok, b_win, b_reg, b_wrong = flip_counts(b, b_v3)
    c_ok, c_win, c_reg, c_wrong = flip_counts(c, c_v4)
    lines.append("## Flip summary")
    lines.append("")
    lines.append("| comparison | both correct | new wins | regressions | both wrong |")
    lines.append("|---|---:|---:|---:|---:|")
    lines.append(f"| B vs B_v3 | {b_ok} | {b_win} | {b_reg} | {b_wrong} |")
    lines.append(f"| C vs C_v4 | {c_ok} | {c_win} | {c_reg} | {c_wrong} |")
    lines.append("")

    # Go judgment
    b_v3_yt = metrics_for(filter_rows(b_v3_list, lambda r: (r.get("source") or "").startswith("youtube")))
    c_v4_yt = metrics_for(filter_rows(c_v4_list, lambda r: (r.get("source") or "").startswith("youtube")))
    c_v4_full = metrics_for(c_v4_list)

    gate_b_yt = b_v3_yt["macro_f1"] >= GO_B_YT_THRESHOLD
    gate_c_yt = c_v4_yt["macro_f1"] >= GO_C_YT_THRESHOLD
    gate_c_full = c_v4_full["macro_f1"] >= GO_C_FULL_THRESHOLD
    any_gate = gate_b_yt or gate_c_yt or gate_c_full
    verdict = "Go" if any_gate else "No-Go"

    lines.append("## Go / No-Go judgment")
    lines.append("")
    lines.append("| gate | threshold | measured | pass? |")
    lines.append("|---|---:|---:|:-:|")
    lines.append(f"| B_v3 YouTube macro F1 | >= {GO_B_YT_THRESHOLD:.3f} | {b_v3_yt['macro_f1']:.3f} "
                 f"| {'OK' if gate_b_yt else 'X'} |")
    lines.append(f"| C_v4 YouTube macro F1 | >= {GO_C_YT_THRESHOLD:.3f} | {c_v4_yt['macro_f1']:.3f} "
                 f"| {'OK' if gate_c_yt else 'X'} |")
    lines.append(f"| C_v4 full macro F1   | >= {GO_C_FULL_THRESHOLD:.3f} | {c_v4_full['macro_f1']:.3f} "
                 f"| {'OK' if gate_c_full else 'X'} |")
    lines.append("")
    lines.append(f"**{verdict}** (any of the three gates is sufficient).")
    lines.append("")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(f"Verdict: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
