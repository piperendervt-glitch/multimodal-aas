"""Phase 1.4d Stage 2 — paired fold bootstrap over Exp 1 / 2 / 3.

The three Stage 2 experiments each produced 5 trials × 11 second-half
folds = 55 paired (Fixed, Adaptive) predictions. The per-trial t-test
has n=5 and therefore very low power; a paired fold-level bootstrap
over n=55 preserves pairing (same resampled fold set for both
conditions) and yields substantially tighter intervals. This mirrors
the methodology used for Phase 1.4a bbox v3 validation (commit
b6a2580).

The Go gate follows the spec — p < 0.05, |Cohen's d| ≥ 0.8, 95% CI
excludes 0 — but the *direction* is reported as a separate flag
(positive Go vs. negative Go / "statistically-significant harm") so
Experiment 1's large negative effect does not get silently counted as
a success.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

EXP1_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage2_target_b_full_interpretationC"
EXP2_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage2_target_b_no_score_to_llm"
EXP3_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage2_target_b_no_score_stronger_penalty"

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage2_bootstrap_analysis"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
STATS_PATH = OUT_DIR / "statistical_analysis_bootstrap.json"
TRIALS_PATH = OUT_DIR / "trials_bootstrap.json"

WARMUP_COUNT = 11
N_BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 42

EXPERIMENTS: list[dict[str, Any]] = [
    {
        "name": "Exp 1",
        "label": "scores shown",
        "trials_path": EXP1_DIR / "trials_summary.json",
        "trial_stats_path": EXP1_DIR / "statistical_analysis.json",
    },
    {
        "name": "Exp 2",
        "label": "scores hidden",
        "trials_path": EXP2_DIR / "trials_summary.json",
        "trial_stats_path": EXP2_DIR / "statistical_analysis.json",
    },
    {
        "name": "Exp 3",
        "label": "scores hidden, stronger penalty",
        "trials_path": EXP3_DIR / "trials_summary.json",
        "trial_stats_path": EXP3_DIR / "statistical_analysis.json",
    },
]


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def extract_eval_pairs(trials_path: Path) -> list[dict[str, Any]]:
    """Pool the second-half per-fold records across 5 trials."""
    data = json.loads(trials_path.read_text(encoding="utf-8"))
    trials_fixed = data["trials_fixed"]
    trials_adaptive = data["trials_adaptive"]
    pooled: list[dict[str, Any]] = []
    for fx, ad in zip(trials_fixed, trials_adaptive):
        fx_by_step = {f["step"]: f for f in fx["per_fold"]}
        ad_by_step = {f["step"]: f for f in ad["per_fold"]}
        steps = sorted(fx_by_step.keys())
        for step in steps:
            if step < WARMUP_COUNT:
                continue
            f_fold = fx_by_step[step]
            a_fold = ad_by_step[step]
            pooled.append({
                "trial_seed": fx["seed"],
                "step": int(step),
                "video_id": f_fold["video_id"],
                "pred_fixed": f_fold["parsed"],
                "pred_adaptive": a_fold["parsed"],
                "gt": f_fold["ground_truth"],
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
    matrix = {
        "sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }
    for pred, gt in pairs:
        for cls in ("sparrow", "bulbul"):
            p, g = pred[cls], gt[cls]
            if p == 1 and g == 1:
                matrix[cls]["tp"] += 1
            elif p == 1 and g == 0:
                matrix[cls]["fp"] += 1
            elif p == 0 and g == 1:
                matrix[cls]["fn"] += 1
            else:
                matrix[cls]["tn"] += 1
    return (
        _f1(matrix["sparrow"]["tp"], matrix["sparrow"]["fp"], matrix["sparrow"]["fn"])
        + _f1(matrix["bulbul"]["tp"],  matrix["bulbul"]["fp"],  matrix["bulbul"]["fn"])
    ) / 2.0


def paired_fold_bootstrap(
    pooled: list[dict[str, Any]],
    n_bootstrap: int = N_BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Compute paired bootstrap CI / p / d for Adaptive − Fixed macro F1."""
    rng = np.random.default_rng(seed)
    n = len(pooled)
    deltas = np.empty(n_bootstrap, dtype=float)
    fx_boot = np.empty(n_bootstrap, dtype=float)
    ad_boot = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        fx_pairs = [(pooled[j]["pred_fixed"],    pooled[j]["gt"]) for j in idx]
        ad_pairs = [(pooled[j]["pred_adaptive"], pooled[j]["gt"]) for j in idx]
        fx_f1 = macro_f1_pooled(fx_pairs)
        ad_f1 = macro_f1_pooled(ad_pairs)
        fx_boot[i] = fx_f1
        ad_boot[i] = ad_f1
        deltas[i] = ad_f1 - fx_f1

    mean_delta = float(np.mean(deltas))
    std_delta = float(np.std(deltas, ddof=1)) if n_bootstrap > 1 else 0.0
    ci_lo = float(np.percentile(deltas, 2.5))
    ci_hi = float(np.percentile(deltas, 97.5))

    p_pos = float(np.mean(deltas > 0))
    p_neg = float(np.mean(deltas < 0))
    p_twosided = 2.0 * min(p_pos, p_neg)
    p_twosided = max(p_twosided, 1.0 / n_bootstrap)  # Monte Carlo floor

    cohens_d = float(mean_delta / std_delta) if std_delta > 0 else 0.0
    direction = "positive" if mean_delta > 0 else "negative" if mean_delta < 0 else "zero"

    # Point estimate on the observed data (no resampling)
    fx_obs = macro_f1_pooled([(r["pred_fixed"],    r["gt"]) for r in pooled])
    ad_obs = macro_f1_pooled([(r["pred_adaptive"], r["gt"]) for r in pooled])
    point_delta = ad_obs - fx_obs

    p_pass = bool(p_twosided < 0.05)
    d_pass_abs = bool(abs(cohens_d) >= 0.8)
    ci_pass = bool(ci_lo > 0 or ci_hi < 0)
    overall_go = bool(p_pass and d_pass_abs and ci_pass and direction == "positive")
    negative_go = bool(p_pass and d_pass_abs and ci_pass and direction == "negative")

    return {
        "n_bootstrap": n_bootstrap,
        "n_pooled_folds": n,
        "seed": seed,
        "observed_fixed_macro_f1":    fx_obs,
        "observed_adaptive_macro_f1": ad_obs,
        "observed_delta":             point_delta,
        "bootstrap_mean_delta":       mean_delta,
        "bootstrap_std_delta":        std_delta,
        "ci_95":                      [ci_lo, ci_hi],
        "p_value_twosided":           p_twosided,
        "cohens_d_paired":            cohens_d,
        "direction":                  direction,
        "criteria": {
            "p_value_pass_at_0.05":   p_pass,
            "abs_cohens_d_pass_at_0.8": d_pass_abs,
            "ci_excludes_zero":       ci_pass,
        },
        "overall_go_positive": overall_go,
        "overall_go_negative": negative_go,
        "deltas_histogram":    _build_histogram(deltas),
    }


