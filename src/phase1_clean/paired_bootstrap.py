"""Paired bootstrap CI for Phase 1.4a Go judgments (Grok round-2 Q2).

Unpaired CIs on the clean 22-fold set were wide enough (half-widths
±0.08 to ±0.20) that Phase 1.4a C_v3's point estimate 0.869 could not
be distinguished from Phase 1.3 C's 0.823 in isolation. This script
runs a *paired* bootstrap: each resample draws the same 22 fold
indices for both topologies, recomputes pooled F1 independently on
each side, and records the delta. Paired resampling removes the fold-
level common variance and yields a tighter CI for the delta.

Comparisons:
    * C_v3 vs Phase 1.3 C   (clean 22 folds, macro / sparrow / bulbul F1)
    * B_v3 vs Phase 1.3 B   (clean YouTube only, 11 folds, macro F1)

Outputs:
    results/phase1_clean/paired_bootstrap_results.md
    results/phase1_clean/go_judgment_update.md
    results/phase1_clean/graphs/bootstrap_{C_vs_Cv3_overall,B_vs_Bv3_youtube}.png

Verdict rules (per spec):
    * CI excludes 0 and P(Δ>0) >= 0.95           -> statistical Go
    * CI includes 0 and point Δ >= 0.02          -> practical Go (caveat)
    * CI includes 0 and point Δ <  0.02          -> No-Go
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4a_common.clean_tiers import load_usable_video_ids

PH13_C_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_c"
PH13_B_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_b"
C_V3_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v3"
B_V3_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_b_v3"
YT_METADATA_PATH = REPO_ROOT / "data" / "youtube_metadata.json"

OUT_DIR = REPO_ROOT / "results" / "phase1_clean"
GRAPHS_DIR = OUT_DIR / "graphs"
RESULTS_MD = OUT_DIR / "paired_bootstrap_results.md"
GO_UPDATE_MD = OUT_DIR / "go_judgment_update.md"

N_RESAMPLES = 10_000
SEED = 42
PRACTICAL_DELTA_THRESHOLD = 0.02


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


def _pool_counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    matrix = {
        "sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }
    for r in rows:
        if "error" in r:
            continue
        pred = r.get("final_prediction") or {}
        gt = r.get("ground_truth") or {}
        for cls in ("sparrow", "bulbul"):
            p, g = pred.get(cls), gt.get(cls)
            if p not in (0, 1) or g not in (0, 1):
                continue
            if p == 1 and g == 1:
                matrix[cls]["tp"] += 1
            elif p == 1 and g == 0:
                matrix[cls]["fp"] += 1
            elif p == 0 and g == 1:
                matrix[cls]["fn"] += 1
            else:
                matrix[cls]["tn"] += 1
    return matrix


def _f1_of(m: dict[str, int]) -> float:
    tp, fp, fn = m["tp"], m["fp"], m["fn"]
    if tp == 0:
        return 0.0
    pr = tp / (tp + fp) if (tp + fp) else 0.0
    rc = tp / (tp + fn) if (tp + fn) else 0.0
    if pr + rc == 0:
        return 0.0
    return 2 * pr * rc / (pr + rc)


def macro_f1(rows: list[dict[str, Any]]) -> float:
    m = _pool_counts(rows)
    return (_f1_of(m["sparrow"]) + _f1_of(m["bulbul"])) / 2.0


def class_f1(rows: list[dict[str, Any]], cls: str) -> float:
    return _f1_of(_pool_counts(rows)[cls])


def _align(base: dict[str, dict[str, Any]], new: dict[str, dict[str, Any]], keep_ids: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return rows from base and new in the order of keep_ids, dropping any vid missing on either side."""
    a_list: list[dict[str, Any]] = []
    b_list: list[dict[str, Any]] = []
    for vid in keep_ids:
        if vid in base and vid in new:
            a_list.append(base[vid])
            b_list.append(new[vid])
    return a_list, b_list


def paired_bootstrap(
    base_rows: list[dict[str, Any]],
    new_rows: list[dict[str, Any]],
    metric: Callable[[list[dict[str, Any]]], float],
    n_iter: int = N_RESAMPLES,
    seed: int = SEED,
) -> dict[str, Any]:
    """Return paired bootstrap summary for metric(new) - metric(base)."""
    try:
        import numpy as np
    except ImportError as e:
        raise RuntimeError("numpy is required for paired bootstrap") from e
    assert len(base_rows) == len(new_rows), "paired inputs must have equal length"
    N = len(base_rows)
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(n_iter):
        idx = rng.integers(0, N, size=N)
        sample_base = [base_rows[i] for i in idx]
        sample_new = [new_rows[i] for i in idx]
        deltas.append(metric(sample_new) - metric(sample_base))
    deltas_sorted = sorted(deltas)
    ci_lo = deltas_sorted[int(0.025 * n_iter)]
    ci_hi = deltas_sorted[int(0.975 * n_iter)]
    point = metric(new_rows) - metric(base_rows)
    p_greater = sum(1 for d in deltas if d > 0) / n_iter
    return {
        "n": N,
        "n_iter": n_iter,
        "point_delta": point,
        "base_point": metric(base_rows),
        "new_point": metric(new_rows),
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "p_greater": p_greater,
        "deltas": deltas,
    }


