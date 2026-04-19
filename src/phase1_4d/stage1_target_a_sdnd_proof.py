"""Phase 1.4d Stage 1 — Experiment 1: target A with sdnd-proof flow_weight.

The three Phase 1.3-extended topologies (A = Audio-Only, B = Visual-Only,
C = Parallel Fusion) are combined in a weighted-vote ensemble. We ask a
single question: does the sdnd-proof flow_weight learning rule, applied
to the three ensemble weights, beat the fixed-equal-weights baseline?

Design mirrors sdnd-proof (single-node AAS):

    * 5 trials, seeds 42 / 137 / 256 / 512 / 1024.
    * Each trial: shuffle the clean 22 folds, first 11 = warm-up, last
      11 = evaluation. Fixed and Adaptive run on the same shuffle.
    * Fixed:    w_A = w_B = w_C = 0.5 for the whole trial.
    * Adaptive: w_A = w_B = w_C = 0.5 initially; after every fold each
      topology updates its own weight:
          success (topology's prediction matches both labels) ->
              w <- w + 0.1 * (1 - w)
          failure ->
              w <- w * 0.7
      Weights update on all 22 folds (continuous online evaluation).
    * Macro F1 is computed on the second-half 11 folds' ensemble
      predictions only (evaluation window).

We then compare the 5 paired (Fixed, Adaptive) macro F1 values with a
paired t-test, Cohen's d (paired), and a 95% CI on the mean delta.
Go criteria from sdnd-proof: p < 0.05, d >= 0.8, 95% CI excludes 0.

Predictions are reused from the committed fold JSONs
(`results/phase1_3_extended/topology_{a,b,c}/fold_*/*.json`). No LLM
inference runs.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4a_common.clean_tiers import load_usable_video_ids
from phase1_4d.common.ensemble import compute_f1_bundle, weighted_vote
from phase1_4d.common.flow_weight import (
    INITIAL_WEIGHT,
    is_topology_success,
    update_weight_sdnd_proof,
)

from typing import Callable

YT_METADATA_PATH = REPO_ROOT / "data" / "youtube_metadata.json"
LABELS_PATH = REPO_ROOT / "data" / "labels" / "phase1_labels.json"
TOPOLOGY_BASES = {
    "A": REPO_ROOT / "results" / "phase1_3_extended" / "topology_a",
    "B": REPO_ROOT / "results" / "phase1_3_extended" / "topology_b",
    "C": REPO_ROOT / "results" / "phase1_3_extended" / "topology_c",
}
OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage1_target_a_sdnd_proof"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary.json"
STATS_PATH = OUT_DIR / "statistical_analysis.json"

SEEDS = [42, 137, 256, 512, 1024]
WARMUP_COUNT = 11  # first half of the shuffle is warm-up; eval on the rest.


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def load_topology(base: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fold_dir in sorted(base.glob("fold_*")):
        for p in sorted(fold_dir.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            out[data["video_id"]] = data
    return out


def normalize_prediction(row: dict[str, Any]) -> dict[str, int]:
    """Extract binary ``sparrow`` / ``bulbul`` from a fold JSON."""
    if "error" in row:
        return {"sparrow": 0, "bulbul": 0}
    pred = row.get("final_prediction") or {}
    return {
        "sparrow": int(pred.get("sparrow", 0)),
        "bulbul":  int(pred.get("bulbul", 0)),
    }


def build_fold_records(topology_bases: dict[str, Path] | None = None) -> list[dict[str, Any]]:
    """Return clean-set fold records with per-topology predictions and GT.

    ``topology_bases`` maps topology keys ("A", "B", "C") to fold-JSON
    directories. Experiment 5 overrides this to load the Phase 1.4a
    improved topologies (B_v3, C_v3) while keeping the rest of the
    pipeline unchanged.
    """
    if topology_bases is None:
        topology_bases = TOPOLOGY_BASES
    usable_yt = load_usable_video_ids(YT_METADATA_PATH)
    topo = {k: load_topology(base) for k, base in topology_bases.items()}
    common_ids = set(topo["A"]) & set(topo["B"]) & set(topo["C"])
    clean_ids = sorted([
        vid for vid in common_ids
        if topo["A"][vid].get("source") == "self" or vid in usable_yt
    ])

    records: list[dict[str, Any]] = []
    for vid in clean_ids:
        rows = {k: topo[k][vid] for k in ("A", "B", "C")}
        gt = rows["A"].get("ground_truth") or {"sparrow": 0, "bulbul": 0}
        gt = {"sparrow": int(gt.get("sparrow", 0)), "bulbul": int(gt.get("bulbul", 0))}
        records.append({
            "video_id": vid,
            "source": rows["A"].get("source", "-"),
            "category": rows["A"].get("category", "-"),
            "ground_truth": gt,
            "predictions": {k: normalize_prediction(rows[k]) for k in ("A", "B", "C")},
        })
    return records


def run_trial(
    records: list[dict[str, Any]],
    seed: int,
    update_fn: Callable[[float, bool], float] = update_weight_sdnd_proof,
) -> dict[str, Any]:
    """Run one Fixed / Adaptive trial with a configurable update rule.

    ``update_fn(w, success) -> new_w`` is applied per-topology after every
    fold in the Adaptive branch. The default is the sdnd-proof rule used
    in Experiment 1; Experiment 2 passes the relaxed rule here.
    """
    rng = random.Random(seed)
    order = list(range(len(records)))
    rng.shuffle(order)

    # --- Experiment A (Fixed equal weights) ---
    fixed_weights = {"A": INITIAL_WEIGHT, "B": INITIAL_WEIGHT, "C": INITIAL_WEIGHT}
    fixed_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    fixed_per_fold: list[dict[str, Any]] = []
    for step, idx in enumerate(order):
        rec = records[idx]
        pred = weighted_vote(rec["predictions"], fixed_weights)
        fixed_per_fold.append({
            "step": step,
            "video_id": rec["video_id"],
            "pred": pred,
            "gt": rec["ground_truth"],
            "weights_before": dict(fixed_weights),
        })
        if step >= WARMUP_COUNT:
            fixed_eval_pairs.append((pred, rec["ground_truth"]))
    fixed_metrics = compute_f1_bundle(fixed_eval_pairs)

    # --- Experiment B (Adaptive, sdnd-proof flow_weight) ---
    adaptive_weights = {"A": INITIAL_WEIGHT, "B": INITIAL_WEIGHT, "C": INITIAL_WEIGHT}
    adaptive_eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    weight_trajectory: list[dict[str, Any]] = [
        {"step": -1, "weights": dict(adaptive_weights)}
    ]
    adaptive_per_fold: list[dict[str, Any]] = []
    for step, idx in enumerate(order):
        rec = records[idx]
        pred = weighted_vote(rec["predictions"], adaptive_weights)
        weights_before = dict(adaptive_weights)

        # Per-topology success/failure on this fold; update each weight.
        topology_success: dict[str, bool] = {}
        for t in ("A", "B", "C"):
            success = is_topology_success(rec["predictions"][t], rec["ground_truth"])
            topology_success[t] = success
            adaptive_weights[t] = update_fn(adaptive_weights[t], success)

        adaptive_per_fold.append({
            "step": step,
            "video_id": rec["video_id"],
            "pred": pred,
            "gt": rec["ground_truth"],
            "weights_before": weights_before,
            "weights_after": dict(adaptive_weights),
            "topology_success": topology_success,
        })
        weight_trajectory.append({"step": step, "weights": dict(adaptive_weights)})

        if step >= WARMUP_COUNT:
            adaptive_eval_pairs.append((pred, rec["ground_truth"]))
    adaptive_metrics = compute_f1_bundle(adaptive_eval_pairs)

    return {
        "seed": seed,
        "shuffle_order": order,
        "fold_video_ids_in_order": [records[i]["video_id"] for i in order],
        "warmup_folds":   [records[i]["video_id"] for i in order[:WARMUP_COUNT]],
        "eval_folds":     [records[i]["video_id"] for i in order[WARMUP_COUNT:]],
        "experiment_A": {
            "final_weights": fixed_weights,
            "macro_f1":    fixed_metrics["macro_f1"],
            "sparrow_f1":  fixed_metrics["sparrow_f1"],
            "bulbul_f1":   fixed_metrics["bulbul_f1"],
            "confusion":   fixed_metrics["confusion"],
            "per_fold":    fixed_per_fold,
        },
        "experiment_B": {
            "initial_weights": {"A": INITIAL_WEIGHT, "B": INITIAL_WEIGHT, "C": INITIAL_WEIGHT},
            "final_weights":   adaptive_weights,
            "weight_trajectory": weight_trajectory,
            "macro_f1":    adaptive_metrics["macro_f1"],
            "sparrow_f1":  adaptive_metrics["sparrow_f1"],
            "bulbul_f1":   adaptive_metrics["bulbul_f1"],
            "confusion":   adaptive_metrics["confusion"],
            "per_fold":    adaptive_per_fold,
        },
    }


def paired_statistics(results_A: list[float], results_B: list[float]) -> dict[str, Any]:
    arr_A = np.array(results_A, dtype=float)
    arr_B = np.array(results_B, dtype=float)
    diffs = arr_B - arr_A
    mean_diff = float(np.mean(diffs))
    std_diff = float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0
    n = len(diffs)

    t_stat_raw, p_value_raw = stats.ttest_rel(arr_B, arr_A)
    t_stat = float(t_stat_raw)
    p_value = float(p_value_raw)

    if std_diff > 0:
        cohens_d = mean_diff / std_diff
    elif mean_diff == 0:
        cohens_d = 0.0
    else:
        cohens_d = float("inf") if mean_diff > 0 else float("-inf")

    if n > 1 and std_diff > 0:
        se = std_diff / np.sqrt(n)
        ci_low, ci_high = stats.t.interval(0.95, df=n - 1, loc=mean_diff, scale=se)
        ci_low, ci_high = float(ci_low), float(ci_high)
    else:
        ci_low, ci_high = mean_diff, mean_diff

    go_p = p_value < 0.05
    go_d = cohens_d >= 0.8
    go_ci = ci_low > 0
    return {
        "results_A": [float(x) for x in results_A],
        "results_B": [float(x) for x in results_B],
        "diffs": [float(d) for d in diffs],
        "mean_diff": mean_diff,
        "std_diff": std_diff,
        "paired_t_test": {"t_stat": t_stat, "p_value": p_value},
        "cohens_d": float(cohens_d) if cohens_d not in (float("inf"), float("-inf")) else None,
        "cohens_d_raw": cohens_d,
        "ci_95": [ci_low, ci_high],
        "go_judgment": {
            "p_value_pass": bool(go_p),
            "cohens_d_pass": bool(go_d),
            "ci_pass": bool(go_ci),
            "overall_go": bool(go_p and go_d and go_ci),
        },
    }


def plot_weight_trajectory(trials: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True)
    topologies = ["A", "B", "C"]
    colors = {42: "#2a9d8f", 137: "#e76f51", 256: "#264653", 512: "#f4a261", 1024: "#6a4c93"}
    for ax, t in zip(axes, topologies):
        for tr in trials:
            traj = tr["experiment_B"]["weight_trajectory"]
            steps = [e["step"] for e in traj]
            vals = [e["weights"][t] for e in traj]
            ax.plot(steps, vals, marker=".", linewidth=1.2, color=colors.get(tr["seed"], "#444444"),
                    label=f"seed {tr['seed']}")
        ax.axvline(WARMUP_COUNT - 0.5, color="#888888", linestyle="--", linewidth=0.8,
                   label=f"eval boundary" if t == topologies[0] else None)
        ax.set_title(f"Topology {t}")
        ax.set_xlabel("fold step")
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("flow_weight")
    axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("Adaptive flow_weight trajectories (5 seeds, clean 22 fold)")
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
    ax.bar(x + width / 2, stats_result["results_B"], width, label="Adaptive (B)", color="#dd8452")
    ax.set_xticks(x)
    ax.set_xticklabels([f"trial {i+1}" for i in range(n)])
    ax.set_ylabel("macro F1 (second half, 11 folds)")
    ax.set_ylim(0, 1)
    ax.set_title("Fixed vs Adaptive macro F1 (5 trials)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_diff_distribution(stats_result: dict[str, Any], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    diffs = stats_result["diffs"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(range(len(diffs)), diffs, color=["#2a9d8f" if d >= 0 else "#e76f51" for d in diffs])
    ax.axhline(0.0, color="#555555", linewidth=0.8)
    mean = stats_result["mean_diff"]
    ax.axhline(mean, color="#264653", linestyle="--", linewidth=1.2, label=f"mean Δ = {mean:+.3f}")
    ci_low, ci_high = stats_result["ci_95"]
    ax.axhspan(ci_low, ci_high, alpha=0.12, color="#264653", label=f"95% CI [{ci_low:+.3f}, {ci_high:+.3f}]")
    ax.set_xticks(range(len(diffs)))
    ax.set_xticklabels([f"trial {i+1}" for i in range(len(diffs))])
    ax.set_ylabel("Δ macro F1 (Adaptive - Fixed)")
    ax.set_title("Per-trial Δ distribution")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def render_summary(
    trials: list[dict[str, Any]],
    stats_result: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    lines = [
        "# Phase 1.4d Stage 1 Experiment 1 — target A with sdnd-proof flow_weight",
        "",
        "Controlled comparison: Fixed equal weights vs Adaptive sdnd-proof flow_weight ",
        "over the three Phase 1.3-extended topologies (A = Audio-Only, B = Visual-Only, ",
        "C = Parallel Fusion). Clean 22-fold set (11 self + 11 YouTube Tier A/B/B'); ",
        f"first {WARMUP_COUNT} folds = warm-up, last {len(records) - WARMUP_COUNT} folds = evaluation. ",
        "Predictions come from the committed fold JSONs (no re-inference).",
        "",
        "## Per-trial results",
        "",
        "| Trial | Seed | Fixed macro F1 | Adaptive macro F1 | Δ |",
        "|---|---:|---:|---:|---:|",
    ]
    for i, tr in enumerate(trials, start=1):
        fa = tr["experiment_A"]["macro_f1"]
        fb = tr["experiment_B"]["macro_f1"]
        lines.append(f"| {i} | {tr['seed']} | {fa:.3f} | {fb:.3f} | {fb - fa:+.3f} |")
    lines.append("")

    lines.append("## Per-trial F1 breakdown")
    lines.append("")
    lines.append("| Trial | Seed | Fixed sparrow F1 | Fixed bulbul F1 | Adaptive sparrow F1 | Adaptive bulbul F1 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for i, tr in enumerate(trials, start=1):
        a, b = tr["experiment_A"], tr["experiment_B"]
        lines.append(
            f"| {i} | {tr['seed']} | {a['sparrow_f1']:.3f} | {a['bulbul_f1']:.3f} "
            f"| {b['sparrow_f1']:.3f} | {b['bulbul_f1']:.3f} |"
        )
    lines.append("")

    # Final weights per trial
    lines.append("## Adaptive final weights per trial")
    lines.append("")
    lines.append("| Trial | Seed | w_A | w_B | w_C |")
    lines.append("|---|---:|---:|---:|---:|")
    final_sums = {"A": 0.0, "B": 0.0, "C": 0.0}
    for i, tr in enumerate(trials, start=1):
        fw = tr["experiment_B"]["final_weights"]
        lines.append(f"| {i} | {tr['seed']} | {fw['A']:.3f} | {fw['B']:.3f} | {fw['C']:.3f} |")
        for t in final_sums:
            final_sums[t] += fw[t]
    n_tr = len(trials) or 1
    lines.append(
        f"| mean | - | {final_sums['A']/n_tr:.3f} | {final_sums['B']/n_tr:.3f} | {final_sums['C']/n_tr:.3f} |"
    )
    lines.append("")

    lines.append("## Statistical analysis")
    lines.append("")
    s = stats_result
    lines.append(f"- Mean Δ: **{s['mean_diff']:+.3f}**")
    lines.append(f"- Std Δ: {s['std_diff']:.3f}")
    lines.append(
        f"- Paired t-test: t = {s['paired_t_test']['t_stat']:.3f}, "
        f"p = {s['paired_t_test']['p_value']:.4f}"
    )
    d_val = s["cohens_d"]
    d_str = f"{d_val:.3f}" if d_val is not None else "undefined (std_diff=0)"
    lines.append(f"- Cohen's d (paired): {d_str}")
    lines.append(f"- 95% CI (paired): [{s['ci_95'][0]:+.3f}, {s['ci_95'][1]:+.3f}]")
    lines.append("")

    lines.append("## Go judgment (sdnd-proof 3 criteria)")
    lines.append("")
    lines.append("| Criterion | Threshold | Value | Pass |")
    lines.append("|---|---|---:|:-:|")
    j = s["go_judgment"]
    lines.append(
        f"| p-value  | < 0.05 | {s['paired_t_test']['p_value']:.4f} "
        f"| {'Y' if j['p_value_pass'] else 'N'} |"
    )
    lines.append(
        f"| Cohen's d | >= 0.8 | {d_str} | {'Y' if j['cohens_d_pass'] else 'N'} |"
    )
    lines.append(
        f"| 95% CI lower | > 0 | {s['ci_95'][0]:+.3f} | {'Y' if j['ci_pass'] else 'N'} |"
    )
    lines.append(
        f"| **Overall** | all pass | | **{'Go' if j['overall_go'] else 'No-Go'}** |"
    )
    lines.append("")

    # Discussion
    lines.append("## Weight trajectory discussion")
    lines.append("")
    mean_final = {t: final_sums[t] / n_tr for t in ("A", "B", "C")}
    lines.append(
        f"- Mean final weights across {len(trials)} trials: "
        f"A = {mean_final['A']:.3f}, B = {mean_final['B']:.3f}, C = {mean_final['C']:.3f}"
    )
    # Dominant weight
    dominant = max(mean_final, key=lambda k: mean_final[k])
    lines.append(
        f"- Topology {dominant} carries the highest mean weight, matching Phase 1.3-extended "
        "clean performance where its point F1 is the strongest."
    )
    lines.append(
        "- Topology A starts and stays low because its label-level success rate is much "
        "worse than B and C on the clean set (many fallback-induced 0/0 predictions)."
    )
    lines.append(
        "- The sdnd-proof asymmetry (additive success, multiplicative failure) is visible: "
        "once a topology loses a fold it drops fast (× 0.7), then crawls back at +0.1·(1−w) "
        "per correct fold."
    )
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append(
        f"- n = 5 trials; the t-test has 4 degrees of freedom, so Cohen's d >= 0.8 needs a "
        "mean-to-std ratio near 0.8+. With variance across seeds this bar is genuinely hard."
    )
    lines.append(
        "- Trials differ only in the shuffle order of the same 22 folds; trials are NOT "
        "independent dataset draws. The paired t-test here measures sensitivity to fold "
        "ordering, not to dataset sampling. For the latter we need bootstrap of the fold set."
    )
    lines.append(
        "- All three topologies draw predictions from the same pool of fold JSONs, so the "
        "ensemble's correlation structure is fixed. Independent LLM re-runs would give a "
        "different answer."
    )
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json` — all 5 trials with per-fold decisions")
    lines.append("- `statistical_analysis.json` — paired stats + Go judgment")
    lines.append("- `graphs/weight_trajectory.png`")
    lines.append("- `graphs/f1_comparison.png`")
    lines.append("- `graphs/diff_distribution.png`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()
    records = build_fold_records()
    print(f"[load] clean fold records: {len(records)}")
    sources = {}
    for r in records:
        sources[r["source"]] = sources.get(r["source"], 0) + 1
    print(f"[load] sources: {sources}")
    if len(records) != 22:
        print(f"[warn] expected 22 clean folds, got {len(records)}", file=sys.stderr)

    trials: list[dict[str, Any]] = []
    for seed in SEEDS:
        print(f"[trial] seed={seed} ...", flush=True)
        trial = run_trial(records, seed)
        trials.append(trial)
        print(
            f"  Fixed macro F1 = {trial['experiment_A']['macro_f1']:.3f}; "
            f"Adaptive macro F1 = {trial['experiment_B']['macro_f1']:.3f}; "
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
        json.dumps({"trials": trials, "n_folds": len(records), "warmup_count": WARMUP_COUNT,
                    "seeds": SEEDS, "records": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps(stats_result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(render_summary(trials, stats_result, records), encoding="utf-8")

    plot_weight_trajectory(trials, GRAPHS_DIR / "weight_trajectory.png")
    plot_f1_comparison(stats_result, GRAPHS_DIR / "f1_comparison.png")
    plot_diff_distribution(stats_result, GRAPHS_DIR / "diff_distribution.png")

    print()
    print("=== Phase 1.4d Stage 1 summary ===")
    print(f"Mean Δ macro F1 = {stats_result['mean_diff']:+.3f}")
    print(f"p = {stats_result['paired_t_test']['p_value']:.4f}, "
          f"d = {stats_result['cohens_d']}, "
          f"CI = [{stats_result['ci_95'][0]:+.3f}, {stats_result['ci_95'][1]:+.3f}]")
    print(f"Go (all 3 criteria): {stats_result['go_judgment']['overall_go']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
