"""Phase 1.4d Stage 1 Experiment 3 — label-specific flow_weight.

Experiment 1 (sdnd-proof ×0.7, shared weight per topology) and
Experiment 2 (×0.9, shared weight per topology) both returned No-Go.
The structural diagnosis from Experiment 2 is that a single scalar
weight per topology cannot diverge without collapsing ensemble
diversity.

Experiment 3 changes the weight *structure* rather than the penalty:
each topology owns TWO independent scalar weights — one for
``sparrow``, one for ``bulbul`` — and each is updated by the
sdnd-proof rule (×0.7 penalty, +0.1·(1−w) success) against its own
label's correctness. The ensemble vote is then computed per-label
with per-label total normalisation. 5 trials, same seeds, same clean
22 folds, same Fixed / Adaptive split, same 3-criterion Go gate.
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

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_label_specific"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary.json"
STATS_PATH = OUT_DIR / "statistical_analysis.json"

LABELS = ("sparrow", "bulbul")
TOPOLOGIES = ("A", "B", "C")


def initial_label_weights() -> dict[str, dict[str, float]]:
    return {t: {cls: INITIAL_WEIGHT for cls in LABELS} for t in TOPOLOGIES}


def run_trial(records: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    order = list(range(len(records)))
    rng.shuffle(order)

    # Experiment A (Fixed) — 6 weights all at 0.5 for the whole trial.
    fixed_weights = initial_label_weights()
    fixed_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    fixed_per_fold: list[dict[str, Any]] = []
    for step, idx in enumerate(order):
        rec = records[idx]
        pred = weighted_vote_label_specific(rec["predictions"], fixed_weights)
        fixed_per_fold.append({
            "step": step,
            "video_id": rec["video_id"],
            "pred": pred,
            "gt": rec["ground_truth"],
        })
        if step >= WARMUP_COUNT:
            fixed_eval_pairs.append((pred, rec["ground_truth"]))
    fixed_metrics = compute_f1_bundle(fixed_eval_pairs)

    # Experiment B (Adaptive label-specific) — 6 weights, each updated per fold.
    adaptive_weights = initial_label_weights()
    adaptive_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    weight_trajectory: list[dict[str, Any]] = [
        {"step": -1, "weights": copy.deepcopy(adaptive_weights)}
    ]
    adaptive_per_fold: list[dict[str, Any]] = []

    for step, idx in enumerate(order):
        rec = records[idx]
        pred = weighted_vote_label_specific(rec["predictions"], adaptive_weights)
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
            "step": step,
            "video_id": rec["video_id"],
            "pred": pred,
            "gt": rec["ground_truth"],
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
        "shuffle_order": order,
        "fold_video_ids_in_order": [records[i]["video_id"] for i in order],
        "warmup_folds": [records[i]["video_id"] for i in order[:WARMUP_COUNT]],
        "eval_folds":   [records[i]["video_id"] for i in order[WARMUP_COUNT:]],
        "experiment_A": {
            "final_weights": fixed_weights,
            "macro_f1":    fixed_metrics["macro_f1"],
            "sparrow_f1":  fixed_metrics["sparrow_f1"],
            "bulbul_f1":   fixed_metrics["bulbul_f1"],
            "confusion":   fixed_metrics["confusion"],
            "per_fold":    fixed_per_fold,
        },
        "experiment_B": {
            "initial_weights": initial_label_weights(),
            "final_weights":   adaptive_weights,
            "weight_trajectory": weight_trajectory,
            "macro_f1":    adaptive_metrics["macro_f1"],
            "sparrow_f1":  adaptive_metrics["sparrow_f1"],
            "bulbul_f1":   adaptive_metrics["bulbul_f1"],
            "confusion":   adaptive_metrics["confusion"],
            "per_fold":    adaptive_per_fold,
        },
    }


def _collapse_exp1_weights(final_weights: dict[str, float]) -> dict[str, dict[str, float]]:
    """Lift Experiment 1/2 single-weight dict to label-specific shape for comparison."""
    return {t: {cls: final_weights[t] for cls in LABELS} for t in TOPOLOGIES}


def load_prior_experiment(trials_path: Path, stats_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    trials = json.loads(trials_path.read_text(encoding="utf-8"))["trials"]
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    return trials, stats


def render_summary(
    trials: list[dict[str, Any]],
    stats_result: dict[str, Any],
    exp1_trials: list[dict[str, Any]],
    exp1_stats: dict[str, Any],
    exp2_trials: list[dict[str, Any]],
    exp2_stats: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    lines = [
        "# Phase 1.4d Stage 1 Experiment 3 — label-specific flow_weight",
        "",
        "Weight structure changed from 3 scalars (one per topology) to 6 scalars ",
        "(one per **topology × label** pair). The sdnd-proof update rule is restored to ",
        "its original form (×0.7 penalty) but applied *per label*, so a topology that ",
        "is strong on bulbul but weak on sparrow can lose its sparrow-weight without ",
        "giving up its bulbul-weight.",
        "",
        f"Same design as Exp 1 / Exp 2 otherwise: 5 trials on seeds {SEEDS}, clean "
        f"22 folds (11 self + 11 YouTube Tier A/B/B'), first {WARMUP_COUNT} folds "
        "warm-up, last 11 folds evaluation. Predictions reused from "
        "`results/phase1_3_extended/`.",
        "",
        "## Per-trial macro F1 across 3 experiments",
        "",
        "| Trial | Seed | Fixed | Adaptive Exp 1 | Adaptive Exp 2 | Adaptive Exp 3 | Exp 1 Δ | Exp 2 Δ | Exp 3 Δ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    exp1_by_seed = {tr["seed"]: tr for tr in exp1_trials}
    exp2_by_seed = {tr["seed"]: tr for tr in exp2_trials}
    for i, tr in enumerate(trials, start=1):
        fa = tr["experiment_A"]["macro_f1"]
        fb = tr["experiment_B"]["macro_f1"]
        e1 = exp1_by_seed.get(tr["seed"])
        e2 = exp2_by_seed.get(tr["seed"])
        e1_b = e1["experiment_B"]["macro_f1"] if e1 else float("nan")
        e2_b = e2["experiment_B"]["macro_f1"] if e2 else float("nan")
        d1 = e1_b - (e1["experiment_A"]["macro_f1"] if e1 else float("nan"))
        d2 = e2_b - (e2["experiment_A"]["macro_f1"] if e2 else float("nan"))
        d3 = fb - fa
        lines.append(
            f"| {i} | {tr['seed']} | {fa:.3f} "
            f"| {e1_b:.3f} | {e2_b:.3f} | {fb:.3f} "
            f"| {d1:+.3f} | {d2:+.3f} | {d3:+.3f} |"
        )
    lines.append("")

    # Per-label F1 (Exp 3 only)
    lines.append("## Per-trial F1 breakdown (Experiment 3)")
    lines.append("")
    lines.append("| Trial | Seed | Fixed sparrow | Fixed bulbul | Adaptive sparrow | Adaptive bulbul |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for i, tr in enumerate(trials, start=1):
        a, b = tr["experiment_A"], tr["experiment_B"]
        lines.append(
            f"| {i} | {tr['seed']} | {a['sparrow_f1']:.3f} | {a['bulbul_f1']:.3f} "
            f"| {b['sparrow_f1']:.3f} | {b['bulbul_f1']:.3f} |"
        )
    lines.append("")

    # Final label-specific weights
    lines.append("## Experiment 3 final weights (per trial)")
    lines.append("")
    lines.append("| Trial | Seed | A.sparrow | A.bulbul | B.sparrow | B.bulbul | C.sparrow | C.bulbul |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    sums = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    for i, tr in enumerate(trials, start=1):
        w = tr["experiment_B"]["final_weights"]
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

    # Mean final weights matrix
    lines.append("## Mean final weights (5-trial average)")
    lines.append("")
    lines.append("|          | sparrow | bulbul |")
    lines.append("|---|---:|---:|")
    for t in TOPOLOGIES:
        lines.append(f"| Topology {t} | {sums[t]['sparrow']/n_tr:.3f} | {sums[t]['bulbul']/n_tr:.3f} |")
    lines.append("")

    # Statistical analysis block
    s = stats_result
    lines.append("## Experiment 3 statistical analysis")
    lines.append("")
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

    # Go judgment 3-way
    lines.append("## Go judgment (sdnd-proof 3 criteria)")
    lines.append("")
    lines.append("| Criterion | Threshold | Exp 1 | Exp 2 | Exp 3 | Exp 3 pass |")
    lines.append("|---|---|---:|---:|---:|:-:|")
    j = s["go_judgment"]
    def d_fmt(d): return f"{d:.3f}" if d is not None else "undefined"
    lines.append(
        f"| p-value | < 0.05 | {exp1_stats['paired_t_test']['p_value']:.4f} "
        f"| {exp2_stats['paired_t_test']['p_value']:.4f} "
        f"| {s['paired_t_test']['p_value']:.4f} "
        f"| {'Y' if j['p_value_pass'] else 'N'} |"
    )
    lines.append(
        f"| Cohen's d | >= 0.8 | {d_fmt(exp1_stats['cohens_d'])} "
        f"| {d_fmt(exp2_stats['cohens_d'])} "
        f"| {d_str} | {'Y' if j['cohens_d_pass'] else 'N'} |"
    )
    lines.append(
        f"| 95% CI lower | > 0 | {exp1_stats['ci_95'][0]:+.3f} "
        f"| {exp2_stats['ci_95'][0]:+.3f} "
        f"| {s['ci_95'][0]:+.3f} | {'Y' if j['ci_pass'] else 'N'} |"
    )
    exp3_overall = "Go" if j["overall_go"] else "No-Go"
    lines.append(
        f"| **Overall** | all pass "
        f"| **{'Go' if exp1_stats['go_judgment']['overall_go'] else 'No-Go'}** "
        f"| **{'Go' if exp2_stats['go_judgment']['overall_go'] else 'No-Go'}** "
        f"| **{exp3_overall}** | |"
    )
    lines.append("")

    # Label-specific weight discussion
    lines.append("## Label-specific weight discussion")
    lines.append("")
    mean_ws = {t: {cls: sums[t][cls] / n_tr for cls in LABELS} for t in TOPOLOGIES}
    for t in TOPOLOGIES:
        sp = mean_ws[t]["sparrow"]
        bu = mean_ws[t]["bulbul"]
        if abs(sp - bu) >= 0.10:
            stronger = "sparrow" if sp > bu else "bulbul"
            lines.append(
                f"- Topology {t}: sparrow={sp:.3f} vs bulbul={bu:.3f} — "
                f"meaningful split favouring **{stronger}** (|Δ|={abs(sp - bu):.3f}). "
                "Label independence detected a per-label strength difference that the "
                "shared-weight rule could not express."
            )
        else:
            lines.append(
                f"- Topology {t}: sparrow={sp:.3f} vs bulbul={bu:.3f} — no meaningful "
                "per-label split (|Δ|<0.10)."
            )
    lines.append("")

    # Interpret verdict
    if j["overall_go"]:
        lines.append(
            "**Go**: label-specific weights clear all three sdnd-proof criteria. "
            "Hypothesis confirmed — a single scalar per topology was the limiting factor."
        )
    else:
        lines.append(
            "**No-Go**: label independence preserves per-label weight structure but does "
            "not cross the 3-criterion bar on n=5 trials. The label-specific split may "
            "still be a meaningful diagnostic — see the weight table above for which "
            "topologies gain a per-label identity."
        )
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append(
        "- 5 trials over the same 22 folds measure sensitivity to ordering, not dataset "
        "sampling. Bootstrap of the fold set is needed for a broader claim."
    )
    lines.append(
        "- Per-label independence doubles the number of updates per fold (6 updates vs 3). "
        "With ×0.7 on failures, the 6-weight system decays faster toward zero on whatever "
        "label the topology gets wrong frequently."
    )
    lines.append(
        "- The 0.5 decision threshold still applies. If none of the 6 weights grow ≈ >0.5·total "
        "for their own label, the per-label majority is purely decided by the count of 1s — same "
        "as Fixed."
    )
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `statistical_analysis.json`")
    lines.append("- `graphs/weight_trajectory_label_specific.png`")
    lines.append("- `graphs/label_specific_comparison.png`")
    lines.append("- `graphs/f1_comparison_3exp.png`")
    lines.append("")
    return "\n".join(lines)


def plot_weight_trajectory_label_specific(trials: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    colors = {42: "#2a9d8f", 137: "#e76f51", 256: "#264653",
              512: "#f4a261", 1024: "#6a4c93"}
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharey=True, sharex=True)
    for row_idx, cls in enumerate(LABELS):
        for col_idx, t in enumerate(TOPOLOGIES):
            ax = axes[row_idx, col_idx]
            for tr in trials:
                traj = tr["experiment_B"]["weight_trajectory"]
                steps = [e["step"] for e in traj]
                vals = [e["weights"][t][cls] for e in traj]
                ax.plot(
                    steps, vals, marker=".", linewidth=1.0, alpha=0.9,
                    color=colors.get(tr["seed"], "#444444"),
                    label=f"seed {tr['seed']}" if (col_idx == 0 and row_idx == 0) else None,
                )
            ax.axvline(WARMUP_COUNT - 0.5, color="#888888", linestyle="--", linewidth=0.7)
            ax.set_title(f"{cls} · Topology {t}")
            ax.set_ylim(0, 1)
            ax.grid(alpha=0.3)
            if col_idx == 0:
                ax.set_ylabel("flow_weight")
            if row_idx == 1:
                ax.set_xlabel("fold step")
    axes[0, 0].legend(loc="lower left", fontsize=7)
    fig.suptitle("Experiment 3 — 6-weight trajectories (row = label, col = topology)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_label_specific_comparison(trials: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    # Mean final weights matrix as grouped bars.
    sums = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    for tr in trials:
        w = tr["experiment_B"]["final_weights"]
        for t in TOPOLOGIES:
            for cls in LABELS:
                sums[t][cls] += w[t][cls]
    n = len(trials) or 1
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(TOPOLOGIES))
    width = 0.38
    sp_values = [sums[t]["sparrow"] / n for t in TOPOLOGIES]
    bu_values = [sums[t]["bulbul"]  / n for t in TOPOLOGIES]
    ax.bar(x - width / 2, sp_values, width, label="sparrow", color="#4c72b0")
    ax.bar(x + width / 2, bu_values, width, label="bulbul",  color="#dd8452")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Topology {t}" for t in TOPOLOGIES])
    ax.set_ylabel("mean final flow_weight")
    ax.set_ylim(0, 1)
    ax.set_title("Experiment 3 — mean final weights by topology × label")
    ax.axhline(0.5, color="#555555", linestyle=":", linewidth=0.8, label="initial 0.5")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_f1_comparison_3exp(
    stats_result: dict[str, Any],
    exp1_stats: dict[str, Any],
    exp2_stats: dict[str, Any],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(10, 4.5))
    n = len(stats_result["results_A"])
    x = np.arange(n)
    width = 0.18
    ax.bar(x - 1.5 * width, stats_result["results_A"], width, label="Fixed", color="#4c72b0")
    ax.bar(x - 0.5 * width, exp1_stats["results_B"], width, label="Adaptive Exp 1 (×0.7)", color="#dd8452")
    ax.bar(x + 0.5 * width, exp2_stats["results_B"], width, label="Adaptive Exp 2 (×0.9)", color="#55a868")
    ax.bar(x + 1.5 * width, stats_result["results_B"], width, label="Adaptive Exp 3 (label-specific)", color="#c44e52")
    ax.set_xticks(x)
    ax.set_xticklabels([f"trial {i+1}" for i in range(n)])
    ax.set_ylabel("macro F1 (second half, 11 folds)")
    ax.set_ylim(0, 1)
    ax.set_title("Fixed vs 3 Adaptive variants (Phase 1.4d Stage 1)")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:
    ensure_utf8_streams()
    records = build_fold_records()
    print(f"[load] clean fold records: {len(records)}")

    exp1_trials, exp1_stats = load_prior_experiment(EXP1_TRIALS_PATH, EXP1_STATS_PATH)
    exp2_trials, exp2_stats = load_prior_experiment(EXP2_TRIALS_PATH, EXP2_STATS_PATH)
    print(f"[load] Exp 1 trials: {len(exp1_trials)}, Exp 2 trials: {len(exp2_trials)}")

    trials: list[dict[str, Any]] = []
    for seed in SEEDS:
        print(f"[trial] seed={seed} ...", flush=True)
        tr = run_trial(records, seed)
        trials.append(tr)
        w = tr["experiment_B"]["final_weights"]
        print(
            f"  Fixed = {tr['experiment_A']['macro_f1']:.3f}; "
            f"Adaptive = {tr['experiment_B']['macro_f1']:.3f}"
        )
        print(
            "  final weights: "
            f"A.s={w['A']['sparrow']:.3f} A.b={w['A']['bulbul']:.3f} "
            f"B.s={w['B']['sparrow']:.3f} B.b={w['B']['bulbul']:.3f} "
            f"C.s={w['C']['sparrow']:.3f} C.b={w['C']['bulbul']:.3f}"
        )

    results_A = [tr["experiment_A"]["macro_f1"] for tr in trials]
    results_B = [tr["experiment_B"]["macro_f1"] for tr in trials]
    stats_result = paired_statistics(results_A, results_B)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    TRIALS_PATH.write_text(
        json.dumps(
            {
                "trials": trials,
                "n_folds": len(records),
                "warmup_count": WARMUP_COUNT,
                "seeds": SEEDS,
                "records": records,
                "weight_structure": "label-specific (6 weights: 3 topologies × 2 labels)",
                "failure_multiplier": 0.7,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps(stats_result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(
        render_summary(trials, stats_result, exp1_trials, exp1_stats, exp2_trials, exp2_stats, records),
        encoding="utf-8",
    )

    plot_weight_trajectory_label_specific(trials, GRAPHS_DIR / "weight_trajectory_label_specific.png")
    plot_label_specific_comparison(trials, GRAPHS_DIR / "label_specific_comparison.png")
    plot_f1_comparison_3exp(stats_result, exp1_stats, exp2_stats, GRAPHS_DIR / "f1_comparison_3exp.png")

    print()
    print("=== Phase 1.4d Stage 1 Experiment 3 summary ===")
    print(f"Mean Δ macro F1 = {stats_result['mean_diff']:+.3f}")
    print(f"p = {stats_result['paired_t_test']['p_value']:.4f}, "
          f"d = {stats_result['cohens_d']}, "
          f"CI = [{stats_result['ci_95'][0]:+.3f}, {stats_result['ci_95'][1]:+.3f}]")
    print(f"Go (all 3 criteria): {stats_result['go_judgment']['overall_go']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
