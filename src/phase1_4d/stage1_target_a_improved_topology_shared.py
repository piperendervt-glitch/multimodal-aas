"""Phase 1.4d Stage 1 Experiment 5a — shared weight over improved topology.

Same ensemble frame as Experiment 1 (sdnd-proof rule, shared scalar
weight per topology, threshold 0.5) but the topology predictions are
now drawn from the Phase 1.4a improved set:

    A  = phase1_3_extended/topology_a      (unchanged)
    B  = phase1_4a/topology_b_v3           (bbox prompt v3)
    C  = phase1_4a/topology_c_v3           (temporal_sync)

The Fixed baseline is also recomputed on the new topology set so the
Adaptive vs Fixed comparison stays fair. Direct side-by-side with
Experiment 1 is included in the summary.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4d.stage1_target_a_sdnd_proof import (
    SEEDS,
    WARMUP_COUNT,
    build_fold_records,
    ensure_utf8_streams,
    paired_statistics,
    run_trial,
)

IMPROVED_BASES = {
    "A": REPO_ROOT / "results" / "phase1_3_extended" / "topology_a",
    "B": REPO_ROOT / "results" / "phase1_4a" / "topology_b_v3",
    "C": REPO_ROOT / "results" / "phase1_4a" / "topology_c_v3",
}

EXP1_TRIALS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_sdnd_proof" / "trials_summary.json"
EXP1_STATS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_sdnd_proof" / "statistical_analysis.json"

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_improved_topology_shared"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary.json"
STATS_PATH = OUT_DIR / "statistical_analysis.json"


def load_prior(trials_path: Path, stats_path: Path):
    return (
        json.loads(trials_path.read_text(encoding="utf-8"))["trials"],
        json.loads(stats_path.read_text(encoding="utf-8")),
    )


def render_summary(trials, stats_result, exp1_trials, exp1_stats, records) -> str:
    e1_by = {tr["seed"]: tr for tr in exp1_trials}
    lines = [
        "# Phase 1.4d Stage 1 Experiment 5a — shared weight, improved topology",
        "",
        "Same rule as Experiment 1 (shared scalar weight per topology, sdnd-proof ",
        "rule ×0.7, threshold 0.5). The difference is the topology set:",
        "",
        "    Experiment 1: Phase 1.3 extended A / B / C",
        "    Experiment 5a: Phase 1.3 A + Phase 1.4a B_v3 + Phase 1.4a C_v3",
        "",
        "The Fixed baseline on the improved topology set is recomputed (Fixed_new); "
        "the Adaptive vs Fixed gate applies to Fixed_new, not to Fixed_old.",
        "",
        "## Per-trial macro F1",
        "",
        "| Trial | Seed | Fixed_old (Exp 1) | Fixed_new (Exp 5a) | Exp 1 Adaptive | **Exp 5a Adaptive** | Exp 1 Δ | **Exp 5a Δ (vs Fixed_new)** |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, tr in enumerate(trials, start=1):
        s = tr["seed"]
        fa = tr["experiment_A"]["macro_f1"]
        fb = tr["experiment_B"]["macro_f1"]
        e1 = e1_by[s]
        fa_old = e1["experiment_A"]["macro_f1"]
        fb_old = e1["experiment_B"]["macro_f1"]
        lines.append(
            f"| {i} | {s} | {fa_old:.3f} | {fa:.3f} "
            f"| {fb_old:.3f} | **{fb:.3f}** "
            f"| {fb_old - fa_old:+.3f} | **{fb - fa:+.3f}** |"
        )
    lines.append("")

    # Fixed comparison alone
    lines.append("## Fixed baseline comparison (mean across 5 trials)")
    lines.append("")
    fa_old_list = [e1_by[tr['seed']]["experiment_A"]["macro_f1"] for tr in trials]
    fa_new_list = [tr["experiment_A"]["macro_f1"] for tr in trials]
    mean_old = sum(fa_old_list) / len(fa_old_list)
    mean_new = sum(fa_new_list) / len(fa_new_list)
    lines.append(f"- Fixed_old (Phase 1.3 A/B/C): **{mean_old:.3f}** (trials: {[f'{x:.3f}' for x in fa_old_list]})")
    lines.append(f"- Fixed_new (Phase 1.3 A + B_v3 + C_v3): **{mean_new:.3f}** (trials: {[f'{x:.3f}' for x in fa_new_list]})")
    lines.append(f"- ΔFixed = **{mean_new - mean_old:+.3f}**")
    lines.append("")

    # Final weights (Exp 5a)
    lines.append("## Experiment 5a final Adaptive weights (per trial)")
    lines.append("")
    lines.append("| Trial | Seed | w_A | w_B | w_C |")
    lines.append("|---|---:|---:|---:|---:|")
    sums = {"A": 0.0, "B": 0.0, "C": 0.0}
    for i, tr in enumerate(trials, start=1):
        fw = tr["experiment_B"]["final_weights"]
        lines.append(f"| {i} | {tr['seed']} | {fw['A']:.3f} | {fw['B']:.3f} | {fw['C']:.3f} |")
        for t in sums:
            sums[t] += fw[t]
    n = len(trials) or 1
    lines.append(f"| mean | - | {sums['A']/n:.3f} | {sums['B']/n:.3f} | {sums['C']/n:.3f} |")
    lines.append("")

    s = stats_result
    lines.append("## Statistical analysis (Exp 5a vs Fixed_new)")
    lines.append("")
    lines.append(f"- Mean Δ: **{s['mean_diff']:+.3f}**")
    lines.append(f"- Std Δ: {s['std_diff']:.3f}")
    lines.append(
        f"- Paired t-test: t = {s['paired_t_test']['t_stat']:.3f}, "
        f"p = {s['paired_t_test']['p_value']:.4f}"
    )
    d_val = s["cohens_d"]
    d_str = f"{d_val:.3f}" if d_val is not None else "undefined"
    lines.append(f"- Cohen's d: {d_str}")
    lines.append(f"- 95% CI: [{s['ci_95'][0]:+.3f}, {s['ci_95'][1]:+.3f}]")
    lines.append("")

    lines.append("## Go judgment vs Experiment 1 (shared-weight comparison)")
    lines.append("")
    lines.append("| Criterion | Threshold | Exp 1 | **Exp 5a** | Exp 5a pass |")
    lines.append("|---|---|---:|---:|:-:|")
    j = s["go_judgment"]
    def dfmt(d): return f"{d:.3f}" if d is not None else "n/a"
    lines.append(
        f"| p-value | < 0.05 | {exp1_stats['paired_t_test']['p_value']:.4f} "
        f"| **{s['paired_t_test']['p_value']:.4f}** | {'Y' if j['p_value_pass'] else 'N'} |"
    )
    lines.append(
        f"| Cohen's d | >= 0.8 | {dfmt(exp1_stats['cohens_d'])} "
        f"| **{d_str}** | {'Y' if j['cohens_d_pass'] else 'N'} |"
    )
    lines.append(
        f"| 95% CI lower | > 0 | {exp1_stats['ci_95'][0]:+.3f} "
        f"| **{s['ci_95'][0]:+.3f}** | {'Y' if j['ci_pass'] else 'N'} |"
    )
    exp1_overall = "No-Go" if not exp1_stats["go_judgment"]["overall_go"] else "Go"
    exp5a_overall = "Go" if j["overall_go"] else "No-Go"
    lines.append(
        f"| **Overall** | all pass | **{exp1_overall}** | **{exp5a_overall}** | |"
    )
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append(
        "- Fixed_new uses the improved topology predictions with equal weights. Every "
        "shift in Fixed reflects the B_v3 + C_v3 upgrade, not the weight-learning rule."
    )
    lines.append(
        "- n=5 trials over shuffle-only variation; the paired t-test does not generalise "
        "to dataset sampling."
    )
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `statistical_analysis.json`")
    lines.append("- `graphs/weight_trajectory.png`")
    lines.append("- `graphs/f1_comparison_vs_exp1.png`")
    lines.append("")
    return "\n".join(lines)


def plot_weight_trajectory(trials, out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    colors = {42: "#2a9d8f", 137: "#e76f51", 256: "#264653",
              512: "#f4a261", 1024: "#6a4c93"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True)
    for ax, t in zip(axes, ["A", "B", "C"]):
        for tr in trials:
            traj = tr["experiment_B"]["weight_trajectory"]
            steps = [e["step"] for e in traj]
            vals = [e["weights"][t] for e in traj]
            ax.plot(steps, vals, marker=".", linewidth=1.2, color=colors.get(tr["seed"], "#444"),
                    label=f"seed {tr['seed']}")
        ax.axvline(WARMUP_COUNT - 0.5, color="#888", linestyle="--", linewidth=0.7)
        ax.set_title(f"Topology {t}")
        ax.set_xlabel("fold step")
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("flow_weight")
    axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("Exp 5a — Adaptive flow_weight (shared, improved topology)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_f1_comparison_vs_exp1(trials, exp1_trials, out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    e1_by = {tr["seed"]: tr for tr in exp1_trials}
    n = len(trials)
    x = np.arange(n)
    width = 0.2
    fa_old = [e1_by[tr["seed"]]["experiment_A"]["macro_f1"] for tr in trials]
    fa_new = [tr["experiment_A"]["macro_f1"] for tr in trials]
    fb_old = [e1_by[tr["seed"]]["experiment_B"]["macro_f1"] for tr in trials]
    fb_new = [tr["experiment_B"]["macro_f1"] for tr in trials]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(x - 1.5*width, fa_old, width, label="Fixed_old (Exp 1)", color="#4c72b0")
    ax.bar(x - 0.5*width, fa_new, width, label="Fixed_new (Exp 5a)", color="#55a868")
    ax.bar(x + 0.5*width, fb_old, width, label="Adaptive (Exp 1)", color="#dd8452")
    ax.bar(x + 1.5*width, fb_new, width, label="Adaptive (Exp 5a)", color="#c44e52")
    ax.set_xticks(x)
    ax.set_xticklabels([f"trial {i+1}" for i in range(n)])
    ax.set_ylim(0, 1)
    ax.set_ylabel("macro F1")
    ax.set_title("Shared-weight experiments: Phase 1.3 topology (Exp 1) vs improved topology (Exp 5a)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:
    ensure_utf8_streams()
    records = build_fold_records(topology_bases=IMPROVED_BASES)
    print(f"[load] clean fold records: {len(records)}")

    exp1_trials, exp1_stats = load_prior(EXP1_TRIALS_PATH, EXP1_STATS_PATH)
    trials = []
    for seed in SEEDS:
        print(f"[trial] seed={seed} ...", flush=True)
        tr = run_trial(records, seed)
        trials.append(tr)
        print(
            f"  Fixed = {tr['experiment_A']['macro_f1']:.3f}; "
            f"Adaptive = {tr['experiment_B']['macro_f1']:.3f}; "
            f"weights -> A={tr['experiment_B']['final_weights']['A']:.3f} "
            f"B={tr['experiment_B']['final_weights']['B']:.3f} "
            f"C={tr['experiment_B']['final_weights']['C']:.3f}"
        )

    results_A = [tr["experiment_A"]["macro_f1"] for tr in trials]
    results_B = [tr["experiment_B"]["macro_f1"] for tr in trials]
    stats_result = paired_statistics(results_A, results_B)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    TRIALS_PATH.write_text(
        json.dumps(
            {"trials": trials, "n_folds": len(records), "warmup_count": WARMUP_COUNT,
             "seeds": SEEDS, "records": records,
             "topology_bases": {k: str(v.relative_to(REPO_ROOT)).replace("\\", "/")
                                for k, v in IMPROVED_BASES.items()}},
            ensure_ascii=False, indent=2,
        ) + "\n", encoding="utf-8",
    )
    STATS_PATH.write_text(json.dumps(stats_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(trials, stats_result, exp1_trials, exp1_stats, records), encoding="utf-8")

    plot_weight_trajectory(trials, GRAPHS_DIR / "weight_trajectory.png")
    plot_f1_comparison_vs_exp1(trials, exp1_trials, GRAPHS_DIR / "f1_comparison_vs_exp1.png")

    print()
    print("=== Phase 1.4d Stage 1 Experiment 5a summary ===")
    print(f"Mean Δ macro F1 = {stats_result['mean_diff']:+.3f}")
    print(f"p = {stats_result['paired_t_test']['p_value']:.4f}, "
          f"d = {stats_result['cohens_d']}, "
          f"CI = [{stats_result['ci_95'][0]:+.3f}, {stats_result['ci_95'][1]:+.3f}]")
    print(f"Go (all 3 criteria): {stats_result['go_judgment']['overall_go']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
