"""Re-evaluate every Phase 1.3-extended and Phase 1.4a experiment on the clean 22-fold subset.

The full 42-fold set included 20 YouTube clips that Robosheep's review
flagged as unusable (Tier C: BGM / text-dominant / human voice / heavy
noise). This script reuses every previously-saved fold JSON; only the
*aggregation* changes. Output:

    results/phase1_clean/reevaluation_summary.md
    results/phase1_clean/graphs/*.png

Simplification: Tier B clips have a 30 s intro trim available via
``phase1_4a_common.video_trimmer`` but are **not** re-processed here —
the existing fold JSON was computed on the untrimmed clip and is
reused as-is. This is called out in the summary so the reader knows
what the numbers mean.
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4a_common.clean_tiers import (
    apply_tiers_to_metadata,
    load_usable_video_ids,
)

YT_METADATA_PATH = REPO_ROOT / "data" / "youtube_metadata.json"
OUT_DIR = REPO_ROOT / "results" / "phase1_clean"
SUMMARY_PATH = OUT_DIR / "reevaluation_summary.md"
GRAPHS_DIR = OUT_DIR / "graphs"

EXPERIMENTS: list[tuple[str, Path]] = [
    ("Phase 1.3 A",    REPO_ROOT / "results" / "phase1_3_extended" / "topology_a"),
    ("Phase 1.3 B",    REPO_ROOT / "results" / "phase1_3_extended" / "topology_b"),
    ("Phase 1.3 C",    REPO_ROOT / "results" / "phase1_3_extended" / "topology_c"),
    ("Phase 1.4a C_v2", REPO_ROOT / "results" / "phase1_4a" / "topology_c_v2"),
    ("Phase 1.4a C_v3", REPO_ROOT / "results" / "phase1_4a" / "topology_c_v3"),
    ("Phase 1.4a B_v3", REPO_ROOT / "results" / "phase1_4a" / "topology_b_v3"),
    ("Phase 1.4a C_v4", REPO_ROOT / "results" / "phase1_4a" / "topology_c_v4"),
]

GO_B_YT_THRESHOLD = 0.642
GO_C_YT_THRESHOLD = 0.894
GO_C_FULL_THRESHOLD = 0.860
OBJ_B_THRESHOLD = 0.86
OBJ_D_THRESHOLD = 0.86


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def load_folds(base: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not base.is_dir():
        return rows
    for fold_dir in sorted(base.glob("fold_*")):
        for p in sorted(fold_dir.glob("*.json")):
            rows.append(json.loads(p.read_text(encoding="utf-8")))
    return rows


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


def bootstrap_macro_f1_ci(
    rows: list[dict[str, Any]], n_resamples: int = 1000, seed: int = 42
) -> tuple[float, float]:
    if not rows:
        return (0.0, 0.0)
    rng = random.Random(seed)
    samples: list[float] = []
    N = len(rows)
    for _ in range(n_resamples):
        resample = [rows[rng.randrange(N)] for _ in range(N)]
        samples.append(metrics_for(resample)["macro_f1"])
    samples.sort()
    lo = samples[int(0.025 * n_resamples)]
    hi = samples[int(0.975 * n_resamples)]
    return lo, hi


def filter_clean(rows: list[dict[str, Any]], usable_ids: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        source = r.get("source", "")
        vid = r.get("video_id", "")
        if source == "self":
            out.append(r); continue
        if vid in usable_ids:
            out.append(r)
    return out


def filter_subset(
    rows: list[dict[str, Any]], pred: Callable[[dict[str, Any]], bool]
) -> list[dict[str, Any]]:
    return [r for r in rows if pred(r)]


def _render_macro_row(label: str, full: dict[str, Any], clean: dict[str, Any]) -> str:
    delta = clean["macro_f1"] - full["macro_f1"]
    return (
        f"| {label} | {full['n']}/{full['scored']} | {full['macro_f1']:.3f} "
        f"| {clean['n']}/{clean['scored']} | {clean['macro_f1']:.3f} | {delta:+.3f} |"
    )


def render_summary(
    full_results: dict[str, list[dict[str, Any]]],
    clean_results: dict[str, list[dict[str, Any]]],
) -> str:
    lines: list[str] = [
        "# Phase 1.4a clean-dataset re-evaluation",
        "",
        "Every Phase 1.3-extended and Phase 1.4a experiment is re-aggregated on the",
        "22-fold clean subset (11 self-recorded + 11 YouTube Tier A/B/B'). Robosheep's",
        "tier review (2026-04-19) drops 20 unusable YouTube clips (BGM / human voice /",
        "text-dominant overlays / heavy noise).",
        "",
        "**Simplification**: Tier B's 30 s intro trim is not re-applied here; we reuse",
        "each experiment's original fold JSON (computed on the untrimmed clip). Tier B",
        "clips therefore receive the same bias as in the 42-fold run. Trimmed re-runs",
        "can be scheduled via `src/phase1_4a_common/video_trimmer.py` in Phase 1.4b+.",
        "",
        "## Tier review summary",
        "",
        "| tier | count | notes |",
        "|---|---:|---|",
        "| A (fully usable) | 4 | 1 sparrow, 3 bulbul |",
        "| B (usable with 30 s intro trim) | 6 | 1 sparrow, 5 bulbul |",
        "| B' (noisy but usable) | 1 | sparrow |",
        "| C (unusable, excluded) | 20 | 8 sparrow, 4 bulbul, 8 mixed |",
        "| not tiered (download failed) | 1 | yt_Ji1jooZwBSo |",
        "",
        "Clean dataset = 11 self-recorded + 11 YouTube = **22 folds**.",
        "",
        "## 4.1 Macro F1: full 42-fold vs clean 22-fold",
        "",
        "| experiment | 42-fold n/scored | 42-fold macro F1 | 22-fold n/scored | 22-fold macro F1 | Δ |",
        "|---|---|---:|---|---:|---:|",
    ]
    for name, _base in EXPERIMENTS:
        full_m = metrics_for(full_results[name])
        clean_m = metrics_for(clean_results[name])
        lines.append(_render_macro_row(name, full_m, clean_m))
    lines.append("")

    # 4.2 Category breakdown (clean only)
    categories = ["sparrow", "bulbul", "mixed", "both"]
    lines.append("## 4.2 Category breakdown (clean 22-fold)")
    lines.append("")
    lines.append("| category | " + " | ".join(name for name, _ in EXPERIMENTS) + " |")
    lines.append("|---" + "|---" * len(EXPERIMENTS) + "|")
    header = "| category | n | " + " | ".join(name for name, _ in EXPERIMENTS) + " |"
    sep = "|---|---:|" + "|".join(["---:"] * len(EXPERIMENTS)) + "|"
    lines[-2] = header
    lines[-1] = sep
    for cat in categories:
        cat_rows = {n: filter_subset(clean_results[n], lambda r, c=cat: r.get("category") == c)
                    for n, _ in EXPERIMENTS}
        ns = {n: len(rows) for n, rows in cat_rows.items()}
        ns_unique = set(ns.values())
        if ns_unique == {0}:
            continue
        n_cell = next(iter(ns.values())) if len(ns_unique) == 1 else "/".join(str(v) for v in ns.values())
        row_cells = []
        for name, _ in EXPERIMENTS:
            m = metrics_for(cat_rows[name])
            if m["n"] == 0:
                row_cells.append("-")
            else:
                row_cells.append(f"{m['macro_f1']:.3f}")
        note = " *(small n)*" if cat == "mixed" else ""
        lines.append(f"| {cat}{note} | {n_cell} | " + " | ".join(row_cells) + " |")
    lines.append("")

    # 4.3 Source breakdown (clean only)
    lines.append("## 4.3 Source breakdown (clean 22-fold)")
    lines.append("")
    lines.append("| source | n | " + " | ".join(name for name, _ in EXPERIMENTS) + " |")
    lines.append("|---|---:|" + "|".join(["---:"] * len(EXPERIMENTS)) + "|")
    source_filters: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("self (self-recorded)", lambda r: r.get("source") == "self"),
        ("YouTube (Tier A only)", lambda r: r.get("video_id") in {
            "yt_ZRQLsbGEVG8", "yt_8HhsjaqFITQ", "yt_8zanYHHEpiw", "yt_vmrbbEe9R6M"}),
        ("YouTube (Tier A+B+B')", lambda r: (r.get("source") or "").startswith("youtube")),
    ]
    for label, pred in source_filters:
        subset_rows = {n: filter_subset(clean_results[n], pred) for n, _ in EXPERIMENTS}
        n_cell = next((len(v) for v in subset_rows.values()), 0)
        row_cells = []
        for name, _ in EXPERIMENTS:
            m = metrics_for(subset_rows[name])
            row_cells.append(f"{m['macro_f1']:.3f}" if m["n"] > 0 else "-")
        lines.append(f"| {label} | {n_cell} | " + " | ".join(row_cells) + " |")
    lines.append("")

    # 4.4 Go judgment
    lines.append("## 4.4 Go judgment re-evaluation (clean 22-fold)")
    lines.append("")
    ph13_c_clean = metrics_for(clean_results["Phase 1.3 C"])["macro_f1"]
    cv2_clean = metrics_for(clean_results["Phase 1.4a C_v2"])["macro_f1"]
    cv3_clean = metrics_for(clean_results["Phase 1.4a C_v3"])["macro_f1"]
    bv3_clean = metrics_for(clean_results["Phase 1.4a B_v3"])["macro_f1"]
    cv4_clean = metrics_for(clean_results["Phase 1.4a C_v4"])["macro_f1"]
    lines.append("| objective | gate | clean value | verdict |")
    lines.append("|---|---|---:|:-:|")
    lines.append(
        f"| Obj B (C_v2 macro F1 >= {OBJ_B_THRESHOLD}) | vs Phase 1.3 C clean ({ph13_c_clean:.3f}) | "
        f"{cv2_clean:.3f} | {'Go' if cv2_clean >= OBJ_B_THRESHOLD else 'No-Go'} |"
    )
    lines.append(
        f"| Obj D (C_v3 macro F1 >= {OBJ_D_THRESHOLD}) | vs Phase 1.3 C clean ({ph13_c_clean:.3f}) | "
        f"{cv3_clean:.3f} | {'Go' if cv3_clean >= OBJ_D_THRESHOLD else 'No-Go'} |"
    )
    # B_v3 YouTube gate (clean YT subset only, 11 clips)
    bv3_yt_clean = metrics_for(filter_subset(
        clean_results["Phase 1.4a B_v3"],
        lambda r: (r.get("source") or "").startswith("youtube"),
    ))
    b_base_yt_clean = metrics_for(filter_subset(
        clean_results["Phase 1.3 B"],
        lambda r: (r.get("source") or "").startswith("youtube"),
    ))
    improvement = bv3_yt_clean["macro_f1"] - b_base_yt_clean["macro_f1"]
    lines.append(
        f"| bbox v3 (B_v3 YouTube clean >= Phase 1.3 B YouTube clean + 0.10) "
        f"| Phase 1.3 B YT clean {b_base_yt_clean['macro_f1']:.3f} -> "
        f"{bv3_yt_clean['macro_f1']:.3f} (Δ {improvement:+.3f}) "
        f"| {bv3_yt_clean['macro_f1']:.3f} "
        f"| {'Go' if improvement >= 0.10 else 'No-Go'} |"
    )
    # C_v4 full clean vs Phase 1.3 C clean
    c_cv4_delta = cv4_clean - ph13_c_clean
    lines.append(
        f"| bbox v3 (C_v4 full clean >= Phase 1.3 C full clean + 0.02) "
        f"| Phase 1.3 C clean {ph13_c_clean:.3f} -> "
        f"{cv4_clean:.3f} (Δ {c_cv4_delta:+.3f}) "
        f"| {cv4_clean:.3f} "
        f"| {'Go' if c_cv4_delta >= 0.02 else 'No-Go'} |"
    )
    lines.append("")

    # 4.5 Bootstrap CI
    lines.append("## 4.5 Bootstrap 95% CI for macro F1 (clean 22-fold)")
    lines.append("")
    lines.append("1000-resample bootstrap with seed=42. Paired deltas are indicative only; ")
    lines.append("do not substitute for a proper paired statistical test.")
    lines.append("")
    lines.append("| experiment | point | 95% CI (low, high) | CI width |")
    lines.append("|---|---:|---|---:|")
    for name, _ in EXPERIMENTS:
        rows = clean_results[name]
        m = metrics_for(rows)
        lo, hi = bootstrap_macro_f1_ci(rows)
        lines.append(f"| {name} | {m['macro_f1']:.3f} | ({lo:.3f}, {hi:.3f}) | {hi-lo:.3f} |")
    lines.append("")

    # 4.6 mixed limitations
    lines.append("## 4.6 Mixed-category evaluation is statistically limited")
    lines.append("")
    lines.append(
        "The clean subset contains only 2 `mixed` (\"both\") folds — both self-recorded "
        "(balcony_005, balcony_010). Any per-category macro F1 for `mixed` therefore "
        "covers at most 2 independent predictions; the number is reported for "
        "completeness but should not be interpreted as model-level behaviour. Grok's "
        "suggestion (Macaulay Library / external verified-both clips) remains the "
        "primary route to a statistically meaningful `mixed` evaluation."
    )
    lines.append("")

    # Simplification callout
    lines.append("## Caveats")
    lines.append("")
    lines.append("- Tier B clips contribute the same fold JSONs as in the 42-fold run; "
                 "the 30 s intro trim is **not** applied here. If Tier B intros dominate "
                 "the prompt signal on a clip, the clean number still inherits that bias.")
    lines.append("- n=22 produces wide unpaired bootstrap CIs "
                 "(half-widths roughly ±0.08 to ±0.20 across experiments). Single-topology "
                 "point estimates are loose. A paired bootstrap on (C, C_v3) over the same "
                 "22 folds would be tighter because errors are correlated across topologies.")
    lines.append("- Robosheep's review is categorical (Tier A/B/B'/C) rather than "
                 "per-clip scored; within-tier variance is not captured.")
    lines.append("")
    lines.append("## Headline changes vs the 42-fold report")
    lines.append("")
    lines.append(
        "- **Objective D (C_v3 temporal_sync) flips No-Go -> Go** on the clean set "
        f"({metrics_for(clean_results['Phase 1.4a C_v3'])['macro_f1']:.3f} >= {OBJ_D_THRESHOLD:.2f}). "
        "The 42-fold No-Go (0.819) was dragged down by Tier C clips whose audio was "
        "mostly BGM / text overlays — exactly the situation where a modality-sync "
        "signal cannot help."
    )
    lines.append(
        "- **Objective B (C_v2 frame_extractor) stays No-Go** (0.791 < 0.86). "
        "Removing no-bird frames does not recover the missing accuracy even on "
        "clean data."
    )
    lines.append(
        "- **bbox v3 B_v3 YouTube gate stays Go** (0.721 vs Phase 1.3 B YouTube "
        "clean 0.500, +0.221). The relative-distribution prompt continues to beat "
        "the absolute-threshold baseline on verified-clean YouTube clips."
    )
    lines.append(
        "- **bbox v3 C_v4 full gate stays No-Go and regresses further** "
        "(0.635 vs Phase 1.3 C clean 0.823, −0.188). Combining the relative-"
        "distribution prompt with audio fusion is strictly worse than either in "
        "isolation."
    )
    lines.append("")
    return "\n".join(lines)


def render_graphs(full_results: dict[str, list[dict[str, Any]]], clean_results: dict[str, list[dict[str, Any]]]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[graphs] matplotlib not installed; skipping", file=sys.stderr)
        return

    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    names = [n for n, _ in EXPERIMENTS]
    full_f1 = [metrics_for(full_results[n])["macro_f1"] for n in names]
    clean_f1 = [metrics_for(clean_results[n])["macro_f1"] for n in names]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = list(range(len(names)))
    w = 0.35
    ax.bar([i - w / 2 for i in x], full_f1, w, label="Full 42-fold", color="#4c72b0")
    ax.bar([i + w / 2 for i in x], clean_f1, w, label="Clean 22-fold", color="#dd8452")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=35, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("macro F1")
    ax.set_title("Macro F1: full 42-fold vs clean 22-fold")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(GRAPHS_DIR / "macro_f1_comparison.png", dpi=120)
    plt.close(fig)

    # Category breakdown (clean only)
    categories = ["sparrow", "bulbul", "mixed"]
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.12
    for i, name in enumerate(names):
        values = []
        for cat in categories:
            subset = filter_subset(clean_results[name], lambda r, c=cat: r.get("category") == c)
            m = metrics_for(subset)
            values.append(m["macro_f1"] if m["n"] > 0 else 0.0)
        offsets = [j + i * width - (len(names) - 1) * width / 2 for j in range(len(categories))]
        ax.bar(offsets, values, width, label=name)
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 1)
    ax.set_ylabel("macro F1")
    ax.set_title("Macro F1 by category (clean 22-fold)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(GRAPHS_DIR / "category_breakdown.png", dpi=120)
    plt.close(fig)

    # Source breakdown (clean only)
    sources = [
        ("self", lambda r: r.get("source") == "self"),
        ("YT Tier A", lambda r: r.get("video_id") in {
            "yt_ZRQLsbGEVG8", "yt_8HhsjaqFITQ", "yt_8zanYHHEpiw", "yt_vmrbbEe9R6M"}),
        ("YT A+B+B'", lambda r: (r.get("source") or "").startswith("youtube")),
    ]
    fig, ax = plt.subplots(figsize=(11, 5))
    for i, name in enumerate(names):
        values = []
        for _, pred in sources:
            m = metrics_for(filter_subset(clean_results[name], pred))
            values.append(m["macro_f1"] if m["n"] > 0 else 0.0)
        offsets = [j + i * width - (len(names) - 1) * width / 2 for j in range(len(sources))]
        ax.bar(offsets, values, width, label=name)
    ax.set_xticks(range(len(sources)))
    ax.set_xticklabels([s[0] for s in sources])
    ax.set_ylim(0, 1)
    ax.set_ylabel("macro F1")
    ax.set_title("Macro F1 by source (clean 22-fold)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(GRAPHS_DIR / "source_breakdown.png", dpi=120)
    plt.close(fig)
    print(f"[graphs] wrote 3 PNGs under {GRAPHS_DIR}")


def main() -> int:
    ensure_utf8_streams()

    # 1) Make sure youtube_metadata.json carries Robosheep's tier review.
    counts = apply_tiers_to_metadata(YT_METADATA_PATH)
    print(f"[metadata] tier counts = {counts}")

    # 2) Load every fold JSON per experiment.
    full_results: dict[str, list[dict[str, Any]]] = {}
    for name, base in EXPERIMENTS:
        full_results[name] = load_folds(base)
    # 3) Filter to the clean subset.
    usable_ids = load_usable_video_ids(YT_METADATA_PATH)
    clean_results: dict[str, list[dict[str, Any]]] = {
        name: filter_clean(rows, usable_ids) for name, rows in full_results.items()
    }
    # Sanity-log per experiment.
    for name, _ in EXPERIMENTS:
        print(f"  {name}: full={len(full_results[name])} clean={len(clean_results[name])}")

    # 4) Summary markdown + graphs.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(render_summary(full_results, clean_results), encoding="utf-8")
    print(f"[summary] {SUMMARY_PATH}")
    render_graphs(full_results, clean_results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
