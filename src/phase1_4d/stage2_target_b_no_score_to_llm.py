"""Phase 1.4d Stage 2 Experiment 2 — info filtering without exposing weights.

Direct response to Experiment 1 (commit 2f247e0): showing the LLM
numerical reliability scores significantly hurt macro F1 (Δ=-0.081,
d=-1.320, p=0.042). Experiment 2 holds the weight-learning machinery
but **removes the scores from the prompt** — the LLM only sees the
visual and audio detection sections, filtered at a detail tier the
operator picked in silence based on the learned weights.

Three changes vs Experiment 1 (commit 2f247e0):

    1. Prompt: no "Reliability scores" block, no explicit "detail"
       label (the LLM sees a vanilla Visual + Audio sections prompt).
    2. Detail thresholds tightened: full = w_avg > 0.6 (was 0.7) to
       pull weights out of the medium-stuck zone observed in Exp 1.
    3. Four label-specific failure multipliers:
            visual_sparrow = 0.80   visual_bulbul = 0.90
            audio_sparrow  = 0.75   audio_bulbul  = 0.95
       Reflects the observed per-label difficulty (audio sparrow the
       hardest, audio bulbul the easiest).

Everything else matches Experiment 1 exactly: seeds, clean 22 folds,
warm-up 11 / eval 11, second-half macro F1, single-modality updates
through Topology A (audio) and Topology B_v3 (visual) predictions.
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
from scipy import stats as sp_stats

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_4a_common.clean_tiers import load_usable_video_ids
from phase1_4d.common.modality_filter import (
    SYSTEM_PROMPT_NO_SCORE,
    build_prompt_no_score,
    parse_prediction,
)
from phase1_4d.stage2_target_b_full_interpretationC import (
    INITIAL_WEIGHT,
    LLM_MAX_RETRIES,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SEC,
    MODEL,
    OLLAMA_TAGS_URL,
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

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage2_target_b_no_score_to_llm"
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

DETAIL_THRESHOLDS = (0.4, 0.6)
PENALTIES = {
    "visual": {"sparrow": 0.80, "bulbul": 0.90},
    "audio":  {"sparrow": 0.75, "bulbul": 0.95},
}


def llm_generate(system: str, prompt_text: str, timeout: int = LLM_TIMEOUT_SEC) -> dict[str, Any]:
    payload = {
        "model": MODEL,
        "system": system,
        "prompt": prompt_text,
        "format": "json",
        "stream": False,
        "options": {"temperature": LLM_TEMPERATURE},
    }
    t0 = time.perf_counter()
    resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    elapsed = time.perf_counter() - t0
    resp.raise_for_status()
    return {"raw": resp.json().get("response", ""), "elapsed_sec": round(elapsed, 3)}


def llm_with_retry(system: str, prompt_text: str) -> dict[str, Any]:
    last_error: str | None = None
    total_elapsed = 0.0
    for attempt in range(LLM_MAX_RETRIES):
        try:
            out = llm_generate(system, prompt_text)
            total_elapsed += out["elapsed_sec"]
            parsed = parse_prediction(out["raw"])
            return {
                "raw": out["raw"],
                "parsed": parsed,
                "elapsed_sec": total_elapsed,
                "attempts": attempt + 1,
                "error": None,
            }
        except requests.ReadTimeout as e:
            last_error = f"timeout (attempt {attempt + 1}): {e}"
            total_elapsed += LLM_TIMEOUT_SEC
        except requests.RequestException as e:
            last_error = f"http error (attempt {attempt + 1}): {e}"
    return {
        "raw": None,
        "parsed": None,
        "elapsed_sec": total_elapsed,
        "attempts": LLM_MAX_RETRIES,
        "error": last_error,
    }


def update_weight_labeled(w: float, success: bool, penalty: float) -> float:
    if success:
        return w + SUCCESS_STEP * (1.0 - w)
    return w * penalty


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
            "step": step,
            "video_id": rec["video_id"],
            "weights_before": weights_before,
            "weights_after": copy.deepcopy(weights),
            "visual_level": meta["visual_level"],
            "audio_level": meta["audio_level"],
            "prompt": prompt,
            "llm_raw": llm["raw"],
            "parsed": parsed,
            "llm_error": llm["error"],
            "llm_attempts": llm["attempts"],
            "llm_elapsed_sec": llm["elapsed_sec"],
            "topology_updates": updates,
            "ground_truth": gt,
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


def evaluate_fixed_trial(records, fixed_cache: dict[str, dict[str, Any]], seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    order = list(range(len(records)))
    rng.shuffle(order)
    eval_pairs: list[tuple[dict[str, int], dict[str, int]]] = []
    per_fold: list[dict[str, Any]] = []
    for step, idx in enumerate(order):
        rec = records[idx]
        cached = fixed_cache[rec["video_id"]]
        parsed = cached["parsed"]
        per_fold.append({
            "step": step, "video_id": rec["video_id"],
            "visual_level": cached["visual_level"],
            "audio_level":  cached["audio_level"],
            "parsed": parsed, "ground_truth": rec["ground_truth"],
        })
        if step >= WARMUP_COUNT:
            eval_pairs.append((parsed, rec["ground_truth"]))
    metrics = pooled_f1(eval_pairs)
    return {
        "seed": seed, "shuffle_order": order,
        "eval_folds": [records[i]["video_id"] for i in order[WARMUP_COUNT:]],
        "macro_f1":   metrics["macro_f1"],
        "sparrow_f1": metrics["sparrow_f1"],
        "bulbul_f1":  metrics["bulbul_f1"],
        "confusion":  metrics["confusion"],
        "per_fold":   per_fold,
    }


def _load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def render_summary(
    trials_fixed: list[dict[str, Any]],
    trials_adaptive: list[dict[str, Any]],
    stats_result: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    exp1_stats = _load_json(EXP1_STATS_PATH) if EXP1_STATS_PATH.is_file() else None
    exp1_trials = _load_json(EXP1_TRIALS_PATH)["trials_adaptive"] if EXP1_TRIALS_PATH.is_file() else None
    exp1_fixed_trials = _load_json(EXP1_TRIALS_PATH)["trials_fixed"] if EXP1_TRIALS_PATH.is_file() else None
    exp5b_stats = _load_json(STAGE1_EXP5B_STATS) if STAGE1_EXP5B_STATS.is_file() else None

    lines = [
        "# Phase 1.4d Stage 2 Experiment 2 — info filtering without showing scores",
        "",
        "Hypothesis: Experiment 1's collapse (d=−1.320, p=0.042) was caused by "
        "exposing the LLM to numerical reliability scores. This experiment keeps "
        "everything else constant and **removes those scores from the prompt**; the "
        "learned weights only drive *which detail tier* each modality's section is "
        "rendered at. Three small changes accompany the removal:",
        "",
        "- Prompt: no `Reliability scores` block, no detail-tier label in the text.",
        "- Detail thresholds: tightened from (0.4, 0.7) to (0.4, 0.6) so more folds "
        "can reach the `full` tier instead of getting stuck at `medium`.",
        f"- Label-specific failure penalties: visual_sparrow={PENALTIES['visual']['sparrow']}, "
        f"visual_bulbul={PENALTIES['visual']['bulbul']}, audio_sparrow={PENALTIES['audio']['sparrow']}, "
        f"audio_bulbul={PENALTIES['audio']['bulbul']} (reflects the measured per-label "
        "difficulty).",
        "",
        "Everything else matches Exp 1: clean 22 folds, 5 seeds, "
        f"warm-up {WARMUP_COUNT} / eval {len(records) - WARMUP_COUNT}, single-modality "
        "updates through Topology A (audio) / Topology B_v3 (visual).",
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
    for i, ad in enumerate(trials_adaptive, start=1):
        w = ad["final_weights"]
        lines.append(
            f"| {i} | {ad['seed']} "
            f"| {w['visual']['sparrow']:.3f} | {w['visual']['bulbul']:.3f} "
            f"| {w['audio']['sparrow']:.3f} | {w['audio']['bulbul']:.3f} |"
        )
        sums["v_sparrow"] += w["visual"]["sparrow"]
        sums["v_bulbul"] += w["visual"]["bulbul"]
        sums["a_sparrow"] += w["audio"]["sparrow"]
        sums["a_bulbul"] += w["audio"]["bulbul"]
    n_tr = len(trials_adaptive) or 1
    lines.append(
        f"| mean | - | {sums['v_sparrow']/n_tr:.3f} | {sums['v_bulbul']/n_tr:.3f} "
        f"| {sums['a_sparrow']/n_tr:.3f} | {sums['a_bulbul']/n_tr:.3f} |"
    )
    lines.append("")

    # Detail level frequencies
    vis_counts = {"brief": 0, "medium": 0, "full": 0}
    aud_counts = {"brief": 0, "medium": 0, "full": 0}
    for ad in trials_adaptive:
        for fold in ad["per_fold"]:
            vis_counts[fold["visual_level"]] += 1
            aud_counts[fold["audio_level"]] += 1
    lines.append(f"## Adaptive detail-level frequencies (5 × {len(records)} = {5 * len(records)} decisions)")
    lines.append("")
    lines.append("| level | visual | audio |")
    lines.append("|---|---:|---:|")
    for level in ("brief", "medium", "full"):
        lines.append(f"| {level} | {vis_counts[level]} | {aud_counts[level]} |")
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

    # Exp 1 vs Exp 2 table
    if exp1_stats:
        fixed_means_exp1 = [tr["macro_f1"] for tr in (exp1_fixed_trials or [])]
        adapt_means_exp1 = [tr["macro_f1"] for tr in (exp1_trials or [])]
        fixed_mean_e2 = sum(tr["macro_f1"] for tr in trials_fixed) / len(trials_fixed)
        adapt_mean_e2 = sum(tr["macro_f1"] for tr in trials_adaptive) / len(trials_adaptive)
        lines.append("## Stage 2 Exp 1 vs Exp 2 comparison (prompt-design ablation)")
        lines.append("")
        lines.append(
            "| experiment | prompt | thresholds | penalty | Fixed mean | Adaptive mean | mean Δ | d | p | verdict |"
        )
        lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---|")
        d1 = exp1_stats.get("cohens_d")
        d1_str = f"{d1:.3f}" if d1 is not None else "n/a"
        v1 = "Go" if exp1_stats["go_judgment"]["overall_go"] else "No-Go"
        lines.append(
            f"| Exp 1 | shows scores | (0.4, 0.7) | ×0.9 uniform "
            f"| {sum(fixed_means_exp1)/len(fixed_means_exp1):.3f} "
            f"| {sum(adapt_means_exp1)/len(adapt_means_exp1):.3f} "
            f"| {exp1_stats['mean_diff']:+.3f} | {d1_str} "
            f"| {exp1_stats['paired_t_test']['p_value']:.3f} | **{v1}** |"
        )
        v2 = "Go" if j["overall_go"] else "No-Go"
        lines.append(
            f"| **Exp 2** | **no scores** | **(0.4, 0.6)** | **4× label-specific** "
            f"| {fixed_mean_e2:.3f} | {adapt_mean_e2:.3f} "
            f"| {s['mean_diff']:+.3f} | {d_str} "
            f"| {s['paired_t_test']['p_value']:.3f} | **{v2}** |"
        )
        lines.append("")

    # Commentary
    lines.append("## Discussion")
    lines.append("")
    lines.append(
        "1. **Prompt design vs. weight learning**: with the scores removed from the "
        "prompt, the weight-learning machinery now acts only as an information "
        "gatekeeper — the LLM never sees that any weighting is happening. This is "
        "the cleanest test of the *information filtering* hypothesis we can run "
        "without rebuilding the ensemble."
    )
    lines.append(
        "2. **Detail-level utilisation** (vs Exp 1): threshold 0.4 / 0.6 lets more "
        "modality-averages escape the `medium` zone. The detail-frequency table "
        "above shows whether `full` and `brief` tiers actually got used this time."
    )
    lines.append(
        "3. **Label-specific penalties**: the four penalty values encode observed "
        "per-label difficulty (audio sparrow hardest at 0.75, audio bulbul easiest "
        "at 0.95). The final-weights table above shows whether those asymmetries "
        "survived 22 folds of learning."
    )
    lines.append("")
    if exp5b_stats:
        lines.append(
            "## Stage 1 Exp 5b anchor"
        )
        lines.append("")
        d5 = exp5b_stats["cohens_d"]
        d5_str = f"{d5:.3f}" if d5 is not None else "n/a"
        lines.append(
            f"For reference, Stage 1 Exp 5b (ensemble voting, not single-LLM): "
            f"Δ={exp5b_stats['mean_diff']:+.3f}, d={d5_str}, "
            f"p={exp5b_stats['paired_t_test']['p_value']:.3f}. Stage 2 operates on a "
            "different architectural layer (single-LLM with modality-filtered input); "
            "the absolute F1 numbers are not directly comparable to Stage 1."
        )
        lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json`")
    lines.append("- `statistical_analysis.json`")
    lines.append("- `graphs/weight_trajectory.png`")
    lines.append("- `graphs/detail_level_evolution.png`")
    lines.append("- `graphs/f1_comparison.png`")
    lines.append("- `graphs/exp1_vs_exp2_comparison.png`")
    lines.append("")
    return "\n".join(lines)


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
        ax.set_title(f"{modality} · {cls} (penalty ×{PENALTIES[modality][cls]})")
        ax.set_ylim(0, 1); ax.grid(alpha=0.3)
    axes[0, 0].legend(loc="lower left", fontsize=7)
    axes[1, 0].set_xlabel("fold step"); axes[1, 1].set_xlabel("fold step")
    axes[0, 0].set_ylabel("flow_weight"); axes[1, 0].set_ylabel("flow_weight")
    fig.suptitle("Stage 2 Exp 2 — 4 modality-label weights (no scores in prompt)")
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
    fig.suptitle("Adaptive detail-level evolution (tighter thresholds)")
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_f1_comparison(
    trials_fixed: list[dict[str, Any]],
    trials_adaptive: list[dict[str, Any]],
    out_path: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    n = len(trials_fixed)
    x = np.arange(n)
    width = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x - width / 2, [t["macro_f1"] for t in trials_fixed], width,
           label="Fixed (no-score prompt)", color="#4c72b0")
    ax.bar(x + width / 2, [t["macro_f1"] for t in trials_adaptive], width,
           label="Adaptive (silent info filtering)", color="#dd8452")
    ax.set_xticks(x)
    ax.set_xticklabels([f"trial {i+1}" for i in range(n)])
    ax.set_ylim(0, 1)
    ax.set_ylabel("macro F1")
    ax.set_title("Stage 2 Exp 2 — Fixed vs Adaptive")
    ax.grid(axis="y", alpha=0.3); ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_exp1_vs_exp2(stats_result: dict[str, Any], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    exp1 = _load_json(EXP1_STATS_PATH) if EXP1_STATS_PATH.is_file() else None
    if exp1 is None:
        return
    fig, ax = plt.subplots(figsize=(9, 4.5))
    labels = ["Exp 1 (scores shown)", "Exp 2 (no scores)"]
    means = [exp1["mean_diff"], stats_result["mean_diff"]]
    cis = [exp1["ci_95"], stats_result["ci_95"]]
    x = np.arange(len(labels))
    for i, (m, ci) in enumerate(zip(means, cis)):
        ax.errorbar([i], [m], yerr=[[m - ci[0]], [ci[1] - m]],
                    fmt="o", color="#264653", capsize=6, markersize=8)
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("mean Δ macro F1 with 95% CI")
    ax.set_title("Prompt-design ablation: Exp 1 vs Exp 2")
    ax.grid(axis="y", alpha=0.3)
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
                    "prompt_mode": "no_score_to_llm",
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

    plot_weight_trajectory(trials_adaptive, GRAPHS_DIR / "weight_trajectory.png")
    plot_detail_level_evolution(trials_adaptive, GRAPHS_DIR / "detail_level_evolution.png")
    plot_f1_comparison(trials_fixed, trials_adaptive, GRAPHS_DIR / "f1_comparison.png")
    plot_exp1_vs_exp2(stats_result, GRAPHS_DIR / "exp1_vs_exp2_comparison.png")

    print()
    print("=== Phase 1.4d Stage 2 Exp 2 summary ===")
    print(f"Mean Δ macro F1 = {stats_result['mean_diff']:+.3f}")
    print(f"p = {stats_result['paired_t_test']['p_value']:.4f}, "
          f"d = {stats_result['cohens_d']}, "
          f"CI = [{stats_result['ci_95'][0]:+.3f}, {stats_result['ci_95'][1]:+.3f}]")
    print(f"Go (all 3 criteria): {stats_result['go_judgment']['overall_go']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
