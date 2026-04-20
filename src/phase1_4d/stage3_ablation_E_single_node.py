"""Phase 1.4d Stage 3 Ablation E — single-node degenerate ensemble.

Runs Target C's ensemble-voting framework but with the topology subset
reduced to **C_v3 alone**. The purpose is a clean architecture-boundary
test: if the ensemble *framework* (weighted vote + gate + consensus
signal + multiplicative integration) were itself the reason for Target
C's d=+4.014, collapsing to a single topology should still produce a
detectable lift. If the lift comes from topology diversity, this
collapses to Δ=0.

Analytical prediction — with one node the effective contribution is
`w × g`, the weighted score is `(w × g) × pred / (w × g) = pred`, so
adaptive and fixed arms always emit the *same* binary prediction
regardless of weight or gate values. Δ macro F1 is identically zero
across every trial.

Same 20 seeds, 22 clean folds, 11-warm-up / 11-eval split, paired fold
bootstrap n=220 as Target C and the earlier ablations — so the d falls
out on the same axis.
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

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage3_ablation_E"
SUMMARY_PATH = OUT_DIR / "summary.md"
TARGET_C_STATS   = REPO_ROOT / "results" / "phase1_4d" / "stage3_target_c_gate_learning" / "bootstrap_analysis.json"
EXP5B_STATS      = REPO_ROOT / "results" / "phase1_4d" / "stage1_exp5b_extended"        / "bootstrap_analysis.json"
STAGE2_EXP2_STATS = REPO_ROOT / "results" / "phase1_4d" / "stage2_target_b_no_score_extended" / "bootstrap_analysis_extended.json"

SUBSET = ("C",)  # C_v3 only


def render_summary(
    trials: list[dict[str, Any]],
    trial_stats: dict[str, Any],
    boot: dict[str, Any],
) -> str:
    tc_boot, _ = load_reference(TARGET_C_STATS)
    e5_boot, _ = load_reference(EXP5B_STATS)

    # Stage 2 Exp 2 extended stores its n=220 bootstrap under a different
    # top-level key ("bootstrap_n220") in a file located outside the common
    # path; we still pull it for the "single-LLM / same count" comparison.
    stage2_boot = None
    if STAGE2_EXP2_STATS.is_file():
        import json
        data = json.loads(STAGE2_EXP2_STATS.read_text(encoding="utf-8"))
        stage2_boot = data.get("bootstrap_n220")

    description = (
        "Ensemble-voting framework applied to a **single topology** (C_v3 "
        "only). With one node in the vote the multiplicative `w × g` "
        "mixing reduces to `pred` identically, so fixed and adaptive arms "
        "emit the same prediction on every fold by construction. The "
        "observation is whether the actual bootstrap behaves as the "
        "analytic prediction demands — d ≈ 0, CI tight around 0."
    )
    lines = render_common_summary_head(
        title="Phase 1.4d Stage 3 Ablation E — single-node degenerate ensemble (C_v3)",
        description=description,
        subset=SUBSET,
        trials=trials,
        trial_stats=trial_stats,
        boot=boot,
        references=[
            ("Stage 2 Exp 2 extended (single-LLM, silent filter)", stage2_boot),
            ("Exp 5b extended (3-topology, weight only)", e5_boot),
            ("Target C (3-topology, weight + consensus gate)", tc_boot),
        ],
    )

    # Interpretation
    d = boot["cohens_d_paired"]
    delta = boot["observed_delta"]
    lines.append("## Interpretation")
    lines.append("")
    if abs(delta) < 1e-9 and abs(d) < 1e-6:
        lines.append(
            "**Case A — architecture boundary confirmed.** With one topology in "
            "the vote, Fixed and Adaptive arms produce identical predictions on "
            "every fold (Δ = 0 exactly, Cohen's d ≈ 0, CI clamped to zero). The "
            "ensemble code framework alone — weight + gate + consensus signal + "
            "multiplicative integration — carries zero lift when topology "
            "diversity is absent. Target C's d=+4.014 therefore lives in the "
            "diversity across A / B_v3 / C_v3, not in the code structure that "
            "mixes them. Paper 1 Chapter 1's 'Ensemble voting works, Single-LLM "
            "does not' claim survives the strongest null check available."
        )
    elif abs(d) < 0.8:
        lines.append(
            "**Case A-weak — architecture boundary largely supported.** Some "
            f"residual motion (Δ={delta:+.3f}, d={d:+.3f}) appears — likely a "
            "rare 0.5-threshold boundary crossing — but the effect is well "
            "below the Go threshold. Consistent with the analytical prediction "
            "that one-node 'ensembles' cannot transfer sdnd-proof."
        )
    else:
        lines.append(
            f"**Case B — unexpected effect** (d={d:+.3f}). The analytic "
            "prediction is Δ=0, so any clear lift would indicate a "
            "configuration bug or a subtle interaction between the vote "
            "threshold and the learning dynamics. Investigate before reporting."
        )
    lines.append("")

    # Diagnostic: how many (trial, fold) pairs had Fixed≠Adaptive?
    flip_count = 0
    total = 0
    for tr in trials:
        for f, a in zip(tr["experiment_A"]["per_fold"], tr["experiment_B"]["per_fold"]):
            total += 1
            if f["pred"] != a["pred"]:
                flip_count += 1
    lines.append("## Diagnostic — Fixed vs Adaptive prediction equality")
    lines.append("")
    lines.append(
        f"Across {total} (trial, fold) pairs, Fixed and Adaptive emitted "
        f"**different** predictions in **{flip_count}** cases."
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
    print("=== Phase 1.4d Stage 3 Ablation E summary ===")
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
