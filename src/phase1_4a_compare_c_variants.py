"""Three-way comparison: Phase 1.3 C vs Phase 1.4a C_v2 vs Phase 1.4a C_v3.

Writes:
    * ``results/phase1_4a/c_vs_cv2_vs_cv3_comparison.md``
    * ``results/phase1_4a/go_judgment_d.md``

Go threshold for objective D: macro F1 >= 0.86 on the 42-fold set.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
PH13_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_c"
C_V2_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v2"
C_V3_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v3"
OUT_CMP = REPO_ROOT / "results" / "phase1_4a" / "c_vs_cv2_vs_cv3_comparison.md"
OUT_GO = REPO_ROOT / "results" / "phase1_4a" / "go_judgment_d.md"

GO_MACRO_F1_THRESHOLD = 0.86
PH13_BASELINE_MACRO_F1 = 0.840
C_V2_MACRO_F1 = 0.826


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
        return "(no row)"
    if "error" in row:
        return "ERR"
    p = row.get("final_prediction") or {}
    return f"{p.get('sparrow','?')}/{p.get('bulbul','?')}"


def full_ok(row: dict[str, Any] | None) -> bool | None:
    if row is None or "error" in row:
        return None
    ok = row.get("is_correct") or {}
    return bool(ok.get("sparrow") and ok.get("bulbul"))


def render_scope_table(
    title: str,
    c: dict[str, Any],
    c2: dict[str, Any],
    c3: dict[str, Any],
) -> list[str]:
    return [
        f"### {title}",
        "",
        "| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |",
        "|---|---:|---:|---:|---:|",
        f"| n (scored) | {c['n']} ({c['scored']}) | {c2['n']} ({c2['scored']}) "
        f"| {c3['n']} ({c3['scored']}) | - |",
        f"| fallback | {c['fallback']} | {c2['fallback']} | {c3['fallback']} "
        f"| {c3['fallback']-c['fallback']:+d} |",
        f"| macro F1 | {c['macro_f1']:.3f} | {c2['macro_f1']:.3f} | {c3['macro_f1']:.3f} "
        f"| {c3['macro_f1']-c['macro_f1']:+.3f} |",
        f"| sparrow F1 | {c['sparrow_f1']:.3f} | {c2['sparrow_f1']:.3f} "
        f"| {c3['sparrow_f1']:.3f} | {c3['sparrow_f1']-c['sparrow_f1']:+.3f} |",
        f"| bulbul F1 | {c['bulbul_f1']:.3f} | {c2['bulbul_f1']:.3f} "
        f"| {c3['bulbul_f1']:.3f} | {c3['bulbul_f1']-c['bulbul_f1']:+.3f} |",
        "",
    ]


def render_comparison(
    c_rows: dict[str, dict[str, Any]],
    c2_rows: dict[str, dict[str, Any]],
    c3_rows: dict[str, dict[str, Any]],
) -> str:
    ids = sorted(set(c_rows) | set(c2_rows) | set(c3_rows))

    def fold_key(vid: str) -> int:
        for d in (c_rows, c2_rows, c3_rows):
            if vid in d and isinstance(d[vid].get("fold"), int):
                return int(d[vid]["fold"])
        return 9999

    ids = sorted(ids, key=fold_key)

    c_list = list(c_rows.values())
    c2_list = list(c2_rows.values())
    c3_list = list(c3_rows.values())

    scopes: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("Full (self + YouTube)", lambda r: True),
        ("Self-recorded only", lambda r: r.get("source") == "self"),
        ("YouTube only", lambda r: (r.get("source") or "").startswith("youtube")),
        ("YouTube-grok", lambda r: r.get("source") == "youtube-grok"),
        ("YouTube-claude", lambda r: r.get("source") == "youtube-claude"),
    ]
    categories = sorted({r.get("category") for r in c3_list if r.get("category")})

    lines = [
        "# Phase 1.4a Topology variants comparison (C / C_v2 / C_v3)",
        "",
        "- Phase 1.3 C: Parallel Fusion, no frame pre-filter, no temporal alignment",
        "- Phase 1.4a C_v2: + frame_extractor pre-filter (objective B)",
        "- Phase 1.4a C_v3: + temporal_sampler (2s windows, sync_summary) -- objective D",
        "",
        f"- Folds: C={len(c_rows)}  C_v2={len(c2_rows)}  C_v3={len(c3_rows)}",
        "",
        "## Metric deltas",
        "",
    ]
    for title, pred in scopes:
        lines.extend(render_scope_table(
            title,
            metrics_for(filter_rows(c_list, pred)),
            metrics_for(filter_rows(c2_list, pred)),
            metrics_for(filter_rows(c3_list, pred)),
        ))
    for cat in categories:
        def pred(r: dict[str, Any], cat_: str = cat) -> bool:
            return r.get("category") == cat_
        lines.extend(render_scope_table(
            f"Category = {cat}",
            metrics_for(filter_rows(c_list, pred)),
            metrics_for(filter_rows(c2_list, pred)),
            metrics_for(filter_rows(c3_list, pred)),
        ))

    # Per-fold flip analysis (v3 vs Phase 1.3 C baseline)
    v3_wins = v3_regress = both_ok = both_wrong = 0
    flips: list[dict[str, Any]] = []
    for vid in ids:
        c = c_rows.get(vid); c3 = c3_rows.get(vid)
        ok_c = full_ok(c); ok_c3 = full_ok(c3)
        if ok_c is None or ok_c3 is None:
            continue
        if ok_c and ok_c3:
            both_ok += 1
        elif ok_c3 and not ok_c:
            v3_wins += 1
            flips.append({"vid": vid, "kind": "v3 improvement", "c": c, "c3": c3})
        elif ok_c and not ok_c3:
            v3_regress += 1
            flips.append({"vid": vid, "kind": "v3 regression", "c": c, "c3": c3})
        else:
            both_wrong += 1

    lines.append("## Per-video flip summary (C vs C_v3)")
    lines.append("")
    lines.append(f"- Both correct: {both_ok}")
    lines.append(f"- C_v3 improved over C: {v3_wins}")
    lines.append(f"- C_v3 regressed from C: {v3_regress}")
    lines.append(f"- Both wrong: {both_wrong}")
    lines.append("")

    if flips:
        lines.append("### Flip details")
        lines.append("")
        lines.append("| fold | video_id | source | category | GT S/B | C pred | C_v3 pred | sync_rate | kind |")
        lines.append("|---:|---|---|---|:-:|:-:|:-:|---:|---|")
        for f in flips:
            c = f["c"]; c3 = f["c3"]
            fold = c3.get("fold") or c.get("fold")
            fold_str = f"{fold:02d}" if isinstance(fold, int) else str(fold)
            gt = (c3.get("ground_truth") or c.get("ground_truth") or {})
            source = c3.get("source") or c.get("source") or "-"
            category = c3.get("category") or c.get("category") or "-"
            sync = (c3.get("sync_summary") or {}).get("sync_rate", 0.0)
            lines.append(
                f"| {fold_str} | {f['vid']} | {source} | {category} "
                f"| {gt.get('sparrow','-')}/{gt.get('bulbul','-')} "
                f"| {pred_cell(c)} | {pred_cell(c3)} | {sync:.3f} | {f['kind']} |"
            )
        lines.append("")

    # Per-fold side-by-side
    lines.append("## Per-fold side-by-side (42 folds)")
    lines.append("")
    lines.append(
        "| fold | video_id | source | category | GT S/B | C | C_v2 | C_v3 | sync_rate | sel_rate |"
    )
    lines.append("|---:|---|---|---|:-:|:-:|:-:|:-:|---:|---:|")
    for vid in ids:
        c = c_rows.get(vid); c2 = c2_rows.get(vid); c3 = c3_rows.get(vid)
        base = c3 or c2 or c or {}
        fold = base.get("fold", "-")
        fold_str = f"{fold:02d}" if isinstance(fold, int) else str(fold)
        gt = base.get("ground_truth", {"sparrow": "-", "bulbul": "-"})
        source = base.get("source", "-")
        category = base.get("category", "-")
        sync = (c3.get("sync_summary") or {}).get("sync_rate", 0.0) if c3 else 0.0
        sel = (c2.get("frame_extractor") or {}).get("frame_selection_rate", 0.0) if c2 else 0.0
        lines.append(
            f"| {fold_str} | {vid} | {source} | {category} "
            f"| {gt.get('sparrow','-')}/{gt.get('bulbul','-')} "
            f"| {pred_cell(c)} | {pred_cell(c2)} | {pred_cell(c3)} "
            f"| {sync:.3f} | {sel:.3f} |"
        )
    lines.append("")

    # sync_rate correlation
    correct: list[float] = []
    wrong: list[float] = []
    for vid in ids:
        c3 = c3_rows.get(vid)
        if c3 is None or "error" in c3:
            continue
        sync = float((c3.get("sync_summary") or {}).get("sync_rate", 0.0))
        if full_ok(c3):
            correct.append(sync)
        else:
            wrong.append(sync)

    def mean_or_dash(xs: list[float]) -> str:
        return f"{sum(xs)/len(xs):.3f}" if xs else "-"

    lines.append("## C_v3 sync_rate vs correctness")
    lines.append("")
    lines.append("| subset | n | mean sync_rate |")
    lines.append("|---|---:|---:|")
    lines.append(f"| C_v3 fully correct | {len(correct)} | {mean_or_dash(correct)} |")
    lines.append(f"| C_v3 at least one class wrong | {len(wrong)} | {mean_or_dash(wrong)} |")
    lines.append("")
    return "\n".join(lines)


def render_go_judgment(
    c_rows: dict[str, dict[str, Any]],
    c2_rows: dict[str, dict[str, Any]],
    c3_rows: dict[str, dict[str, Any]],
) -> str:
    c_full = metrics_for(list(c_rows.values()))
    c2_full = metrics_for(list(c2_rows.values()))
    c3_full = metrics_for(list(c3_rows.values()))
    delta_v3_c = c3_full["macro_f1"] - c_full["macro_f1"]
    go = c3_full["macro_f1"] >= GO_MACRO_F1_THRESHOLD
    verdict = "Go" if go else "No-Go"

    lines = [
        "# Phase 1.4a Objective D — Go/No-Go judgment",
        "",
        "## Criterion",
        "",
        f"- Go threshold: C_v3 macro F1 >= **{GO_MACRO_F1_THRESHOLD:.2f}** ",
        f"  (Phase 1.3 C baseline {PH13_BASELINE_MACRO_F1:.3f}; C_v2 was {C_V2_MACRO_F1:.3f})",
        "",
        "## Measured values (42 folds, self + YouTube)",
        "",
        "| metric | Phase 1.3 C | C_v2 | C_v3 | Δ(C_v3 - C) |",
        "|---|---:|---:|---:|---:|",
        f"| macro F1 | {c_full['macro_f1']:.3f} | {c2_full['macro_f1']:.3f} "
        f"| {c3_full['macro_f1']:.3f} | {delta_v3_c:+.3f} |",
        f"| sparrow F1 | {c_full['sparrow_f1']:.3f} | {c2_full['sparrow_f1']:.3f} "
        f"| {c3_full['sparrow_f1']:.3f} | {c3_full['sparrow_f1']-c_full['sparrow_f1']:+.3f} |",
        f"| bulbul F1 | {c_full['bulbul_f1']:.3f} | {c2_full['bulbul_f1']:.3f} "
        f"| {c3_full['bulbul_f1']:.3f} | {c3_full['bulbul_f1']-c_full['bulbul_f1']:+.3f} |",
        f"| fallback | {c_full['fallback']} | {c2_full['fallback']} "
        f"| {c3_full['fallback']} | {c3_full['fallback']-c_full['fallback']:+d} |",
        "",
        "## Verdict",
        "",
        f"**{verdict}** (C_v3 macro F1 = {c3_full['macro_f1']:.3f}, "
        f"threshold = {GO_MACRO_F1_THRESHOLD:.2f}).",
        "",
    ]
    if go:
        lines.extend([
            "Objective D (modality synchronisation) is satisfied by the ",
            "temporal_sampler + LLM prompt update. Suggested next step:",
            "",
            "- **Objective C (temporal detail)**: extend the timeline from a ",
            "  sync summary to per-window species predictions; let the LLM ",
            "  stitch a per-second species track.",
            "- **Objective A (efficiency)**: the per-frame YOLO + BirdNET are ",
            "  now measured together; profile and consolidate.",
        ])
    else:
        lines.extend([
            "Objective D is **not** satisfied on its own. Candidate next steps:",
            "",
            "- Tighten the temporal prompt: explicit rules for sparrow/bulbul ",
            "  co-occurrence in different windows (mixed category).",
            "- Combine with objective B (frame_extractor) and see if the two ",
            "  interventions are additive.",
            "- Extend the 42-fold set; n=42 leaves a non-trivial uncertainty ",
            "  on the macro F1 delta (one-fold noise ≈ ±0.02).",
        ])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()
    c = load_folds(PH13_BASE)
    c2 = load_folds(C_V2_BASE)
    c3 = load_folds(C_V3_BASE)

    OUT_CMP.parent.mkdir(parents=True, exist_ok=True)
    OUT_CMP.write_text(render_comparison(c, c2, c3), encoding="utf-8")
    OUT_GO.write_text(render_go_judgment(c, c2, c3), encoding="utf-8")
    print(f"Wrote {OUT_CMP}")
    print(f"Wrote {OUT_GO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