def classify(result: dict[str, Any]) -> str:
    excludes_zero = result["ci_lo"] > 0 or result["ci_hi"] < 0
    p_greater = result["p_greater"]
    if excludes_zero and p_greater >= 0.95:
        return "statistical Go"
    if result["point_delta"] >= PRACTICAL_DELTA_THRESHOLD:
        return "practical Go (CI includes 0)"
    return "No-Go"


def plot_histogram(deltas: list[float], title: str, out_path: Path, ci_lo: float, ci_hi: float, point: float) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"[plot] matplotlib not available, skipping {out_path}", file=sys.stderr)
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(deltas, bins=60, color="#4c72b0", alpha=0.75, edgecolor="white")
    ax.axvline(0.0, color="#555555", linestyle="--", linewidth=1.2, label="Δ = 0")
    ax.axvline(point, color="#dd3333", linewidth=2.0, label=f"point Δ = {point:.3f}")
    ax.axvline(ci_lo, color="#2a9d8f", linestyle=":", linewidth=1.5, label=f"95% CI = [{ci_lo:.3f}, {ci_hi:.3f}]")
    ax.axvline(ci_hi, color="#2a9d8f", linestyle=":", linewidth=1.5)
    ax.set_xlabel("Δ (new - baseline)")
    ax.set_ylabel("count")
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def format_result_row(label: str, result: dict[str, Any]) -> str:
    verdict = classify(result)
    return (
        f"| {label} | {result['n']} | {result['point_delta']:+.3f} "
        f"| [{result['ci_lo']:+.3f}, {result['ci_hi']:+.3f}] "
        f"| {result['p_greater']:.3f} | {verdict} |"
    )


def _fmt_metric(base: float, new: float) -> str:
    return f"{base:.3f} → {new:.3f}"


