"""Phase 1.4d Stage 2 Experiment 3 — stronger penalties, scores still hidden.

Direct follow-up to Experiment 2 (commit 2dd8756). Exp 2 flipped
Cohen's d from −1.320 (Exp 1, scores shown) to +0.447 (scores hidden)
— a clean prompt-design ablation — but the 3-criterion Go gate
(d ≥ 0.8) remained out of reach. Exp 3 keeps everything else identical
and only strengthens the four label-specific failure multipliers:

    visual_sparrow: 0.80 → 0.70
    visual_bulbul:  0.90 → 0.85
    audio_sparrow:  0.75 → 0.60   (largest strengthening)
    audio_bulbul:   0.95 → 0.90

The hypothesis is that stronger penalties will pull at least one weight
below the 0.4 `brief` threshold, activating the lowest detail tier for
some folds and creating more variance between Fixed and Adaptive. If
Cohen's d climbs past 0.8, Stage 2 gets a Go; if it collapses, we hit
the Stage 1 Exp 1 diversity-collapse regime again — both outcomes are
informative.
"""

from __future__ import annotations

import copy
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4d.common.modality_filter import (
    SYSTEM_PROMPT_NO_SCORE,
    build_prompt_no_score,
)
from phase1_4d.stage2_target_b_full_interpretationC import (
    INITIAL_WEIGHT,
    LLM_MAX_RETRIES,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SEC,
    MODEL,
    OLLAMA_URL,
    STAGE1_EXP5B_STATS,
    SEEDS,
    SUCCESS_STEP,
    WARMUP_COUNT,
    build_clean_records,
    check_ollama_ready,
    ensure_utf8_streams,
    paired_statistics,
    pooled_f1,
)
from phase1_4d.stage2_target_b_no_score_to_llm import (
    DETAIL_THRESHOLDS,
    evaluate_fixed_trial,
    llm_with_retry,
    update_weight_labeled,
)

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage2_target_b_no_score_stronger_penalty"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary.json"
STATS_PATH = OUT_DIR / "statistical_analysis.json"

EXP1_STATS_PATH = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage2_target_b_full_interpretationC" / "statistical_analysis.json"
)
EXP1_TRIALS_PATH = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage2_target_b_full_interpretationC" / "trials_summary.json"
)
EXP2_STATS_PATH = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage2_target_b_no_score_to_llm" / "statistical_analysis.json"
)
EXP2_TRIALS_PATH = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage2_target_b_no_score_to_llm" / "trials_summary.json"
)

PENALTIES = {
    "visual": {"sparrow": 0.70, "bulbul": 0.85},
    "audio":  {"sparrow": 0.60, "bulbul": 0.90},
}


