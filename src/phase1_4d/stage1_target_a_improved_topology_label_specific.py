"""Phase 1.4d Stage 1 Experiment 5b — label-specific weight, improved topology.

Same ensemble frame as Experiment 3 (6-weight label-specific, sdnd-proof
rule ×0.7, threshold 0.5) but topology predictions come from the Phase
1.4a improved set (A + B_v3 + C_v3). Direct side-by-side with
Experiment 3 is included in the summary.
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
)
from phase1_4d.stage1_target_a_label_specific import run_trial

IMPROVED_BASES = {
    "A": REPO_ROOT / "results" / "phase1_3_extended" / "topology_a",
    "B": REPO_ROOT / "results" / "phase1_4a" / "topology_b_v3",
    "C": REPO_ROOT / "results" / "phase1_4a" / "topology_c_v3",
}

EXP3_TRIALS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_label_specific" / "trials_summary.json"
EXP3_STATS_PATH = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_label_specific" / "statistical_analysis.json"

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_improved_topology_label_specific"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary.json"
STATS_PATH = OUT_DIR / "statistical_analysis.json"

LABELS = ("sparrow", "bulbul")
TOPOLOGIES = ("A", "B", "C")


def load_prior(trials_path: Path, stats_path: Path):
    return (
        json.loads(trials_path.read_text(encoding="utf-8"))["trials"],
        json.loads(stats_path.read_text(encoding="utf-8")),
    )


def render_summary(trials, stats_result, exp3_trials, exp3_stats, records) -> str:
    e3_by = {tr["seed"]: tr for tr in exp3_trials}
    lines = [
        "# Phase 1.4d Stage 1 Experiment 5b — label-specific, improved topology",
        "",
        "Same rule as Experiment 3 (6 weights = 3 topologies × 2 labels, sdnd-proof ",
        "rule ×0.7, threshold 0.5). The difference is the topology set:",
        "",
        "    Experiment 3:  Phase 1.3 extended A / B / C",
        "    Experiment 5b: Phase 1.3 A + Phase 1.4a B_v3 + Phase 1.4a C_v3",
        "",
        "## Per-trial macro F1",
        "",
        "| Trial | Seed | Fixed_old (Exp 3) | Fixed_new (Exp 5b) | Exp 3 Adaptive | **Exp 5b Adaptive** | Exp 3 Δ | **Exp 5b Δ (vs Fixed_new)** |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, tr in enumerate(trials, start=1):
        s = tr["seed"]
        fa = tr["experiment_A"]["macro_f1"]
        fb = tr["experiment_B"]["macro_f1"]
        e3 = e3_by[s]
        fa_old = e3["experiment_A"]["macro_f1"]
        fb_old = e3["experiment_B"]["macro_f1"]
        lines.append(
            f"| {i} | {s} | {fa_old:.3f} | {fa:.3f} "
            f"| {fb_old:.3f} | **{fb:.3f}** "
            f"| {fb_old - fa_old:+.3f} | **{fb - fa:+.3f}** |"
        )
    lines.append("")

    # Fixed comparison
    fa_old_list = [e3_by[tr['seed']]["experiment_A"]["macro_f1"] for tr in trials]
    fa_new_list = [tr["experiment_A"]["macro_f1"] for tr in trials]
    mean_old = sum(fa_old_list) / len(fa_old_list)
    mean_new = sum(fa_new_list) / len(fa_new_list)
    lines.append("## Fixed baseline comparison (mean across 5 trials)")
    lines.append("")
    lines.append(f"- Fixed_old (Phase 1.3 A/B/C): **{mean_old:.3f}**")
    lines.append(f"- Fixed_new (Phase 1.3 A + B_v3 + C_v3): **{mean_new:.3f}**")
    lines.append(f"- ΔFixed = **{mean_new - mean_old:+.3f}**")
    lines.append("")

    # Final weights (Exp 5b)
    lines.append("## Experiment 5b final Adaptive weights (per trial)")
    lines.append("")
    lines.append("| Trial | Seed | A.s | A.b | B.s | B.b | C.s | C.b |")
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
    n = len(trials) or 1
    lines.append(
        f"| mean | - "
        f"| {sums['A']['sparrow']/n:.3f} | {sums['A']['bulbul']/n:.3f} "
        f"| {sums['B']['sparrow']/n:.3f} | {sums['B']['bulbul']/n:.3f} "
        f"| {sums['C']['sparrow']/n:.3f} | {sums['C']['bulbul']/n:.3f} |"
    )
    lines.append("")

    # Exp 3 vs Exp 5b label-specific weights side-by-side
    e3_sums = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    for tr in exp3_trials:
        w = tr["experiment_B"]["final_weights"]
        for t in TOPOLOGIES:
            for cls in LABELS:
                e3_sums[t][cls] += w[t][cls]
    n3 = len(exp3_trials) or 1
    lines.append("## Mean label-specific weight comparison (Exp 3 vs Exp 5b)")
    lines.append("")
    lines.append(
        "| Topology | Exp 3 sparrow | Exp 3 bulbul | Exp 5b sparrow | Exp 5b bulbul "
        "| Exp 3 \\|Δ\\| | Exp 5b \\|Δ\\| |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for t in TOPOLOGIES:
        e3_sp, e3_bu = e3_sums[t]["sparrow"] / n3, e3_sums[t]["bulbul"] / n3
        new_sp, new_bu = sums[t]["sparrow"] / n, sums[t]["bulbul"] / n
        t_label = {"A": "A", "B": "B (→B_v3)", "C": "C (→C_v3)"}[t]
        lines.append(
            f"| {t_label} | {e3_sp:.3f} | {e3_bu:.3f} | {new_sp:.3f} | {new_bu:.3f} "
            f"| {abs(e3_sp - e3_bu):.3f} | {abs(new_sp - new_bu):.3f} |"
        )
    lines.append("")

    # Statistics
    s = stats_result
    lines.append("## Statistical analysis (Exp 5b vs Fixed_new)")
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

    # Go judgment
    lines.append("## Go judgment vs Experiment 3 (label-specific comparison)")
    lines.append("")
    lines.append("| Criterion | Threshold | Exp 3 | **Exp 5b** | Exp 5b pass |")
    lines.append("|---|---|---:|---:|:-:|")
    j = s["go_judgment"]
    def dfmt(d): return f"{d:.3f}" if d is not None else "n/a"
    lines.append(
        f"| p-value | < 0.05 | {exp3_stats['paired_t_test']['p_value']:.4f} "
        f"| **{s['paired_t_test']['p_value']:.4f}** | {'Y' if j['p_value_pass'] else 'N'} |"
    )
    lines.append(
        f"| Cohen's d | >= 0.8 | {dfmt(exp3_stats['cohens_d'])} "
        f"| **{d_str}** | {'Y' if j['cohens_d_pass'] else 'N'} |"
    )
    lines.append(
        f"| 95% CI lower | > 0 | {exp3_stats['ci_95'][0]:+.3f} "
        f"| **{s['ci_95'][0]:+.3f}** | {'Y' if j['ci_pass'] else 'N'} |"
    )
    exp3_overall = "No-Go" if not exp3_stats["go_judgment"]["overall_go"] else "Go"
    exp5b_overall = "Go" if j["overall_go"] else "No-Go"
    lines.append(
        f"| **Overall** | all pass | **{exp3_overall}** | **{exp5b_overall}** | |"
    )
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append(
        "- B_v3 was specifically designed to reduce the sparrow / bulbul split. "
        "Any residual split in Exp 5b is what the flow_weight learning still finds "
        "on top of that engineering change."
    )
    lines.append(
        "- n=5 trials (shuffle-only variation)."
    )
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `statistical_analysis.json`")
    lines.append("- `graphs/weight_trajectory_label_specific.png`")
    lines.append("- `graphs/label_weight_comparison_exp3_exp5b.png`")
    lines.append("")
    return "\n".join(lines)


def plot_trajectory(trials, out_path: Path) -> None:
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
    for r, cls in enumerate(LABELS):
        for c, t in enumerate(TOPOLOGIES):
            ax = axes[r, c]
            for tr in trials:
                traj = tr["experiment_B"]["weight_trajectory"]
                steps = [e["step"] for e in traj]
                vals = [e["weights"][t][cls] for e in traj]
                ax.plot(steps, vals, marker=".", linewidth=1.0, alpha=0.9,
                        color=colors.get(tr["seed"], "#444"),
                        label=f"seed {tr['seed']}" if (r == 0 and c == 0) else None)
            ax.axvline(WARMUP_COUNT - 0.5, color="#888", linestyle="--", linewidth=0.7)
            ax.set_title(f"{cls} · Topology {t}")
            ax.set_ylim(0, 1); ax.grid(alpha=0.3)
            if c == 0: ax.set_ylabel("flow_weight")
            if r == 1: ax.set_xlabel("fold step")
    axes[0, 0].legend(loc="lower left", fontsize=7)
    fig.suptitle("Exp 5b — label-specific weights on improved topology (A + B_v3 + C_v3)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_label_weight_comparison(trials, exp3_trials, out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    sums = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    for tr in trials:
        w = tr["experiment_B"]["final_weights"]
        for t in TOPOLOGIES:
            for cls in LABELS:
                sums[t][cls] += w[t][cls]
    n = len(trials) or 1
    e3_sums = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    for tr in exp3_trials:
        w = tr["experiment_B"]["final_weights"]
        for t in TOPOLOGIES:
            for cls in LABELS:
                e3_sums[t][cls] += w[t][cls]
    n3 = len(exp3_trials) or 1

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, (label_title, src, n_src) in zip(
        axes, (("Exp 3 (Phase 1.3 A/B/C)", e3_sums, n3), ("Exp 5b (A + B_v3 + C_v3)", sums, n))
    ):
        x = np.arange(len(TOPOLOGIES))
        width = 0.38
        sp_values = [src[t]["sparrow"] / n_src for t in TOPOLOGIES]
        bu_values = [src[t]["bulbul"] / n_src for t in TOPOLOGIES]
        ax.bar(x - width / 2, sp_values, width, label="sparrow", color="#4c72b0")
        ax.bar(x + width / 2, bu_values, width, label="bulbul", color="#dd8452")
        ax.set_xticks(x); ax.set_xticklabels([f"Topology {t}" for t in TOPOLOGIES])
        ax.set_title(label_title)
        ax.set_ylim(0, 1); ax.grid(axis="y", alpha=0.3)
        ax.axhline(0.5, color="#555", linestyle=":", linewidth=0.7)
        ax.legend()
    axes[0].set_ylabel("mean final flow_weight")
    fig.suptitle("Label-specific weight balance: Exp 3 (original topology) vs Exp 5b (improved)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:
    ensure_utf8_streams()
    records = build_fold_records(topology_bases=IMPROVED_BASES)
    print(f"[load] clean fold records: {len(records)}")

    exp3_trials, exp3_stats = load_prior(EXP3_TRIALS_PATH, EXP3_STATS_PATH)
    trials = []
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
            {"trials": trials, "n_folds": len(records), "warmup_count": WARMUP_COUNT,
             "seeds": SEEDS, "records": records,
             "topology_bases": {k: str(v.relative_to(REPO_ROOT)).replace("\\", "/")
                                for k, v in IMPROVED_BASES.items()},
             "weight_structure": "label-specific (6 weights: 3 topologies × 2 labels)",
             "failure_multiplier": 0.7},
            ensure_ascii=False, indent=2,
        ) + "\n", encoding="utf-8",
    )
    STATS_PATH.write_text(json.dumps(stats_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(trials, stats_result, exp3_trials, exp3_stats, records), encoding="utf-8")

    plot_trajectory(trials, GRAPHS_DIR / "weight_trajectory_label_specific.png")
    plot_label_weight_comparison(trials, exp3_trials, GRAPHS_DIR / "label_weight_comparison_exp3_exp5b.png")

    print()
    print("=== Phase 1.4d Stage 1 Experiment 5b summary ===")
    print(f"Mean Δ macro F1 = {stats_result['mean_diff']:+.3f}")
    print(f"p = {stats_result['paired_t_test']['p_value']:.4f}, "
          f"d = {stats_result['cohens_d']}, "
          f"CI = [{stats_result['ci_95'][0]:+.3f}, {stats_result['ci_95'][1]:+.3f}]")
    print(f"Go (all 3 criteria): {stats_result['go_judgment']['overall_go']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
