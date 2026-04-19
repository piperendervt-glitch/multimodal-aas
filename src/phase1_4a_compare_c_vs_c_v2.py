"""Compare Phase 1.3 Topology C with Phase 1.4a Topology C_v2.

Emits:
    * ``results/phase1_4a/c_vs_c_v2_comparison.md`` — side-by-side
      per-fold table, per-scope metric deltas, and win/regression counts.
    * ``results/phase1_4a/go_judgment_b.md`` — Go/No-Go decision on
      objective B with rationale (Go threshold: macro F1 >= 0.86).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
PH13_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_c"
PH14A_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v2"
OUT_CMP = REPO_ROOT / "results" / "phase1_4a" / "c_vs_c_v2_comparison.md"
OUT_GO = REPO_ROOT / "results" / "phase1_4a" / "go_judgment_b.md"

GO_MACRO_F1_THRESHOLD = 0.86
PH13_BASELINE_MACRO_F1 = 0.840


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


def filter_rows(
    rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]
) -> list[dict[str, Any]]:
    return [r for r in rows if predicate(r)]


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


def render_scope_table(title: str, c: dict[str, Any], c2: dict[str, Any]) -> list[str]:
    delta_macro = c2["macro_f1"] - c["macro_f1"]
    delta_sp = c2["sparrow_f1"] - c["sparrow_f1"]
    delta_bu = c2["bulbul_f1"] - c["bulbul_f1"]
    return [
        f"### {title}",
        "",
        "| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |",
        "|---|---:|---:|---:|",
        f"| n (scored) | {c['n']} ({c['scored']}) | {c2['n']} ({c2['scored']}) | - |",
        f"| fallback  | {c['fallback']} | {c2['fallback']} | {c2['fallback']-c['fallback']:+d} |",
        f"| macro F1  | {c['macro_f1']:.3f} | {c2['macro_f1']:.3f} | {delta_macro:+.3f} |",
        f"| sparrow F1 | {c['sparrow_f1']:.3f} | {c2['sparrow_f1']:.3f} | {delta_sp:+.3f} |",
        f"| bulbul F1  | {c['bulbul_f1']:.3f} | {c2['bulbul_f1']:.3f} | {delta_bu:+.3f} |",
        "",
    ]


def render_comparison(c_rows: dict[str, dict[str, Any]], c2_rows: dict[str, dict[str, Any]]) -> str:
    ids = sorted(set(c_rows) | set(c2_rows))

    def fold_key(vid: str) -> int:
        for d in (c_rows, c2_rows):
            if vid in d and isinstance(d[vid].get("fold"), int):
                return int(d[vid]["fold"])
        return 9999

    ids = sorted(ids, key=fold_key)

    c_list = list(c_rows.values())
    c2_list = list(c2_rows.values())

    scopes: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("Full (self + YouTube)", lambda r: True),
        ("Self-recorded only", lambda r: r.get("source") == "self"),
        ("YouTube only", lambda r: (r.get("source") or "").startswith("youtube")),
        ("YouTube-grok", lambda r: r.get("source") == "youtube-grok"),
        ("YouTube-claude", lambda r: r.get("source") == "youtube-claude"),
    ]
    categories = sorted({r.get("category") for r in (c_list + c2_list) if r.get("category")})

    lines = [
        "# Phase 1.4a C_v2 vs Phase 1.3 C",
        "",
        "Side-by-side comparison of the Parallel Fusion topology with and without ",
        "the frame_extractor pre-filter. Both runs use identical prompts, BirdNET ",
        "configuration (`target_threshold=None`), and the same 42-fold video set.",
        "",
        f"- Phase 1.3 folds: {len(c_rows)}",
        f"- Phase 1.4a folds: {len(c2_rows)}",
        "",
        "## Metric deltas",
        "",
    ]
    for title, pred in scopes:
        c_scope = filter_rows(c_list, pred)
        c2_scope = filter_rows(c2_list, pred)
        lines.extend(render_scope_table(title, metrics_for(c_scope), metrics_for(c2_scope)))
    for cat in categories:
        def pred(r: dict[str, Any], cat_: str = cat) -> bool:
            return r.get("category") == cat_
        c_scope = filter_rows(c_list, pred)
        c2_scope = filter_rows(c2_list, pred)
        lines.extend(render_scope_table(f"Category = {cat}", metrics_for(c_scope), metrics_for(c2_scope)))

    # Per-fold flip analysis
    c_wins = c2_wins = both_ok = both_wrong = 0
    flips: list[dict[str, Any]] = []
    for vid in ids:
        c = c_rows.get(vid); c2 = c2_rows.get(vid)
        ok_c = full_ok(c)
        ok_c2 = full_ok(c2)
        if ok_c is None or ok_c2 is None:
            continue
        if ok_c and ok_c2:
            both_ok += 1
        elif ok_c and not ok_c2:
            c_wins += 1
            flips.append({"vid": vid, "kind": "regression (C_v2 wrong)", "c": c, "c2": c2})
        elif ok_c2 and not ok_c:
            c2_wins += 1
            flips.append({"vid": vid, "kind": "improvement (C_v2 right)", "c": c, "c2": c2})
        else:
            both_wrong += 1

    lines.append("## Per-video flip summary")
    lines.append("")
    lines.append(f"- Both correct: {both_ok}")
    lines.append(f"- C_v2 improved over C: {c2_wins}")
    lines.append(f"- C_v2 regressed from C: {c_wins}")
    lines.append(f"- Both wrong: {both_wrong}")
    lines.append("")

    if flips:
        lines.append("### Flip details")
        lines.append("")
        lines.append("| fold | video_id | source | category | GT S/B | C pred | C_v2 pred | sel_rate | kind |")
        lines.append("|---:|---|---|---|:-:|:-:|:-:|---:|---|")
        for f in flips:
            c = f["c"]; c2 = f["c2"]
            fold = c2.get("fold") or c.get("fold")
            fold_str = f"{fold:02d}" if isinstance(fold, int) else str(fold)
            gt = (c2.get("ground_truth") or c.get("ground_truth") or {})
            source = c2.get("source") or c.get("source") or "-"
            category = c2.get("category") or c.get("category") or "-"
            sel = (c2.get("frame_extractor") or {}).get("frame_selection_rate", 0.0)
            lines.append(
                f"| {fold_str} | {f['vid']} | {source} | {category} "
                f"| {gt.get('sparrow','-')}/{gt.get('bulbul','-')} "
                f"| {pred_cell(c)} | {pred_cell(c2)} | {sel:.3f} | {f['kind']} |"
            )
        lines.append("")

    # Full per-fold side-by-side
    lines.append("## Per-video side-by-side (42 folds)")
    lines.append("")
    lines.append("| fold | video_id | source | category | GT S/B | C pred | C_v2 pred | sel_rate | C ok | C_v2 ok |")
    lines.append("|---:|---|---|---|:-:|:-:|:-:|---:|:-:|:-:|")
    for vid in ids:
        c = c_rows.get(vid); c2 = c2_rows.get(vid)
        base = c2 or c or {}
        fold = base.get("fold", "-")
        fold_str = f"{fold:02d}" if isinstance(fold, int) else str(fold)
        gt = base.get("ground_truth", {"sparrow": "-", "bulbul": "-"})
        source = base.get("source", "-")
        category = base.get("category", "-")
        sel = (base.get("frame_extractor") or {}).get("frame_selection_rate", 0.0)
        ok_c = full_ok(c)
        ok_c2 = full_ok(c2)
        lines.append(
            f"| {fold_str} | {vid} | {source} | {category} "
            f"| {gt.get('sparrow','-')}/{gt.get('bulbul','-')} "
            f"| {pred_cell(c)} | {pred_cell(c2)} | {sel:.3f} "
            f"| {'OK' if ok_c else 'X' if ok_c is not None else '-'} "
            f"| {'OK' if ok_c2 else 'X' if ok_c2 is not None else '-'} |"
        )
    lines.append("")

    # Selection rate vs correctness
    sel_rates_correct = []
    sel_rates_wrong = []
    for vid in ids:
        c2 = c2_rows.get(vid)
        if c2 is None or "error" in c2:
            continue
        sel = (c2.get("frame_extractor") or {}).get("frame_selection_rate", 0.0)
        if full_ok(c2):
            sel_rates_correct.append(sel)
        else:
            sel_rates_wrong.append(sel)

    def mean_or_na(xs: list[float]) -> str:
        if not xs:
            return "-"
        return f"{sum(xs)/len(xs):.3f}"

    lines.append("## Selection-rate vs correctness (C_v2)")
    lines.append("")
    lines.append("| subset | n | mean selection rate |")
    lines.append("|---|---:|---:|")
    lines.append(f"| C_v2 fully correct | {len(sel_rates_correct)} | {mean_or_na(sel_rates_correct)} |")
    lines.append(f"| C_v2 at least one class wrong | {len(sel_rates_wrong)} | {mean_or_na(sel_rates_wrong)} |")
    lines.append("")
    return "\n".join(lines)


def render_go_judgment(c_rows: dict[str, dict[str, Any]], c2_rows: dict[str, dict[str, Any]]) -> str:
    c_full = metrics_for(list(c_rows.values()))
    c2_full = metrics_for(list(c2_rows.values()))
    delta = c2_full["macro_f1"] - c_full["macro_f1"]
    go = c2_full["macro_f1"] >= GO_MACRO_F1_THRESHOLD
    verdict = "Go" if go else "No-Go"

    lines = [
        "# Phase 1.4a Objective B — Go/No-Go judgment",
        "",
        "## Criterion",
        "",
        f"- Go threshold: Topology C_v2 macro F1 >= **{GO_MACRO_F1_THRESHOLD:.2f}** ",
        f"  (Phase 1.3 Topology C baseline was {PH13_BASELINE_MACRO_F1:.3f}; target = +0.02).",
        "",
        "## Measured values (42 folds, self + YouTube)",
        "",
        "| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |",
        "|---|---:|---:|---:|",
        f"| macro F1 | {c_full['macro_f1']:.3f} | {c2_full['macro_f1']:.3f} | {delta:+.3f} |",
        f"| sparrow F1 | {c_full['sparrow_f1']:.3f} | {c2_full['sparrow_f1']:.3f} "
        f"| {c2_full['sparrow_f1']-c_full['sparrow_f1']:+.3f} |",
        f"| bulbul F1 | {c_full['bulbul_f1']:.3f} | {c2_full['bulbul_f1']:.3f} "
        f"| {c2_full['bulbul_f1']-c_full['bulbul_f1']:+.3f} |",
        f"| fallback | {c_full['fallback']} | {c2_full['fallback']} "
        f"| {c2_full['fallback']-c_full['fallback']:+d} |",
        "",
        "## Verdict",
        "",
        f"**{verdict}** (measured macro F1 = {c2_full['macro_f1']:.3f}, "
        f"threshold = {GO_MACRO_F1_THRESHOLD:.2f}).",
        "",
    ]
    if go:
        lines.extend([
            "Objective B is satisfied by the frame_extractor pre-filter. The next ",
            "Phase 1.4a step targets **objective D (modality synchronisation)** — ",
            "align the temporal cues from the visual and audio nodes so the LLM can ",
            "reason over co-occurring evidence rather than frame-aggregated summaries.",
        ])
    else:
        lines.extend([
            "Objective B is **not** satisfied by the frame_extractor alone.",
            "Options:",
            "- Revisit the bbox-size prompt thresholds (the YouTube regression in B ",
            "  was the primary driver; C_v2 inherits the same prompt).",
            "- Consider objective D (modality sync) even under No-Go, because ",
            "  temporal alignment may unlock gains the frame-level aggregate hides.",
            "- Measure uncertainty: with n=42 the F1 estimate has non-trivial ",
            "  variance; a bootstrap CI on the delta may still clear the bar.",
        ])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()
    c_rows = load_folds(PH13_BASE)
    c2_rows = load_folds(PH14A_BASE)

    OUT_CMP.parent.mkdir(parents=True, exist_ok=True)
    OUT_CMP.write_text(render_comparison(c_rows, c2_rows), encoding="utf-8")
    OUT_GO.write_text(render_go_judgment(c_rows, c2_rows), encoding="utf-8")
    print(f"Wrote {OUT_CMP}")
    print(f"Wrote {OUT_GO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
