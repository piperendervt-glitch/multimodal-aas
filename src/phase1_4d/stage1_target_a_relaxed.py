"""Phase 1.4d Stage 1 Experiment 2 — relaxed-penalty flow_weight.

Experiment 1 (commit 45f5b9c, `stage1_target_a_sdnd_proof.py`) inherited
the sdnd-proof rule verbatim (success +0.1·(1−w), failure ×0.7) and got
No-Go on all three criteria; the adaptive ensemble collapsed onto
Topology C and lost the diversity advantage of the fixed equal-weight
vote.

Experiment 2 tests a single hypothesis: the 0.7 multiplicative penalty
is too harsh for a multi-node ensemble. Raising the multiplier to 0.9
("failure ×0.9") keeps weaker topologies contributing for longer. All
other pieces — seeds, shuffle, clean 22 folds, second-half evaluation,
per-fold success definition, sdnd-proof 3-criterion Go gate — are
reused from Experiment 1.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4d.common.flow_weight import update_weight_relaxed
from phase1_4d.stage1_target_a_sdnd_proof import (
    SEEDS,
    WARMUP_COUNT,
    build_fold_records,
    ensure_utf8_streams,
    paired_statistics,
    run_trial,
)

EXP1_TRIALS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_sdnd_proof" / "trials_summary.json"
EXP1_STATS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_sdnd_proof" / "statistical_analysis.json"

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_relaxed"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary.json"
STATS_PATH = OUT_DIR / "statistical_analysis.json"

FAILURE_RATE = 0.9


def load_exp1() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    trials = json.loads(EXP1_TRIALS_PATH.read_text(encoding="utf-8"))["trials"]
    stats = json.loads(EXP1_STATS_PATH.read_text(encoding="utf-8"))
    return trials, stats


def render_summary(
    trials: list[dict[str, Any]],
    stats_result: dict[str, Any],
    exp1_trials: list[dict[str, Any]],
    exp1_stats: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    lines = [
        "# Phase 1.4d Stage 1 Experiment 2 — relaxed-penalty flow_weight",
        "",
        "Single-knob change vs Experiment 1 (commit 45f5b9c):",
        "",
        "    Exp 1: success = w + 0.1 · (1 − w), failure = w × **0.7** (sdnd-proof)",
        "    Exp 2: success = w + 0.1 · (1 − w), failure = w × **0.9** (relaxed)",
        "",
        "All other design choices are identical — 5 trials over seeds "
        f"{SEEDS}, clean 22 folds (11 self + 11 YouTube Tier A/B/B'), "
        f"first {WARMUP_COUNT} folds warm-up, last {len(records) - WARMUP_COUNT} folds "
        "evaluation, predictions reused from `results/phase1_3_extended/`.",
        "",
        "## Per-trial results (Fixed / Adaptive Exp 1 / Adaptive Exp 2)",
        "",
        "| Trial | Seed | Fixed | Adaptive Exp 1 | Adaptive Exp 2 | Exp 1 Δ | Exp 2 Δ |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    exp1_by_seed = {tr["seed"]: tr for tr in exp1_trials}
    for i, tr in enumerate(trials, start=1):
        fa = tr["experiment_A"]["macro_f1"]
        fb = tr["experiment_B"]["macro_f1"]
        exp1 = exp1_by_seed.get(tr["seed"])
        fa_exp1 = exp1["experiment_A"]["macro_f1"] if exp1 else float("nan")
        fb_exp1 = exp1["experiment_B"]["macro_f1"] if exp1 else float("nan")
        d1 = fb_exp1 - fa_exp1
        d2 = fb - fa
        lines.append(
            f"| {i} | {tr['seed']} | {fa:.3f} "
            f"| {fb_exp1:.3f} | {fb:.3f} "
            f"| {d1:+.3f} | {d2:+.3f} |"
        )
    lines.append("")

    # Per-trial F1 breakdown (Exp 2 only for brevity)
    lines.append("## Per-trial F1 breakdown (Experiment 2)")
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

    # Final weights
    lines.append("## Final weights comparison (Experiment 1 vs 2)")
    lines.append("")
    lines.append("| Trial | Seed | Exp 1 w_A | Exp 1 w_B | Exp 1 w_C | Exp 2 w_A | Exp 2 w_B | Exp 2 w_C |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    sum_exp1 = {"A": 0.0, "B": 0.0, "C": 0.0}
    sum_exp2 = {"A": 0.0, "B": 0.0, "C": 0.0}
    for i, tr in enumerate(trials, start=1):
        exp1 = exp1_by_seed.get(tr["seed"])
        w1 = exp1["experiment_B"]["final_weights"] if exp1 else {"A": 0, "B": 0, "C": 0}
        w2 = tr["experiment_B"]["final_weights"]
        for t in ("A", "B", "C"):
            sum_exp1[t] += w1[t]
            sum_exp2[t] += w2[t]
        lines.append(
            f"| {i} | {tr['seed']} "
            f"| {w1['A']:.3f} | {w1['B']:.3f} | {w1['C']:.3f} "
            f"| {w2['A']:.3f} | {w2['B']:.3f} | {w2['C']:.3f} |"
        )
    n_tr = len(trials) or 1
    lines.append(
        f"| mean | - | {sum_exp1['A']/n_tr:.3f} | {sum_exp1['B']/n_tr:.3f} | {sum_exp1['C']/n_tr:.3f} "
        f"| {sum_exp2['A']/n_tr:.3f} | {sum_exp2['B']/n_tr:.3f} | {sum_exp2['C']/n_tr:.3f} |"
    )
    lines.append("")

    # Statistics block
    s = stats_result
    lines.append("## Experiment 2 statistical analysis")
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

    # Go comparison
    lines.append("## Go judgment (sdnd-proof 3 criteria)")
    lines.append("")
    lines.append("| Criterion | Threshold | Exp 1 value | Exp 2 value | Exp 2 pass |")
    lines.append("|---|---|---:|---:|:-:|")
    j = s["go_judgment"]
    exp1_p = exp1_stats["paired_t_test"]["p_value"]
    exp1_d = exp1_stats["cohens_d"]
    exp1_ci_low = exp1_stats["ci_95"][0]
    d1_str = f"{exp1_d:.3f}" if exp1_d is not None else "undefined"
    lines.append(
        f"| p-value | < 0.05 | {exp1_p:.4f} | {s['paired_t_test']['p_value']:.4f} "
        f"| {'Y' if j['p_value_pass'] else 'N'} |"
    )
    lines.append(
        f"| Cohen's d | >= 0.8 | {d1_str} | {d_str} "
        f"| {'Y' if j['cohens_d_pass'] else 'N'} |"
    )
    lines.append(
        f"| 95% CI lower | > 0 | {exp1_ci_low:+.3f} | {s['ci_95'][0]:+.3f} "
        f"| {'Y' if j['ci_pass'] else 'N'} |"
    )
    exp1_overall = "No-Go" if not exp1_stats["go_judgment"]["overall_go"] else "Go"
    exp2_overall = "Go" if j["overall_go"] else "No-Go"
    lines.append(
        f"| **Overall** | all pass | **{exp1_overall}** | **{exp2_overall}** | |"
    )
    lines.append("")

    # Diversity discussion
    lines.append("## Weight-trajectory discussion")
    lines.append("")
    lines.append(
        f"- Exp 1 mean final weights: A = {sum_exp1['A']/n_tr:.3f}, "
        f"B = {sum_exp1['B']/n_tr:.3f}, C = {sum_exp1['C']/n_tr:.3f}"
    )
    lines.append(
        f"- Exp 2 mean final weights: A = {sum_exp2['A']/n_tr:.3f}, "
        f"B = {sum_exp2['B']/n_tr:.3f}, C = {sum_exp2['C']/n_tr:.3f}"
    )
    e1_spread = max(sum_exp1.values()) - min(sum_exp1.values())
    e2_spread = max(sum_exp2.values()) - min(sum_exp2.values())
    lines.append(
        f"- Weight spread (max − min) across topologies: "
        f"Exp 1 = {e1_spread/n_tr:.3f}, Exp 2 = {e2_spread/n_tr:.3f}"
    )
    if e2_spread < e1_spread:
        lines.append(
            "- Exp 2's smaller spread confirms the relaxed penalty preserves more "
            "ensemble diversity than Exp 1."
        )
    else:
        lines.append(
            "- Exp 2 did NOT preserve more diversity than Exp 1; the relaxation "
            "was insufficient to keep weaker topologies in the vote."
        )
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append(
        "- n = 5 trials with non-independent shuffles (same 22 folds, different "
        "permutations). The t-test measures sensitivity to ordering, not to "
        "dataset sampling."
    )
    lines.append(
        "- Fixed macro F1 is already 0.861 ± 0.051 across trials; there is "
        "little headroom for Adaptive to show a large positive Δ. Improving "
        "Fixed is only realistic with a higher-capacity topology set."
    )
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `statistical_analysis.json`")
    lines.append("- `graphs/weight_trajectory_comparison.png` (Exp 1 vs Exp 2)")
    lines.append("- `graphs/f1_comparison.png` (Fixed vs Adaptive Exp 2)")
    lines.append("- `graphs/diff_distribution_comparison.png` (Exp 1 vs Exp 2 Δ)")
    lines.append("")
    return "\n".join(lines)


def plot_weight_trajectory_comparison(
    exp1_trials: list[dict[str, Any]],
    exp2_trials: list[dict[str, Any]],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharey=True, sharex=True)
    topologies = ["A", "B", "C"]
    colors = {42: "#2a9d8f", 137: "#e76f51", 256: "#264653",
              512: "#f4a261", 1024: "#6a4c93"}
    for row_idx, (row_label, trials_set) in enumerate((("Exp 1 (×0.7)", exp1_trials),
                                                       ("Exp 2 (×0.9)", exp2_trials))):
        for col_idx, t in enumerate(topologies):
            ax = axes[row_idx, col_idx]
            for tr in trials_set:
                traj = tr["experiment_B"]["weight_trajectory"]
                steps = [e["step"] for e in traj]
                vals = [e["weights"][t] for e in traj]
                ax.plot(steps, vals, marker=".", linewidth=1.0, alpha=0.9,
                        color=colors.get(tr["seed"], "#444444"),
                        label=f"seed {tr['seed']}" if col_idx == 0 else None)
            ax.axvline(WARMUP_COUNT - 0.5, color="#888888", linestyle="--", linewidth=0.7)
            ax.set_title(f"{row_label}  ·  Topology {t}")
            ax.set_ylim(0, 1)
            ax.grid(alpha=0.3)
            if col_idx == 0:
                ax.set_ylabel("flow_weight")
            if row_idx == 1:
                ax.set_xlabel("fold step")
    axes[0, 0].legend(loc="lower left", fontsize=7)
    fig.suptitle("Adaptive flow_weight trajectories — Exp 1 (×0.7) vs Exp 2 (×0.9)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_f1_comparison(stats_result: dict[str, Any], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(8, 4.5))
    n = len(stats_result["results_A"])
    x = np.arange(n)
    width = 0.38
    ax.bar(x - width / 2, stats_result["results_A"], width, label="Fixed (A)", color="#4c72b0")
    ax.bar(x + width / 2, stats_result["results_B"], width, label="Adaptive Exp 2 (×0.9)", color="#dd8452")
    ax.set_xticks(x)
    ax.set_xticklabels([f"trial {i+1}" for i in range(n)])
    ax.set_ylabel("macro F1 (second half, 11 folds)")
    ax.set_ylim(0, 1)
    ax.set_title("Fixed vs Adaptive (relaxed) macro F1")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_diff_distribution_comparison(
    exp1_stats: dict[str, Any],
    stats_result: dict[str, Any],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(9, 4.5))
    n = len(stats_result["diffs"])
    x = np.arange(n)
    width = 0.38
    ax.bar(x - width / 2, exp1_stats["diffs"], width, label="Exp 1 (×0.7)", color="#4c72b0")
    ax.bar(x + width / 2, stats_result["diffs"], width, label="Exp 2 (×0.9)", color="#dd8452")
    ax.axhline(0.0, color="#555555", linewidth=0.8)
    ax.axhline(exp1_stats["mean_diff"], color="#4c72b0", linestyle="--", linewidth=1.0,
               label=f"Exp 1 mean Δ = {exp1_stats['mean_diff']:+.3f}")
    ax.axhline(stats_result["mean_diff"], color="#dd8452", linestyle="--", linewidth=1.0,
               label=f"Exp 2 mean Δ = {stats_result['mean_diff']:+.3f}")
    ax.set_xticks(x)
    ax.set_xticklabels([f"trial {i+1}" for i in range(n)])
    ax.set_ylabel("Δ macro F1 (Adaptive − Fixed)")
    ax.set_title("Per-trial Δ distribution: Exp 1 vs Exp 2")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:
    ensure_utf8_streams()
    records = build_fold_records()
    print(f"[load] clean fold records: {len(records)}")

    exp1_trials, exp1_stats = load_exp1()
    print(f"[load] Experiment 1 trials: {len(exp1_trials)}")

    trials: list[dict[str, Any]] = []
    for seed in SEEDS:
        print(f"[trial] seed={seed} ...", flush=True)
        trial = run_trial(
            records,
            seed,
            update_fn=lambda w, s: update_weight_relaxed(w, s, failure_rate=FAILURE_RATE),
        )
        trials.append(trial)
        print(
            f"  Fixed = {trial['experiment_A']['macro_f1']:.3f}; "
            f"Adaptive = {trial['experiment_B']['macro_f1']:.3f}; "
            f"weights -> A={trial['experiment_B']['final_weights']['A']:.3f} "
            f"B={trial['experiment_B']['final_weights']['B']:.3f} "
            f"C={trial['experiment_B']['final_weights']['C']:.3f}"
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
                "failure_rate": FAILURE_RATE,
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
        render_summary(trials, stats_result, exp1_trials, exp1_stats, records),
        encoding="utf-8",
    )

    plot_weight_trajectory_comparison(
        exp1_trials, trials, GRAPHS_DIR / "weight_trajectory_comparison.png"
    )
    plot_f1_comparison(stats_result, GRAPHS_DIR / "f1_comparison.png")
    plot_diff_distribution_comparison(
        exp1_stats, stats_result, GRAPHS_DIR / "diff_distribution_comparison.png"
    )

    print()
    print("=== Phase 1.4d Stage 1 Experiment 2 summary ===")
    print(f"Mean Δ macro F1 = {stats_result['mean_diff']:+.3f}")
    print(f"p = {stats_result['paired_t_test']['p_value']:.4f}, "
          f"d = {stats_result['cohens_d']}, "
          f"CI = [{stats_result['ci_95'][0]:+.3f}, {stats_result['ci_95'][1]:+.3f}]")
    print(f"Go (all 3 criteria): {stats_result['go_judgment']['overall_go']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
