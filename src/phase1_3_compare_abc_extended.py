"""Phase 1.3 extended — A vs B vs C on 43 folds (self + YouTube).

Reads per-fold JSON under ``results/phase1_3_extended/topology_{a,b,c}/``
and writes ``results/phase1_3_extended/abc_extended_comparison.md``.

Produces:
    * Overall metrics and per-source, per-category breakdowns per topology.
    * Per-video comparison table (fold x topology predictions).
    * Pairwise agreement (A↔B, A↔C, B↔C).
    * Self-vs-YouTube delta for each topology (was Topology A low-F1 a
      webcam audio problem, or fundamental to BirdNET fusion?).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE = REPO_ROOT / "results" / "phase1_3_extended"
OUT_PATH = BASE / "abc_extended_comparison.md"


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


def _filter(rows: list[dict[str, Any]], pred: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
    return [r for r in rows if pred(r)]


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


def pred_cell(row: dict[str, Any] | None) -> str:
    if row is None:
        return "(no row)"
    if "error" in row:
        return "ERR"
    p = row.get("final_prediction") or {}
    return f"{p.get('sparrow','?')}/{p.get('bulbul','?')}"


def pair_agreement(x: dict[str, dict[str, Any]], y: dict[str, dict[str, Any]]) -> dict[str, int]:
    s_agree = b_agree = both_agree = comparable = 0
    for vid in set(x) & set(y):
        rx, ry = x[vid], y[vid]
        if "error" in rx or "error" in ry:
            continue
        px = rx.get("final_prediction") or {}
        py = ry.get("final_prediction") or {}
        if (px.get("sparrow") not in (0, 1) or py.get("sparrow") not in (0, 1)
                or px.get("bulbul") not in (0, 1) or py.get("bulbul") not in (0, 1)):
            continue
        comparable += 1
        s = px["sparrow"] == py["sparrow"]
        b = px["bulbul"] == py["bulbul"]
        s_agree += int(s)
        b_agree += int(b)
        both_agree += int(s and b)
    return {"comparable": comparable, "sparrow_agree": s_agree, "bulbul_agree": b_agree, "both_agree": both_agree}


def render_metric_block(label: str, m: dict[str, Any]) -> str:
    return (
        f"| {label} | {m['n']} / {m['scored']} | {m['fallback']} | {m['errors']} "
        f"| {m['macro_f1']:.3f} | {m['sparrow_f1']:.3f} | {m['bulbul_f1']:.3f} |"
    )


def render_topology_block(name: str, rows: list[dict[str, Any]]) -> list[str]:
    m_full = metrics_for(rows)
    m_self = metrics_for(_filter(rows, lambda r: r.get("source") == "self"))
    m_yt = metrics_for(_filter(rows, lambda r: (r.get("source") or "").startswith("youtube")))
    m_grok = metrics_for(_filter(rows, lambda r: r.get("source") == "youtube-grok"))
    m_claude = metrics_for(_filter(rows, lambda r: r.get("source") == "youtube-claude"))
    categories = sorted({r.get("category") for r in rows if r.get("category")})

    lines = [f"### Topology {name}", ""]
    lines.append("| scope | n / scored | fallback | errors | macro F1 | sparrow F1 | bulbul F1 |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    lines.append(render_metric_block("full", m_full))
    lines.append(render_metric_block("self-recorded", m_self))
    lines.append(render_metric_block("youtube (all)", m_yt))
    lines.append(render_metric_block("youtube-grok", m_grok))
    lines.append(render_metric_block("youtube-claude", m_claude))
    for c in categories:
        m = metrics_for(_filter(rows, lambda r, c=c: r.get("category") == c))
        lines.append(render_metric_block(f"category={c}", m))
    lines.append("")
    return lines


def main() -> int:
    ensure_utf8_streams()
    a = load_folds(BASE / "topology_a")
    b = load_folds(BASE / "topology_b")
    c = load_folds(BASE / "topology_c")

    a_rows = list(a.values())
    b_rows = list(b.values())
    c_rows = list(c.values())

    ids = sorted(set(a) | set(b) | set(c))

    lines: list[str] = [
        "# Phase 1.3 extended — Topology A vs B vs C (43 folds)",
        "",
        "- A = Audio-Only (BirdNET -> LLM)",
        "- B = Visual-Only (YOLOv8n -> LLM)",
        "- C = Parallel Fusion (BirdNET + YOLOv8n -> LLM, target_threshold=None)",
        "",
        f"- Folds with A result: {len(a)} | B: {len(b)} | C: {len(c)}",
        "",
        "## Topology-level metric breakdowns",
        "",
    ]
    lines.extend(render_topology_block("A", a_rows))
    lines.extend(render_topology_block("B", b_rows))
    lines.extend(render_topology_block("C", c_rows))

    # Side-by-side per-video (keep it in fold order of A if present, else first available)
    lines.append("## Per-video comparison")
    lines.append("")
    lines.append("| fold | video_id | source | category | GT S/B | A pred | B pred | C pred | A full-ok | B full-ok | C full-ok |")
    lines.append("|---:|---|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|")

    def fold_key(vid: str) -> int:
        for d in (a, b, c):
            if vid in d and isinstance(d[vid].get("fold"), int):
                return int(d[vid]["fold"])
        return 9999

    for vid in sorted(ids, key=fold_key):
        ar = a.get(vid); br = b.get(vid); cr = c.get(vid)
        any_row = ar or br or cr or {}
        gt = any_row.get("ground_truth", {"sparrow": "-", "bulbul": "-"})
        source = any_row.get("source", "-")
        category = any_row.get("category", "-")
        fold = any_row.get("fold", "-")
        fold_str = f"{fold:02d}" if isinstance(fold, int) else str(fold)

        def full_ok(row: dict[str, Any] | None) -> str:
            if row is None or "error" in row:
                return "-"
            ok = row.get("is_correct") or {}
            return "OK" if ok.get("sparrow") and ok.get("bulbul") else "X"

        lines.append(
            f"| {fold_str} | {vid} | {source} | {category} "
            f"| {gt.get('sparrow','-')}/{gt.get('bulbul','-')} "
            f"| {pred_cell(ar)} | {pred_cell(br)} | {pred_cell(cr)} "
            f"| {full_ok(ar)} | {full_ok(br)} | {full_ok(cr)} |"
        )
    lines.append("")

    lines.append("## Pairwise agreement (both sides scored)")
    lines.append("")
    lines.append("| pair | comparable | sparrow agree | bulbul agree | full match |")
    lines.append("|---|---:|---:|---:|---:|")
    for label, ag in (("A vs B", pair_agreement(a, b)),
                      ("A vs C", pair_agreement(a, c)),
                      ("B vs C", pair_agreement(b, c))):
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

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
