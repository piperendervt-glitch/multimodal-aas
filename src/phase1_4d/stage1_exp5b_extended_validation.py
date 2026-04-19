"""Phase 1.4d Stage 1 Exp 5b extended validation.

Stage 2 Exp 2 extended (commit d2fc14e) proved that what looked like a
positive effect at n=5 (d=+0.447) was a small-sample artifact — the
effect collapsed to d=−0.115 when the trial count climbed to 20 and
fold-level bootstrap power to n_pooled=220.

Stage 1 Exp 5b reports the *same* trial-level Cohen's d = +0.447 on
n=5 but on a structurally different pipeline (ensemble voting over
Topology A + B_v3 + C_v3, label-specific weights, no LLM rewrite).
This script applies the exact same n-expansion methodology to Exp 5b
to answer a single question: is the +0.447 here a true positive (the
ensemble voting architecture transfers sdnd-proof in a way the single-
LLM substrate did not) or the same artifact?

No new LLM inference is needed. Every additional trial differs only in
shuffle order and weight trajectory; the underlying topology
predictions are loaded from committed fold JSONs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4d.stage1_target_a_improved_topology_label_specific import IMPROVED_BASES
from phase1_4d.stage1_target_a_label_specific import run_trial
from phase1_4d.stage1_target_a_sdnd_proof import (
    WARMUP_COUNT,
    build_fold_records,
    ensure_utf8_streams,
    paired_statistics,
)

EXP5B_TRIALS_PATH = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage1_target_a_improved_topology_label_specific" / "trials_summary.json"
)
EXP5B_STATS_PATH = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage1_target_a_improved_topology_label_specific" / "statistical_analysis.json"
)
STAGE2_EXP2_EXTENDED_STATS = (
    REPO_ROOT / "results" / "phase1_4d" / "stage2_target_b_no_score_extended"
    / "bootstrap_analysis_extended.json"
)

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage1_exp5b_extended"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary_extended.json"
STATS_PATH = OUT_DIR / "bootstrap_analysis.json"

EXISTING_SEEDS = [42, 137, 256, 512, 1024]
NEW_SEEDS = [
    2048, 4096, 8192, 16384, 32768,
    65536, 131072, 262144, 524288, 1048576,
    2097152, 4194304, 8388608, 16777216, 33554432,
]
ALL_SEEDS = EXISTING_SEEDS + NEW_SEEDS

N_BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 42
LABELS = ("sparrow", "bulbul")
TOPOLOGIES = ("A", "B", "C")


def load_existing_trials() -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    data = json.loads(EXP5B_TRIALS_PATH.read_text(encoding="utf-8"))
    stats = None
    if EXP5B_STATS_PATH.is_file():
        stats = json.loads(EXP5B_STATS_PATH.read_text(encoding="utf-8"))
    return data.get("trials", []), stats


# ---------------------------------------------------------------------------
# Paired fold bootstrap (shared shape with Stage 2 analyses)
# ---------------------------------------------------------------------------

def extract_eval_records(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pooled: list[dict[str, Any]] = []
    for tr in trials:
        fx_by_step = {f["step"]: f for f in tr["experiment_A"]["per_fold"]}
        ad_by_step = {f["step"]: f for f in tr["experiment_B"]["per_fold"]}
        for step in sorted(fx_by_step.keys()):
            if step < WARMUP_COUNT:
                continue
            f_fold = fx_by_step[step]
            a_fold = ad_by_step[step]
            pooled.append({
                "trial_seed": tr["seed"],
                "step": int(step),
                "video_id": f_fold["video_id"],
                "pred_fixed": f_fold["pred"],
                "pred_adaptive": a_fold["pred"],
                "gt": f_fold["gt"],
            })
    return pooled


def _f1(tp: int, fp: int, fn: int) -> float:
    if tp == 0:
        return 0.0
    pr = tp / (tp + fp) if (tp + fp) else 0.0
    rc = tp / (tp + fn) if (tp + fn) else 0.0
    if pr + rc == 0:
        return 0.0
    return 2 * pr * rc / (pr + rc)


def macro_f1_pooled(pairs: list[tuple[dict[str, int], dict[str, int]]]) -> float:
    m = {
        "sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }
    for pred, gt in pairs:
        for cls in ("sparrow", "bulbul"):
            p, g = pred[cls], gt[cls]
            if p == 1 and g == 1: m[cls]["tp"] += 1
            elif p == 1 and g == 0: m[cls]["fp"] += 1
            elif p == 0 and g == 1: m[cls]["fn"] += 1
            else: m[cls]["tn"] += 1
    return (
        _f1(m["sparrow"]["tp"], m["sparrow"]["fp"], m["sparrow"]["fn"])
        + _f1(m["bulbul"]["tp"],  m["bulbul"]["fp"],  m["bulbul"]["fn"])
    ) / 2.0


def paired_fold_bootstrap(
    pooled: list[dict[str, Any]],
    n_bootstrap: int = N_BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    n = len(pooled)
    deltas = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        fx = [(pooled[j]["pred_fixed"],    pooled[j]["gt"]) for j in idx]
        ad = [(pooled[j]["pred_adaptive"], pooled[j]["gt"]) for j in idx]
        deltas[i] = macro_f1_pooled(ad) - macro_f1_pooled(fx)

    mean_d = float(np.mean(deltas))
    std_d = float(np.std(deltas, ddof=1)) if n_bootstrap > 1 else 0.0
    ci_lo = float(np.percentile(deltas, 2.5))
    ci_hi = float(np.percentile(deltas, 97.5))
    p_pos = float(np.mean(deltas > 0))
    p_neg = float(np.mean(deltas < 0))
    p_two = max(2.0 * min(p_pos, p_neg), 1.0 / n_bootstrap)
    d = float(mean_d / std_d) if std_d > 0 else 0.0
    direction = "positive" if mean_d > 0 else "negative" if mean_d < 0 else "zero"

    fx_obs = macro_f1_pooled([(r["pred_fixed"],    r["gt"]) for r in pooled])
    ad_obs = macro_f1_pooled([(r["pred_adaptive"], r["gt"]) for r in pooled])
    point_delta = ad_obs - fx_obs

    c_p = bool(p_two < 0.05)
    c_d = bool(abs(d) >= 0.8)
    c_ci = bool(ci_lo > 0 or ci_hi < 0)

    counts, edges = np.histogram(deltas, bins=60)
    return {
        "n_pooled_folds": n,
        "n_bootstrap": n_bootstrap,
        "seed": seed,
        "observed_fixed_macro_f1":    fx_obs,
        "observed_adaptive_macro_f1": ad_obs,
        "observed_delta":             point_delta,
        "bootstrap_mean_delta":       mean_d,
        "bootstrap_std_delta":        std_d,
        "ci_95":                      [ci_lo, ci_hi],
        "p_value_twosided":           p_two,
        "cohens_d_paired":            d,
        "direction":                  direction,
        "criteria": {
            "p_value_pass_at_0.05":     c_p,
            "abs_cohens_d_pass_at_0.8": c_d,
            "ci_excludes_zero":         c_ci,
        },
        "overall_go_positive": bool(c_p and c_d and c_ci and direction == "positive"),
        "overall_go_negative": bool(c_p and c_d and c_ci and direction == "negative"),
        "deltas_histogram": {
            "bin_edges": [float(x) for x in edges],
            "counts":    [int(c) for c in counts],
        },
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _verdict(boot: dict[str, Any]) -> str:
    if boot["overall_go_positive"]:
        return "Go (positive)"
    if boot["overall_go_negative"]:
        return "Go (negative)"
    return "No-Go"


def load_stage2_exp2_extended_stats() -> dict[str, Any] | None:
    if not STAGE2_EXP2_EXTENDED_STATS.is_file():
        return None
    data = json.loads(STAGE2_EXP2_EXTENDED_STATS.read_text(encoding="utf-8"))
    return data


def render_summary(
    trials_all: list[dict[str, Any]],
    trial_stats_n20: dict[str, Any],
    boot_n220: dict[str, Any],
    exp5b_trial_stats: dict[str, Any] | None,
    boot_n55: dict[str, Any] | None,
    stage2_extended: dict[str, Any] | None,
) -> str:
    lines = [
        "# Phase 1.4d Stage 1 Exp 5b extended validation",
        "",
        "**Question**: is Exp 5b's n=5 Cohen's d = +0.447 a true positive (ensemble "
        "voting over the Phase 1.4a improved topology transfers sdnd-proof) or the "
        "same small-sample artifact that Stage 2 Exp 2 extended diagnosed?",
        "",
        "Methodology mirrors Stage 2 Exp 2 extended (commit d2fc14e): add 15 new seeds "
        "(powers of two after 1024), re-run Adaptive + Fixed using the same recipe "
        "(label-specific 6-weight update, sdnd-proof ×0.7 penalty, label-independent "
        "credit assignment, 0.5 threshold). No new LLM inference is required — every "
        "trial's predictions come from the committed Topology A / B_v3 / C_v3 fold "
        "JSONs and differ only in shuffle order and learned weights.",
        "",
        f"Seeds: {EXISTING_SEEDS} (existing) + {NEW_SEEDS} (new).",
        f"Pool size for bootstrap: 20 trials × {22 - WARMUP_COUNT} second-half folds "
        f"= {20 * (22 - WARMUP_COUNT)} paired (Fixed, Adaptive) prediction pairs.",
        "",
    ]

    # Per-trial macro F1
    lines.append("## Per-trial macro F1 (all 20 trials)")
    lines.append("")
    lines.append("| Trial | Seed | origin | Fixed | Adaptive | Δ |")
    lines.append("|---|---:|---|---:|---:|---:|")
    for i, tr in enumerate(trials_all, start=1):
        origin = "existing" if tr["seed"] in EXISTING_SEEDS else "new"
        fa = tr["experiment_A"]["macro_f1"]
        fb = tr["experiment_B"]["macro_f1"]
        lines.append(
            f"| {i} | {tr['seed']} | {origin} | {fa:.3f} | {fb:.3f} "
            f"| {fb - fa:+.3f} |"
        )
    lines.append("")

    # Δ sign distribution
    pos = neg = zero = 0
    for tr in trials_all:
        d_val = tr["experiment_B"]["macro_f1"] - tr["experiment_A"]["macro_f1"]
        if d_val > 1e-9: pos += 1
        elif d_val < -1e-9: neg += 1
        else: zero += 1
    lines.append("## Δ sign distribution across 20 trials")
    lines.append("")
    lines.append("| direction | count |")
    lines.append("|---|---:|")
    lines.append(f"| Δ > 0 | {pos} |")
    lines.append(f"| Δ = 0 | {zero} |")
    lines.append(f"| Δ < 0 | {neg} |")
    lines.append("")
    lines.append(
        "Stage 2 Exp 2 extended reference: 2 positive / 12 zero / 6 negative. "
        f"Exp 5b extended: **{pos} positive / {zero} zero / {neg} negative**."
    )
    lines.append("")

    # Statistical comparison across n
    lines.append("## Statistical methods compared")
    lines.append("")
    lines.append(
        "| method | n | point Δ | Cohen's d | p | 95% CI | verdict |"
    )
    lines.append("|---|---:|---:|---:|---:|---|---|")
    if exp5b_trial_stats:
        d_orig = exp5b_trial_stats.get("cohens_d")
        d_orig_str = f"{d_orig:+.3f}" if d_orig is not None else "n/a"
        v_orig = "Go" if exp5b_trial_stats.get("go_judgment", {}).get("overall_go") else "No-Go"
        lines.append(
            f"| trial t-test (Exp 5b original) | 5 "
            f"| {exp5b_trial_stats['mean_diff']:+.3f} | {d_orig_str} "
            f"| {exp5b_trial_stats['paired_t_test']['p_value']:.4f} "
            f"| [{exp5b_trial_stats['ci_95'][0]:+.3f}, {exp5b_trial_stats['ci_95'][1]:+.3f}] "
            f"| {v_orig} |"
        )
    if boot_n55:
        v_n55 = _verdict(boot_n55)
        lines.append(
            f"| paired fold bootstrap (n=55) | {boot_n55['n_pooled_folds']} "
            f"| {boot_n55['observed_delta']:+.3f} "
            f"| {boot_n55['cohens_d_paired']:+.3f} "
            f"| {boot_n55['p_value_twosided']:.4f} "
            f"| [{boot_n55['ci_95'][0]:+.3f}, {boot_n55['ci_95'][1]:+.3f}] | {v_n55} |"
        )
    d20 = trial_stats_n20.get("cohens_d")
    d20_str = f"{d20:+.3f}" if d20 is not None else "n/a"
    v20 = "Go" if trial_stats_n20.get("go_judgment", {}).get("overall_go") else "No-Go"
    lines.append(
        f"| **trial t-test (extended)** | **20** | {trial_stats_n20['mean_diff']:+.3f} "
        f"| **{d20_str}** | **{trial_stats_n20['paired_t_test']['p_value']:.4f}** "
        f"| [{trial_stats_n20['ci_95'][0]:+.3f}, {trial_stats_n20['ci_95'][1]:+.3f}] "
        f"| **{v20}** |"
    )
    v220 = _verdict(boot_n220)
    lines.append(
        f"| **paired fold bootstrap (extended)** | **{boot_n220['n_pooled_folds']}** "
        f"| {boot_n220['observed_delta']:+.3f} "
        f"| **{boot_n220['cohens_d_paired']:+.3f}** "
        f"| **{boot_n220['p_value_twosided']:.4f}** "
        f"| [{boot_n220['ci_95'][0]:+.3f}, {boot_n220['ci_95'][1]:+.3f}] "
        f"| **{v220}** |"
    )
    lines.append("")

    # Go criteria breakdown
    c = boot_n220["criteria"]
    lines.append("## Bootstrap Go criteria (extended n=220)")
    lines.append("")
    lines.append("| Criterion | Value | Pass |")
    lines.append("|---|---:|:-:|")
    lines.append(
        f"| p-value < 0.05 | {boot_n220['p_value_twosided']:.4f} "
        f"| {'Y' if c['p_value_pass_at_0.05'] else 'N'} |"
    )
    lines.append(
        f"| |Cohen's d| ≥ 0.8 | {boot_n220['cohens_d_paired']:+.3f} "
        f"| {'Y' if c['abs_cohens_d_pass_at_0.8'] else 'N'} |"
    )
    lines.append(
        f"| 95% CI excludes 0 | [{boot_n220['ci_95'][0]:+.3f}, {boot_n220['ci_95'][1]:+.3f}] "
        f"| {'Y' if c['ci_excludes_zero'] else 'N'} |"
    )
    lines.append(
        f"| direction | {boot_n220['direction']} | — |"
    )
    lines.append(
        f"| **Overall** | — | **{_verdict(boot_n220)}** |"
    )
    lines.append("")

    # Cross-experiment comparison
    if stage2_extended:
        s2_boot = stage2_extended.get("bootstrap_n220")
        lines.append("## Side-by-side with Stage 2 Exp 2 extended (same methodology)")
        lines.append("")
        lines.append(
            "| experiment | architecture | n=5 d (trial) | n=55 d (boot) | n=220 d (boot) | interpretation |"
        )
        lines.append("|---|---|---:|---:|---:|---|")
        lines.append(
            "| Stage 2 Exp 2 extended | single-LLM + info filter | +0.447 | +0.978 "
            f"| {s2_boot['cohens_d_paired']:+.3f} | small-sample artifact confirmed |"
        )
        # For Stage 1 Exp 5b, we want to show d at n=55 and n=220
        lines.append(
            f"| **Stage 1 Exp 5b extended** | **ensemble voting (A + B_v3 + C_v3)** "
            f"| +0.447 "
            f"| {boot_n55['cohens_d_paired']:+.3f} "
            f"| **{boot_n220['cohens_d_paired']:+.3f}** | "
            + ("small-sample artifact (same pattern as Stage 2)"
               if boot_n220["direction"] != "positive" or boot_n220["cohens_d_paired"] < 0.3
               else "possible true-positive (different trajectory)")
            + " |"
        )
        lines.append("")

    # Final weights (n=20 average)
    sums: dict[str, dict[str, float]] = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    for tr in trials_all:
        w = tr["experiment_B"]["final_weights"]
        for t in TOPOLOGIES:
            for cls in LABELS:
                sums[t][cls] += w[t][cls]
    n_tr = len(trials_all) or 1
    lines.append("## Adaptive final weights (mean across 20 trials)")
    lines.append("")
    lines.append(
        "| weight | Exp 5b (n=5) | Exp 5b extended (n=20) |"
    )
    lines.append("|---|---:|---:|")
    # Known means from Exp 5b summary (n=5)
    exp5b_n5 = {
        "A.sparrow":   0.341, "A.bulbul":   0.455,
        "B_v3.sparrow": 0.362, "B_v3.bulbul": 0.363,
        "C_v3.sparrow": 0.637, "C_v3.bulbul": 0.651,
    }
    display_map = [
        ("A.sparrow",   "A", "sparrow"),
        ("A.bulbul",    "A", "bulbul"),
        ("B_v3.sparrow","B", "sparrow"),
        ("B_v3.bulbul", "B", "bulbul"),
        ("C_v3.sparrow","C", "sparrow"),
        ("C_v3.bulbul", "C", "bulbul"),
    ]
    for label, t, cls in display_map:
        new = sums[t][cls] / n_tr
        lines.append(f"| {label} | {exp5b_n5[label]:.3f} | {new:.3f} |")
    lines.append("")

    # Headline verdict
    lines.append("## Verdict")
    lines.append("")
    if boot_n220["overall_go_positive"]:
        lines.append(
            "**Case B — possible true positive.** The extended bootstrap clears the "
            "full sdnd-proof 3-criterion gate in the positive direction, i.e. "
            "ensemble voting across A + B_v3 + C_v3 does transfer the sdnd-proof "
            "learning rule in a way the single-LLM substrate did not. Target C "
            "per-label routing is a defensible next step."
        )
    elif boot_n220["cohens_d_paired"] >= 0.3 and boot_n220["direction"] == "positive":
        lines.append(
            "**Case C — weak true positive.** The effect shrinks at extended n but "
            "keeps a positive direction and non-trivial Cohen's d. The Go gate is "
            "not cleared; the question is whether the residual signal is worth the "
            "Target C effort."
        )
    else:
        lines.append(
            "**Case A — small-sample artifact.** The n=5 d=+0.447 does not survive "
            "the 20-trial / 220-fold expansion. Stage 1 Exp 5b follows the same "
            "trajectory as Stage 2 Exp 2 extended (apparent positive at small n, "
            "collapse near zero at n=220). Ensemble voting does NOT transfer "
            "sdnd-proof in the way the n=5 read suggested."
        )
    lines.append("")

    # Paper 1 implications block
    lines.append("## Paper 1 implications")
    lines.append("")
    if boot_n220["overall_go_positive"]:
        lines.append(
            "- Paper 1 can report a mixed-result story: **prompt-injection harms "
            "(Exp 1 negative Go)** + **ensemble-voting transfers weakly (Exp 5b "
            "extended positive Go)** + **single-LLM filter fails (Exp 2 extended "
            "No-Go)**. Target C still warranted."
        )
    elif boot_n220["cohens_d_paired"] >= 0.3 and boot_n220["direction"] == "positive":
        lines.append(
            "- Paper 1 can argue that Exp 5b extended shows **a consistent but "
            "underpowered positive signal** (d around +0.3–0.5 but CI includes 0 "
            "at n=220). Recommended next step: decide whether to scale further "
            "(n=500+) or accept practical-Go caveat."
        )
    else:
        lines.append(
            "- Paper 1 must honestly report that the only Go-class result in "
            "Phase 1.4d is the **negative Go of Exp 1** (prompt injection harms "
            "accuracy). The ensemble-voting 'positive' at n=5 was small-sample "
            "noise. Target C should **not** be run on this substrate; focus on "
            "the negative-result story and deeper diagnosis of why transfer "
            "fails."
        )
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary_extended.json`")
    lines.append("- `bootstrap_analysis.json`")
    lines.append("- `graphs/delta_distribution.png`")
    lines.append("- `graphs/cohens_d_comparison.png`")
    lines.append("- `graphs/ci_across_n.png`")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_delta_distribution(boot_n220: dict[str, Any], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    edges = np.array(boot_n220["deltas_histogram"]["bin_edges"])
    counts = np.array(boot_n220["deltas_histogram"]["counts"])
    centers = 0.5 * (edges[:-1] + edges[1:])
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(centers, counts, width=(edges[1] - edges[0]), color="#2a9d8f", alpha=0.75)
    ax.axvline(0.0, color="#555", linestyle="--", linewidth=0.8)
    ax.axvline(boot_n220["observed_delta"], color="#111", linewidth=1.6,
               label=f"observed Δ = {boot_n220['observed_delta']:+.3f}")
    ax.axvline(boot_n220["ci_95"][0], color="#c44e52", linestyle=":", linewidth=1.3,
               label=(f"95% CI = [{boot_n220['ci_95'][0]:+.3f}, "
                      f"{boot_n220['ci_95'][1]:+.3f}]"))
    ax.axvline(boot_n220["ci_95"][1], color="#c44e52", linestyle=":", linewidth=1.3)
    ax.set_xlabel("Δ macro F1 (Adaptive − Fixed)")
    ax.set_ylabel("bootstrap count")
    ax.set_title(f"Exp 5b extended — bootstrap Δ distribution (n={boot_n220['n_pooled_folds']})")
    ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)


def plot_cohens_d_comparison(
    exp5b_points: dict[str, float],
    stage2_points: dict[str, float],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    labels = ["trial n=5", "bootstrap n=55", "trial n=20", "bootstrap n=220"]
    xs = np.arange(len(labels))
    exp5b_vals = [
        exp5b_points.get("trial_n5"),
        exp5b_points.get("boot_n55"),
        exp5b_points.get("trial_n20"),
        exp5b_points.get("boot_n220"),
    ]
    stage2_vals = [
        stage2_points.get("trial_n5"),
        stage2_points.get("boot_n55"),
        stage2_points.get("trial_n20"),
        stage2_points.get("boot_n220"),
    ]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(xs, exp5b_vals, marker="o", linewidth=2.0, color="#2a9d8f",
            label="Stage 1 Exp 5b (ensemble voting)")
    ax.plot(xs, stage2_vals, marker="s", linewidth=2.0, color="#c44e52",
            label="Stage 2 Exp 2 extended (single-LLM)")
    for x, v in zip(xs, exp5b_vals):
        if v is not None:
            ax.annotate(f"{v:+.3f}", (x, v), textcoords="offset points",
                        xytext=(0, 10), ha="center", fontsize=8, color="#2a9d8f")
    for x, v in zip(xs, stage2_vals):
        if v is not None:
            ax.annotate(f"{v:+.3f}", (x, v), textcoords="offset points",
                        xytext=(0, -14), ha="center", fontsize=8, color="#c44e52")
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.axhline(0.8, color="#264653", linestyle=":", linewidth=1.0,
               label="Go threshold (|d|=0.8)")
    ax.set_xticks(xs); ax.set_xticklabels(labels)
    ax.set_ylabel("Cohen's d")
    ax.set_title("Cohen's d — Stage 1 Exp 5b vs Stage 2 Exp 2 extended")
    ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="best")
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)


def plot_ci_across_n(
    exp5b_points: dict[str, tuple[float, list[float]]],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    labels_and_keys = [
        ("trial n=5",       "trial_n5"),
        ("bootstrap n=55",  "boot_n55"),
        ("trial n=20",      "trial_n20"),
        ("bootstrap n=220", "boot_n220"),
    ]
    xs = np.arange(len(labels_and_keys))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, (label, key) in enumerate(labels_and_keys):
        pt = exp5b_points.get(key)
        if pt is None:
            continue
        mean_d, ci = pt
        ax.errorbar([i], [mean_d], yerr=[[mean_d - ci[0]], [ci[1] - mean_d]],
                    fmt="o", color="#264653", capsize=6, markersize=8)
        ax.annotate(f"[{ci[0]:+.3f}, {ci[1]:+.3f}]", (i, ci[1]),
                    textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=8)
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xticks(xs); ax.set_xticklabels([l for l, _ in labels_and_keys], rotation=15)
    ax.set_ylabel("mean Δ macro F1 with 95% CI")
    ax.set_title("Exp 5b extended — CI narrowing / drift across n")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _bootstrap_subset(trials_subset: list[dict[str, Any]]) -> dict[str, Any]:
    pooled = extract_eval_records(trials_subset)
    return paired_fold_bootstrap(pooled)


def main() -> int:
    ensure_utf8_streams()

    existing_trials, exp5b_trial_stats = load_existing_trials()
    existing_by_seed = {tr["seed"]: tr for tr in existing_trials}
    print(f"[load] existing Exp 5b trials: {len(existing_trials)}")

    records = build_fold_records(topology_bases=IMPROVED_BASES)
    print(f"[load] clean fold records: {len(records)}")

    trials_all: list[dict[str, Any]] = []
    for seed in ALL_SEEDS:
        if seed in existing_by_seed:
            trials_all.append(existing_by_seed[seed])
            print(f"[reuse] seed={seed}")
        else:
            tr = run_trial(records, seed)
            trials_all.append(tr)
            fa = tr["experiment_A"]["macro_f1"]
            fb = tr["experiment_B"]["macro_f1"]
            print(f"[new  ] seed={seed}: Fixed={fa:.3f} Adaptive={fb:.3f} "
                  f"Δ={fb - fa:+.3f}")

    # Trial t-test at n=20
    trial_stats_n20 = paired_statistics(
        [tr["experiment_A"]["macro_f1"] for tr in trials_all],
        [tr["experiment_B"]["macro_f1"] for tr in trials_all],
    )

    # Bootstrap at n=55 (first 5 seeds — equivalent to Stage 2 bootstrap methodology)
    n5_trials = [tr for tr in trials_all if tr["seed"] in EXISTING_SEEDS]
    boot_n55 = _bootstrap_subset(n5_trials)
    # Bootstrap at n=220 (all 20 seeds)
    boot_n220 = _bootstrap_subset(trials_all)
    print(f"[bootstrap n=55]  d={boot_n55['cohens_d_paired']:+.3f}, "
          f"p={boot_n55['p_value_twosided']:.4f}, "
          f"CI=[{boot_n55['ci_95'][0]:+.3f}, {boot_n55['ci_95'][1]:+.3f}]")
    print(f"[bootstrap n=220] d={boot_n220['cohens_d_paired']:+.3f}, "
          f"p={boot_n220['p_value_twosided']:.4f}, "
          f"CI=[{boot_n220['ci_95'][0]:+.3f}, {boot_n220['ci_95'][1]:+.3f}] "
          f"({boot_n220['direction']})")

    stage2_extended = load_stage2_exp2_extended_stats()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    TRIALS_PATH.write_text(
        json.dumps({
            "existing_seeds": EXISTING_SEEDS, "new_seeds": NEW_SEEDS,
            "all_seeds": ALL_SEEDS, "warmup_count": WARMUP_COUNT,
            "trials_all": trials_all,
            "trial_stats_n20": trial_stats_n20,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps({
            "trial_stats_n20": trial_stats_n20,
            "bootstrap_n55":   boot_n55,
            "bootstrap_n220":  boot_n220,
            "reference": {
                "exp5b_trial_stats_n5": exp5b_trial_stats,
                "stage2_exp2_extended": stage2_extended,
            },
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    SUMMARY_PATH.write_text(
        render_summary(trials_all, trial_stats_n20, boot_n220,
                       exp5b_trial_stats, boot_n55, stage2_extended),
        encoding="utf-8",
    )

    # Plots: Δ distribution + cross-exp comparison + CI across n
    plot_delta_distribution(boot_n220, GRAPHS_DIR / "delta_distribution.png")
    exp5b_cohens = {
        "trial_n5":  (exp5b_trial_stats or {}).get("cohens_d"),
        "boot_n55":  boot_n55["cohens_d_paired"],
        "trial_n20": trial_stats_n20.get("cohens_d"),
        "boot_n220": boot_n220["cohens_d_paired"],
    }
    s2 = (stage2_extended or {})
    s2_boot = s2.get("bootstrap_n220") or {}
    s2_ref = (s2.get("reference") or {})
    s2_trial_stats_n5 = (s2_ref.get("trial_stats_n5") or {}).get("cohens_d")
    s2_boot_n55 = (s2_ref.get("bootstrap_n55") or {}).get("cohens_d_paired")
    s2_trial_stats_n20 = (s2.get("trial_stats_n20") or {}).get("cohens_d")
    stage2_cohens = {
        "trial_n5":  s2_trial_stats_n5,
        "boot_n55":  s2_boot_n55,
        "trial_n20": s2_trial_stats_n20,
        "boot_n220": s2_boot.get("cohens_d_paired"),
    }
    plot_cohens_d_comparison(exp5b_cohens, stage2_cohens, GRAPHS_DIR / "cohens_d_comparison.png")
    exp5b_ci = {
        "trial_n5":  ((exp5b_trial_stats or {}).get("mean_diff"),
                       (exp5b_trial_stats or {}).get("ci_95"))
                       if exp5b_trial_stats else None,
        "boot_n55":  (boot_n55["bootstrap_mean_delta"], boot_n55["ci_95"]),
        "trial_n20": (trial_stats_n20["mean_diff"], trial_stats_n20["ci_95"]),
        "boot_n220": (boot_n220["bootstrap_mean_delta"], boot_n220["ci_95"]),
    }
    plot_ci_across_n(exp5b_ci, GRAPHS_DIR / "ci_across_n.png")

    print()
    print("=== Phase 1.4d Stage 1 Exp 5b extended validation ===")
    print(f"n=20 trial Δ={trial_stats_n20['mean_diff']:+.3f}, "
          f"d={trial_stats_n20.get('cohens_d')}, "
          f"CI=[{trial_stats_n20['ci_95'][0]:+.3f}, {trial_stats_n20['ci_95'][1]:+.3f}]")
    print(f"n=220 bootstrap Δ={boot_n220['observed_delta']:+.3f}, "
          f"d={boot_n220['cohens_d_paired']:+.3f}, "
          f"p={boot_n220['p_value_twosided']:.4f}, "
          f"CI=[{boot_n220['ci_95'][0]:+.3f}, {boot_n220['ci_95'][1]:+.3f}]")
    print(f"Overall verdict: {_verdict(boot_n220)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
