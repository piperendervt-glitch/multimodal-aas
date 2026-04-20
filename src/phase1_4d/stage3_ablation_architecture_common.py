"""Shared infrastructure for Phase 1.4d Stage 3 architecture-boundary ablations.

Ablations E and F-1/F-2/F-3 all re-run Target C's weight + gate + consensus
pipeline on a **subset of the three topologies** (A = Phase 1.3 Topology A,
B = Phase 1.4a Topology B_v3, C = Phase 1.4a Topology C_v3). Only the
topology subset changes — update rule, integration, reward signal, seeds,
warm-up count, and bootstrap protocol are identical to Target C so the
resulting Cohen's d values are directly comparable to Target C (+4.014,
commit `bfd840d`), Exp 5b extended (+2.041, commit `2db9ca2`), and Stage
2 Exp 2 extended (−0.115, commit `d2fc14e`).
"""

from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4d.stage1_target_a_sdnd_proof import WARMUP_COUNT  # re-exported
from phase1_4d.common.ensemble import compute_f1_bundle
from phase1_4d.common.flow_weight import INITIAL_WEIGHT, update_weight_sdnd_proof

LABELS: tuple[str, ...] = ("sparrow", "bulbul")
TOPOLOGIES_ALL: tuple[str, ...] = ("A", "B", "C")

ALL_SEEDS: list[int] = [
    42, 137, 256, 512, 1024,
    2048, 4096, 8192, 16384, 32768,
    65536, 131072, 262144, 524288, 1048576,
    2097152, 4194304, 8388608, 16777216, 33554432,
]

N_BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 42

FRIENDLY_TOPOLOGY_NAME = {"A": "A", "B": "B_v3", "C": "C_v3"}


# ---------------------------------------------------------------------------
# Core ensemble primitives, parametrised by topology subset
# ---------------------------------------------------------------------------

def initial_table(subset: Sequence[str]) -> dict[str, dict[str, float]]:
    return {t: {cls: INITIAL_WEIGHT for cls in LABELS} for t in subset}


def weighted_vote_gated_subset(
    preds_all: dict[str, dict[str, int]],
    weights: dict[str, dict[str, float]],
    gates: dict[str, dict[str, float]],
    subset: Sequence[str],
    threshold: float = 0.5,
) -> dict[str, int]:
    """Weighted-vote ensemble using only ``subset`` of the loaded topologies.

    ``preds_all`` still contains all three topologies (because
    ``build_fold_records`` loads them together), but only those in
    ``subset`` contribute to the vote.
    """
    out: dict[str, int] = {}
    for cls in LABELS:
        eff = {t: weights[t][cls] * gates[t][cls] for t in subset}
        total = sum(eff.values())
        if total <= 1e-9:
            out[cls] = 0
            continue
        score = sum(eff[t] * preds_all[t][cls] for t in subset) / total
        out[cls] = 1 if score >= threshold else 0
    return out


