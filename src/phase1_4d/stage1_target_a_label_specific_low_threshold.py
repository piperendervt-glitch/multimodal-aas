"""Phase 1.4d Stage 1 Experiment 4 — label-specific + threshold 0.4.

Experiment 3 (label-specific weights, threshold 0.5) returned No-Go,
but Trial 3 produced an isolated +0.056 gain: C.sparrow grew to 0.588,
which with the 0.5 threshold was just enough for C alone to trigger
``sparrow=1`` on a fold where A and B both predicted 0 (but ground
truth was 1). Experiment 4 tests whether that single-node breakthrough
can be made consistent by lowering the decision threshold from 0.5 to
0.4, letting a single confident topology override the majority.

Design (otherwise identical to Experiment 3):
    * 6 weights (topology × label), initialised at 0.5, sdnd-proof rule
      (success +0.1·(1−w), failure ×0.7).
    * Fixed baseline (Fixed_0.4) is *also* evaluated at threshold 0.4
      for a fair A/B comparison. Primary Go gate is Exp 4 vs Fixed_0.4.
    * Reference-only comparison against Fixed_0.5 (Exp 3's Fixed)
      shown alongside in the summary.

Predictions are reused from ``results/phase1_3_extended/`` with no
re-inference.
"""

from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4d.common.ensemble import compute_f1_bundle, weighted_vote_label_specific
from phase1_4d.common.flow_weight import INITIAL_WEIGHT, update_weight_sdnd_proof
from phase1_4d.stage1_target_a_sdnd_proof import (
    SEEDS,
    WARMUP_COUNT,
    build_fold_records,
    ensure_utf8_streams,
    paired_statistics,
)

EXP1_TRIALS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_sdnd_proof" / "trials_summary.json"
EXP1_STATS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_sdnd_proof" / "statistical_analysis.json"
EXP2_TRIALS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_relaxed" / "trials_summary.json"
EXP2_STATS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_relaxed" / "statistical_analysis.json"
EXP3_TRIALS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_label_specific" / "trials_summary.json"
EXP3_STATS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_label_specific" / "statistical_analysis.json"

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_label_specific_low_threshold"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary.json"
STATS_PATH = OUT_DIR / "statistical_analysis.json"

LABELS = ("sparrow", "bulbul")
TOPOLOGIES = ("A", "B", "C")
THRESHOLD = 0.4


def initial_label_weights() -> dict[str, dict[str, float]]:
    return {t: {cls: INITIAL_WEIGHT for cls in LABELS} for t in TOPOLOGIES}


