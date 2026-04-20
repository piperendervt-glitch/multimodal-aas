"""Phase 1.4d Stage 3 Ablation 5 — Gate updated against ground truth.

Target C (commit bfd840d) introduced a **consensus-agreement** gate:
each gate rewards the topology when its own prediction matches the
ensemble's final prediction. The stated novelty in the Target C write-
up is that reward signal — two variables (weight, gate) sharing the
same asymmetric sdnd-proof update rule but diverging because they are
fed different correctness signals.

Ablation 5 tests whether that signal split is the load-bearing design
choice. Weight and gate are both updated using **ground truth** as the
correctness signal (same signal for both):

    weight (w): success iff topology prediction matches GT     [same as Target C]
    gate   (g): success iff topology prediction matches GT     [CHANGED]

Integration is unchanged (effective = w × g). If d stays near Target
C's +4.014 the Target C effect comes from having a second multiplicative
variable, not from the consensus signal. If d drops toward Exp 5b
extended's +2.041 the consensus-agreement reward is the real novelty.
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

from phase1_4d.stage1_target_a_improved_topology_label_specific import IMPROVED_BASES
from phase1_4d.stage1_target_a_sdnd_proof import (
    WARMUP_COUNT,
    build_fold_records,
    ensure_utf8_streams,
    paired_statistics,
)
from phase1_4d.common.ensemble import compute_f1_bundle
from phase1_4d.common.flow_weight import (
    INITIAL_WEIGHT,
    update_weight_sdnd_proof,
)

TARGET_C_STATS = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage3_target_c_gate_learning" / "bootstrap_analysis.json"
)
EXP5B_EXTENDED_STATS = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage1_exp5b_extended" / "bootstrap_analysis.json"
)
ABLATION_1_STATS = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage3_ablation_1_gate_only" / "bootstrap_analysis.json"
)

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage3_ablation_5_gt_based_gate"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary.json"
STATS_PATH = OUT_DIR / "bootstrap_analysis.json"

ALL_SEEDS = [
    42, 137, 256, 512, 1024,
    2048, 4096, 8192, 16384, 32768,
    65536, 131072, 262144, 524288, 1048576,
    2097152, 4194304, 8388608, 16777216, 33554432,
]
N_BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 42

LABELS = ("sparrow", "bulbul")
TOPOLOGIES = ("A", "B", "C")


def _initial_table() -> dict[str, dict[str, float]]:
    return {t: {cls: INITIAL_WEIGHT for cls in LABELS} for t in TOPOLOGIES}


def weighted_vote_gated(
    preds: dict[str, dict[str, int]],
    weights: dict[str, dict[str, float]],
    gates: dict[str, dict[str, float]],
    threshold: float = 0.5,
) -> dict[str, int]:
    out: dict[str, int] = {}
    for cls in LABELS:
        eff = {t: weights[t][cls] * gates[t][cls] for t in preds.keys()}
        total = sum(eff.values())
        if total <= 1e-9:
            out[cls] = 0
            continue
        score = sum(eff[t] * preds[t][cls] for t in preds.keys()) / total
        out[cls] = 1 if score >= threshold else 0
    return out


def run_trial(records: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    order = list(range(len(records)))
    rng.shuffle(order)

    # Fixed arm: weights + gates pinned at 0.5 (same as Target C fixed).
    fixed_w = _initial_table()
    fixed_g = _initial_table()
    fixed_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    fixed_per_fold: list[dict[str, Any]] = []
    for step, idx in enumerate(order):
        rec = records[idx]
        pred = weighted_vote_gated(rec["predictions"], fixed_w, fixed_g)
        fixed_per_fold.append({
            "step": step, "video_id": rec["video_id"],
            "pred": pred, "gt": rec["ground_truth"],
        })
        if step >= WARMUP_COUNT:
            fixed_eval_pairs.append((pred, rec["ground_truth"]))
    fixed_metrics = compute_f1_bundle(fixed_eval_pairs)

    # Adaptive arm: BOTH weight and gate updated against GT. Weights
    # and gates share the same update rule AND the same signal, so by
    # construction they co-evolve (w == g along every trajectory given
    # identical initialisation). The ensemble vote still mixes with
    # w × g (= w² after the first step).
    weights = _initial_table()
    gates   = _initial_table()
    weight_traj: list[dict[str, Any]] = [{"step": -1, "weights": copy.deepcopy(weights)}]
    gate_traj:   list[dict[str, Any]] = [{"step": -1, "gates":   copy.deepcopy(gates)}]
    adaptive_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    adaptive_per_fold: list[dict[str, Any]] = []

    for step, idx in enumerate(order):
        rec = records[idx]
        preds = rec["predictions"]
        final_pred = weighted_vote_gated(preds, weights, gates)

        weights_before = copy.deepcopy(weights)
        gates_before   = copy.deepcopy(gates)
        topo_weight_success: dict[str, dict[str, bool]] = {t: {} for t in TOPOLOGIES}
        topo_gate_success:   dict[str, dict[str, bool]] = {t: {} for t in TOPOLOGIES}

        for t in TOPOLOGIES:
            for cls in LABELS:
                # Weight: compare topology pred vs GT (same as Target C).
                w_ok = preds[t][cls] == rec["ground_truth"][cls]
                topo_weight_success[t][cls] = w_ok
                weights[t][cls] = update_weight_sdnd_proof(weights[t][cls], w_ok)

                # Gate: compare topology pred vs GT — the Ablation 5
                # change. Same signal as the weight: redundant by design.
                g_ok = preds[t][cls] == rec["ground_truth"][cls]
                topo_gate_success[t][cls] = g_ok
                gates[t][cls] = update_weight_sdnd_proof(gates[t][cls], g_ok)

        weight_traj.append({"step": step, "weights": copy.deepcopy(weights)})
        gate_traj.append({"step": step, "gates": copy.deepcopy(gates)})
        adaptive_per_fold.append({
            "step": step, "video_id": rec["video_id"],
            "pred": final_pred, "gt": rec["ground_truth"],
            "weights_before": weights_before, "weights_after": copy.deepcopy(weights),
            "gates_before":   gates_before,   "gates_after":   copy.deepcopy(gates),
            "topo_weight_success": topo_weight_success,
            "topo_gate_success":   topo_gate_success,
        })
        if step >= WARMUP_COUNT:
            adaptive_eval_pairs.append((final_pred, rec["ground_truth"]))

    adaptive_metrics = compute_f1_bundle(adaptive_eval_pairs)
    return {
        "seed": seed,
        "shuffle_order": order,
        "fold_video_ids_in_order": [records[i]["video_id"] for i in order],
        "warmup_folds": [records[i]["video_id"] for i in order[:WARMUP_COUNT]],
        "eval_folds":   [records[i]["video_id"] for i in order[WARMUP_COUNT:]],
        "experiment_A": {
            "final_weights": fixed_w,
            "final_gates":   fixed_g,
            "macro_f1":   fixed_metrics["macro_f1"],
            "sparrow_f1": fixed_metrics["sparrow_f1"],
            "bulbul_f1":  fixed_metrics["bulbul_f1"],
            "confusion":  fixed_metrics["confusion"],
            "per_fold":   fixed_per_fold,
        },
        "experiment_B": {
            "initial_weights": _initial_table(),
            "initial_gates":   _initial_table(),
            "final_weights":   weights,
            "final_gates":     gates,
            "weight_trajectory": weight_traj,
            "gate_trajectory":   gate_traj,
            "macro_f1":   adaptive_metrics["macro_f1"],
            "sparrow_f1": adaptive_metrics["sparrow_f1"],
            "bulbul_f1":  adaptive_metrics["bulbul_f1"],
            "confusion":  adaptive_metrics["confusion"],
            "per_fold":   adaptive_per_fold,
        },
    }


# ---------------------------------------------------------------------------
# Paired fold bootstrap (identical to Target C / Ablation 1)
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
                "trial_seed": tr["seed"], "step": int(step),
                "video_id": f_fold["video_id"],
                "pred_fixed":    f_fold["pred"],
                "pred_adaptive": a_fold["pred"],
                "gt":            f_fold["gt"],
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
        for cls in LABELS:
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
        "observed_delta":             ad_obs - fx_obs,
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


def _load_reference(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not path.is_file():
        return None, None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("bootstrap_n220"), data.get("trial_stats_n20")


def render_summary(
    trials: list[dict[str, Any]],
    trial_stats: dict[str, Any],
    boot: dict[str, Any],
) -> str:
    tc_boot, tc_trial = _load_reference(TARGET_C_STATS)
    e5_boot, e5_trial = _load_reference(EXP5B_EXTENDED_STATS)
    ab1_boot, ab1_trial = _load_reference(ABLATION_1_STATS)
    lines = [
        "# Phase 1.4d Stage 3 Ablation 5 — Ground-truth based gate update",
        "",
        "Same substrate as Target C (ensemble voting over A + B_v3 + C_v3, "
        "6 weights + 6 gates, effective vote = w × g), same weight update "
        "(GT-driven sdnd-proof), but the **gate update signal is swapped** "
        "from consensus-agreement to ground truth:",
        "",
        "    Target C:   g_ok = (topology_pred == ensemble_final_pred)",
        "    Ablation 5: g_ok = (topology_pred == ground_truth)      ← same as the weight",
        "",
        "Because both variables now share identical update rule and signal "
        "starting from w = g = 0.5, the gate collapses onto the weight trajectory "
        "(w ≡ g along every run) and the effective vote reduces to w² · pred. "
        "This is the explicit test of whether Target C's novelty lives in the "
        "*consensus signal* or merely in having a second multiplicative knob.",
        "",
        f"Seeds: {ALL_SEEDS}. 20 trials × 11 second-half folds = "
        f"n_pooled = {20 * (22 - WARMUP_COUNT)}.",
        "",
        "## Per-trial macro F1",
        "",
        "| Trial | Seed | Fixed | Adaptive | Δ |",
        "|---|---:|---:|---:|---:|",
    ]
    for i, tr in enumerate(trials, start=1):
        fa = tr["experiment_A"]["macro_f1"]
        fb = tr["experiment_B"]["macro_f1"]
        lines.append(
            f"| {i} | {tr['seed']} | {fa:.3f} | {fb:.3f} | {fb - fa:+.3f} |"
        )
    lines.append("")

    pos = neg = zero = 0
    for tr in trials:
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

    # Stats + references
    lines.append("## Statistical analysis")
    lines.append("")
    lines.append("| method | n | point Δ | Cohen's d | p | 95% CI | verdict |")
    lines.append("|---|---:|---:|---:|---:|---|---|")
    d20 = trial_stats.get("cohens_d")
    d20_str = f"{d20:+.3f}" if d20 is not None else "n/a"
    v20 = "Go" if trial_stats.get("go_judgment", {}).get("overall_go") else "No-Go"
    lines.append(
        f"| Ablation 5 trial t-test | 20 | {trial_stats['mean_diff']:+.3f} "
        f"| {d20_str} | {trial_stats['paired_t_test']['p_value']:.4f} "
        f"| [{trial_stats['ci_95'][0]:+.3f}, {trial_stats['ci_95'][1]:+.3f}] | {v20} |"
    )
    lines.append(
        f"| **Ablation 5 paired fold bootstrap** | **{boot['n_pooled_folds']}** "
        f"| {boot['observed_delta']:+.3f} "
        f"| **{boot['cohens_d_paired']:+.3f}** "
        f"| **{boot['p_value_twosided']:.4f}** "
        f"| [{boot['ci_95'][0]:+.3f}, {boot['ci_95'][1]:+.3f}] "
        f"| **{_verdict(boot)}** |"
    )
    if tc_boot:
        lines.append(
            f"| Target C paired fold bootstrap (ref) | {tc_boot['n_pooled_folds']} "
            f"| {tc_boot['observed_delta']:+.3f} "
            f"| {tc_boot['cohens_d_paired']:+.3f} "
            f"| {tc_boot['p_value_twosided']:.4f} "
            f"| [{tc_boot['ci_95'][0]:+.3f}, {tc_boot['ci_95'][1]:+.3f}] "
            f"| {_verdict(tc_boot)} |"
        )
    if ab1_boot:
        lines.append(
            f"| Ablation 1 paired fold bootstrap (ref) | {ab1_boot['n_pooled_folds']} "
            f"| {ab1_boot['observed_delta']:+.3f} "
            f"| {ab1_boot['cohens_d_paired']:+.3f} "
            f"| {ab1_boot['p_value_twosided']:.4f} "
            f"| [{ab1_boot['ci_95'][0]:+.3f}, {ab1_boot['ci_95'][1]:+.3f}] "
            f"| {_verdict(ab1_boot)} |"
        )
    if e5_boot:
        lines.append(
            f"| Exp 5b extended paired fold bootstrap (ref) | {e5_boot['n_pooled_folds']} "
            f"| {e5_boot['observed_delta']:+.3f} "
            f"| {e5_boot['cohens_d_paired']:+.3f} "
            f"| {e5_boot['p_value_twosided']:.4f} "
            f"| [{e5_boot['ci_95'][0]:+.3f}, {e5_boot['ci_95'][1]:+.3f}] "
            f"| {_verdict(e5_boot)} |"
        )
    lines.append("")

    c = boot["criteria"]
    lines.append("## Bootstrap Go criteria (n=220)")
    lines.append("")
    lines.append("| Criterion | Value | Pass |")
    lines.append("|---|---:|:-:|")
    lines.append(
        f"| p-value < 0.05 | {boot['p_value_twosided']:.4f} | "
        f"{'Y' if c['p_value_pass_at_0.05'] else 'N'} |"
    )
    lines.append(
        f"| |Cohen's d| ≥ 0.8 | {boot['cohens_d_paired']:+.3f} | "
        f"{'Y' if c['abs_cohens_d_pass_at_0.8'] else 'N'} |"
    )
    lines.append(
        f"| 95% CI excludes 0 | [{boot['ci_95'][0]:+.3f}, {boot['ci_95'][1]:+.3f}] | "
        f"{'Y' if c['ci_excludes_zero'] else 'N'} |"
    )
    lines.append(f"| direction | {boot['direction']} | — |")
    lines.append(f"| **Overall** | — | **{_verdict(boot)}** |")
    lines.append("")

    # Final w and g (n=20 mean)
    sums_w = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    sums_g = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    max_abs_diff = 0.0
    for tr in trials:
        w = tr["experiment_B"]["final_weights"]
        g = tr["experiment_B"]["final_gates"]
        for t in TOPOLOGIES:
            for cls in LABELS:
                sums_w[t][cls] += w[t][cls]
                sums_g[t][cls] += g[t][cls]
                diff = abs(w[t][cls] - g[t][cls])
                if diff > max_abs_diff:
                    max_abs_diff = diff
    n_tr = len(trials) or 1

    lines.append("## Final weights and gates (mean across 20 trials)")
    lines.append("")
    lines.append("| label | topology | weight | gate | w × g | |w − g| check |")
    lines.append("|---|---|---:|---:|---:|---:|")
    friendly = {"A": "A", "B": "B_v3", "C": "C_v3"}
    for cls in LABELS:
        for t in TOPOLOGIES:
            w_mean = sums_w[t][cls] / n_tr
            g_mean = sums_g[t][cls] / n_tr
            lines.append(
                f"| {cls} | {friendly[t]} | {w_mean:.3f} | {g_mean:.3f} "
                f"| {w_mean * g_mean:.3f} | {abs(w_mean - g_mean):.3g} |"
            )
    lines.append("")
    lines.append(
        f"Max |w − g| across all (trial, topology, label) cells: **{max_abs_diff:.3g}**. "
        "With identical initialisation and identical update signal this should be "
        "numerically zero — the gate collapses onto the weight trajectory."
    )
    lines.append("")

    # Interpretation
    lines.append("## Interpretation")
    lines.append("")
    d_ab5 = boot["cohens_d_paired"]
    d_tc = tc_boot["cohens_d_paired"] if tc_boot else None
    d_e5 = e5_boot["cohens_d_paired"] if e5_boot else None
    if d_tc is not None and d_e5 is not None:
        if d_ab5 <= 2.5:
            case = (
                "**Case A — consensus signal IS the novelty.** Swapping the gate "
                "to a ground-truth signal drops Cohen's d from Target C's {:+.3f} "
                "down to {:+.3f}, comparable to or below Exp 5b extended ({:+.3f}). "
                "The consensus-agreement reward is load-bearing; a second GT-driven "
                "variable is redundant with the weight and the w × g sharpening "
                "only helps when the second variable encodes a *different* signal. "
                "This is the primary novelty to claim in Paper 1 Chapter 5."
            ).format(d_tc, d_ab5, d_e5)
        elif d_ab5 >= 3.5:
            case = (
                "**Case B — signal source is not the novelty.** Ablation 5 "
                "preserves most of Target C's effect (d={:+.3f} vs Target C "
                "{:+.3f}). What matters is having a second multiplicative knob "
                "(the w × g sharpening), not the consensus-vs-GT distinction. "
                "The Paper 1 novelty should be reframed around the multiplicative "
                "integration rather than the consensus reward."
            ).format(d_ab5, d_tc)
        else:  # 2.5 .. 3.5
            case = (
                "**Case C — partial contribution.** Ablation 5 sits between "
                "Exp 5b extended (d={:+.3f}) and Target C (d={:+.3f}) at "
                "d={:+.3f}. Both the consensus signal and the multiplicative "
                "w × g integration contribute; neither alone explains Target "
                "C's effect. Paper 1 can claim the combination as the novelty "
                "but must share credit with the integration choice."
            ).format(d_e5, d_tc, d_ab5)
    else:
        case = "(reference stats missing — interpretation skipped)"
    lines.append(case)
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `bootstrap_analysis.json`")
    lines.append("- `graphs/weight_gate_trajectory.png`")
    lines.append("- `graphs/cohens_d_comparison.png`")
    lines.append("")
    return "\n".join(lines)


def plot_weight_gate_trajectory(trials: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharey=True, sharex=True)
    friendly = {"A": "A", "B": "B_v3", "C": "C_v3"}
    for row, cls in enumerate(LABELS):
        for col, t in enumerate(TOPOLOGIES):
            ax = axes[row, col]
            for tr in trials:
                w_traj = tr["experiment_B"]["weight_trajectory"]
                g_traj = tr["experiment_B"]["gate_trajectory"]
                ax.plot([e["step"] for e in w_traj],
                        [e["weights"][t][cls] for e in w_traj],
                        color="#4c72b0", alpha=0.35, linewidth=0.9)
                ax.plot([e["step"] for e in g_traj],
                        [e["gates"][t][cls] for e in g_traj],
                        color="#dd8452", alpha=0.35, linewidth=0.9, linestyle="--")
            ax.axvline(WARMUP_COUNT - 0.5, color="#888", linestyle="--", linewidth=0.7)
            ax.set_title(f"{cls} · Topology {friendly[t]}")
            ax.set_ylim(0, 1); ax.grid(alpha=0.3)
            if col == 0: ax.set_ylabel("value")
            if row == 1: ax.set_xlabel("fold step")
    axes[0, 0].plot([], [], color="#4c72b0", label="weight (GT)")
    axes[0, 0].plot([], [], color="#dd8452", linestyle="--", label="gate (GT — should overlap weight)")
    axes[0, 0].legend(fontsize=8, loc="lower left")
    fig.suptitle("Ablation 5 — weight and gate share GT signal (trajectories should overlap)")
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)


def plot_cohens_d_comparison(boot: dict[str, Any], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    tc_boot, _ = _load_reference(TARGET_C_STATS)
    e5_boot, _ = _load_reference(EXP5B_EXTENDED_STATS)
    ab1_boot, _ = _load_reference(ABLATION_1_STATS)
    labels = []
    ds = []
    colors = []
    if e5_boot:
        labels.append("Exp 5b extended\n(w only, GT)")
        ds.append(e5_boot["cohens_d_paired"])
        colors.append("#4c72b0")
    if ab1_boot:
        labels.append("Ablation 1\n(g only, consensus)")
        ds.append(ab1_boot["cohens_d_paired"])
        colors.append("#dd8452")
    labels.append("Ablation 5\n(w + g, both GT)")
    ds.append(boot["cohens_d_paired"])
    colors.append("#c44e52")
    if tc_boot:
        labels.append("Target C\n(w GT + g consensus)")
        ds.append(tc_boot["cohens_d_paired"])
        colors.append("#2a9d8f")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    xs = np.arange(len(labels))
    ax.bar(xs, ds, color=colors)
    for x, d in zip(xs, ds):
        ax.annotate(f"d = {d:+.3f}", (x, d), textcoords="offset points",
                    xytext=(0, 8 if d >= 0 else -14), ha="center", fontsize=9)
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.axhline(0.8, color="#264653", linestyle=":", linewidth=1.0,
               label="Go threshold (|d|=0.8)")
    ax.set_xticks(xs); ax.set_xticklabels(labels)
    ax.set_ylabel("Cohen's d (paired, n=220 bootstrap)")
    ax.set_title("Ablation 5 — gate signal ablation within the Stage 3 family")
    ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=8, loc="best")
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ensure_utf8_streams()
    records = build_fold_records(topology_bases=IMPROVED_BASES)
    print(f"[load] clean fold records: {len(records)}")

    trials: list[dict[str, Any]] = []
    for seed in ALL_SEEDS:
        tr = run_trial(records, seed)
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

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    TRIALS_PATH.write_text(
        json.dumps({
            "seeds": ALL_SEEDS, "warmup_count": WARMUP_COUNT,
            "n_folds_per_trial": len(records),
            "trials": trials,
            "trial_stats": trial_stats,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps({
            "trial_stats_n20": trial_stats,
            "bootstrap_n220":  boot,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(render_summary(trials, trial_stats, boot), encoding="utf-8")

    plot_weight_gate_trajectory(trials, GRAPHS_DIR / "weight_gate_trajectory.png")
    plot_cohens_d_comparison(boot, GRAPHS_DIR / "cohens_d_comparison.png")

    print()
    print("=== Phase 1.4d Stage 3 Ablation 5 summary ===")
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
    print(f"Overall verdict: {_verdict(boot)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