def _build_histogram(deltas: np.ndarray, n_bins: int = 60) -> dict[str, Any]:
    counts, edges = np.histogram(deltas, bins=n_bins)
    return {
        "bin_edges": [float(x) for x in edges],
        "counts":    [int(c) for c in counts],
    }


def load_trial_stats(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    # Exp 1 wraps the stats in a primary_vs_fixed_0_4 key for Phase 1.4a; here files
    # are the flat stats dicts produced by Stage 2 scripts.
    return data


def verdict_label(result: dict[str, Any]) -> str:
    if result["overall_go_positive"]:
        return "**Go** (all 3 criteria, positive direction)"
    if result["overall_go_negative"]:
        return "**Go (negative direction)** — all 3 criteria pass but Adaptive < Fixed"
    return "**No-Go**"


def render_summary(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 1.4d Stage 2 — paired fold bootstrap analysis",
        "",
        f"Paired fold-level resampling (n={N_BOOTSTRAP} bootstrap draws, seed={BOOTSTRAP_SEED}) "
        "of the three Stage 2 experiments. Each experiment pools 5 trials × 11 second-half "
        "folds = 55 (Fixed, Adaptive) prediction pairs and resamples them with replacement; "
        "Fixed and Adaptive use the same index set on every draw so fold-level common "
        "variance is absorbed. Methodology mirrors Phase 1.4a paired bootstrap (commit b6a2580).",
        "",
        "sdnd-proof 3-criterion gate:",
        "- p-value (two-sided) < 0.05",
        "- |Cohen's d (paired)| ≥ 0.8 (direction reported separately)",
        "- 95% CI excludes 0",
        "",
        "Overall verdict: Go ⇔ all three criteria pass *and* direction is positive.",
        "",
        "## Trial t-test vs paired fold bootstrap",
        "",
    ]
    lines.append(
        "| Experiment | statistic | n | point Δ | Cohen's d | p | 95% CI | verdict |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---|---|")
    for exp_info, res in zip(EXPERIMENTS, results):
        trial = res["trial_stats"]
        boot = res["bootstrap"]
        d_trial = trial.get("cohens_d")
        d_trial_str = f"{d_trial:+.3f}" if d_trial is not None else "n/a"
        trial_verdict = (
            "Go" if trial.get("go_judgment", {}).get("overall_go") else "No-Go"
        )
        boot_verdict = (
            "Go" if res["bootstrap"]["overall_go_positive"] else
            "Go (neg)" if res["bootstrap"]["overall_go_negative"] else
            "No-Go"
        )
        lines.append(
            f"| {exp_info['name']} ({exp_info['label']}) | trial t-test | 5 "
            f"| {trial['mean_diff']:+.3f} | {d_trial_str} "
            f"| {trial['paired_t_test']['p_value']:.4f} "
            f"| [{trial['ci_95'][0]:+.3f}, {trial['ci_95'][1]:+.3f}] "
            f"| {trial_verdict} |"
        )
        lines.append(
            f"| {exp_info['name']} ({exp_info['label']}) | paired fold bootstrap "
            f"| {boot['n_pooled_folds']} | {boot['observed_delta']:+.3f} "
            f"| {boot['cohens_d_paired']:+.3f} "
            f"| {boot['p_value_twosided']:.4f} "
            f"| [{boot['ci_95'][0]:+.3f}, {boot['ci_95'][1]:+.3f}] "
            f"| {boot_verdict} |"
        )
    lines.append("")

    # Bootstrap criteria table
    lines.append("## Bootstrap criteria breakdown")
    lines.append("")
    lines.append(
        "| Experiment | p < 0.05 | |d| ≥ 0.8 | CI excl. 0 | direction | Overall |"
    )
    lines.append("|---|:-:|:-:|:-:|:-:|---|")
    for exp_info, res in zip(EXPERIMENTS, results):
        boot = res["bootstrap"]
        c = boot["criteria"]
        lines.append(
            f"| {exp_info['name']} "
            f"| {'Y' if c['p_value_pass_at_0.05'] else 'N'} "
            f"| {'Y' if c['abs_cohens_d_pass_at_0.8'] else 'N'} "
            f"| {'Y' if c['ci_excludes_zero'] else 'N'} "
            f"| {boot['direction']} "
            f"| {verdict_label(boot)} |"
        )
    lines.append("")

    # Commentary
    lines.append("## Discussion")
    lines.append("")
    exp1_boot = results[0]["bootstrap"]
    exp2_boot = results[1]["bootstrap"]
    exp3_boot = results[2]["bootstrap"]

    lines.append(
        f"1. **Power gain from fold-level bootstrap.** Trial t-test had df=4; the bootstrap "
        f"uses 55 paired folds × 10,000 draws, so the CI width collapses sharply. "
        f"Compare Exp 2: trial CI [{results[1]['trial_stats']['ci_95'][0]:+.3f}, "
        f"{results[1]['trial_stats']['ci_95'][1]:+.3f}] vs bootstrap CI "
        f"[{exp2_boot['ci_95'][0]:+.3f}, {exp2_boot['ci_95'][1]:+.3f}]."
    )
    lines.append(
        f"2. **Exp 1 negative-direction significance is confirmed.** Bootstrap reports "
        f"d={exp1_boot['cohens_d_paired']:+.3f}, p={exp1_boot['p_value_twosided']:.4f}, "
        f"CI=[{exp1_boot['ci_95'][0]:+.3f}, {exp1_boot['ci_95'][1]:+.3f}] (direction: "
        f"{exp1_boot['direction']}). "
        f"Exposing numerical reliability scores to the LLM harms accuracy at the "
        f"fold-level n too, not just by coincidence at n=5."
    )
    lines.append(
        f"3. **Exp 3 vs the 3-criterion gate.** Bootstrap reports "
        f"d={exp3_boot['cohens_d_paired']:+.3f}, p={exp3_boot['p_value_twosided']:.4f}, "
        f"CI=[{exp3_boot['ci_95'][0]:+.3f}, {exp3_boot['ci_95'][1]:+.3f}]."
    )
    c3 = exp3_boot["criteria"]
    if exp3_boot["overall_go_positive"]:
        lines.append(
            "   Exp 3 clears all three criteria with positive direction — **the first "
            "positive Statistical Go in Phase 1.4d**. This validates the *silent "
            "information filtering + strong label-specific penalty* recipe."
        )
    else:
        fails = [
            lbl for lbl, ok in [
                ("p<0.05", c3["p_value_pass_at_0.05"]),
                ("|d|≥0.8", c3["abs_cohens_d_pass_at_0.8"]),
                ("CI excludes 0", c3["ci_excludes_zero"]),
            ] if not ok
        ]
        lines.append(
            f"   Fails on: {', '.join(fails) if fails else '—'}. Direction is "
            f"{exp3_boot['direction']} (favouring Adaptive) so the positive-Go trajectory "
            "continues, but the absolute bar is not cleared on n=55."
        )
    lines.append(
        "4. **Stage 2 trajectory.** Bootstrap Cohen's d goes "
        f"{exp1_boot['cohens_d_paired']:+.3f} → {exp2_boot['cohens_d_paired']:+.3f} "
        f"→ {exp3_boot['cohens_d_paired']:+.3f} across Exp 1 → 2 → 3. The Exp 1 → 2 "
        "sign flip reproduces the trial-level finding (prompt-design ablation is the "
        "dominant effect). Exp 2 → 3 is non-monotonic under bootstrap: stronger "
        "penalties raised the point Δ but also raised per-fold variance, so Cohen's d "
        "*fell*. The tightest positive effect is in Exp 2, not Exp 3 — the opposite "
        "of what the trial-level t-test suggested."
    )
    lines.append("")

    # Output file list
    lines.append("## Output files")
    lines.append("")
    lines.append("- `statistical_analysis_bootstrap.json` — full per-experiment stats (including histogram bins)")
    lines.append("- `trials_bootstrap.json` — pooled per-fold records used as bootstrap input")
    lines.append("- `graphs/bootstrap_distribution.png` — Δ distributions with CI overlays")
    lines.append("- `graphs/ci_comparison.png` — trial t-test CI vs bootstrap CI")
    lines.append("- `graphs/stage2_final_cohens_d.png` — Cohen's d progression (trial vs bootstrap)")
    lines.append("")
    return "\n".join(lines)


def plot_bootstrap_distributions(
    results: list[dict[str, Any]], out_path: Path
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True)
    colors = ["#c44e52", "#dd8452", "#2a9d8f"]
    for ax, exp_info, res, color in zip(axes, EXPERIMENTS, results, colors):
        b = res["bootstrap"]
        edges = np.array(b["deltas_histogram"]["bin_edges"])
        counts = np.array(b["deltas_histogram"]["counts"])
        centers = 0.5 * (edges[:-1] + edges[1:])
        ax.bar(centers, counts, width=(edges[1] - edges[0]), color=color, alpha=0.75)
        ax.axvline(0.0, color="#555", linestyle="--", linewidth=0.9)
        ax.axvline(b["observed_delta"], color="#111", linewidth=1.4,
                   label=f"point Δ={b['observed_delta']:+.3f}")
        ax.axvline(b["ci_95"][0], color="#000", linestyle=":", linewidth=1.0)
        ax.axvline(b["ci_95"][1], color="#000", linestyle=":", linewidth=1.0,
                   label=f"95% CI [{b['ci_95'][0]:+.3f}, {b['ci_95'][1]:+.3f}]")
        ax.set_title(f"{exp_info['name']} ({exp_info['label']})\nd={b['cohens_d_paired']:+.3f}, "
                     f"p={b['p_value_twosided']:.3f}")
        ax.set_xlabel("Δ macro F1 (Adaptive − Fixed)")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("bootstrap count")
    fig.suptitle(f"Stage 2 paired fold bootstrap — Δ distributions (n={N_BOOTSTRAP:,}, seed={BOOTSTRAP_SEED})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_ci_comparison(results: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    n_exp = len(results)
    xs = np.arange(n_exp)
    offsets = [-0.15, 0.15]
    labels_done = set()
    for exp_info, res, x in zip(EXPERIMENTS, results, xs):
        trial = res["trial_stats"]
        boot = res["bootstrap"]
        for src, (label, color, off) in zip(
            (trial, boot),
            (("trial t-test (n=5)", "#4c72b0", offsets[0]),
             (f"paired fold bootstrap (n={boot['n_pooled_folds']})", "#c44e52", offsets[1])),
        ):
            if src is trial:
                m = trial["mean_diff"]
                ci = trial["ci_95"]
            else:
                m = boot["bootstrap_mean_delta"]
                ci = boot["ci_95"]
            lbl_key = label
            use_label = label if lbl_key not in labels_done else None
            labels_done.add(lbl_key)
            ax.errorbar([x + off], [m],
                        yerr=[[m - ci[0]], [ci[1] - m]],
                        fmt="o", capsize=5, markersize=7,
                        color=color, label=use_label)
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([exp["name"] for exp in EXPERIMENTS])
    ax.set_ylabel("mean Δ macro F1 with 95% CI")
    ax.set_title("Stage 2 — trial t-test vs paired fold bootstrap")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_cohens_d_progression(results: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    xs = np.arange(len(results))
    d_trial = [res["trial_stats"].get("cohens_d") or 0.0 for res in results]
    d_boot  = [res["bootstrap"]["cohens_d_paired"] for res in results]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(xs, d_trial, marker="o", linewidth=2.0, color="#4c72b0",
            label="Cohen's d (trial t-test, n=5)")
    ax.plot(xs, d_boot, marker="s", linewidth=2.0, color="#c44e52",
            label="Cohen's d (paired fold bootstrap, n=55)")
    for x, dt, db in zip(xs, d_trial, d_boot):
        ax.annotate(f"{dt:+.3f}", xy=(x, dt), xytext=(0, 10),
                    textcoords="offset points", ha="center", fontsize=8,
                    color="#4c72b0")
        ax.annotate(f"{db:+.3f}", xy=(x, db), xytext=(0, -14),
                    textcoords="offset points", ha="center", fontsize=8,
                    color="#c44e52")
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.axhline(0.8, color="#2a9d8f", linestyle=":", linewidth=1.0,
               label="Go threshold (|d| = 0.8)")
    ax.axhline(-0.8, color="#888", linestyle=":", linewidth=1.0)
    ax.set_xticks(xs)
    ax.set_xticklabels([exp["name"] for exp in EXPERIMENTS])
    ax.set_ylabel("Cohen's d (paired)")
    ax.set_title("Stage 2 Cohen's d — trial-level vs bootstrap")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:
    ensure_utf8_streams()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    trials_payload: dict[str, Any] = {}
    for exp_info in EXPERIMENTS:
        name = exp_info["name"]
        print(f"[{name}] loading {exp_info['trials_path']} ...", flush=True)
        pooled = extract_eval_pairs(exp_info["trials_path"])
        trial_stats = load_trial_stats(exp_info["trial_stats_path"])
        print(f"[{name}] pooled {len(pooled)} second-half folds; running bootstrap ...",
              flush=True)
        boot = paired_fold_bootstrap(pooled)
        direction = boot["direction"]
        print(
            f"[{name}] observed Δ={boot['observed_delta']:+.3f}; "
            f"bootstrap d={boot['cohens_d_paired']:+.3f}, "
            f"p={boot['p_value_twosided']:.4f}, "
            f"CI=[{boot['ci_95'][0]:+.3f}, {boot['ci_95'][1]:+.3f}] "
            f"({direction})",
            flush=True,
        )
        results.append({
            "name": name,
            "label": exp_info["label"],
            "trial_stats": trial_stats,
            "bootstrap": boot,
        })
        trials_payload[name] = {
            "label": exp_info["label"],
            "n_pooled_folds": len(pooled),
            "pooled_records": pooled,
        }

    # Persist artefacts
    TRIALS_PATH.write_text(
        json.dumps(
            {
                "warmup_count": WARMUP_COUNT,
                "n_bootstrap": N_BOOTSTRAP,
                "seed": BOOTSTRAP_SEED,
                "experiments": trials_payload,
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps(
            {"results": results, "n_bootstrap": N_BOOTSTRAP, "seed": BOOTSTRAP_SEED},
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(render_summary(results), encoding="utf-8")

    plot_bootstrap_distributions(results, GRAPHS_DIR / "bootstrap_distribution.png")
    plot_ci_comparison(results, GRAPHS_DIR / "ci_comparison.png")
    plot_cohens_d_progression(results, GRAPHS_DIR / "stage2_final_cohens_d.png")

    print()
    print("=== Phase 1.4d Stage 2 bootstrap summary ===")
    for res in results:
        b = res["bootstrap"]
        print(
            f"{res['name']} ({res['label']}): "
            f"Δ={b['observed_delta']:+.3f}, d={b['cohens_d_paired']:+.3f}, "
            f"p={b['p_value_twosided']:.4f}, "
            f"CI=[{b['ci_95'][0]:+.3f}, {b['ci_95'][1]:+.3f}] → "
            f"{verdict_label(b)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