def run_trial_low_threshold(records: list[dict[str, Any]], seed: int, threshold: float = THRESHOLD) -> dict[str, Any]:
    rng = random.Random(seed)
    order = list(range(len(records)))
    rng.shuffle(order)

    # Fixed_0.4 — all weights at 0.5, threshold = 0.4.
    fixed_weights = initial_label_weights()
    fixed_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    fixed_per_fold: list[dict[str, Any]] = []
    for step, idx in enumerate(order):
        rec = records[idx]
        pred = weighted_vote_label_specific(rec["predictions"], fixed_weights, threshold=threshold)
        fixed_per_fold.append({
            "step": step, "video_id": rec["video_id"],
            "pred": pred, "gt": rec["ground_truth"],
        })
        if step >= WARMUP_COUNT:
            fixed_eval_pairs.append((pred, rec["ground_truth"]))
    fixed_metrics = compute_f1_bundle(fixed_eval_pairs)

    # Adaptive_0.4 — label-specific sdnd-proof updates, threshold = 0.4.
    adaptive_weights = initial_label_weights()
    adaptive_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    weight_trajectory: list[dict[str, Any]] = [
        {"step": -1, "weights": copy.deepcopy(adaptive_weights)}
    ]
    adaptive_per_fold: list[dict[str, Any]] = []
    for step, idx in enumerate(order):
        rec = records[idx]
        pred = weighted_vote_label_specific(rec["predictions"], adaptive_weights, threshold=threshold)
        weights_before = copy.deepcopy(adaptive_weights)
        topology_success: dict[str, dict[str, bool]] = {t: {} for t in TOPOLOGIES}
        for t in TOPOLOGIES:
            for cls in LABELS:
                success = rec["predictions"][t][cls] == rec["ground_truth"][cls]
                topology_success[t][cls] = success
                adaptive_weights[t][cls] = update_weight_sdnd_proof(
                    adaptive_weights[t][cls], success
                )
        adaptive_per_fold.append({
            "step": step, "video_id": rec["video_id"],
            "pred": pred, "gt": rec["ground_truth"],
            "weights_before": weights_before,
            "weights_after": copy.deepcopy(adaptive_weights),
            "topology_success": topology_success,
        })
        weight_trajectory.append({"step": step, "weights": copy.deepcopy(adaptive_weights)})
        if step >= WARMUP_COUNT:
            adaptive_eval_pairs.append((pred, rec["ground_truth"]))
    adaptive_metrics = compute_f1_bundle(adaptive_eval_pairs)

    return {
        "seed": seed,
        "threshold": threshold,
        "shuffle_order": order,
        "fold_video_ids_in_order": [records[i]["video_id"] for i in order],
        "warmup_folds": [records[i]["video_id"] for i in order[:WARMUP_COUNT]],
        "eval_folds":   [records[i]["video_id"] for i in order[WARMUP_COUNT:]],
        "fixed_0_4": {
            "final_weights": fixed_weights,
            "macro_f1":   fixed_metrics["macro_f1"],
            "sparrow_f1": fixed_metrics["sparrow_f1"],
            "bulbul_f1":  fixed_metrics["bulbul_f1"],
            "confusion":  fixed_metrics["confusion"],
            "per_fold":   fixed_per_fold,
        },
        "adaptive_0_4": {
            "initial_weights": initial_label_weights(),
            "final_weights":   adaptive_weights,
            "weight_trajectory": weight_trajectory,
            "macro_f1":   adaptive_metrics["macro_f1"],
            "sparrow_f1": adaptive_metrics["sparrow_f1"],
            "bulbul_f1":  adaptive_metrics["bulbul_f1"],
            "confusion":  adaptive_metrics["confusion"],
            "per_fold":   adaptive_per_fold,
        },
    }


