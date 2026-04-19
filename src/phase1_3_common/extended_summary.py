"""Shared summary helpers for Phase 1.3 extended topology runs.

Breaks down macro / per-class F1 by source (self / youtube-grok /
youtube-claude), by category (sparrow / bulbul / mixed / both), and by
self-vs-youtube aggregation. Emits a Markdown section that the three
extended topology scripts can embed next to their topology-specific
per-fold tables.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from phase1_3_common.loocv_runner import compute_metrics


def _subset(rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
    return [r for r in rows if predicate(r)]


def metric_block(metrics: dict[str, Any]) -> str:
    if metrics["n_rows"] == 0:
        return "n=0 / -"
    return (
        f"n={metrics['n_rows']} (scored {metrics['n_scored']}, "
        f"fallback {metrics['fallback_triggered']}, "
        f"parse_fail {metrics['parse_fail']}, errors {metrics['errors']}) | "
        f"macro_f1={metrics['macro_f1']:.3f} | "
        f"sparrow_f1={metrics['f1']['sparrow']:.3f} | "
        f"bulbul_f1={metrics['f1']['bulbul']:.3f} | "
        f"accuracy S={metrics['accuracy']['sparrow']:.3f} "
        f"B={metrics['accuracy']['bulbul']:.3f}"
    )


def render_breakdown(rows: list[dict[str, Any]]) -> str:
    """Per-source / per-category / self-vs-YouTube metric tables."""
    full = compute_metrics(rows)
    self_rows = _subset(rows, lambda r: r.get("source") == "self")
    yt_rows = _subset(rows, lambda r: (r.get("source") or "").startswith("youtube"))
    grok_rows = _subset(rows, lambda r: r.get("source") == "youtube-grok")
    claude_rows = _subset(rows, lambda r: r.get("source") == "youtube-claude")

    categories: list[str] = sorted({r.get("category") for r in rows if r.get("category")})
    cat_metrics = {c: compute_metrics(_subset(rows, lambda r, c=c: r.get("category") == c)) for c in categories}

    lines: list[str] = []
    lines.append("## Aggregate metrics")
    lines.append("")
    lines.append("| scope | n / scored | fallback | parse_fail | errors | macro F1 | sparrow F1 | bulbul F1 |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    def row(label: str, m: dict[str, Any]) -> str:
        return (
            f"| {label} | {m['n_rows']} / {m['n_scored']} | "
            f"{m['fallback_triggered']} | {m['parse_fail']} | {m['errors']} | "
            f"{m['macro_f1']:.3f} | {m['f1']['sparrow']:.3f} | {m['f1']['bulbul']:.3f} |"
        )
    lines.append(row("**full (self + youtube)**", full))
    lines.append(row("self-recorded", compute_metrics(self_rows)))
    lines.append(row("youtube (all)", compute_metrics(yt_rows)))
    lines.append(row("youtube-grok",  compute_metrics(grok_rows)))
    lines.append(row("youtube-claude", compute_metrics(claude_rows)))
    lines.append("")

    lines.append("## Per-category metrics (full set)")
    lines.append("")
    lines.append("| category | n / scored | fallback | macro F1 | sparrow F1 | bulbul F1 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for c in categories:
        m = cat_metrics[c]
        lines.append(
            f"| {c} | {m['n_rows']} / {m['n_scored']} | {m['fallback_triggered']} "
            f"| {m['macro_f1']:.3f} | {m['f1']['sparrow']:.3f} | {m['f1']['bulbul']:.3f} |"
        )
    lines.append("")
    return "\n".join(lines)


def per_fold_table_header(extra_cols: Iterable[str] = ()) -> list[str]:
    base = ["fold", "video_id", "source", "category", "GT S/B", "pred S/B", "S OK", "B OK", "fallback", "t_total"]
    header = base + list(extra_cols)
    return [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]


def per_fold_row(row: dict[str, Any], extra_cells: Iterable[str] = ()) -> str:
    if "error" in row:
        gt = row.get("ground_truth", {})
        cells = [
            f"{row.get('fold','-'):02d}" if isinstance(row.get('fold'), int) else str(row.get('fold', '-')),
            row.get("video_id", "-"),
            row.get("source", "-"),
            row.get("category", "-"),
            f"{gt.get('sparrow','-')}/{gt.get('bulbul','-')}",
            "ERR", "-", "-", "-", "-",
        ]
        cells.extend(extra_cells)
        return "| " + " | ".join(cells) + " |"
    pred = row.get("final_prediction", {}) or {}
    gt = row.get("ground_truth", {}) or {}
    ok = row.get("is_correct", {}) or {}
    t_total = ((row.get("elapsed_sec") or {}).get("total") or 0.0)
    cells = [
        f"{row['fold']:02d}",
        row.get("video_id", "-"),
        row.get("source", "-"),
        row.get("category", "-"),
        f"{gt.get('sparrow','-')}/{gt.get('bulbul','-')}",
        f"{pred.get('sparrow','-')}/{pred.get('bulbul','-')}",
        "OK" if ok.get("sparrow") else "X",
        "OK" if ok.get("bulbul") else "X",
        "Y" if row.get("fallback_triggered") else "-",
        f"{float(t_total):.2f}",
    ]
    cells.extend(str(c) for c in extra_cells)
    return "| " + " | ".join(cells) + " |"
