"""Phase 1.4d Stage 3 Ablation F-1 — 2-topology subset (A + B_v3).

Removes the fusion topology (C_v3) from Target C's ensemble and re-runs
the full weight + consensus-gate + multiplicative-integration pipeline
on the remaining two topologies (pure audio A + pure visual B_v3).
Paired against F-2 (A + C_v3, no pure visual) and F-3 (B_v3 + C_v3, no
pure audio), this quantifies each topology's individual contribution to
Target C's d=+4.014.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4d.stage1_target_a_improved_topology_label_specific import IMPROVED_BASES
from phase1_4d.stage1_target_a_sdnd_proof import (
    WARMUP_COUNT, build_fold_records, ensure_utf8_streams, paired_statistics,
)
from phase1_4d.stage3_ablation_architecture_common import (
    ALL_SEEDS, FRIENDLY_TOPOLOGY_NAME, LABELS,
    extract_eval_records, load_reference, paired_fold_bootstrap,
    render_common_summary_head, run_trial_subset, verdict,
    write_trial_and_stats,
)

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage3_ablation_F1"
SUMMARY_PATH = OUT_DIR / "summary.md"
TARGET_C_STATS = REPO_ROOT / "results" / "phase1_4d" / "stage3_target_c_gate_learning" / "bootstrap_analysis.json"
EXP5B_STATS    = REPO_ROOT / "results" / "phase1_4d" / "stage1_exp5b_extended"        / "bootstrap_analysis.json"

SUBSET = ("A", "B")  # A = Topology A, B = Topology B_v3 — excludes C_v3 (fusion)
SUBSET_LABEL = "A + B_v3 (pure audio + pure visual, fusion excluded)"
REMOVED = "C_v3 (temporal-sync fusion)"


def render_summary(
    trials: list[dict[str, Any]],
    trial_stats: dict[str, Any],
    boot: dict[str, Any],
) -> str:
    tc_boot, _ = load_reference(TARGET_C_STATS)
    e5_boot, _ = load_reference(EXP5B_STATS)

    description = (
        f"Drops **{REMOVED}** from Target C's ensemble and re-runs the "
        "weight + consensus-gate + multiplicative-integration pipeline on "
        f"{SUBSET_LABEL}. Identical seeds, warm-up, and bootstrap to "
        "Target C so d falls on the same axis."
    )
    lines = render_common_summary_head(
        title=f"Phase 1.4d Stage 3 Ablation F-1 — 2-topology subset ({SUBSET_LABEL})",
        description=description,
        subset=SUBSET,
        trials=trials,
        trial_stats=trial_stats,
        boot=boot,
        references=[
            ("Exp 5b extended (3-topology, weight only)", e5_boot),
            ("Target C (3-topology, weight + consensus gate)", tc_boot),
        ],
    )

    # Final routing
    sums_w = {t: {cls: 0.0 for cls in LABELS} for t in SUBSET}
    sums_g = {t: {cls: 0.0 for cls in LABELS} for t in SUBSET}
    for tr in trials:
        w = tr["experiment_B"]["final_weights"]
        g = tr["experiment_B"]["final_gates"]
        for t in SUBSET:
            for cls in LABELS:
                sums_w[t][cls] += w[t][cls]
                sums_g[t][cls] += g[t][cls]
    n_tr = len(trials) or 1
    lines.append("## Final weights and gates (mean across 20 trials)")
    lines.append("")
    lines.append("| label | topology | weight | gate | w × g |")
    lines.append("|---|---|---:|---:|---:|")
    for cls in LABELS:
        for t in SUBSET:
            wm = sums_w[t][cls] / n_tr
            gm = sums_g[t][cls] / n_tr
            lines.append(
                f"| {cls} | {FRIENDLY_TOPOLOGY_NAME[t]} | {wm:.3f} | {gm:.3f} "
                f"| {wm * gm:.3f} |"
            )
    lines.append("")

    # Routing share
    lines.append("## Routing analysis — mean effective contribution per label")
    lines.append("")
    lines.append("| label | top topology | share | runner-up | share |")
    lines.append("|---|---|---:|---|---:|")
    for cls in LABELS:
        eff = {t: (sums_w[t][cls] / n_tr) * (sums_g[t][cls] / n_tr) for t in SUBSET}
        total = sum(eff.values()) or 1.0
        ordering = sorted(eff.items(), key=lambda kv: -kv[1])
        names = [(FRIENDLY_TOPOLOGY_NAME[t], v / total) for t, v in ordering]
        lines.append(
            f"| {cls} | {names[0][0]} | {names[0][1]:.2%} "
            f"| {names[1][0]} | {names[1][1]:.2%} |"
        )
    lines.append("")

    # Interpretation: quantify contribution of removed topology
    d_here = boot["cohens_d_paired"]
    lines.append("## Interpretation")
    lines.append("")
    if tc_boot is not None:
        loss = tc_boot["cohens_d_paired"] - d_here
        if d_here <= 0 or not boot["overall_go_positive"]:
            lines.append(
                f"**Case: removed topology was critical.** Dropping {REMOVED} "
                f"collapses d to {d_here:+.3f} (Target C = {tc_boot['cohens_d_paired']:+.3f}; "
                f"loss ≈ {loss:+.3f}). The two remaining topologies alone cannot "
                "carry the consensus-gate lift."
            )
        elif loss > 2.0:
            lines.append(
                f"**Case: removed topology contributed substantially.** d drops "
                f"from {tc_boot['cohens_d_paired']:+.3f} to {d_here:+.3f} "
                f"(loss ≈ {loss:+.3f}), i.e. the majority of Target C's effect "
                f"traces to including {REMOVED} in the vote."
            )
        elif loss > 0.8:
            lines.append(
                f"**Case: modest contribution.** d loses {loss:+.3f} when "
                f"{REMOVED} is removed ({tc_boot['cohens_d_paired']:+.3f} → "
                f"{d_here:+.3f}). The remaining pair still clears the 3-"
                "criterion gate."
            )
        else:
            lines.append(
                f"**Case: removed topology was near-redundant.** d changes by "
                f"only {loss:+.3f} ({tc_boot['cohens_d_paired']:+.3f} → "
                f"{d_here:+.3f}). Target C's effect is mostly carried by "
                f"{SUBSET_LABEL}."
            )
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `bootstrap_analysis.json`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()
    records = build_fold_records(topology_bases=IMPROVED_BASES)
    print(f"[load] clean fold records: {len(records)}")
    print(f"[subset] {SUBSET} ({', '.join(FRIENDLY_TOPOLOGY_NAME[t] for t in SUBSET)})")

    trials: list[dict[str, Any]] = []
    for seed in ALL_SEEDS:
        tr = run_trial_subset(records, seed, SUBSET)
        trials.append(tr)
        fa = tr["experiment_A"]["macro_f1"]
        fb = tr["experiment_B"]["macro_f1"]
        print(f"[trial seed={seed}] Fixed={fa:.3f} Adaptive={fb:.3f} Δ={fb - fa:+.3f}")

    trial_stats = paired_statistics(
        [tr["experiment_A"]["macro_f1"] for tr in trials],
        [tr["experiment_B"]["macro_f1"] for tr in trials],
    )
    pooled = extract_eval_records(trials)
    boot = paired_fold_bootstrap(pooled)
    print(
        f"[bootstrap n={boot['n_pooled_folds']}] "
        f"Δ={boot['observed_delta']:+.3f}, d={boot['cohens_d_paired']:+.3f}, "
        f"p={boot['p_value_twosided']:.4f}, "
        f"CI=[{boot['ci_95'][0]:+.3f}, {boot['ci_95'][1]:+.3f}] "
        f"({boot['direction']})"
    )

    write_trial_and_stats(OUT_DIR, trials, trial_stats, boot, n_folds=len(records))
    SUMMARY_PATH.write_text(render_summary(trials, trial_stats, boot), encoding="utf-8")

    print()
    print("=== Phase 1.4d Stage 3 Ablation F-1 summary ===")
    print(
        f"trial n=20 Δ={trial_stats['mean_diff']:+.3f}, "
        f"d={trial_stats.get('cohens_d')}, "
        f"CI=[{trial_stats['ci_95'][0]:+.3f}, {trial_stats['ci_95'][1]:+.3f}]"
    )
    print(
        f"bootstrap n=220 Δ={boot['observed_delta']:+.3f}, "
        f"d={boot['cohens_d_paired']:+.3f}, "
        f"p={boot['p_value_twosided']:.4f}, "
        f"CI=[{boot['ci_95'][0]:+.3f}, {boot['ci_95'][1]:+.3f}]"
    )
    print(f"Overall verdict: {verdict(boot)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
