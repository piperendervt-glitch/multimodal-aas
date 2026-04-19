"""Phase 1.4d Stage 2 Experiment 2 extended — n=220 paired fold bootstrap.

Exp 2 (commit 2dd8756) cleared Cohen's d ≥ 0.8 and p < 0.05 under the
55-fold paired bootstrap (commit 0d0903c) but its 95% CI lower bound
landed at exactly +0.000 — the Statistical Go gate was missed by a
hairline. This extension keeps every Exp 2 setting identical and only
enlarges the trial set from 5 seeds to 20. The new seeds follow the
sdnd-proof style (powers of two after 42, 137, 256, 512, 1024) so the
full list is:

    42, 137, 256, 512, 1024,
    2048, 4096, 8192, 16384, 32768,
    65536, 131072, 262144, 524288, 1048576,
    2097152, 4194304, 8388608, 16777216, 33554432

The five original seeds' trials are reused unchanged (no re-inference).
The 15 new seeds need 22 Adaptive inferences each (330 total). The
Fixed baseline is cached per video (Exp 2's fixed_cache already
contains all 22 unique Fixed predictions) so Fixed evaluation for every
seed is just a shuffle + lookup with zero new LLM calls.

Primary output: paired fold bootstrap on n_pooled = 20 × 11 = 220.
Target: push the 2.5% CI edge above zero and secure the first positive
Statistical Go in Phase 1.4d.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4d.stage2_target_b_full_interpretationC import (
    INITIAL_WEIGHT,
    LLM_MAX_RETRIES,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SEC,
    MODEL,
    SUCCESS_STEP,
    WARMUP_COUNT,
    build_clean_records,
    check_ollama_ready,
    ensure_utf8_streams,
    paired_statistics,
    pooled_f1,
)
from phase1_4d.stage2_target_b_no_score_to_llm import (
    DETAIL_THRESHOLDS,
    PENALTIES,
    evaluate_fixed_trial,
    run_adaptive_trial,
)

EXP2_TRIALS_PATH = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage2_target_b_no_score_to_llm" / "trials_summary.json"
)
EXP2_STATS_PATH = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage2_target_b_no_score_to_llm" / "statistical_analysis.json"
)
EXP2_BOOTSTRAP_PATH = (
    REPO_ROOT / "results" / "phase1_4d" / "stage2_bootstrap_analysis"
    / "statistical_analysis_bootstrap.json"
)

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage2_target_b_no_score_extended"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary_extended.json"
STATS_PATH = OUT_DIR / "bootstrap_analysis_extended.json"

EXISTING_SEEDS = [42, 137, 256, 512, 1024]
NEW_SEEDS = [
    2048, 4096, 8192, 16384, 32768,
    65536, 131072, 262144, 524288, 1048576,
    2097152, 4194304, 8388608, 16777216, 33554432,
]
ALL_SEEDS = EXISTING_SEEDS + NEW_SEEDS

N_BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 42


# ---------------------------------------------------------------------------
# Load existing trial data
# ---------------------------------------------------------------------------

def load_exp2_payload() -> dict[str, Any]:
    return json.loads(EXP2_TRIALS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Bootstrap (same shape as stage2_fold_bootstrap.py)
# ---------------------------------------------------------------------------

def extract_eval_records(
    trials_fixed: list[dict[str, Any]],
    trials_adaptive: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pooled: list[dict[str, Any]] = []
    for fx, ad in zip(trials_fixed, trials_adaptive):
        fx_by_step = {f["step"]: f for f in fx["per_fold"]}
        ad_by_step = {f["step"]: f for f in ad["per_fold"]}
        for step in sorted(fx_by_step.keys()):
            if step < WARMUP_COUNT:
                continue
            f_fold = fx_by_step[step]
            a_fold = ad_by_step[step]
            pooled.append({
                "trial_seed": fx["seed"],
                "step": int(step),
                "video_id": f_fold["video_id"],
                "pred_fixed": f_fold["parsed"],
                "pred_adaptive": a_fold["parsed"],
                "gt": f_fold["ground_truth"],
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
    matrix = {
        "sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }
    for pred, gt in pairs:
        for cls in ("sparrow", "bulbul"):
            p, g = pred[cls], gt[cls]
            if p == 1 and g == 1: matrix[cls]["tp"] += 1
            elif p == 1 and g == 0: matrix[cls]["fp"] += 1
            elif p == 0 and g == 1: matrix[cls]["fn"] += 1
            else: matrix[cls]["tn"] += 1
    return (
        _f1(matrix["sparrow"]["tp"], matrix["sparrow"]["fp"], matrix["sparrow"]["fn"])
        + _f1(matrix["bulbul"]["tp"],  matrix["bulbul"]["fp"],  matrix["bulbul"]["fn"])
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
        fx_pairs = [(pooled[j]["pred_fixed"],    pooled[j]["gt"]) for j in idx]
        ad_pairs = [(pooled[j]["pred_adaptive"], pooled[j]["gt"]) for j in idx]
        deltas[i] = macro_f1_pooled(ad_pairs) - macro_f1_pooled(fx_pairs)

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

    p_pass = bool(p_two < 0.05)
    d_abs_pass = bool(abs(d) >= 0.8)
    ci_pass = bool(ci_lo > 0 or ci_hi < 0)

    # Histogram for later plotting
    counts, edges = np.histogram(deltas, bins=60)
    return {
        "n_pooled_folds":    n,
        "n_bootstrap":       n_bootstrap,
        "seed":              seed,
        "observed_fixed_macro_f1":    fx_obs,
        "observed_adaptive_macro_f1": ad_obs,
        "observed_delta":             ad_obs - fx_obs,
        "bootstrap_mean_delta":       mean_d,
        "bootstrap_std_delta":        std_d,
        "ci_95":                      [ci_lo, ci_hi],
        "p_value_twosided":           p_two,
        "cohens_d_paired":            d,
        "direction":                  direction,
        "criteria": {
            "p_value_pass_at_0.05":     p_pass,
            "abs_cohens_d_pass_at_0.8": d_abs_pass,
            "ci_excludes_zero":         ci_pass,
        },
        "overall_go_positive": bool(p_pass and d_abs_pass and ci_pass and direction == "positive"),
        "overall_go_negative": bool(p_pass and d_abs_pass and ci_pass and direction == "negative"),
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


def render_summary(
    trials_fixed_all: list[dict[str, Any]],
    trials_adaptive_all: list[dict[str, Any]],
    trial_stats_n20: dict[str, Any],
    boot_n220: dict[str, Any],
    boot_n55_from_disk: dict[str, Any] | None,
    trial_stats_n5: dict[str, Any] | None,
) -> str:
    lines = [
        "# Phase 1.4d Stage 2 Experiment 2 extended — n=220 paired fold bootstrap",
        "",
        "Exp 2 (commit 2dd8756) cleared |d| ≥ 0.8 and p < 0.05 under 55-fold paired "
        "bootstrap (commit 0d0903c) but its 95% CI lower edge landed at +0.000 — "
        "the Statistical Go gate missed by a hairline. This extension keeps every "
        "Exp 2 setting unchanged and only enlarges the trial set from 5 seeds to 20.",
        "",
        f"Seeds: {ALL_SEEDS[:5]} (existing) + {ALL_SEEDS[5:]} (new).",
        "Fixed baseline: Exp 2's `fixed_cache` is reused (22 unique per-video "
        "predictions). The 5 existing Adaptive trials are reused verbatim (no "
        "re-inference). The 15 new seeds contribute 15 × 22 = 330 fresh Adaptive "
        "LLM calls.",
        "",
        "## Per-trial macro F1 (all 20 trials)",
        "",
        "| Trial | Seed | Fixed | Adaptive | Δ |",
        "|---|---:|---:|---:|---:|",
    ]
    for i, (fx, ad) in enumerate(zip(trials_fixed_all, trials_adaptive_all), start=1):
        d_val = ad["macro_f1"] - fx["macro_f1"]
        tag = " (existing)" if fx["seed"] in EXISTING_SEEDS else " (new)"
        lines.append(
            f"| {i}{tag} | {fx['seed']} | {fx['macro_f1']:.3f} "
            f"| {ad['macro_f1']:.3f} | {d_val:+.3f} |"
        )
    lines.append("")

    # Final weights (aggregated)
    sums = {"v_sparrow": 0.0, "v_bulbul": 0.0, "a_sparrow": 0.0, "a_bulbul": 0.0}
    for ad in trials_adaptive_all:
        w = ad["final_weights"]
        sums["v_sparrow"] += w["visual"]["sparrow"]
        sums["v_bulbul"]  += w["visual"]["bulbul"]
        sums["a_sparrow"] += w["audio"]["sparrow"]
        sums["a_bulbul"]  += w["audio"]["bulbul"]
    n_tr = len(trials_adaptive_all) or 1
    lines.append("## Adaptive final weights (mean across 20 trials)")
    lines.append("")
    lines.append("| weight | Exp 2 (n=5) | Exp 2 extended (n=20) |")
    lines.append("|---|---:|---:|")
    exp2_means = {"v_sparrow": 0.458, "v_bulbul": 0.596, "a_sparrow": 0.382, "a_bulbul": 0.816}
    for key, label in (("v_sparrow", "visual.sparrow"), ("v_bulbul", "visual.bulbul"),
                        ("a_sparrow", "audio.sparrow"), ("a_bulbul", "audio.bulbul")):
        lines.append(
            f"| {label} | {exp2_means[key]:.3f} | {sums[key]/n_tr:.3f} |"
        )
    lines.append("")

    # Detail level frequencies
    vis_counts = {"brief": 0, "medium": 0, "full": 0}
    aud_counts = {"brief": 0, "medium": 0, "full": 0}
    for ad in trials_adaptive_all:
        for fold in ad["per_fold"]:
            vis_counts[fold["visual_level"]] += 1
            aud_counts[fold["audio_level"]] += 1
    total_decisions = sum(len(ad["per_fold"]) for ad in trials_adaptive_all)
    lines.append(f"## Detail-level frequencies (20 trials × 22 = {total_decisions} decisions)")
    lines.append("")
    lines.append("| level | visual | audio |")
    lines.append("|---|---:|---:|")
    for level in ("brief", "medium", "full"):
        lines.append(f"| {level} | {vis_counts[level]} | {aud_counts[level]} |")
    lines.append("")

    # Statistics comparison: trial n=5 vs trial n=20 vs bootstrap n=55 vs bootstrap n=220
    lines.append("## Statistical methods compared")
    lines.append("")
    lines.append(
        "| method | n | point Δ | Cohen's d | p | 95% CI | verdict |"
    )
    lines.append("|---|---:|---:|---:|---:|---|---|")

    # Trial t-test n=5 (from disk)
    if trial_stats_n5:
        d5 = trial_stats_n5.get("cohens_d")
        d5_str = f"{d5:+.3f}" if d5 is not None else "n/a"
        v5 = "Go" if trial_stats_n5.get("go_judgment", {}).get("overall_go") else "No-Go"
        lines.append(
            f"| trial t-test (Exp 2 original) | 5 | {trial_stats_n5['mean_diff']:+.3f} "
            f"| {d5_str} | {trial_stats_n5['paired_t_test']['p_value']:.4f} "
            f"| [{trial_stats_n5['ci_95'][0]:+.3f}, {trial_stats_n5['ci_95'][1]:+.3f}] "
            f"| {v5} |"
        )

    # Trial t-test n=20
    d20 = trial_stats_n20.get("cohens_d")
    d20_str = f"{d20:+.3f}" if d20 is not None else "n/a"
    v20 = "Go" if trial_stats_n20.get("go_judgment", {}).get("overall_go") else "No-Go"
    lines.append(
        f"| **trial t-test (extended)** | **20** | {trial_stats_n20['mean_diff']:+.3f} "
        f"| **{d20_str}** | **{trial_stats_n20['paired_t_test']['p_value']:.4f}** "
        f"| [{trial_stats_n20['ci_95'][0]:+.3f}, {trial_stats_n20['ci_95'][1]:+.3f}] "
        f"| **{v20}** |"
    )

    # Bootstrap n=55 (from disk)
    if boot_n55_from_disk:
        v55 = _verdict(boot_n55_from_disk)
        lines.append(
            f"| paired fold bootstrap (Exp 2 original) | {boot_n55_from_disk['n_pooled_folds']} "
            f"| {boot_n55_from_disk['observed_delta']:+.3f} "
            f"| {boot_n55_from_disk['cohens_d_paired']:+.3f} "
            f"| {boot_n55_from_disk['p_value_twosided']:.4f} "
            f"| [{boot_n55_from_disk['ci_95'][0]:+.3f}, {boot_n55_from_disk['ci_95'][1]:+.3f}] "
            f"| {v55} |"
        )

    # Bootstrap n=220 (this extension)
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

    # Criteria breakdown
    lines.append("## Go criteria breakdown")
    lines.append("")
    lines.append(
        "| method | n | p < 0.05 | |d| ≥ 0.8 | CI excl. 0 | direction | Overall |"
    )
    lines.append("|---|---:|:-:|:-:|:-:|:-:|---|")
    if boot_n55_from_disk:
        c = boot_n55_from_disk["criteria"]
        lines.append(
            f"| bootstrap (original) | {boot_n55_from_disk['n_pooled_folds']} "
            f"| {'Y' if c['p_value_pass_at_0.05'] else 'N'} "
            f"| {'Y' if c['abs_cohens_d_pass_at_0.8'] else 'N'} "
            f"| {'Y' if c['ci_excludes_zero'] else 'N'} "
            f"| {boot_n55_from_disk['direction']} "
            f"| {_verdict(boot_n55_from_disk)} |"
        )
    c220 = boot_n220["criteria"]
    lines.append(
        f"| **bootstrap (extended)** | **{boot_n220['n_pooled_folds']}** "
        f"| {'Y' if c220['p_value_pass_at_0.05'] else 'N'} "
        f"| {'Y' if c220['abs_cohens_d_pass_at_0.8'] else 'N'} "
        f"| {'Y' if c220['ci_excludes_zero'] else 'N'} "
        f"| {boot_n220['direction']} "
        f"| **{_verdict(boot_n220)}** |"
    )
    lines.append("")

    # Discussion
    lines.append("## Discussion")
    lines.append("")
    if boot_n220["overall_go_positive"]:
        lines.append(
            "🎯 **Statistical Go achieved.** All three sdnd-proof criteria clear on "
            "n=220 with positive direction. The 2.5% CI edge moved off the 0 boundary "
            f"({'> 0' if boot_n220['ci_95'][0] > 0 else 'exact 0'}) to "
            f"{boot_n220['ci_95'][0]:+.3f}, resolving the hairline miss at n=55. "
            "This is the first positive Statistical Go in Phase 1.4d."
        )
    else:
        fails = [
            lbl for lbl, ok in [
                ("p<0.05", c220["p_value_pass_at_0.05"]),
                ("|d|≥0.8", c220["abs_cohens_d_pass_at_0.8"]),
                ("CI excludes 0", c220["ci_excludes_zero"]),
            ] if not ok
        ]
        lines.append(
            f"**Not-Go** at extended n. Failing criterion/criteria: "
            f"{', '.join(fails) if fails else '—'}. "
            f"CI edges [{boot_n220['ci_95'][0]:+.3f}, {boot_n220['ci_95'][1]:+.3f}], "
            f"d={boot_n220['cohens_d_paired']:+.3f}, "
            f"p={boot_n220['p_value_twosided']:.4f}. "
        )
        if boot_n55_from_disk and boot_n55_from_disk["overall_go_positive"]:
            lines.append(
                "Note: the 55-fold bootstrap previously read as positive Go; extended "
                "data moves the estimate."
            )
        lines.append(
            "The extra 15 trials change the balance between effect and variance. "
            "Reading off the table: how did Cohen's d move from n=55 to n=220? "
            "Did the effect size shrink (variance-dominated) or grow (more signal)?"
        )
    lines.append("")

    # Weight-trajectory observations
    lines.append("## Weight-trajectory observations (n=20 mean)")
    lines.append("")
    for key, label in (("v_sparrow", "visual.sparrow"), ("v_bulbul", "visual.bulbul"),
                        ("a_sparrow", "audio.sparrow"), ("a_bulbul", "audio.bulbul")):
        old = exp2_means[key]
        new = sums[key] / n_tr
        drift = new - old
        lines.append(
            f"- {label}: {old:.3f} → {new:.3f} ({drift:+.3f})"
        )
    lines.append("")

    # Output files
    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary_extended.json`")
    lines.append("- `bootstrap_analysis_extended.json`")
    lines.append("- `graphs/weight_trajectory_20trials.png`")
    lines.append("- `graphs/ci_n_comparison.png`")
    lines.append("- `graphs/cohens_d_final.png`")
    lines.append("- `graphs/go_criteria_visualization.png`")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_weight_trajectory(trials_adaptive: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5), sharey=True, sharex=True)
    panels = [
        ("visual", "sparrow", axes[0, 0]),
        ("visual", "bulbul",  axes[0, 1]),
        ("audio",  "sparrow", axes[1, 0]),
        ("audio",  "bulbul",  axes[1, 1]),
    ]
    cmap_idx = 0
    for modality, cls, ax in panels:
        for ad in trials_adaptive:
            existing = ad["seed"] in EXISTING_SEEDS
            color = "#4c72b0" if existing else "#dd8452"
            alpha = 0.45
            steps = [e["step"] for e in ad["weight_trajectory"]]
            vals = [e["weights"][modality][cls] for e in ad["weight_trajectory"]]
            ax.plot(steps, vals, linewidth=0.9, alpha=alpha, color=color)
        ax.axvline(WARMUP_COUNT - 0.5, color="#888", linestyle="--", linewidth=0.7)
        ax.set_title(f"{modality} · {cls} (penalty ×{PENALTIES[modality][cls]})")
        ax.set_ylim(0, 1); ax.grid(alpha=0.3)
    axes[0, 0].plot([], [], color="#4c72b0", label="existing 5 seeds")
    axes[0, 0].plot([], [], color="#dd8452", label="new 15 seeds")
    axes[0, 0].legend(fontsize=8, loc="lower left")
    axes[1, 0].set_xlabel("fold step"); axes[1, 1].set_xlabel("fold step")
    axes[0, 0].set_ylabel("flow_weight"); axes[1, 0].set_ylabel("flow_weight")
    fig.suptitle("Stage 2 Exp 2 extended — 20-trial Adaptive weight trajectories")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_ci_n_comparison(
    trial_stats_n5: dict[str, Any] | None,
    trial_stats_n20: dict[str, Any],
    boot_n55: dict[str, Any] | None,
    boot_n220: dict[str, Any],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, float, list[float]]] = []
    if trial_stats_n5:
        entries.append((
            "trial t-test n=5",
            trial_stats_n5["mean_diff"],
            trial_stats_n5["ci_95"],
        ))
    entries.append((
        "trial t-test n=20",
        trial_stats_n20["mean_diff"],
        trial_stats_n20["ci_95"],
    ))
    if boot_n55:
        entries.append((
            "bootstrap n=55",
            boot_n55["bootstrap_mean_delta"],
            boot_n55["ci_95"],
        ))
    entries.append((
        "bootstrap n=220",
        boot_n220["bootstrap_mean_delta"],
        boot_n220["ci_95"],
    ))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    xs = np.arange(len(entries))
    for x, (label, m, ci) in zip(xs, entries):
        ax.errorbar([x], [m], yerr=[[m - ci[0]], [ci[1] - m]],
                    fmt="o", color="#264653", capsize=6, markersize=8)
        ax.annotate(f"[{ci[0]:+.3f}, {ci[1]:+.3f}]",
                    xy=(x, ci[1]), xytext=(0, 8),
                    textcoords="offset points", ha="center", fontsize=8)
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xticks(xs); ax.set_xticklabels([e[0] for e in entries], rotation=15)
    ax.set_ylabel("mean Δ macro F1 with 95% CI")
    ax.set_title("CI narrowing: n=5 → n=20 → n=55 → n=220")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_cohens_d_final(
    trial_stats_n5: dict[str, Any] | None,
    trial_stats_n20: dict[str, Any],
    boot_n55: dict[str, Any] | None,
    boot_n220: dict[str, Any],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    labels, ds = [], []
    if trial_stats_n5 and trial_stats_n5.get("cohens_d") is not None:
        labels.append("trial n=5"); ds.append(trial_stats_n5["cohens_d"])
    if trial_stats_n20.get("cohens_d") is not None:
        labels.append("trial n=20"); ds.append(trial_stats_n20["cohens_d"])
    if boot_n55:
        labels.append("bootstrap n=55"); ds.append(boot_n55["cohens_d_paired"])
    labels.append("bootstrap n=220"); ds.append(boot_n220["cohens_d_paired"])
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(range(len(labels)), ds, marker="o", linewidth=2.0, color="#264653")
    for i, d in enumerate(ds):
        ax.annotate(f"{d:+.3f}", xy=(i, d), xytext=(0, 10),
                    textcoords="offset points", ha="center", fontsize=9)
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.axhline(0.8, color="#2a9d8f", linestyle=":", linewidth=1.0,
               label="|d|=0.8 (Go threshold)")
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
    ax.set_ylabel("Cohen's d (paired)")
    ax.set_title("Exp 2 Cohen's d progression across n")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_go_criteria_visualization(
    boot_n220: dict[str, Any], out_path: Path
) -> None:
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
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(centers, counts, width=(edges[1] - edges[0]), color="#2a9d8f", alpha=0.75)
    ax.axvline(0.0, color="#555", linestyle="--", linewidth=0.9, label="Δ = 0")
    ax.axvline(boot_n220["observed_delta"], color="#111", linewidth=1.6,
               label=f"observed Δ = {boot_n220['observed_delta']:+.3f}")
    ax.axvline(boot_n220["ci_95"][0], color="#c44e52", linestyle=":", linewidth=1.4,
               label=(f"95% CI = "
                      f"[{boot_n220['ci_95'][0]:+.3f}, {boot_n220['ci_95'][1]:+.3f}]"))
    ax.axvline(boot_n220["ci_95"][1], color="#c44e52", linestyle=":", linewidth=1.4)
    ax.set_xlabel("Δ macro F1 (Adaptive − Fixed)")
    ax.set_ylabel("bootstrap count")
    c = boot_n220["criteria"]
    title = (
        f"n={boot_n220['n_pooled_folds']} bootstrap  |  "
        f"d={boot_n220['cohens_d_paired']:+.3f}  "
        f"p={boot_n220['p_value_twosided']:.4f}  |  "
        f"p<0.05: {'Y' if c['p_value_pass_at_0.05'] else 'N'}  "
        f"|d|≥0.8: {'Y' if c['abs_cohens_d_pass_at_0.8'] else 'N'}  "
        f"CI excl 0: {'Y' if c['ci_excludes_zero'] else 'N'}"
    )
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ensure_utf8_streams()

    # Load Exp 2 data — reuse fixed_cache, existing 5 adaptive trials, existing Fixed trials.
    exp2_payload = load_exp2_payload()
    fixed_cache = exp2_payload["fixed_cache"]
    existing_adaptive_by_seed = {tr["seed"]: tr for tr in exp2_payload["trials_adaptive"]}
    existing_fixed_by_seed    = {tr["seed"]: tr for tr in exp2_payload["trials_fixed"]}
    exp2_trial_stats = (
        json.loads(EXP2_STATS_PATH.read_text(encoding="utf-8"))
        if EXP2_STATS_PATH.is_file() else None
    )
    exp2_boot = None
    if EXP2_BOOTSTRAP_PATH.is_file():
        data = json.loads(EXP2_BOOTSTRAP_PATH.read_text(encoding="utf-8"))
        # The bootstrap file stores results as [Exp1, Exp2, Exp3]; Exp 2 is index 1.
        for entry in data.get("results", []):
            if entry.get("name") == "Exp 2":
                exp2_boot = entry["bootstrap"]
                break
    print(f"[load] Exp 2 trials_summary.json: "
          f"{len(exp2_payload['trials_adaptive'])} adaptive, "
          f"{len(fixed_cache)} fixed cache entries")

    # Only Ollama-check when new seeds are actually needed.
    new_seeds_needed = [s for s in NEW_SEEDS if s not in existing_adaptive_by_seed]
    if new_seeds_needed:
        check_ollama_ready()

    records = build_clean_records()
    print(f"[load] clean fold records: {len(records)}")

    # Run Adaptive for new seeds. Reuse existing for known seeds.
    trials_adaptive_all: list[dict[str, Any]] = []
    for seed in ALL_SEEDS:
        if seed in existing_adaptive_by_seed:
            trials_adaptive_all.append(existing_adaptive_by_seed[seed])
            print(f"[reuse] adaptive seed={seed}")
            continue
        print(f"[new ] adaptive seed={seed} ...", flush=True)
        start = time.perf_counter()
        tr = run_adaptive_trial(records, seed)
        elapsed = time.perf_counter() - start
        print(f"  macro F1 = {tr['macro_f1']:.3f}  ({elapsed:.1f}s)")
        trials_adaptive_all.append(tr)

    # Fixed evaluation for every seed (cheap, no LLM).
    trials_fixed_all: list[dict[str, Any]] = []
    for seed in ALL_SEEDS:
        if seed in existing_fixed_by_seed:
            trials_fixed_all.append(existing_fixed_by_seed[seed])
        else:
            trials_fixed_all.append(evaluate_fixed_trial(records, fixed_cache, seed))

    # Trial-level stats at n=20
    results_fixed    = [tr["macro_f1"] for tr in trials_fixed_all]
    results_adaptive = [tr["macro_f1"] for tr in trials_adaptive_all]
    trial_stats_n20  = paired_statistics(results_fixed, results_adaptive)

    # Paired fold bootstrap at n=220
    pooled = extract_eval_records(trials_fixed_all, trials_adaptive_all)
    print(f"[bootstrap] pooling {len(pooled)} second-half fold records; "
          f"running {N_BOOTSTRAP} paired resamples ...", flush=True)
    boot_n220 = paired_fold_bootstrap(pooled)
    print(
        f"[bootstrap] d={boot_n220['cohens_d_paired']:+.3f}, "
        f"p={boot_n220['p_value_twosided']:.4f}, "
        f"CI=[{boot_n220['ci_95'][0]:+.3f}, {boot_n220['ci_95'][1]:+.3f}] "
        f"({boot_n220['direction']})"
    )

    # Persist
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    TRIALS_PATH.write_text(
        json.dumps(
            {
                "existing_seeds": EXISTING_SEEDS,
                "new_seeds": NEW_SEEDS,
                "all_seeds": ALL_SEEDS,
                "warmup_count": WARMUP_COUNT,
                "n_folds_per_trial": len(records),
                "records": records,
                "fixed_cache": fixed_cache,
                "trials_fixed": trials_fixed_all,
                "trials_adaptive": trials_adaptive_all,
                "trial_stats_n20": trial_stats_n20,
                "config": {
                    "model": MODEL,
                    "temperature": LLM_TEMPERATURE,
                    "timeout_sec": LLM_TIMEOUT_SEC,
                    "max_retries": LLM_MAX_RETRIES,
                    "success_step": SUCCESS_STEP,
                    "initial_weight": INITIAL_WEIGHT,
                    "detail_thresholds": DETAIL_THRESHOLDS,
                    "penalties": PENALTIES,
                    "prompt_mode": "no_score_extended",
                },
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps({
            "trial_stats_n20": trial_stats_n20,
            "bootstrap_n220": boot_n220,
            "reference": {
                "trial_stats_n5": exp2_trial_stats,
                "bootstrap_n55": exp2_boot,
            },
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(
        render_summary(
            trials_fixed_all, trials_adaptive_all,
            trial_stats_n20, boot_n220,
            exp2_boot, exp2_trial_stats,
        ),
        encoding="utf-8",
    )

    plot_weight_trajectory(trials_adaptive_all, GRAPHS_DIR / "weight_trajectory_20trials.png")
    plot_ci_n_comparison(
        exp2_trial_stats, trial_stats_n20,
        exp2_boot, boot_n220,
        GRAPHS_DIR / "ci_n_comparison.png",
    )
    plot_cohens_d_final(
        exp2_trial_stats, trial_stats_n20,
        exp2_boot, boot_n220,
        GRAPHS_DIR / "cohens_d_final.png",
    )
    plot_go_criteria_visualization(boot_n220, GRAPHS_DIR / "go_criteria_visualization.png")

    print()
    print("=== Phase 1.4d Stage 2 Exp 2 extended summary ===")
    print(
        f"trial n=20 Δ={trial_stats_n20['mean_diff']:+.3f}, "
        f"d={trial_stats_n20.get('cohens_d')}, "
        f"p={trial_stats_n20['paired_t_test']['p_value']:.4f}, "
        f"CI=[{trial_stats_n20['ci_95'][0]:+.3f}, {trial_stats_n20['ci_95'][1]:+.3f}]"
    )
    print(
        f"bootstrap n=220 Δ={boot_n220['observed_delta']:+.3f}, "
        f"d={boot_n220['cohens_d_paired']:+.3f}, "
        f"p={boot_n220['p_value_twosided']:.4f}, "
        f"CI=[{boot_n220['ci_95'][0]:+.3f}, {boot_n220['ci_95'][1]:+.3f}]"
    )
    v = _verdict(boot_n220)
    print(f"Overall verdict (bootstrap n=220): {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