def main() -> int:
    ensure_utf8_streams()

    # 1) Figure out the clean video id set.
    usable_yt = load_usable_video_ids(YT_METADATA_PATH)

    # 2) Align Phase 1.3 C and C_v3 on the clean 22 folds.
    c_rows = load_folds(PH13_C_BASE)
    cv3_rows = load_folds(C_V3_BASE)
    clean_ids_all = sorted({vid for vid, r in c_rows.items()
                             if r.get("source") == "self" or vid in usable_yt})
    c_base, cv3_new = _align(c_rows, cv3_rows, clean_ids_all)
    print(f"[align] C vs C_v3: {len(c_base)} paired folds")

    # 3) Align Phase 1.3 B and B_v3 on YouTube clean 11 folds.
    b_rows = load_folds(PH13_B_BASE)
    bv3_rows = load_folds(B_V3_BASE)
    clean_yt_ids = sorted({vid for vid, r in b_rows.items()
                            if (r.get("source") or "").startswith("youtube") and vid in usable_yt})
    b_base, bv3_new = _align(b_rows, bv3_rows, clean_yt_ids)
    print(f"[align] B vs B_v3 (YouTube clean): {len(b_base)} paired folds")

    # 4) Run bootstraps.
    print(f"[bootstrap] running paired resampling (n={N_RESAMPLES}, seed={SEED}) ...")
    overall = paired_bootstrap(c_base, cv3_new, macro_f1)
    sparrow_only = paired_bootstrap(c_base, cv3_new, lambda rs: class_f1(rs, "sparrow"))
    bulbul_only = paired_bootstrap(c_base, cv3_new, lambda rs: class_f1(rs, "bulbul"))
    bv3_overall = paired_bootstrap(b_base, bv3_new, macro_f1)

    # 5) Write results markdown.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    md = [
        "# Phase 1.4a paired bootstrap results (Grok round-2 Q2)",
        "",
        "Paired bootstrap resampling of fold indices across the clean subset. ",
        f"Each of the {N_RESAMPLES:,} resamples draws the same fold indices for both ",
        "topologies, recomputes pooled F1 on each side independently, and records ",
        "the difference. ",
        "",
        f"- seed = {SEED}",
        f"- n_iter = {N_RESAMPLES}",
        f"- CI: 95% percentile (2.5, 97.5)",
        f"- Verdict rules: CI excludes 0 AND P(Δ>0) ≥ 0.95 → **statistical Go**; ",
        f"  CI includes 0 AND point Δ ≥ {PRACTICAL_DELTA_THRESHOLD:.2f} → **practical Go (caveat)**; ",
        f"  otherwise → **No-Go**.",
        "",
        "## Point estimates on the paired subsets",
        "",
        "| comparison | n | baseline F1 | new F1 | point Δ |",
        "|---|---:|---:|---:|---:|",
        f"| C vs C_v3 (macro, clean 22)  | {overall['n']} | {overall['base_point']:.3f} | {overall['new_point']:.3f} | {overall['point_delta']:+.3f} |",
        f"| C vs C_v3 (sparrow, clean 22) | {sparrow_only['n']} | {sparrow_only['base_point']:.3f} | {sparrow_only['new_point']:.3f} | {sparrow_only['point_delta']:+.3f} |",
        f"| C vs C_v3 (bulbul, clean 22)  | {bulbul_only['n']} | {bulbul_only['base_point']:.3f} | {bulbul_only['new_point']:.3f} | {bulbul_only['point_delta']:+.3f} |",
        f"| B vs B_v3 (macro, clean YT 11) | {bv3_overall['n']} | {bv3_overall['base_point']:.3f} | {bv3_overall['new_point']:.3f} | {bv3_overall['point_delta']:+.3f} |",
        "",
        "## Paired bootstrap CI and verdict",
        "",
        "| Comparison | n | point Δ | 95% CI (paired) | P(Δ>0) | 判定 |",
        "|---|---:|---:|---|---:|---|",
        format_result_row("C_v3 vs C (macro, clean 22)", overall),
        format_result_row("C_v3 vs C (sparrow F1)", sparrow_only),
        format_result_row("C_v3 vs C (bulbul F1)", bulbul_only),
        format_result_row("B_v3 vs B (macro, clean YouTube 11)", bv3_overall),
        "",
        "## Histograms",
        "",
        "- `graphs/bootstrap_C_vs_Cv3_overall.png`",
        "- `graphs/bootstrap_B_vs_Bv3_youtube.png`",
        "",
        "## Interpretation",
        "",
    ]

    def interp(label: str, r: dict[str, Any]) -> str:
        v = classify(r)
        if v.startswith("statistical"):
            return (
                f"- **{label}** — {v}. The paired Δ distribution excludes 0 at α=0.05 "
                f"(P(Δ>0)={r['p_greater']:.3f}); the improvement is statistically "
                "supported on this subset."
            )
        if v.startswith("practical"):
            return (
                f"- **{label}** — {v}. Point Δ ≥ 0.02 so the improvement is "
                f"practically relevant, but the 95% CI [{r['ci_lo']:+.3f}, "
                f"{r['ci_hi']:+.3f}] crosses 0 so the delta is not statistically "
                "significant on this n."
            )
        return (
            f"- **{label}** — {v}. Point Δ {r['point_delta']:+.3f} with 95% CI "
            f"[{r['ci_lo']:+.3f}, {r['ci_hi']:+.3f}]. Neither gate is cleared; do "
            "not claim improvement."
        )

    md.append(interp("C_v3 vs C (macro)", overall))
    md.append(interp("C_v3 vs C (sparrow)", sparrow_only))
    md.append(interp("C_v3 vs C (bulbul)", bulbul_only))
    md.append(interp("B_v3 vs B (YouTube)", bv3_overall))
    md.append("")

    md.extend([
        "## Caveats",
        "",
        "- Paired bootstrap narrows the CI compared to the unpaired version used in ",
        "  `reevaluation_summary.md`, but `n=22` (or `n=11`) is still small; the ",
        "  interval endpoints themselves have non-negligible Monte-Carlo variance.",
        "- Tier B clips contribute the pre-trim fold JSON; the first 30 s of their ",
        "  content is still included in the prompt signal.",
        "- `mixed` (n=2) is excluded from F1 splits; the paired Δ only reflects the ",
        "  20 clean sparrow + bulbul folds for each sparrow/bulbul split view.",
        "",
    ])

    RESULTS_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"[write] {RESULTS_MD}")

    # 6) Histogram plots.
    plot_histogram(
        overall["deltas"],
        f"C_v3 - C  (macro F1, paired, n={overall['n']}, iter={N_RESAMPLES})",
        GRAPHS_DIR / "bootstrap_C_vs_Cv3_overall.png",
        overall["ci_lo"], overall["ci_hi"], overall["point_delta"],
    )
    plot_histogram(
        bv3_overall["deltas"],
        f"B_v3 - B  (YouTube clean macro F1, paired, n={bv3_overall['n']}, iter={N_RESAMPLES})",
        GRAPHS_DIR / "bootstrap_B_vs_Bv3_youtube.png",
        bv3_overall["ci_lo"], bv3_overall["ci_hi"], bv3_overall["point_delta"],
    )

    # 7) go_judgment_update.md
    go_lines = [
        "# Phase 1.4a Go judgment update (post paired bootstrap)",
        "",
        "This finalises Phase 1.4a's Go/No-Go calls by combining the clean-dataset ",
        "re-evaluation (`reevaluation_summary.md`) with the paired-bootstrap results ",
        "in `paired_bootstrap_results.md`.",
        "",
        "| objective | clean point | clean CI (paired) | P(Δ>0) | final verdict |",
        "|---|---:|---|---:|---|",
    ]

    def row(label: str, base: str, new: str, r: dict[str, Any]) -> str:
        v = classify(r)
        return (
            f"| {label} ({base} → {new}) | {r['point_delta']:+.3f} "
            f"| [{r['ci_lo']:+.3f}, {r['ci_hi']:+.3f}] | {r['p_greater']:.3f} | {v} |"
        )

    go_lines.append(row("Obj D: C_v3 vs C (macro)", "0.823", "0.869", overall))
    go_lines.append(row("bbox v3 gate: B_v3 vs B (YouTube)", "0.500", "0.721", bv3_overall))
    # C_v2 (Obj B) and C_v4 are not re-bootstrapped here because the clean point
    # estimate already falls below every gate; adding a paired CI cannot change
    # a No-Go verdict derived from the point estimate.
    go_lines.extend([
        "",
        "## Unchanged verdicts from the 42-fold run (no bootstrap needed)",
        "",
        "- **Obj B (C_v2 macro F1 ≥ 0.86)** — clean point 0.791 below the gate; **No-Go**.",
        "- **bbox v3 + fusion (C_v4 macro F1 ≥ Phase 1.3 C + 0.02)** — clean point 0.635 ",
        "  vs baseline 0.823 (Δ = −0.188); **No-Go** (regression, not improvement).",
        "",
        "## Summary of Phase 1.4a Go state",
        "",
        "| intervention | final verdict | notes |",
        "|---|---|---|",
        f"| Obj B (frame_extractor) | No-Go | point 0.791 < 0.86 on clean data |",
        f"| Obj D (temporal_sync) | {classify(overall)} "
        f"| paired Δ = {overall['point_delta']:+.3f} "
        f"[{overall['ci_lo']:+.3f}, {overall['ci_hi']:+.3f}], P(Δ>0)={overall['p_greater']:.3f} |",
        f"| bbox v3 on B (Grok Q2) | {classify(bv3_overall)} "
        f"| paired Δ = {bv3_overall['point_delta']:+.3f} "
        f"[{bv3_overall['ci_lo']:+.3f}, {bv3_overall['ci_hi']:+.3f}], "
        f"P(Δ>0)={bv3_overall['p_greater']:.3f} on 11 clean YouTube folds |",
        f"| bbox v3 on C (C_v4) | No-Go | Δ = −0.188 on clean data (regression) |",
        "",
        "## Recommendation",
        "",
    ])

    overall_v = classify(overall)
    bv3_v = classify(bv3_overall)
    if overall_v.startswith("statistical") or bv3_v.startswith("statistical"):
        go_lines.append(
            "At least one intervention shows a statistically-significant paired Δ; ",
            )
        go_lines.append(
            "Phase 1.4a can exit with that result as the headline improvement. "
        )
    elif overall_v.startswith("practical") or bv3_v.startswith("practical"):
        go_lines.append(
            "Point estimates clear the practical-Go threshold but the paired CI "
            "includes 0; the Go should be reported with a statistical caveat. "
            "Expanding the clean set or adding paired baselines on additional "
            "topologies is the cheapest way to harden the claim."
        )
    else:
        go_lines.append(
            "Neither intervention clears the paired statistical gate. Treat Phase 1.4a "
            "as yielding process findings (sync_rate correlation, bbox-prompt-paradigm "
            "trade-off) rather than a topology-level headline improvement."
        )
    go_lines.append("")

    GO_UPDATE_MD.write_text("\n".join(go_lines), encoding="utf-8")
    print(f"[write] {GO_UPDATE_MD}")

    # 8) Console summary
    print()
    print("=== Paired bootstrap verdicts ===")
    for label, r in (("C_v3 vs C (macro)", overall),
                      ("C_v3 vs C (sparrow)", sparrow_only),
                      ("C_v3 vs C (bulbul)", bulbul_only),
                      ("B_v3 vs B (YouTube macro)", bv3_overall)):
        print(f"  {label:35s} Δ={r['point_delta']:+.3f} "
              f"CI=[{r['ci_lo']:+.3f}, {r['ci_hi']:+.3f}] "
              f"P(>0)={r['p_greater']:.3f} -> {classify(r)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