def run_fixed_cache(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    fixed_weights = {
        "visual": {"sparrow": INITIAL_WEIGHT, "bulbul": INITIAL_WEIGHT},
        "audio":  {"sparrow": INITIAL_WEIGHT, "bulbul": INITIAL_WEIGHT},
    }
    cache: dict[str, dict[str, Any]] = {}
    for rec in records:
        vid = rec["video_id"]
        prompt, meta = build_prompt_no_score(
            rec["yolo_output"], rec["bbox_distribution"],
            rec["birdnet_output"], fixed_weights,
            thresholds=DETAIL_THRESHOLDS,
        )
        llm = llm_with_retry(SYSTEM_PROMPT_NO_SCORE, prompt)
        parsed = llm["parsed"] or {"sparrow": 0, "bulbul": 0}
        cache[vid] = {
            "prompt": prompt,
            "llm_raw": llm["raw"],
            "parsed": parsed,
            "error": llm["error"],
            "elapsed_sec": llm["elapsed_sec"],
            "visual_level": meta["visual_level"],
            "audio_level": meta["audio_level"],
        }
        status = "ok" if llm["error"] is None else "ERR"
        print(f"  [fixed {vid}] {status} pred={parsed} "
              f"(attempts {llm['attempts']}, {llm['elapsed_sec']:.1f}s)", flush=True)
    return cache


def run_adaptive_trial(records: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    order = list(range(len(records)))
    rng.shuffle(order)
    weights = {
        "visual": {"sparrow": INITIAL_WEIGHT, "bulbul": INITIAL_WEIGHT},
        "audio":  {"sparrow": INITIAL_WEIGHT, "bulbul": INITIAL_WEIGHT},
    }
    trajectory: list[dict[str, Any]] = [
        {"step": -1, "weights": copy.deepcopy(weights)}
    ]
    per_fold: list[dict[str, Any]] = []
    eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []

    for step, idx in enumerate(order):
        rec = records[idx]
        prompt, meta = build_prompt_no_score(
            rec["yolo_output"], rec["bbox_distribution"],
            rec["birdnet_output"], weights,
            thresholds=DETAIL_THRESHOLDS,
        )
        llm = llm_with_retry(SYSTEM_PROMPT_NO_SCORE, prompt)
        parsed = llm["parsed"] or {"sparrow": 0, "bulbul": 0}
        weights_before = copy.deepcopy(weights)

        gt = rec["ground_truth"]
        v_pred = rec["topology_b_v3_prediction"]
        a_pred = rec["topology_a_prediction"]
        updates = {"visual": {}, "audio": {}}
        for cls in ("sparrow", "bulbul"):
            v_ok = v_pred[cls] == gt[cls]
            a_ok = a_pred[cls] == gt[cls]
            updates["visual"][cls] = v_ok
            updates["audio"][cls] = a_ok
            weights["visual"][cls] = update_weight_labeled(
                weights["visual"][cls], v_ok, PENALTIES["visual"][cls]
            )
            weights["audio"][cls] = update_weight_labeled(
                weights["audio"][cls], a_ok, PENALTIES["audio"][cls]
            )

        trajectory.append({"step": step, "weights": copy.deepcopy(weights)})
        per_fold.append({
            "step": step, "video_id": rec["video_id"],
            "weights_before": weights_before,
            "weights_after": copy.deepcopy(weights),
            "visual_level": meta["visual_level"],
            "audio_level": meta["audio_level"],
            "prompt": prompt, "llm_raw": llm["raw"],
            "parsed": parsed, "llm_error": llm["error"],
            "llm_attempts": llm["attempts"],
            "llm_elapsed_sec": llm["elapsed_sec"],
            "topology_updates": updates, "ground_truth": gt,
        })
        print(
            f"  [adaptive seed={seed} step={step:02d}] {rec['video_id']} "
            f"[v={meta['visual_level'][:3]}, a={meta['audio_level'][:3]}] "
            f"pred={parsed} ({llm['elapsed_sec']:.1f}s)",
            flush=True,
        )
        if step >= WARMUP_COUNT:
            eval_pairs.append((parsed, gt))

    metrics = pooled_f1(eval_pairs)
    return {
        "seed": seed,
        "shuffle_order": order,
        "fold_video_ids_in_order": [records[i]["video_id"] for i in order],
        "warmup_folds": [records[i]["video_id"] for i in order[:WARMUP_COUNT]],
        "eval_folds":   [records[i]["video_id"] for i in order[WARMUP_COUNT:]],
        "final_weights": weights,
        "weight_trajectory": trajectory,
        "per_fold": per_fold,
        "macro_f1":   metrics["macro_f1"],
        "sparrow_f1": metrics["sparrow_f1"],
        "bulbul_f1":  metrics["bulbul_f1"],
        "confusion":  metrics["confusion"],
    }


def _load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _safe_d(stats: dict[str, Any]) -> str:
    d = stats.get("cohens_d")
    return f"{d:+.3f}" if d is not None else "n/a"


def render_summary(
    trials_fixed: list[dict[str, Any]],
    trials_adaptive: list[dict[str, Any]],
    stats_result: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    exp1_stats = _load_json(EXP1_STATS_PATH) if EXP1_STATS_PATH.is_file() else None
    exp2_stats = _load_json(EXP2_STATS_PATH) if EXP2_STATS_PATH.is_file() else None
    exp1_trials = _load_json(EXP1_TRIALS_PATH) if EXP1_TRIALS_PATH.is_file() else None
    exp2_trials = _load_json(EXP2_TRIALS_PATH) if EXP2_TRIALS_PATH.is_file() else None
    exp5b_stats = _load_json(STAGE1_EXP5B_STATS) if STAGE1_EXP5B_STATS.is_file() else None

    lines = [
        "# Phase 1.4d Stage 2 Experiment 3 — stronger penalties, scores still hidden",
        "",
        "Single-variable change vs Experiment 2 (commit 2dd8756): each of the four "
        "label-specific failure multipliers is made more aggressive. Everything "
        "else (no-score prompt, detail thresholds 0.4/0.6, 5 seeds, clean 22 folds, "
        "warm-up 11 / eval 11, Topology A & B_v3 single-modality updates) is "
        "carried over verbatim.",
        "",
        "Penalty change:",
        "",
        "| modality-label | Exp 2 | **Exp 3** |",
        "|---|---:|---:|",
        f"| visual.sparrow | 0.80 | **{PENALTIES['visual']['sparrow']}** |",
        f"| visual.bulbul  | 0.90 | **{PENALTIES['visual']['bulbul']}** |",
        f"| audio.sparrow  | 0.75 | **{PENALTIES['audio']['sparrow']}** |",
        f"| audio.bulbul   | 0.95 | **{PENALTIES['audio']['bulbul']}** |",
        "",
        "Objective: pull at least one weight below the 0.4 `brief` threshold so "
        "the detail knob finally sees all three tiers, and push Cohen's d past 0.8.",
        "",
        "## Per-trial macro F1",
        "",
        "| Trial | Seed | Fixed | Adaptive | Δ |",
        "|---|---:|---:|---:|---:|",
    ]
    for i, (fx, ad) in enumerate(zip(trials_fixed, trials_adaptive), start=1):
        lines.append(
            f"| {i} | {fx['seed']} | {fx['macro_f1']:.3f} | {ad['macro_f1']:.3f} "
            f"| {ad['macro_f1'] - fx['macro_f1']:+.3f} |"
        )
    lines.append("")

    # Per-label F1
    lines.append("## Per-trial F1 breakdown")
    lines.append("")
    lines.append("| Trial | Seed | Fixed sparrow | Fixed bulbul | Adaptive sparrow | Adaptive bulbul |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for i, (fx, ad) in enumerate(zip(trials_fixed, trials_adaptive), start=1):
        lines.append(
            f"| {i} | {fx['seed']} | {fx['sparrow_f1']:.3f} | {fx['bulbul_f1']:.3f} "
            f"| {ad['sparrow_f1']:.3f} | {ad['bulbul_f1']:.3f} |"
        )
    lines.append("")

    # Final weights
    lines.append("## Adaptive final weights per trial")
    lines.append("")
    lines.append("| Trial | Seed | v_sparrow | v_bulbul | a_sparrow | a_bulbul |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    sums = {"v_sparrow": 0.0, "v_bulbul": 0.0, "a_sparrow": 0.0, "a_bulbul": 0.0}
    min_w = 1.0
    brief_hits = {"v_sparrow": 0, "v_bulbul": 0, "a_sparrow": 0, "a_bulbul": 0}
    for i, ad in enumerate(trials_adaptive, start=1):
        w = ad["final_weights"]
        lines.append(
            f"| {i} | {ad['seed']} "
            f"| {w['visual']['sparrow']:.3f} | {w['visual']['bulbul']:.3f} "
            f"| {w['audio']['sparrow']:.3f} | {w['audio']['bulbul']:.3f} |"
        )
        for mod, label, key in [
            ("visual", "sparrow", "v_sparrow"),
            ("visual", "bulbul",  "v_bulbul"),
            ("audio",  "sparrow", "a_sparrow"),
            ("audio",  "bulbul",  "a_bulbul"),
        ]:
            val = w[mod][label]
            sums[key] += val
            min_w = min(min_w, val)
            if val < 0.4:
                brief_hits[key] += 1
    n_tr = len(trials_adaptive) or 1
    lines.append(
        f"| mean | - | {sums['v_sparrow']/n_tr:.3f} | {sums['v_bulbul']/n_tr:.3f} "
        f"| {sums['a_sparrow']/n_tr:.3f} | {sums['a_bulbul']/n_tr:.3f} |"
    )
    lines.append("")

    # Brief-tier reach across trials (final weights only; trajectory count separate)
    lines.append(
        f"- Minimum final weight observed across 5 trials × 4 slots: **{min_w:.3f}** "
        f"({'reached brief tier (<0.4)' if min_w < 0.4 else 'did not reach brief'})."
    )
    lines.append("- Final-weight brief-tier hits per slot (out of 5 trials):")
    for key, label in (("v_sparrow", "visual.sparrow"), ("v_bulbul", "visual.bulbul"),
                        ("a_sparrow", "audio.sparrow"), ("a_bulbul", "audio.bulbul")):
        lines.append(f"  - {label}: {brief_hits[key]} / 5")
    lines.append("")

    # Detail level frequencies (Adaptive + Fixed)
    vis_counts = {"brief": 0, "medium": 0, "full": 0}
    aud_counts = {"brief": 0, "medium": 0, "full": 0}
    trajectory_brief: dict[str, int] = {"visual": 0, "audio": 0}
    trajectory_total_steps = 0
    for ad in trials_adaptive:
        for fold in ad["per_fold"]:
            vis_counts[fold["visual_level"]] += 1
            aud_counts[fold["audio_level"]] += 1
            trajectory_total_steps += 1
            # also count brief-tier excursions across trajectory (even if final weight > 0.4)
            w_before = fold["weights_before"]
            v_avg = (w_before["visual"]["sparrow"] + w_before["visual"]["bulbul"]) / 2
            a_avg = (w_before["audio"]["sparrow"]  + w_before["audio"]["bulbul"])  / 2
            if v_avg <= 0.4:
                trajectory_brief["visual"] += 1
            if a_avg <= 0.4:
                trajectory_brief["audio"] += 1
    lines.append(
        f"## Adaptive detail-level frequencies (5 × {len(records)} = "
        f"{5 * len(records)} decisions)"
    )
    lines.append("")
    lines.append("| level | visual | audio |")
    lines.append("|---|---:|---:|")
    for level in ("brief", "medium", "full"):
        lines.append(f"| {level} | {vis_counts[level]} | {aud_counts[level]} |")
    lines.append("")
    lines.append(
        f"Trajectory excursions where the modality average fell at or below 0.4 "
        f"(regardless of final tier): visual = {trajectory_brief['visual']}, "
        f"audio = {trajectory_brief['audio']}."
    )
    lines.append("")

    # Stats
    s = stats_result
    lines.append("## Statistical analysis (Adaptive vs Fixed)")
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
    j = s["go_judgment"]
    lines.append("## Go judgment (sdnd-proof 3 criteria)")
    lines.append("")
    lines.append("| Criterion | Threshold | Value | Pass |")
    lines.append("|---|---|---:|:-:|")
    lines.append(
        f"| p-value | < 0.05 | {s['paired_t_test']['p_value']:.4f} "
        f"| {'Y' if j['p_value_pass'] else 'N'} |"
    )
    lines.append(f"| Cohen's d | >= 0.8 | {d_str} | {'Y' if j['cohens_d_pass'] else 'N'} |")
    lines.append(
        f"| 95% CI lower | > 0 | {s['ci_95'][0]:+.3f} "
        f"| {'Y' if j['ci_pass'] else 'N'} |"
    )
    lines.append(
        f"| **Overall** | all pass | | **{'Go' if j['overall_go'] else 'No-Go'}** |"
    )
    lines.append("")

    # Stage 2 three-experiment comparison
    if exp1_stats and exp2_stats and exp1_trials and exp2_trials:
        lines.append("## Stage 2 three-experiment comparison")
        lines.append("")
        lines.append(
            "| Exp | prompt | penalty | Fixed mean | Adaptive mean | mean Δ | d | p | CI | verdict |"
        )
        lines.append("|---|---|---|---:|---:|---:|---:|---:|---|---|")
        fixed_mean = lambda trs: sum(tr["macro_f1"] for tr in trs) / len(trs)
        e1_fx_mean = fixed_mean(exp1_trials["trials_fixed"])
        e1_ad_mean = fixed_mean(exp1_trials["trials_adaptive"])
        e2_fx_mean = fixed_mean(exp2_trials["trials_fixed"])
        e2_ad_mean = fixed_mean(exp2_trials["trials_adaptive"])
        e3_fx_mean = fixed_mean(trials_fixed)
        e3_ad_mean = fixed_mean(trials_adaptive)
        e1_v = "Go" if exp1_stats["go_judgment"]["overall_go"] else "No-Go"
        e2_v = "Go" if exp2_stats["go_judgment"]["overall_go"] else "No-Go"
        e3_v = "Go" if j["overall_go"] else "No-Go"
        lines.append(
            f"| Exp 1 | scores shown | ×0.9 uniform "
            f"| {e1_fx_mean:.3f} | {e1_ad_mean:.3f} "
            f"| {exp1_stats['mean_diff']:+.3f} | {_safe_d(exp1_stats)} "
            f"| {exp1_stats['paired_t_test']['p_value']:.3f} "
            f"| [{exp1_stats['ci_95'][0]:+.3f}, {exp1_stats['ci_95'][1]:+.3f}] "
            f"| **{e1_v}** |"
        )
        lines.append(
            f"| Exp 2 | scores hidden | 0.80/0.90/0.75/0.95 "
            f"| {e2_fx_mean:.3f} | {e2_ad_mean:.3f} "
            f"| {exp2_stats['mean_diff']:+.3f} | {_safe_d(exp2_stats)} "
            f"| {exp2_stats['paired_t_test']['p_value']:.3f} "
            f"| [{exp2_stats['ci_95'][0]:+.3f}, {exp2_stats['ci_95'][1]:+.3f}] "
            f"| **{e2_v}** |"
        )
        lines.append(
            f"| **Exp 3** | **scores hidden** | **0.70/0.85/0.60/0.90** "
            f"| {e3_fx_mean:.3f} | {e3_ad_mean:.3f} "
            f"| {s['mean_diff']:+.3f} | {d_str if d_val is None else f'{d_val:+.3f}'} "
            f"| {s['paired_t_test']['p_value']:.3f} "
            f"| [{s['ci_95'][0]:+.3f}, {s['ci_95'][1]:+.3f}] "
            f"| **{e3_v}** |"
        )
        lines.append("")

    # Commentary / hypothesis check
    lines.append("## Hypothesis check")
    lines.append("")
    e2_audio_sparrow = 0.382  # Exp 2 observation
    e3_audio_sparrow = sums["a_sparrow"] / n_tr
    lines.append(
        f"- **Hypothesis A — brief-tier reach**: Exp 2 audio.sparrow mean was 0.382 "
        f"(just above 0.4). Exp 3 penalty for audio.sparrow is 0.60; final mean is "
        f"**{e3_audio_sparrow:.3f}** "
        f"({'below' if e3_audio_sparrow < 0.4 else 'at or above'} the 0.4 brief boundary). "
        f"Brief-tier decisions in adaptive trajectory: audio = {trajectory_brief['audio']}, "
        f"visual = {trajectory_brief['visual']}."
    )
    lines.append(
        f"- **Hypothesis B — diversity collapse**: if Cohen's d drops below Exp 2's +0.447, "
        "the stronger penalties over-concentrated evidence. Measured d = "
        f"{d_str} (vs Exp 2's +0.447)."
    )
    lines.append(
        f"- **Hypothesis C — Go via penalty strength**: target d ≥ 0.8. Measured d = "
        f"{d_str}. Go gate crossed? {'Yes' if j['overall_go'] else 'No'}."
    )
    lines.append("")

    if exp5b_stats:
        lines.append("## Stage 1 Exp 5b anchor (reminder)")
        lines.append("")
        lines.append(
            f"Stage 1 Exp 5b (ensemble-voting architecture): Δ={exp5b_stats['mean_diff']:+.3f}, "
            f"d={_safe_d(exp5b_stats)}, p={exp5b_stats['paired_t_test']['p_value']:.3f}. "
            "Stage 2 tests the same weight-learning machinery on a single-LLM substrate, "
            "so absolute F1 values are not directly comparable — only the Δ sign and "
            "effect-size magnitude are."
        )
        lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `statistical_analysis.json`")
    lines.append("- `graphs/weight_trajectory_exp3.png`")
    lines.append("- `graphs/detail_level_evolution_exp3.png`")
    lines.append("- `graphs/stage2_comparison.png`")
    lines.append("- `graphs/cohens_d_progression.png`")
    lines.append("")
    return "\n".join(lines)


# --- plots ---

def plot_weight_trajectory(trials_adaptive: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    colors = {42: "#2a9d8f", 137: "#e76f51", 256: "#264653",
              512: "#f4a261", 1024: "#6a4c93"}
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharey=True, sharex=True)
    panels = [
        ("visual", "sparrow", axes[0, 0]),
        ("visual", "bulbul",  axes[0, 1]),
        ("audio",  "sparrow", axes[1, 0]),
        ("audio",  "bulbul",  axes[1, 1]),
    ]
    for modality, cls, ax in panels:
        for ad in trials_adaptive:
            steps = [e["step"] for e in ad["weight_trajectory"]]
            vals = [e["weights"][modality][cls] for e in ad["weight_trajectory"]]
            ax.plot(steps, vals, marker=".", linewidth=1.0, alpha=0.9,
                    color=colors.get(ad["seed"], "#444"),
                    label=f"seed {ad['seed']}")
        ax.axvline(WARMUP_COUNT - 0.5, color="#888", linestyle="--", linewidth=0.7)
        ax.axhline(0.4, color="#c44e52", linestyle=":", linewidth=0.7, alpha=0.7,
                   label="brief tier" if (modality == "visual" and cls == "sparrow") else None)
        ax.axhline(0.6, color="#2a9d8f", linestyle=":", linewidth=0.7, alpha=0.7,
                   label="full tier" if (modality == "visual" and cls == "sparrow") else None)
        ax.set_title(f"{modality} · {cls} (penalty ×{PENALTIES[modality][cls]})")
        ax.set_ylim(0, 1); ax.grid(alpha=0.3)
    axes[0, 0].legend(loc="lower left", fontsize=7)
    axes[1, 0].set_xlabel("fold step"); axes[1, 1].set_xlabel("fold step")
    axes[0, 0].set_ylabel("flow_weight"); axes[1, 0].set_ylabel("flow_weight")
    fig.suptitle("Stage 2 Exp 3 — weights with stronger penalties (brief tier visualised)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_detail_level_evolution(trials_adaptive: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    n_steps = max(len(ad["per_fold"]) for ad in trials_adaptive)
    n_trials = len(trials_adaptive)
    levels = {"brief": 0, "medium": 1, "full": 2}
    visual = np.zeros((n_trials, n_steps), dtype=int)
    audio = np.zeros((n_trials, n_steps), dtype=int)
    for i, ad in enumerate(trials_adaptive):
        for j, fold in enumerate(ad["per_fold"]):
            visual[i, j] = levels[fold["visual_level"]]
            audio[i, j]  = levels[fold["audio_level"]]
    cmap = ListedColormap(["#eeeeee", "#9ec3d4", "#2a9d8f"])
    fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    for ax, data, title in ((axes[0], visual, "Visual detail"), (axes[1], audio, "Audio detail")):
        im = ax.imshow(data, aspect="auto", cmap=cmap, vmin=0, vmax=2)
        ax.set_yticks(range(n_trials))
        ax.set_yticklabels([f"trial {i+1}" for i in range(n_trials)])
        ax.set_title(title)
        ax.axvline(WARMUP_COUNT - 0.5, color="red", linestyle="--", linewidth=0.8)
    axes[1].set_xlabel("fold step")
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), ticks=[0, 1, 2], fraction=0.02, pad=0.02)
    cbar.set_ticklabels(["brief", "medium", "full"])
    fig.suptitle("Stage 2 Exp 3 — detail-level evolution (stronger penalties)")
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_stage2_comparison(stats_result: dict[str, Any], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    if EXP1_STATS_PATH.is_file():
        items.append(("Exp 1\n(scores shown)", _load_json(EXP1_STATS_PATH)))
    if EXP2_STATS_PATH.is_file():
        items.append(("Exp 2\n(scores hidden)", _load_json(EXP2_STATS_PATH)))
    items.append(("Exp 3\n(stronger penalty)", stats_result))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, (label, st) in enumerate(items):
        m = st["mean_diff"]
        ci = st["ci_95"]
        ax.errorbar([i], [m], yerr=[[m - ci[0]], [ci[1] - m]],
                    fmt="o", color="#264653", capsize=6, markersize=8)
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xticks(range(len(items))); ax.set_xticklabels([l for l, _ in items])
    ax.set_ylabel("mean Δ macro F1 with 95% CI")
    ax.set_title("Stage 2 experiments — mean paired Δ with 95% CI")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_cohens_d_progression(stats_result: dict[str, Any], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    labels = []
    ds = []
    if EXP1_STATS_PATH.is_file():
        labels.append("Exp 1")
        ds.append(_load_json(EXP1_STATS_PATH).get("cohens_d") or 0.0)
    if EXP2_STATS_PATH.is_file():
        labels.append("Exp 2")
        ds.append(_load_json(EXP2_STATS_PATH).get("cohens_d") or 0.0)
    labels.append("Exp 3")
    ds.append(stats_result.get("cohens_d") or 0.0)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(range(len(labels)), ds, marker="o", linewidth=2.0, color="#264653")
    for i, d in enumerate(ds):
        ax.annotate(f"{d:+.3f}", xy=(i, d), xytext=(0, 10), textcoords="offset points",
                    ha="center", fontsize=9)
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.axhline(0.8, color="#2a9d8f", linestyle=":", linewidth=1.0,
               label="Go threshold (d = 0.8)")
    ax.axhline(-0.8, color="#c44e52", linestyle=":", linewidth=1.0,
               label="Negative effect (d = −0.8)")
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
    ax.set_ylabel("Cohen's d (paired)")
    ax.set_title("Stage 2 Cohen's d progression across experiments")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:
    ensure_utf8_streams()
    check_ollama_ready()
    records = build_clean_records()
    print(f"[load] clean fold records: {len(records)}")

    print("[fixed] issuing 22 cached LLM calls (no-score prompt) ...", flush=True)
    fixed_cache = run_fixed_cache(records)

    trials_fixed: list[dict[str, Any]] = []
    trials_adaptive: list[dict[str, Any]] = []
    for seed in SEEDS:
        print(f"[trial] seed={seed}", flush=True)
        trials_fixed.append(evaluate_fixed_trial(records, fixed_cache, seed))
        trials_adaptive.append(run_adaptive_trial(records, seed))

    results_A = [tr["macro_f1"] for tr in trials_fixed]
    results_B = [tr["macro_f1"] for tr in trials_adaptive]
    stats_result = paired_statistics(results_A, results_B)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    TRIALS_PATH.write_text(
        json.dumps(
            {
                "seeds": SEEDS, "warmup_count": WARMUP_COUNT,
                "n_folds": len(records), "records": records,
                "fixed_cache": fixed_cache,
                "trials_fixed": trials_fixed,
                "trials_adaptive": trials_adaptive,
                "config": {
                    "model": MODEL, "temperature": LLM_TEMPERATURE,
                    "timeout_sec": LLM_TIMEOUT_SEC, "max_retries": LLM_MAX_RETRIES,
                    "success_step": SUCCESS_STEP,
                    "initial_weight": INITIAL_WEIGHT,
                    "detail_thresholds": DETAIL_THRESHOLDS,
                    "penalties": PENALTIES,
                    "prompt_mode": "no_score_stronger_penalty",
                },
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(json.dumps(stats_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(
        render_summary(trials_fixed, trials_adaptive, stats_result, records),
        encoding="utf-8",
    )

    plot_weight_trajectory(trials_adaptive, GRAPHS_DIR / "weight_trajectory_exp3.png")
    plot_detail_level_evolution(trials_adaptive, GRAPHS_DIR / "detail_level_evolution_exp3.png")
    plot_stage2_comparison(stats_result, GRAPHS_DIR / "stage2_comparison.png")
    plot_cohens_d_progression(stats_result, GRAPHS_DIR / "cohens_d_progression.png")

    print()
    print("=== Phase 1.4d Stage 2 Exp 3 summary ===")
    print(f"Mean Δ macro F1 = {stats_result['mean_diff']:+.3f}")
    print(f"p = {stats_result['paired_t_test']['p_value']:.4f}, "
          f"d = {stats_result['cohens_d']}, "
          f"CI = [{stats_result['ci_95'][0]:+.3f}, {stats_result['ci_95'][1]:+.3f}]")
    print(f"Go (all 3 criteria): {stats_result['go_judgment']['overall_go']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