def run_trial_subset(
    records: list[dict[str, Any]],
    seed: int,
    subset: Sequence[str],
) -> dict[str, Any]:
    """One Fixed/Adaptive trial restricted to ``subset`` topologies.

    Shares Target C's update rule: weight <- GT-based sdnd-proof update,
    gate <- consensus-agreement sdnd-proof update (topology prediction
    compared to the ensemble's own final prediction).
    """
    rng = random.Random(seed)
    order = list(range(len(records)))
    rng.shuffle(order)

    # Fixed arm: weights and gates pinned at 0.5 throughout (the
    # restricted version of Target C's fixed arm).
    fixed_w = initial_table(subset)
    fixed_g = initial_table(subset)
    fixed_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    fixed_per_fold: list[dict[str, Any]] = []
    for step, idx in enumerate(order):
        rec = records[idx]
        pred = weighted_vote_gated_subset(
            rec["predictions"], fixed_w, fixed_g, subset,
        )
        fixed_per_fold.append({
            "step": step, "video_id": rec["video_id"],
            "pred": pred, "gt": rec["ground_truth"],
        })
        if step >= WARMUP_COUNT:
            fixed_eval_pairs.append((pred, rec["ground_truth"]))
    fixed_metrics = compute_f1_bundle(fixed_eval_pairs)

    # Adaptive arm: weights learn against GT, gates learn against the
    # ensemble's final prediction. Identical to Target C, only the
    # topology loop is restricted to ``subset``.
    weights = initial_table(subset)
    gates   = initial_table(subset)
    weight_traj: list[dict[str, Any]] = [{"step": -1, "weights": copy.deepcopy(weights)}]
    gate_traj:   list[dict[str, Any]] = [{"step": -1, "gates":   copy.deepcopy(gates)}]
    adaptive_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    adaptive_per_fold: list[dict[str, Any]] = []

    for step, idx in enumerate(order):
        rec = records[idx]
        preds = rec["predictions"]
        final_pred = weighted_vote_gated_subset(preds, weights, gates, subset)

        weights_before = copy.deepcopy(weights)
        gates_before   = copy.deepcopy(gates)
        topo_weight_success: dict[str, dict[str, bool]] = {t: {} for t in subset}
        topo_gate_success:   dict[str, dict[str, bool]] = {t: {} for t in subset}

        for t in subset:
            for cls in LABELS:
                w_ok = preds[t][cls] == rec["ground_truth"][cls]
                topo_weight_success[t][cls] = w_ok
                weights[t][cls] = update_weight_sdnd_proof(weights[t][cls], w_ok)

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
        "topology_subset": list(subset),
        "shuffle_order": order,
        "fold_video_ids_in_order": [records[i]["video_id"] for i in order],
        "warmup_folds": [records[i]["video_id"] for i in order[:WARMUP_COUNT]],
        "eval_folds":   [records[i]["video_id"] for i in order[WARMUP_COUNT:]],
        "experiment_A": {
            "final_weights": fixed_w, "final_gates": fixed_g,
            "macro_f1":   fixed_metrics["macro_f1"],
            "sparrow_f1": fixed_metrics["sparrow_f1"],
            "bulbul_f1":  fixed_metrics["bulbul_f1"],
            "confusion":  fixed_metrics["confusion"],
            "per_fold":   fixed_per_fold,
        },
        "experiment_B": {
            "initial_weights": initial_table(subset),
            "initial_gates":   initial_table(subset),
            "final_weights":   weights, "final_gates": gates,
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
# Paired fold bootstrap (identical shape to Target C / Ablation 1 / Ablation 5)
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
        "n_pooled_folds": n, "n_bootstrap": n_bootstrap, "seed": seed,
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


def verdict(boot: dict[str, Any]) -> str:
    if boot["overall_go_positive"]:
        return "Go (positive)"
    if boot["overall_go_negative"]:
        return "Go (negative)"
    return "No-Go"


# ---------------------------------------------------------------------------
# Shared driver
# ---------------------------------------------------------------------------

def load_reference(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not path.is_file():
        return None, None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("bootstrap_n220"), data.get("trial_stats_n20")


def delta_sign_counts(trials: list[dict[str, Any]]) -> tuple[int, int, int]:
    pos = neg = zero = 0
    for tr in trials:
        d_val = tr["experiment_B"]["macro_f1"] - tr["experiment_A"]["macro_f1"]
        if d_val > 1e-9: pos += 1
        elif d_val < -1e-9: neg += 1
        else: zero += 1
    return pos, zero, neg


def write_trial_and_stats(
    out_dir: Path,
    trials: list[dict[str, Any]],
    trial_stats: dict[str, Any],
    boot: dict[str, Any],
    n_folds: int,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "trials_summary.json").write_text(
        json.dumps({
            "seeds": ALL_SEEDS, "warmup_count": WARMUP_COUNT,
            "n_folds_per_trial": n_folds,
            "trials": trials,
            "trial_stats": trial_stats,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "bootstrap_analysis.json").write_text(
        json.dumps({
            "trial_stats_n20": trial_stats,
            "bootstrap_n220":  boot,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def render_common_summary_head(
    title: str,
    description: str,
    subset: Sequence[str],
    trials: list[dict[str, Any]],
    trial_stats: dict[str, Any],
    boot: dict[str, Any],
    references: Iterable[tuple[str, dict[str, Any] | None]] = (),
) -> list[str]:
    """Return the per-ablation summary's header lines up to the Go criteria."""
    lines = [
        f"# {title}",
        "",
        description,
        "",
        f"Topology subset in vote: {', '.join(FRIENDLY_TOPOLOGY_NAME[t] for t in subset)} "
        f"(n_topologies = {len(subset)}).",
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

    pos, zero, neg = delta_sign_counts(trials)
    lines.append("## Δ sign distribution across 20 trials")
    lines.append("")
    lines.append("| direction | count |")
    lines.append("|---|---:|")
    lines.append(f"| Δ > 0 | {pos} |")
    lines.append(f"| Δ = 0 | {zero} |")
    lines.append(f"| Δ < 0 | {neg} |")
    lines.append("")

    lines.append("## Statistical analysis")
    lines.append("")
    lines.append("| method | n | point Δ | Cohen's d | p | 95% CI | verdict |")
    lines.append("|---|---:|---:|---:|---:|---|---|")
    d20 = trial_stats.get("cohens_d")
    d20_str = f"{d20:+.3f}" if d20 is not None else "n/a"
    v20 = "Go" if trial_stats.get("go_judgment", {}).get("overall_go") else "No-Go"
    lines.append(
        f"| This experiment — trial t-test | 20 | {trial_stats['mean_diff']:+.3f} "
        f"| {d20_str} | {trial_stats['paired_t_test']['p_value']:.4f} "
        f"| [{trial_stats['ci_95'][0]:+.3f}, {trial_stats['ci_95'][1]:+.3f}] | {v20} |"
    )
    lines.append(
        f"| **This experiment — paired fold bootstrap** | **{boot['n_pooled_folds']}** "
        f"| {boot['observed_delta']:+.3f} "
        f"| **{boot['cohens_d_paired']:+.3f}** "
        f"| **{boot['p_value_twosided']:.4f}** "
        f"| [{boot['ci_95'][0]:+.3f}, {boot['ci_95'][1]:+.3f}] "
        f"| **{verdict(boot)}** |"
    )
    for ref_name, ref_boot in references:
        if ref_boot is None:
            continue
        lines.append(
            f"| {ref_name} (ref) | {ref_boot['n_pooled_folds']} "
            f"| {ref_boot['observed_delta']:+.3f} "
            f"| {ref_boot['cohens_d_paired']:+.3f} "
            f"| {ref_boot['p_value_twosided']:.4f} "
            f"| [{ref_boot['ci_95'][0]:+.3f}, {ref_boot['ci_95'][1]:+.3f}] "
            f"| {verdict(ref_boot)} |"
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
    lines.append(f"| **Overall** | — | **{verdict(boot)}** |")
    lines.append("")

    return lines