def load_prior(trials_path: Path, stats_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return (
        json.loads(trials_path.read_text(encoding="utf-8"))["trials"],
        json.loads(stats_path.read_text(encoding="utf-8")),
    )


def pool_confusion(trials: list[dict[str, Any]], key: str) -> dict[str, dict[str, int]]:
    """Pool per-label confusion counts across all trials for given trial sub-key."""
    pooled = {cls: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for cls in LABELS}
    for tr in trials:
        conf = tr[key]["confusion"]
        for cls in LABELS:
            for k in ("tp", "fp", "fn", "tn"):
                pooled[cls][k] += int(conf[cls][k])
    return pooled


def render_summary(
    trials: list[dict[str, Any]],
    stats_vs_f04: dict[str, Any],
    stats_vs_f05: dict[str, Any],
    exp1_trials, exp1_stats,
    exp2_trials, exp2_stats,
    exp3_trials, exp3_stats,
    records: list[dict[str, Any]],
) -> str:
    e1 = {tr["seed"]: tr for tr in exp1_trials}
    e2 = {tr["seed"]: tr for tr in exp2_trials}
    e3 = {tr["seed"]: tr for tr in exp3_trials}
    lines = [
        "# Phase 1.4d Stage 1 Experiment 4 — label-specific + threshold 0.4",
        "",
        "Same 6-weight label-specific structure as Experiment 3, same sdnd-proof "
        "update rule (×0.7), same 5 trials, same clean 22 folds, same second-half "
        "evaluation. **Only change**: the decision threshold for the per-label "
        f"weighted score is lowered from 0.5 to **{THRESHOLD}**, so a single "
        "confident topology can trigger `label=1` even when the majority disagrees.",
        "",
        "To make the A/B comparison fair, we also compute **Fixed_0.4** (equal "
        "weights at threshold 0.4) on the same shuffles. The primary Go gate is "
        "Adaptive_0.4 vs Fixed_0.4; a reference comparison against Fixed_0.5 "
        "(Exp 3's Fixed, same as Exp 1/2 Fixed) is shown for intuition.",
        "",
        "## Per-trial macro F1 across 4 experiments",
        "",
        "| Trial | Seed | Fixed 0.5 | Fixed 0.4 | Exp 1 | Exp 2 | Exp 3 | **Exp 4** | Δ(Exp 4 − Fixed 0.4) | Δ(Exp 4 − Fixed 0.5) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, tr in enumerate(trials, start=1):
        s = tr["seed"]
        fixed05 = e3[s]["experiment_A"]["macro_f1"]
        fixed04 = tr["fixed_0_4"]["macro_f1"]
        adaptive04 = tr["adaptive_0_4"]["macro_f1"]
        e1_b = e1[s]["experiment_B"]["macro_f1"]
        e2_b = e2[s]["experiment_B"]["macro_f1"]
        e3_b = e3[s]["experiment_B"]["macro_f1"]
        d_vs_f04 = adaptive04 - fixed04
        d_vs_f05 = adaptive04 - fixed05
        lines.append(
            f"| {i} | {s} | {fixed05:.3f} | {fixed04:.3f} | {e1_b:.3f} | {e2_b:.3f} | {e3_b:.3f} "
            f"| **{adaptive04:.3f}** | {d_vs_f04:+.3f} | {d_vs_f05:+.3f} |"
        )
    lines.append("")

    # Per-trial F1 breakdown (Exp 4 only)
    lines.append("## Per-trial F1 breakdown (Experiment 4)")
    lines.append("")
    lines.append(
        "| Trial | Seed | Fixed 0.4 sparrow | Fixed 0.4 bulbul | Adaptive 0.4 sparrow | Adaptive 0.4 bulbul |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")
    for i, tr in enumerate(trials, start=1):
        a, b = tr["fixed_0_4"], tr["adaptive_0_4"]
        lines.append(
            f"| {i} | {tr['seed']} | {a['sparrow_f1']:.3f} | {a['bulbul_f1']:.3f} "
            f"| {b['sparrow_f1']:.3f} | {b['bulbul_f1']:.3f} |"
        )
    lines.append("")

    # Final weights
    lines.append("## Experiment 4 final weights (per trial)")
    lines.append("")
    lines.append(
        "| Trial | Seed | A.s | A.b | B.s | B.b | C.s | C.b |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    sums = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    for i, tr in enumerate(trials, start=1):
        w = tr["adaptive_0_4"]["final_weights"]
        lines.append(
            f"| {i} | {tr['seed']} "
            f"| {w['A']['sparrow']:.3f} | {w['A']['bulbul']:.3f} "
            f"| {w['B']['sparrow']:.3f} | {w['B']['bulbul']:.3f} "
            f"| {w['C']['sparrow']:.3f} | {w['C']['bulbul']:.3f} |"
        )
        for t in TOPOLOGIES:
            for cls in LABELS:
                sums[t][cls] += w[t][cls]
    n_tr = len(trials) or 1
    lines.append(
        f"| mean | - "
        f"| {sums['A']['sparrow']/n_tr:.3f} | {sums['A']['bulbul']/n_tr:.3f} "
        f"| {sums['B']['sparrow']/n_tr:.3f} | {sums['B']['bulbul']/n_tr:.3f} "
        f"| {sums['C']['sparrow']/n_tr:.3f} | {sums['C']['bulbul']/n_tr:.3f} |"
    )
    lines.append("")

    lines.append("## Mean final weights (5-trial average)")
    lines.append("")
    lines.append("|          | sparrow | bulbul | \\|Δ\\| |")
    lines.append("|---|---:|---:|---:|")
    for t in TOPOLOGIES:
        sp = sums[t]["sparrow"] / n_tr
        bu = sums[t]["bulbul"] / n_tr
        lines.append(f"| Topology {t} | {sp:.3f} | {bu:.3f} | {abs(sp - bu):.3f} |")
    lines.append("")

    # Exp 4 vs Fixed_0.4 statistics
    lines.append("## Experiment 4 statistical analysis (primary: vs Fixed_0.4)")
    lines.append("")
    s = stats_vs_f04
    lines.append(f"- Mean Δ: **{s['mean_diff']:+.3f}**")
    lines.append(f"- Std Δ: {s['std_diff']:.3f}")
    lines.append(
        f"- Paired t-test: t = {s['paired_t_test']['t_stat']:.3f}, "
        f"p = {s['paired_t_test']['p_value']:.4f}"
    )
    d_val = s["cohens_d"]
    d_str = f"{d_val:.3f}" if d_val is not None else "undefined"
    lines.append(f"- Cohen's d (paired): {d_str}")
    lines.append(f"- 95% CI (paired): [{s['ci_95'][0]:+.3f}, {s['ci_95'][1]:+.3f}]")
    lines.append("")

    # Exp 4 vs Fixed_0.5 reference
    s2 = stats_vs_f05
    d2 = s2["cohens_d"]
    d2_str = f"{d2:.3f}" if d2 is not None else "n/a"
    lines.append("## Reference: Experiment 4 vs Fixed_0.5 (threshold change + weight learning combined)")
    lines.append("")
    lines.append(
        f"- Mean Δ: {s2['mean_diff']:+.3f}  "
        f"| p = {s2['paired_t_test']['p_value']:.4f}  "
        f"| d = {d2_str}  "
        f"| CI [{s2['ci_95'][0]:+.3f}, {s2['ci_95'][1]:+.3f}]"
    )
    lines.append("")

    # Go judgment 4-way
    lines.append("## Go judgment (sdnd-proof 3 criteria, primary baseline = Fixed_0.4)")
    lines.append("")
    lines.append("| Criterion | Threshold | Exp 1 | Exp 2 | Exp 3 | **Exp 4** | Exp 4 pass |")
    lines.append("|---|---|---:|---:|---:|---:|:-:|")
    j = s["go_judgment"]
    def d_fmt(d): return f"{d:.3f}" if d is not None else "n/a"
    lines.append(
        f"| p-value | < 0.05 | {exp1_stats['paired_t_test']['p_value']:.4f} "
        f"| {exp2_stats['paired_t_test']['p_value']:.4f} "
        f"| {exp3_stats['paired_t_test']['p_value']:.4f} "
        f"| **{s['paired_t_test']['p_value']:.4f}** "
        f"| {'Y' if j['p_value_pass'] else 'N'} |"
    )
    lines.append(
        f"| Cohen's d | >= 0.8 | {d_fmt(exp1_stats['cohens_d'])} "
        f"| {d_fmt(exp2_stats['cohens_d'])} "
        f"| {d_fmt(exp3_stats['cohens_d'])} "
        f"| **{d_str}** | {'Y' if j['cohens_d_pass'] else 'N'} |"
    )
    lines.append(
        f"| 95% CI lower | > 0 | {exp1_stats['ci_95'][0]:+.3f} "
        f"| {exp2_stats['ci_95'][0]:+.3f} "
        f"| {exp3_stats['ci_95'][0]:+.3f} "
        f"| **{s['ci_95'][0]:+.3f}** | {'Y' if j['ci_pass'] else 'N'} |"
    )
    prior_verdicts = {
        "Exp 1": "No-Go" if not exp1_stats["go_judgment"]["overall_go"] else "Go",
        "Exp 2": "No-Go" if not exp2_stats["go_judgment"]["overall_go"] else "Go",
        "Exp 3": "No-Go" if not exp3_stats["go_judgment"]["overall_go"] else "Go",
    }
    exp4_overall = "Go" if j["overall_go"] else "No-Go"
    lines.append(
        "| **Overall** | all pass "
        f"| **{prior_verdicts['Exp 1']}** | **{prior_verdicts['Exp 2']}** "
        f"| **{prior_verdicts['Exp 3']}** | **{exp4_overall}** | |"
    )
    lines.append("")

    # Trial 3 breakthrough analysis
    lines.append("## Trial 3 breakthrough analysis")
    lines.append("")
    exp3_trial3 = e3[256]
    exp4_trial3 = trials[2]
    e3_adaptive = exp3_trial3["experiment_B"]["macro_f1"]
    e4_adaptive = exp4_trial3["adaptive_0_4"]["macro_f1"]
    e3_fixed05 = exp3_trial3["experiment_A"]["macro_f1"]
    e4_fixed04 = exp4_trial3["fixed_0_4"]["macro_f1"]
    lines.append(
        f"- Exp 3 Trial 3 (seed 256): Fixed_0.5 = {e3_fixed05:.3f}, Adaptive_0.5 = {e3_adaptive:.3f} "
        f"(Δ = {e3_adaptive - e3_fixed05:+.3f})."
    )
    lines.append(
        f"- Exp 4 Trial 3 (seed 256): Fixed_0.4 = {e4_fixed04:.3f}, Adaptive_0.4 = {e4_adaptive:.3f} "
        f"(Δ = {e4_adaptive - e4_fixed04:+.3f})."
    )
    # How many trials got Adaptive > Fixed_0.4 in Exp 4?
    positive_trials = sum(1 for tr in trials if tr["adaptive_0_4"]["macro_f1"] > tr["fixed_0_4"]["macro_f1"])
    zero_trials = sum(1 for tr in trials if tr["adaptive_0_4"]["macro_f1"] == tr["fixed_0_4"]["macro_f1"])
    negative_trials = sum(1 for tr in trials if tr["adaptive_0_4"]["macro_f1"] < tr["fixed_0_4"]["macro_f1"])
    lines.append(
        f"- Exp 4 trial-level split vs Fixed_0.4: "
        f"{positive_trials} better, {zero_trials} equal, {negative_trials} worse."
    )
    lines.append("")

    # FP/FN analysis
    lines.append("## False Positive / False Negative analysis (pooled across 5 × 11 = 55 eval folds)")
    lines.append("")
    f04_pool = pool_confusion(trials, "fixed_0_4")
    a04_pool = pool_confusion(trials, "adaptive_0_4")
    f05_pool = pool_confusion(exp3_trials, "experiment_A")
    a05_pool = pool_confusion(exp3_trials, "experiment_B")
    lines.append("| pool | sparrow TP | sparrow FP | sparrow FN | sparrow TN | bulbul TP | bulbul FP | bulbul FN | bulbul TN |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for label, pool in (("Fixed_0.5", f05_pool), ("Fixed_0.4", f04_pool),
                         ("Adaptive_0.5 (Exp 3)", a05_pool), ("Adaptive_0.4 (Exp 4)", a04_pool)):
        lines.append(
            f"| {label} "
            f"| {pool['sparrow']['tp']} | {pool['sparrow']['fp']} | {pool['sparrow']['fn']} | {pool['sparrow']['tn']} "
            f"| {pool['bulbul']['tp']} | {pool['bulbul']['fp']} | {pool['bulbul']['fn']} | {pool['bulbul']['tn']} |"
        )
    lines.append("")

    # Commentary on FP/FN shift
    lines.append("### Threshold-change effect on FP/FN")
    lines.append("")
    fp_change_fixed = (
        (f04_pool['sparrow']['fp'] + f04_pool['bulbul']['fp'])
        - (f05_pool['sparrow']['fp'] + f05_pool['bulbul']['fp'])
    )
    fn_change_fixed = (
        (f04_pool['sparrow']['fn'] + f04_pool['bulbul']['fn'])
        - (f05_pool['sparrow']['fn'] + f05_pool['bulbul']['fn'])
    )
    lines.append(
        f"- Fixed side (0.5 → 0.4): total FP change = {fp_change_fixed:+d}, "
        f"total FN change = {fn_change_fixed:+d}."
    )
    fp_change_adapt = (
        (a04_pool['sparrow']['fp'] + a04_pool['bulbul']['fp'])
        - (a05_pool['sparrow']['fp'] + a05_pool['bulbul']['fp'])
    )
    fn_change_adapt = (
        (a04_pool['sparrow']['fn'] + a04_pool['bulbul']['fn'])
        - (a05_pool['sparrow']['fn'] + a05_pool['bulbul']['fn'])
    )
    lines.append(
        f"- Adaptive side (0.5 → 0.4): total FP change = {fp_change_adapt:+d}, "
        f"total FN change = {fn_change_adapt:+d}."
    )
    if fp_change_fixed > 0 and fn_change_fixed < 0:
        lines.append(
            "- Lowering the threshold traded FN for FP (as expected). Whether that "
            "improves macro F1 depends on whether the new TPs outnumber the new FPs."
        )
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append(
        "- n=5 trials on shuffle-only variation; the t-test does not generalise to "
        "dataset sampling. Bootstrap over the fold set is the next step."
    )
    lines.append(
        "- Lowering the threshold to 0.4 makes `mixed` (both-label) predictions "
        "mechanically more likely; with only 2 `mixed` clips in the clean set, the "
        "positive F1 gain is fragile and tightly coupled to those two folds."
    )
    lines.append(
        "- Fixed_0.4 is a stronger baseline than Fixed_0.5 whenever the 0.4 threshold "
        "recovers TPs that 0.5 missed; this is exactly the headroom Adaptive_0.4 has "
        "to beat."
    )
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `statistical_analysis.json` (primary: Exp 4 vs Fixed_0.4)")
    lines.append("- `graphs/threshold_comparison.png`")
    lines.append("- `graphs/f1_comparison_4exp.png`")
    lines.append("- `graphs/fp_fn_analysis.png`")
    lines.append("- `graphs/weight_trajectory_exp4.png`")
    lines.append("")
    return "\n".join(lines)


def plot_weight_trajectory_exp4(trials: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    colors = {42: "#2a9d8f", 137: "#e76f51", 256: "#264653",
              512: "#f4a261", 1024: "#6a4c93"}
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharey=True, sharex=True)
    for row_idx, cls in enumerate(LABELS):
        for col_idx, t in enumerate(TOPOLOGIES):
            ax = axes[row_idx, col_idx]
            for tr in trials:
                traj = tr["adaptive_0_4"]["weight_trajectory"]
                steps = [e["step"] for e in traj]
                vals = [e["weights"][t][cls] for e in traj]
                ax.plot(steps, vals, marker=".", linewidth=1.0, alpha=0.9,
                        color=colors.get(tr["seed"], "#444"),
                        label=f"seed {tr['seed']}" if (col_idx == 0 and row_idx == 0) else None)
            ax.axvline(WARMUP_COUNT - 0.5, color="#888", linestyle="--", linewidth=0.7)
            # Show threshold-relevant line as half-total; at step 0, total = 1.5, so 0.4·1.5 = 0.6
            ax.axhline(THRESHOLD, color="#c44e52", linestyle=":", linewidth=0.7, alpha=0.7,
                       label=f"threshold {THRESHOLD}" if (col_idx == 0 and row_idx == 0) else None)
            ax.set_title(f"{cls} · Topology {t}")
            ax.set_ylim(0, 1); ax.grid(alpha=0.3)
            if col_idx == 0:
                ax.set_ylabel("flow_weight")
            if row_idx == 1:
                ax.set_xlabel("fold step")
    axes[0, 0].legend(loc="lower left", fontsize=7)
    fig.suptitle(f"Experiment 4 — 6-weight trajectories (threshold {THRESHOLD})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_threshold_comparison(trials: list[dict[str, Any]], exp3_trials: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(9, 4.5))
    e3_by = {tr["seed"]: tr for tr in exp3_trials}
    n = len(trials)
    x = np.arange(n)
    width = 0.2
    fixed05 = [e3_by[tr["seed"]]["experiment_A"]["macro_f1"] for tr in trials]
    fixed04 = [tr["fixed_0_4"]["macro_f1"] for tr in trials]
    adapt05 = [e3_by[tr["seed"]]["experiment_B"]["macro_f1"] for tr in trials]
    adapt04 = [tr["adaptive_0_4"]["macro_f1"] for tr in trials]
    ax.bar(x - 1.5 * width, fixed05, width, label="Fixed 0.5", color="#4c72b0")
    ax.bar(x - 0.5 * width, fixed04, width, label="Fixed 0.4", color="#55a868")
    ax.bar(x + 0.5 * width, adapt05, width, label="Adaptive 0.5 (Exp 3)", color="#dd8452")
    ax.bar(x + 1.5 * width, adapt04, width, label="Adaptive 0.4 (Exp 4)", color="#c44e52")
    ax.set_xticks(x)
    ax.set_xticklabels([f"trial {i+1}" for i in range(n)])
    ax.set_ylim(0, 1)
    ax.set_ylabel("macro F1")
    ax.set_title("Threshold 0.5 vs 0.4 — Fixed and Adaptive")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_f1_comparison_4exp(
    stats4: dict[str, Any],
    exp1_stats: dict[str, Any],
    exp2_stats: dict[str, Any],
    exp3_stats: dict[str, Any],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(11, 4.5))
    n = len(stats4["results_A"])
    x = np.arange(n)
    width = 0.14
    bars = [
        (stats4["results_A"], "Fixed 0.4", "#4c72b0"),
        (exp1_stats["results_B"], "Exp 1 (×0.7 shared)", "#dd8452"),
        (exp2_stats["results_B"], "Exp 2 (×0.9 shared)", "#55a868"),
        (exp3_stats["results_B"], "Exp 3 (label-specific, 0.5)", "#e76f51"),
        (stats4["results_B"], "Exp 4 (label-specific, 0.4)", "#c44e52"),
    ]
    offsets = np.linspace(-2, 2, len(bars)) * width
    for offset, (vals, label, color) in zip(offsets, bars):
        ax.bar(x + offset, vals, width, label=label, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels([f"trial {i+1}" for i in range(n)])
    ax.set_ylim(0, 1)
    ax.set_ylabel("macro F1")
    ax.set_title("Stage 1 Experiments 1 – 4 per-trial macro F1")
    ax.legend(fontsize=7, loc="lower right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_fp_fn_analysis(
    trials: list[dict[str, Any]],
    exp3_trials: list[dict[str, Any]],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    f05 = pool_confusion(exp3_trials, "experiment_A")
    f04 = pool_confusion(trials, "fixed_0_4")
    a05 = pool_confusion(exp3_trials, "experiment_B")
    a04 = pool_confusion(trials, "adaptive_0_4")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, cls in zip(axes, LABELS):
        categories = ["Fixed_0.5", "Fixed_0.4", "Adaptive_0.5", "Adaptive_0.4"]
        tps = [f05[cls]["tp"], f04[cls]["tp"], a05[cls]["tp"], a04[cls]["tp"]]
        fps = [f05[cls]["fp"], f04[cls]["fp"], a05[cls]["fp"], a04[cls]["fp"]]
        fns = [f05[cls]["fn"], f04[cls]["fn"], a05[cls]["fn"], a04[cls]["fn"]]
        x = np.arange(len(categories))
        width = 0.28
        ax.bar(x - width, tps, width, label="TP", color="#2a9d8f")
        ax.bar(x, fps, width, label="FP", color="#e76f51")
        ax.bar(x + width, fns, width, label="FN", color="#f4a261")
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=15)
        ax.set_title(f"{cls} (pooled across 5 × 11 = 55 folds)")
        ax.grid(axis="y", alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("False Positive / False Negative counts by experiment")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:
    ensure_utf8_streams()
    records = build_fold_records()
    print(f"[load] clean fold records: {len(records)}")

    exp1_trials, exp1_stats = load_prior(EXP1_TRIALS_PATH, EXP1_STATS_PATH)
    exp2_trials, exp2_stats = load_prior(EXP2_TRIALS_PATH, EXP2_STATS_PATH)
    exp3_trials, exp3_stats = load_prior(EXP3_TRIALS_PATH, EXP3_STATS_PATH)
    e3_by_seed = {tr["seed"]: tr for tr in exp3_trials}

    trials: list[dict[str, Any]] = []
    for seed in SEEDS:
        print(f"[trial] seed={seed} ...", flush=True)
        tr = run_trial_low_threshold(records, seed, threshold=THRESHOLD)
        trials.append(tr)
        print(
            f"  Fixed_0.4 = {tr['fixed_0_4']['macro_f1']:.3f}; "
            f"Adaptive_0.4 = {tr['adaptive_0_4']['macro_f1']:.3f}"
        )

    fixed_0_4_f1 = [tr["fixed_0_4"]["macro_f1"] for tr in trials]
    adaptive_0_4_f1 = [tr["adaptive_0_4"]["macro_f1"] for tr in trials]
    fixed_0_5_f1 = [e3_by_seed[tr["seed"]]["experiment_A"]["macro_f1"] for tr in trials]

    stats_vs_f04 = paired_statistics(fixed_0_4_f1, adaptive_0_4_f1)
    stats_vs_f05 = paired_statistics(fixed_0_5_f1, adaptive_0_4_f1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    TRIALS_PATH.write_text(
        json.dumps(
            {
                "trials": trials, "n_folds": len(records),
                "warmup_count": WARMUP_COUNT, "seeds": SEEDS,
                "threshold": THRESHOLD,
                "weight_structure": "label-specific (6 weights)",
                "failure_multiplier": 0.7,
                "records": records,
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps(
            {"primary_vs_fixed_0_4": stats_vs_f04,
             "reference_vs_fixed_0_5": stats_vs_f05},
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(
        render_summary(
            trials, stats_vs_f04, stats_vs_f05,
            exp1_trials, exp1_stats,
            exp2_trials, exp2_stats,
            exp3_trials, exp3_stats,
            records,
        ),
        encoding="utf-8",
    )

    plot_weight_trajectory_exp4(trials, GRAPHS_DIR / "weight_trajectory_exp4.png")
    plot_threshold_comparison(trials, exp3_trials, GRAPHS_DIR / "threshold_comparison.png")
    plot_f1_comparison_4exp(
        stats_vs_f04, exp1_stats, exp2_stats, exp3_stats,
        GRAPHS_DIR / "f1_comparison_4exp.png",
    )
    plot_fp_fn_analysis(trials, exp3_trials, GRAPHS_DIR / "fp_fn_analysis.png")

    print()
    print("=== Phase 1.4d Stage 1 Experiment 4 summary ===")
    print(
        f"Primary (vs Fixed_0.4): Δ = {stats_vs_f04['mean_diff']:+.3f}, "
        f"p = {stats_vs_f04['paired_t_test']['p_value']:.4f}, "
        f"d = {stats_vs_f04['cohens_d']}, "
        f"CI = [{stats_vs_f04['ci_95'][0]:+.3f}, {stats_vs_f04['ci_95'][1]:+.3f}]"
    )
    print(
        f"Reference (vs Fixed_0.5): Δ = {stats_vs_f05['mean_diff']:+.3f}, "
        f"p = {stats_vs_f05['paired_t_test']['p_value']:.4f}"
    )
    print(f"Go (all 3 criteria vs Fixed_0.4): {stats_vs_f04['go_judgment']['overall_go']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
