"""Phase 1.4d Stage 3 Target C — per-label routing with gate learning.

Builds on Stage 1 Experiment 5b extended (commit 2db9ca2), which
clinched the first positive Statistical Go in Phase 1.4d
(d=+2.041, p=0.0001, CI [+0.003, +0.026]) on the ensemble-voting
substrate over A + B_v3 + C_v3.

Target C adds an explicit per-label **gate** next to each weight.
Six gates (3 topologies × 2 labels) join the six weights; the ensemble
vote uses the product ``w × g`` as the effective contribution and the
two quantities are updated with different correctness signals so they
can diverge:

    weight (w): success iff the topology's own prediction matches GT
    gate   (g): success iff the topology's own prediction matches the
                ensemble's final prediction (computed just before the
                update with the current w × g vote)

Both update rules share sdnd-proof's asymmetric form
(success → w + 0.1·(1 − w); failure → w × 0.7). The gate therefore
rewards topologies that agree with the majority, which in steady state
encourages winner-take-all routing. The weight still tracks per-label
accuracy against ground truth, as in Exp 5b.

Design philosophy (summarised from the spec):

    1. No numerical values are shown to the LLM (Stage 2 Exp 1 lesson).
    2. Ensemble voting remains the substrate (Exp 5b success).
    3. Gates give the ensemble an explicit routing knob (Target C
       novelty).

No new LLM inference is required — every topology's per-fold
prediction is already on disk. 20 trials, clean 22 folds, second-half
eval, paired fold bootstrap n=220, sdnd-proof 3-criterion gate.
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

EXP5B_EXTENDED_STATS = (
    REPO_ROOT / "results" / "phase1_4d" / "stage1_exp5b_extended" / "bootstrap_analysis.json"
)
EXP5B_EXTENDED_TRIALS = (
    REPO_ROOT / "results" / "phase1_4d" / "stage1_exp5b_extended" / "trials_summary_extended.json"
)

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage3_target_c_gate_learning"
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
TOPOLOGIES = ("A", "B", "C")  # keys inside the records (B = Topology B_v3, C = Topology C_v3)


def _initial_weights() -> dict[str, dict[str, float]]:
    return {t: {cls: INITIAL_WEIGHT for cls in LABELS} for t in TOPOLOGIES}


def weighted_vote_gated(
    preds: dict[str, dict[str, int]],
    weights: dict[str, dict[str, float]],
    gates: dict[str, dict[str, float]],
    threshold: float = 0.5,
) -> dict[str, int]:
    """Ensemble vote with per-topology-label effective contribution w × g."""
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

    # Fixed arm: weights + gates all pinned at 0.5 throughout.
    fixed_w = _initial_weights()
    fixed_g = _initial_weights()
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

    # Adaptive arm: weights updated vs ground truth; gates updated vs
    # ensemble final prediction (see module docstring).
    weights = _initial_weights()
    gates   = _initial_weights()
    weight_traj:  list[dict[str, Any]] = [{"step": -1, "weights": copy.deepcopy(weights)}]
    gate_traj:    list[dict[str, Any]] = [{"step": -1, "gates":   copy.deepcopy(gates)}]
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
                # Weight: compare topology prediction vs ground truth.
                w_ok = preds[t][cls] == rec["ground_truth"][cls]
                topo_weight_success[t][cls] = w_ok
                weights[t][cls] = update_weight_sdnd_proof(weights[t][cls], w_ok)

                # Gate: compare topology prediction vs ensemble's final
                # prediction. A gate "succeeds" when the topology agrees
                # with the majority vote, rewarding alignment with the
                # current routing consensus.
                g_ok = preds[t][cls] == final_pred[cls]
                topo_gate_success[t][cls] = g_ok
                gates[t][cls] = update_weight_sdnd_proof(gates[t][cls], g_ok)

        weight_traj.append({"step": step, "weights": copy.deepcopy(weights)})
        gate_traj.append({"step": step,   "gates":   copy.deepcopy(gates)})
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
            "initial_weights": _initial_weights(),
            "initial_gates":   _initial_weights(),
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


def load_exp5b_reference() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    boot = None
    trial_stats = None
    if EXP5B_EXTENDED_STATS.is_file():
        data = json.loads(EXP5B_EXTENDED_STATS.read_text(encoding="utf-8"))
        boot = data.get("bootstrap_n220")
        trial_stats = data.get("trial_stats_n20")
    return boot, trial_stats


def render_summary(
    trials: list[dict[str, Any]],
    trial_stats: dict[str, Any],
    boot: dict[str, Any],
) -> str:
    exp5b_boot, exp5b_trial_stats = load_exp5b_reference()
    lines = [
        "# Phase 1.4d Stage 3 Target C — per-label routing with gate learning",
        "",
        "Ensemble voting over Topology A + B_v3 + C_v3 with **six weights** "
        "(sparrow / bulbul × A / B_v3 / C_v3) AND **six gates** on top. "
        "Effective contribution of each topology-label pair is `w × g`. "
        "Weights are updated against ground truth (like Exp 5b); gates are "
        "updated against the ensemble's own final prediction, i.e. they "
        "reward topologies that agree with the current consensus.",
        "",
        f"Seeds: {ALL_SEEDS}. 20 trials × 11 second-half folds = "
        f"n_pooled = {20 * (22 - WARMUP_COUNT)}.",
        "No new LLM inference: every per-topology per-fold prediction comes from "
        "the committed Phase 1.3 / Phase 1.4a fold JSONs.",
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

    # Δ sign distribution
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
    lines.append(
        "Exp 5b extended reference: 4 positive / 16 zero / 0 negative. "
        f"Target C: **{pos} positive / {zero} zero / {neg} negative**."
    )
    lines.append("")

    # Stats table
    lines.append("## Statistical analysis")
    lines.append("")
    lines.append("| method | n | point Δ | Cohen's d | p | 95% CI | verdict |")
    lines.append("|---|---:|---:|---:|---:|---|---|")

    t_stats_n20 = trial_stats
    d20 = t_stats_n20.get("cohens_d")
    d20_str = f"{d20:+.3f}" if d20 is not None else "n/a"
    v20 = "Go" if t_stats_n20.get("go_judgment", {}).get("overall_go") else "No-Go"
    lines.append(
        f"| Target C trial t-test | 20 | {t_stats_n20['mean_diff']:+.3f} "
        f"| {d20_str} | {t_stats_n20['paired_t_test']['p_value']:.4f} "
        f"| [{t_stats_n20['ci_95'][0]:+.3f}, {t_stats_n20['ci_95'][1]:+.3f}] | {v20} |"
    )
    lines.append(
        f"| **Target C paired fold bootstrap** | **{boot['n_pooled_folds']}** "
        f"| {boot['observed_delta']:+.3f} "
        f"| **{boot['cohens_d_paired']:+.3f}** "
        f"| **{boot['p_value_twosided']:.4f}** "
        f"| [{boot['ci_95'][0]:+.3f}, {boot['ci_95'][1]:+.3f}] "
        f"| **{_verdict(boot)}** |"
    )
    if exp5b_trial_stats:
        d5 = exp5b_trial_stats.get("cohens_d")
        d5_str = f"{d5:+.3f}" if d5 is not None else "n/a"
        v5 = "Go" if exp5b_trial_stats.get("go_judgment", {}).get("overall_go") else "No-Go"
        lines.append(
            f"| Exp 5b extended trial t-test (ref) | 20 "
            f"| {exp5b_trial_stats['mean_diff']:+.3f} | {d5_str} "
            f"| {exp5b_trial_stats['paired_t_test']['p_value']:.4f} "
            f"| [{exp5b_trial_stats['ci_95'][0]:+.3f}, {exp5b_trial_stats['ci_95'][1]:+.3f}] "
            f"| {v5} |"
        )
    if exp5b_boot:
        v5b = _verdict(exp5b_boot)
        lines.append(
            f"| Exp 5b extended paired fold bootstrap (ref) | {exp5b_boot['n_pooled_folds']} "
            f"| {exp5b_boot['observed_delta']:+.3f} "
            f"| {exp5b_boot['cohens_d_paired']:+.3f} "
            f"| {exp5b_boot['p_value_twosided']:.4f} "
            f"| [{exp5b_boot['ci_95'][0]:+.3f}, {exp5b_boot['ci_95'][1]:+.3f}] | {v5b} |"
        )
    lines.append("")

    # Go criteria breakdown
    c = boot["criteria"]
    lines.append("## Bootstrap Go criteria (extended n=220)")
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
    lines.append(
        f"| direction | {boot['direction']} | — |"
    )
    lines.append(
        f"| **Overall** | — | **{_verdict(boot)}** |"
    )
    lines.append("")

    # Final weights + gates (n=20 mean)
    sums_w = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    sums_g = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    for tr in trials:
        w = tr["experiment_B"]["final_weights"]
        g = tr["experiment_B"]["final_gates"]
        for t in TOPOLOGIES:
            for cls in LABELS:
                sums_w[t][cls] += w[t][cls]
                sums_g[t][cls] += g[t][cls]
    n_tr = len(trials) or 1

    lines.append("## Final weights and gates (mean across 20 trials)")
    lines.append("")
    lines.append("| label | topology | weight | gate | w × g |")
    lines.append("|---|---|---:|---:|---:|")
    friendly = {"A": "A", "B": "B_v3", "C": "C_v3"}
    for cls in LABELS:
        for t in TOPOLOGIES:
            w_mean = sums_w[t][cls] / n_tr
            g_mean = sums_g[t][cls] / n_tr
            lines.append(
                f"| {cls} | {friendly[t]} | {w_mean:.3f} | {g_mean:.3f} "
                f"| {w_mean * g_mean:.3f} |"
            )
    lines.append("")

    # Routing analysis
    lines.append("## Routing analysis — mean effective contribution per label")
    lines.append("")
    lines.append("| label | most-routed topology | effective share | second | third |")
    lines.append("|---|---|---:|---|---|")
    for cls in LABELS:
        eff = {t: (sums_w[t][cls] / n_tr) * (sums_g[t][cls] / n_tr) for t in TOPOLOGIES}
        total = sum(eff.values()) or 1.0
        ordering = sorted(eff.items(), key=lambda kv: -kv[1])
        names = [(friendly[t], v / total) for t, v in ordering]
        lines.append(
            f"| {cls} | {names[0][0]} | {names[0][1]:.2%} "
            f"| {names[1][0]} ({names[1][1]:.2%}) "
            f"| {names[2][0]} ({names[2][1]:.2%}) |"
        )
    lines.append("")

    # Direct comparison to Exp 5b (w*g vs w)
    if exp5b_boot:
        lines.append("## Comparison vs Stage 1 Exp 5b extended (ensemble voting without gates)")
        lines.append("")
        lines.append(
            "| experiment | weight structure | vote mixing | Cohen's d (n=220) | verdict |"
        )
        lines.append("|---|---|---|---:|---|")
        lines.append(
            f"| Exp 5b extended | 6 weights (label-specific) | Σ(w · pred) / Σw "
            f"| {exp5b_boot['cohens_d_paired']:+.3f} | {_verdict(exp5b_boot)} |"
        )
        lines.append(
            f"| **Target C** | **6 weights + 6 gates** | **Σ(w·g · pred) / Σ(w·g)** "
            f"| **{boot['cohens_d_paired']:+.3f}** | **{_verdict(boot)}** |"
        )
        lines.append("")

    # Narrative verdict
    lines.append("## Verdict")
    lines.append("")
    if boot["overall_go_positive"]:
        if exp5b_boot and boot["cohens_d_paired"] > exp5b_boot["cohens_d_paired"]:
            lines.append(
                "**Case A — gates helped.** Target C clears the 3-criterion gate and "
                "Cohen's d exceeds Exp 5b extended. Explicit routing is a genuine "
                "addition on top of label-specific weights."
            )
        else:
            lines.append(
                "**Case B — gates are neutral.** Target C clears the gate but does "
                "not meaningfully exceed Exp 5b extended. The gate and the weight "
                "co-evolve and end up redundant; the sharper w × g mixing does not "
                "translate into additional signal."
            )
    else:
        lines.append(
            "**Case C — gates hurt.** Adding the gate destabilises the Exp 5b "
            "extended positive Go. Candidate causes: feedback loop (gate rewards "
            "consensus → majority topology wins gate → amplifies existing bias), "
            "or plain over-parameterisation on n=22 folds."
        )
    lines.append("")

    # Output files
    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `bootstrap_analysis.json`")
    lines.append("- `graphs/weight_gate_trajectory.png`")
    lines.append("- `graphs/routing_visualization.png`")
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
                        [e["gates"][t][cls]   for e in g_traj],
                        color="#dd8452", alpha=0.35, linewidth=0.9)
            ax.axvline(WARMUP_COUNT - 0.5, color="#888", linestyle="--", linewidth=0.7)
            ax.set_title(f"{cls} · Topology {friendly[t]}")
            ax.set_ylim(0, 1); ax.grid(alpha=0.3)
            if col == 0: ax.set_ylabel("value")
            if row == 1: ax.set_xlabel("fold step")
    axes[0, 0].plot([], [], color="#4c72b0", label="weight")
    axes[0, 0].plot([], [], color="#dd8452", label="gate")
    axes[0, 0].legend(fontsize=8, loc="lower left")
    fig.suptitle("Target C — weight (blue) vs gate (orange) trajectories across 20 trials")
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)


def plot_routing_visualization(trials: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    sums_w = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    sums_g = {t: {cls: 0.0 for cls in LABELS} for t in TOPOLOGIES}
    for tr in trials:
        w = tr["experiment_B"]["final_weights"]
        g = tr["experiment_B"]["final_gates"]
        for t in TOPOLOGIES:
            for cls in LABELS:
                sums_w[t][cls] += w[t][cls]
                sums_g[t][cls] += g[t][cls]
    n = len(trials) or 1
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    friendly = {"A": "A", "B": "B_v3", "C": "C_v3"}
    for ax, cls in zip(axes, LABELS):
        eff = np.array([(sums_w[t][cls] / n) * (sums_g[t][cls] / n) for t in TOPOLOGIES])
        share = eff / eff.sum() if eff.sum() > 0 else eff
        xs = np.arange(len(TOPOLOGIES))
        ax.bar(xs, share, color="#2a9d8f")
        for x, v in zip(xs, share):
            ax.annotate(f"{v:.2%}", (x, v), textcoords="offset points",
                        xytext=(0, 6), ha="center", fontsize=9)
        ax.set_xticks(xs); ax.set_xticklabels([friendly[t] for t in TOPOLOGIES])
        ax.set_ylim(0, 1)
        ax.set_title(f"label = {cls}")
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("effective contribution share (w × g)")
    fig.suptitle("Target C — mean effective routing across 20 trials")
    fig.tight_layout(); fig.savefig(out_path, dpi=120); plt.close(fig)


def plot_cohens_d_comparison(boot: dict[str, Any], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    exp5b_boot, _ = load_exp5b_reference()
    labels = []
    ds = []
    cis = []
    if exp5b_boot:
        labels.append("Exp 5b extended\n(ensemble + weights)")
        ds.append(exp5b_boot["cohens_d_paired"])
        cis.append(exp5b_boot["ci_95"])
    labels.append("Target C\n(ensemble + w × g)")
    ds.append(boot["cohens_d_paired"])
    cis.append(boot["ci_95"])
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    xs = np.arange(len(labels))
    ax.bar(xs, ds, color=["#4c72b0", "#2a9d8f"][: len(labels)])
    for x, d in zip(xs, ds):
        ax.annotate(f"d = {d:+.3f}", (x, d), textcoords="offset points",
                    xytext=(0, 8 if d >= 0 else -14), ha="center", fontsize=9)
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.axhline(0.8, color="#264653", linestyle=":", linewidth=1.0,
               label="Go threshold (|d|=0.8)")
    ax.set_xticks(xs); ax.set_xticklabels(labels)
    ax.set_ylabel("Cohen's d (paired, n=220 bootstrap)")
    ax.set_title("Cohen's d: ensemble-voting architectures")
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
    plot_routing_visualization(trials, GRAPHS_DIR / "routing_visualization.png")
    plot_cohens_d_comparison(boot, GRAPHS_DIR / "cohens_d_comparison.png")

    print()
    print("=== Phase 1.4d Stage 3 Target C summary ===")
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
