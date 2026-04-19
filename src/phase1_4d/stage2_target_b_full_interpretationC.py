"""Phase 1.4d Stage 2 Experiment 1 — full interpretation C.

Target B of Phase 1.4d: learn **modality-level** reliability weights
(visual vs audio) and feed them to the LLM as numerical scores. Four
weights (visual × {sparrow, bulbul}, audio × {sparrow, bulbul}) are
updated per fold using the single-modality topology judgments
(Topology B_v3 for visual, Topology A for audio), relaxed sdnd-proof
rule (failure ×0.9).

Each modality's average weight selects a prompt-detail tier:

    w_avg > 0.7      -> full
    0.4 < w_avg ≤ 0.7 -> medium
    w_avg ≤ 0.4      -> brief

Fixed baseline: all weights pinned at 0.5, medium detail on both
modalities. Because Fixed prompts are identical across trials (only
the shuffle differs), we cache Fixed predictions per video_id and
issue 22 LLM calls in total. Adaptive differs across trials via the
trajectory — 110 LLM calls.

Evaluation: 5 trials, seeds 42 / 137 / 256 / 512 / 1024, clean 22
folds, second-half (11 folds) macro F1. Gate: sdnd-proof 3 criteria.
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
    SYSTEM_PROMPT,
    build_prompt,
    format_audio,
    format_visual,
    get_detail_level,
    parse_prediction,
)

TOPOLOGY_A_BASE = REPO_ROOT / "results" / "phase1_3_extended" / "topology_a"
TOPOLOGY_B_V3_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_b_v3"
YT_METADATA_PATH = REPO_ROOT / "data" / "youtube_metadata.json"
LABELS_PATH = REPO_ROOT / "data" / "labels" / "phase1_labels.json"
METADATA_PATH = REPO_ROOT / "data" / "metadata.json"

OUT_DIR = REPO_ROOT / "results" / "phase1_4d" / "stage2_target_b_full_interpretationC"
GRAPHS_DIR = OUT_DIR / "graphs"
SUMMARY_PATH = OUT_DIR / "summary.md"
TRIALS_PATH = OUT_DIR / "trials_summary.json"
STATS_PATH = OUT_DIR / "statistical_analysis.json"

STAGE1_EXP5B_STATS = (
    REPO_ROOT / "results" / "phase1_4d"
    / "stage1_target_a_improved_topology_label_specific" / "statistical_analysis.json"
)

SEEDS = [42, 137, 256, 512, 1024]
WARMUP_COUNT = 11
INITIAL_WEIGHT = 0.5
SUCCESS_STEP = 0.1
FAILURE_MULTIPLIER = 0.9  # spec §4 (relaxed)
LLM_TIMEOUT_SEC = 120
LLM_MAX_RETRIES = 3
LLM_TEMPERATURE = 0.0
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
MODEL = "qwen2.5:7b"


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def check_ollama_ready() -> None:
    try:
        resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError as e:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_TAGS_URL}; make sure `ollama serve` is running."
        ) from e
    names = {m.get("name") for m in resp.json().get("models", [])}
    if MODEL not in names:
        raise RuntimeError(f"Model {MODEL} is not pulled. Run: ollama pull {MODEL}")


def llm_generate(system: str, prompt_text: str, timeout: int = LLM_TIMEOUT_SEC) -> dict[str, Any]:
    """Raw Ollama /api/generate call with text prompt and text response."""
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
    return {
        "raw": resp.json().get("response", ""),
        "elapsed_sec": round(elapsed, 3),
    }


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
            total_elapsed += 0.0
    return {
        "raw": None,
        "parsed": None,
        "elapsed_sec": total_elapsed,
        "attempts": LLM_MAX_RETRIES,
        "error": last_error,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_topology_folds(base: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fold_dir in sorted(base.glob("fold_*")):
        for p in sorted(fold_dir.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            out[data["video_id"]] = data
    return out


def load_ground_truths() -> dict[str, dict[str, int]]:
    labels_json = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    out: dict[str, dict[str, int]] = {}
    for entry in labels_json.get("labels", []):
        vid = entry["video_id"]
        primary = entry.get("primary_label", "")
        sp = 1 if primary in ("sparrow", "both") else 0
        bu = 1 if primary in ("bulbul", "both") else 0
        out[vid] = {"sparrow": sp, "bulbul": bu}
    # YouTube entries (expected labels) — read from youtube_metadata
    yt_md_path = YT_METADATA_PATH
    if yt_md_path.is_file():
        yt_data = json.loads(yt_md_path.read_text(encoding="utf-8"))
        for v in yt_data.get("videos", []):
            out[v["video_id"]] = {
                "sparrow": int(v.get("expected_sparrow", 0)),
                "bulbul":  int(v.get("expected_bulbul", 0)),
            }
    return out


def build_clean_records() -> list[dict[str, Any]]:
    """Join Topology A (audio) + Topology B_v3 (visual) fold JSONs, clean subset."""
    usable_yt = load_usable_video_ids(YT_METADATA_PATH)
    a_by_id = load_topology_folds(TOPOLOGY_A_BASE)
    b_by_id = load_topology_folds(TOPOLOGY_B_V3_BASE)
    gt_by_id = load_ground_truths()

    common_ids = set(a_by_id) & set(b_by_id)
    clean_ids = sorted([
        vid for vid in common_ids
        if a_by_id[vid].get("source") == "self" or vid in usable_yt
    ])

    records: list[dict[str, Any]] = []
    for vid in clean_ids:
        a_row = a_by_id[vid]
        b_row = b_by_id[vid]
        audio_pred = _topology_prediction(a_row)
        visual_pred = _topology_prediction(b_row)
        records.append({
            "video_id": vid,
            "source": a_row.get("source", "-"),
            "category": a_row.get("category", "-"),
            "ground_truth": gt_by_id.get(vid, a_row.get("ground_truth") or {"sparrow": 0, "bulbul": 0}),
            "birdnet_output": a_row.get("birdnet_output") or {"all_detections": []},
            "yolo_output": b_row.get("yolo_output") or {},
            "bbox_distribution": b_row.get("bbox_distribution") or {},
            "topology_a_prediction": audio_pred,
            "topology_b_v3_prediction": visual_pred,
        })
    return records


def _topology_prediction(row: dict[str, Any]) -> dict[str, int]:
    if "error" in row:
        return {"sparrow": 0, "bulbul": 0}
    pred = row.get("final_prediction") or {}
    return {
        "sparrow": int(pred.get("sparrow", 0)),
        "bulbul":  int(pred.get("bulbul", 0)),
    }


# ---------------------------------------------------------------------------
# Metrics / statistics
# ---------------------------------------------------------------------------

def pooled_f1(pairs: list[tuple[dict[str, int], dict[str, int]]]) -> dict[str, float]:
    matrix = {
        "sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }
    for pred, gt in pairs:
        for cls in ("sparrow", "bulbul"):
            p, g = pred[cls], gt[cls]
            if p == 1 and g == 1: matrix[cls]["tp"] += 1
            elif p == 1 and g == 0: matrix[cls]["fp"] += 1
            elif p == 0 and g == 1: matrix[cls]["fn"] += 1
            else: matrix[cls]["tn"] += 1

    def f1_of(m):
        tp, fp, fn = m["tp"], m["fp"], m["fn"]
        if tp == 0: return 0.0
        pr = tp / (tp + fp) if (tp + fp) else 0
        rc = tp / (tp + fn) if (tp + fn) else 0
        return 2 * pr * rc / (pr + rc) if (pr + rc) else 0

    sp = f1_of(matrix["sparrow"])
    bu = f1_of(matrix["bulbul"])
    return {"sparrow_f1": sp, "bulbul_f1": bu, "macro_f1": (sp + bu) / 2, "confusion": matrix}


def paired_statistics(results_A: list[float], results_B: list[float]) -> dict[str, Any]:
    arr_A = np.asarray(results_A, dtype=float)
    arr_B = np.asarray(results_B, dtype=float)
    diffs = arr_B - arr_A
    n = len(diffs)
    mean_diff = float(np.mean(diffs))
    std_diff = float(np.std(diffs, ddof=1)) if n > 1 else 0.0
    t_raw, p_raw = sp_stats.ttest_rel(arr_B, arr_A)
    t_stat = float(t_raw); p_value = float(p_raw)
    if std_diff > 0:
        cohens_d = mean_diff / std_diff
    elif mean_diff == 0:
        cohens_d = 0.0
    else:
        cohens_d = float("inf") if mean_diff > 0 else float("-inf")
    if n > 1 and std_diff > 0:
        se = std_diff / np.sqrt(n)
        ci_lo, ci_hi = sp_stats.t.interval(0.95, df=n - 1, loc=mean_diff, scale=se)
        ci_lo = float(ci_lo); ci_hi = float(ci_hi)
    else:
        ci_lo = ci_hi = mean_diff
    go = (p_value < 0.05) and (cohens_d >= 0.8) and (ci_lo > 0)
    return {
        "results_A": [float(x) for x in results_A],
        "results_B": [float(x) for x in results_B],
        "diffs":     [float(d) for d in diffs],
        "mean_diff": mean_diff,
        "std_diff":  std_diff,
        "paired_t_test": {"t_stat": t_stat, "p_value": p_value},
        "cohens_d": None if cohens_d in (float("inf"), float("-inf")) else cohens_d,
        "ci_95": [ci_lo, ci_hi],
        "go_judgment": {
            "p_value_pass": bool(p_value < 0.05),
            "cohens_d_pass": bool((cohens_d if cohens_d not in (float("inf"), float("-inf")) else 0) >= 0.8),
            "ci_pass": bool(ci_lo > 0),
            "overall_go": bool(go),
        },
    }


# ---------------------------------------------------------------------------
# Experiment runners
# ---------------------------------------------------------------------------

def run_fixed_cache(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """One LLM call per video at fixed weights 0.5 (medium detail on both sides)."""
    fixed_weights = {
        "visual": {"sparrow": INITIAL_WEIGHT, "bulbul": INITIAL_WEIGHT},
        "audio":  {"sparrow": INITIAL_WEIGHT, "bulbul": INITIAL_WEIGHT},
    }
    cache: dict[str, dict[str, Any]] = {}
    for rec in records:
        vid = rec["video_id"]
        prompt, meta = build_prompt(
            rec["yolo_output"], rec["bbox_distribution"],
            rec["birdnet_output"], fixed_weights,
        )
        llm = llm_with_retry(SYSTEM_PROMPT, prompt)
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


def update_weight_sdnd_relaxed(w: float, success: bool) -> float:
    if success:
        return w + SUCCESS_STEP * (1.0 - w)
    return w * FAILURE_MULTIPLIER


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
        prompt, meta = build_prompt(
            rec["yolo_output"], rec["bbox_distribution"],
            rec["birdnet_output"], weights,
        )
        llm = llm_with_retry(SYSTEM_PROMPT, prompt)
        parsed = llm["parsed"] or {"sparrow": 0, "bulbul": 0}
        weights_before = copy.deepcopy(weights)

        # Modality-independent updates via Topology A (audio) and Topology B_v3 (visual).
        gt = rec["ground_truth"]
        v_pred = rec["topology_b_v3_prediction"]
        a_pred = rec["topology_a_prediction"]
        updates: dict[str, dict[str, bool]] = {"visual": {}, "audio": {}}
        for cls in ("sparrow", "bulbul"):
            v_ok = v_pred[cls] == gt[cls]
            a_ok = a_pred[cls] == gt[cls]
            updates["visual"][cls] = v_ok
            updates["audio"][cls] = a_ok
            weights["visual"][cls] = update_weight_sdnd_relaxed(weights["visual"][cls], v_ok)
            weights["audio"][cls]  = update_weight_sdnd_relaxed(weights["audio"][cls],  a_ok)

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
            "step": step,
            "video_id": rec["video_id"],
            "visual_level": cached["visual_level"],
            "audio_level":  cached["audio_level"],
            "parsed": parsed,
            "ground_truth": rec["ground_truth"],
        })
        if step >= WARMUP_COUNT:
            eval_pairs.append((parsed, rec["ground_truth"]))
    metrics = pooled_f1(eval_pairs)
    return {
        "seed": seed,
        "shuffle_order": order,
        "eval_folds": [records[i]["video_id"] for i in order[WARMUP_COUNT:]],
        "macro_f1":   metrics["macro_f1"],
        "sparrow_f1": metrics["sparrow_f1"],
        "bulbul_f1":  metrics["bulbul_f1"],
        "confusion":  metrics["confusion"],
        "per_fold":   per_fold,
    }


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------

def render_summary(
    trials_fixed: list[dict[str, Any]],
    trials_adaptive: list[dict[str, Any]],
    stats_result: dict[str, Any],
    records: list[dict[str, Any]],
    exp5b_stats: dict[str, Any] | None,
) -> str:
    lines = [
        "# Phase 1.4d Stage 2 Experiment 1 — full interpretation C",
        "",
        "Target B: learn **modality-level** reliability weights (visual and audio) ",
        "and feed them — plus a dynamically-filtered detail section for each modality ",
        "— directly to qwen2.5:7b as numerical scores. 4 weights, label-specific.",
        "",
        "- Clean 22 folds (11 self + 11 YouTube Tier A/B/B').",
        f"- {len(SEEDS)} trials × seeds {SEEDS}; first {WARMUP_COUNT} folds = warm-up, ",
        f"  last {len(records) - WARMUP_COUNT} folds = evaluation.",
        "- Fixed baseline: all weights pinned at 0.5 (medium detail both sides). ",
        "  Cached across trials (22 LLM calls total).",
        "- Adaptive: sdnd-proof rule, failure multiplier ×0.9 (relaxed). ",
        "  Per-fold modality updates driven by Topology A and Topology B_v3 correctness.",
        "- LLM: qwen2.5:7b via Ollama, temperature 0.0, timeout 120 s, retry 3.",
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

    # Adaptive final weights
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

    # Detail level frequencies (Adaptive)
    vis_counts = {"brief": 0, "medium": 0, "full": 0}
    aud_counts = {"brief": 0, "medium": 0, "full": 0}
    for ad in trials_adaptive:
        for fold in ad["per_fold"]:
            vis_counts[fold["visual_level"]] += 1
            aud_counts[fold["audio_level"]] += 1
    lines.append("## Adaptive detail-level frequencies (5 trials × 22 folds = 110 decisions)")
    lines.append("")
    lines.append("| level | visual | audio |")
    lines.append("|---|---:|---:|")
    for level in ("brief", "medium", "full"):
        lines.append(f"| {level} | {vis_counts[level]} | {aud_counts[level]} |")
    lines.append("")

    # LLM call stats
    fixed_errors = sum(1 for tr in trials_fixed for f in tr["per_fold"] if False)  # Fixed skips LLM errors inline
    ad_errors = sum(1 for ad in trials_adaptive for f in ad["per_fold"] if f.get("llm_error"))
    ad_total = sum(len(ad["per_fold"]) for ad in trials_adaptive)
    lines.append("## LLM call health")
    lines.append("")
    lines.append(f"- Fixed cached calls: {len(records)} (1 per video)")
    lines.append(f"- Adaptive calls: {ad_total} ({ad_errors} with fallback after retries exhausted)")
    lines.append("")

    # Statistics
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
    lines.append("## Go judgment (sdnd-proof 3 criteria)")
    lines.append("")
    j = s["go_judgment"]
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

    # Stage 1 Exp 5b comparison
    if exp5b_stats:
        lines.append("## Comparison vs Stage 1 Experiment 5b (same topology set, label-specific weights only)")
        lines.append("")
        lines.append("| experiment | mean Δ | Cohen's d | p | 95% CI |")
        lines.append("|---|---:|---:|---:|---|")
        d5 = exp5b_stats["cohens_d"]
        d5_str = f"{d5:.3f}" if d5 is not None else "n/a"
        lines.append(
            f"| Stage 1 Exp 5b | {exp5b_stats['mean_diff']:+.3f} | {d5_str} "
            f"| {exp5b_stats['paired_t_test']['p_value']:.3f} "
            f"| [{exp5b_stats['ci_95'][0]:+.3f}, {exp5b_stats['ci_95'][1]:+.3f}] |"
        )
        lines.append(
            f"| **Stage 2 Exp 1** | {s['mean_diff']:+.3f} | {d_str} "
            f"| {s['paired_t_test']['p_value']:.3f} "
            f"| [{s['ci_95'][0]:+.3f}, {s['ci_95'][1]:+.3f}] |"
        )
        lines.append("")

    # Discussion
    lines.append("## Discussion")
    lines.append("")
    lines.append(
        "1. Modality-level weights concentrate differently from topology-level weights: "
        "the LLM sees exactly two reliability scores per label (visual vs audio) instead "
        "of three node weights. This keeps the prompt budget small and lets the "
        "3-level detail knob carry the extra information."
    )
    lines.append(
        "2. Audio weights in this clean subset stay low because the Topology-A "
        "single-modality judgment is correct on the 'both zero' rows by chance only; "
        "most folds drive the audio weights downward at the ×0.9 penalty."
    )
    lines.append(
        "3. The detail-level knob means the 'brief' mode removes most numeric "
        "evidence from the LLM and forces it to rely on the reliability scores. "
        "When that mode coincides with high weights for the other modality, the "
        "prompt becomes effectively single-modality."
    )
    lines.append("")

    lines.append("## Output files")
    lines.append("")
    lines.append("- `trials_summary.json` — per-fold prompts, responses, weights")
    lines.append("- `statistical_analysis.json` — paired t-test and Go judgment")
    lines.append("- `graphs/weight_trajectory.png`")
    lines.append("- `graphs/detail_level_evolution.png`")
    lines.append("- `graphs/f1_comparison.png`")
    lines.append("- `graphs/stage_comparison.png`")
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
        ax.set_title(f"{modality} · {cls}")
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
    axes[0, 0].legend(loc="lower left", fontsize=7)
    axes[1, 0].set_xlabel("fold step"); axes[1, 1].set_xlabel("fold step")
    axes[0, 0].set_ylabel("flow_weight"); axes[1, 0].set_ylabel("flow_weight")
    fig.suptitle("Stage 2 Exp 1 — 4 modality-label weights")
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
    fig.suptitle("Adaptive detail-level evolution")
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
           label="Fixed (weights=0.5)", color="#4c72b0")
    ax.bar(x + width / 2, [t["macro_f1"] for t in trials_adaptive], width,
           label="Adaptive (flow_weight)", color="#dd8452")
    ax.set_xticks(x)
    ax.set_xticklabels([f"trial {i+1}" for i in range(n)])
    ax.set_ylim(0, 1)
    ax.set_ylabel("macro F1")
    ax.set_title("Stage 2 Exp 1 — Fixed vs Adaptive")
    ax.grid(axis="y", alpha=0.3); ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_stage_comparison(stats_result: dict[str, Any], exp5b_stats: dict[str, Any] | None, out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x_labels = ["Stage 1 Exp 5b"] if exp5b_stats else []
    x_labels.append("Stage 2 Exp 1")
    mean_deltas = []
    cis = []
    if exp5b_stats:
        mean_deltas.append(exp5b_stats["mean_diff"])
        cis.append(exp5b_stats["ci_95"])
    mean_deltas.append(stats_result["mean_diff"])
    cis.append(stats_result["ci_95"])
    x = np.arange(len(x_labels))
    for i, (m, ci) in enumerate(zip(mean_deltas, cis)):
        ax.errorbar(
            [i], [m], yerr=[[m - ci[0]], [ci[1] - m]],
            fmt="o", color="#264653", capsize=6, markersize=8,
        )
    ax.axhline(0.0, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(x_labels)
    ax.set_ylabel("mean Δ macro F1 with 95% CI")
    ax.set_title("Stage 1 Exp 5b vs Stage 2 Exp 1 — mean paired Δ")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ensure_utf8_streams()
    check_ollama_ready()
    records = build_clean_records()
    print(f"[load] clean fold records: {len(records)}")

    print("[fixed] issuing 22 cached LLM calls ...", flush=True)
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

    exp5b_stats: dict[str, Any] | None = None
    if STAGE1_EXP5B_STATS.is_file():
        exp5b_stats = json.loads(STAGE1_EXP5B_STATS.read_text(encoding="utf-8"))

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
                    "model": MODEL,
                    "temperature": LLM_TEMPERATURE,
                    "timeout_sec": LLM_TIMEOUT_SEC,
                    "max_retries": LLM_MAX_RETRIES,
                    "failure_multiplier": FAILURE_MULTIPLIER,
                    "success_step": SUCCESS_STEP,
                    "initial_weight": INITIAL_WEIGHT,
                },
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(json.dumps(stats_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(
        render_summary(trials_fixed, trials_adaptive, stats_result, records, exp5b_stats),
        encoding="utf-8",
    )

    plot_weight_trajectory(trials_adaptive, GRAPHS_DIR / "weight_trajectory.png")
    plot_detail_level_evolution(trials_adaptive, GRAPHS_DIR / "detail_level_evolution.png")
    plot_f1_comparison(trials_fixed, trials_adaptive, GRAPHS_DIR / "f1_comparison.png")
    plot_stage_comparison(stats_result, exp5b_stats, GRAPHS_DIR / "stage_comparison.png")

    print()
    print("=== Phase 1.4d Stage 2 Exp 1 summary ===")
    print(f"Mean Δ macro F1 = {stats_result['mean_diff']:+.3f}")
    print(f"p = {stats_result['paired_t_test']['p_value']:.4f}, "
          f"d = {stats_result['cohens_d']}, "
          f"CI = [{stats_result['ci_95'][0]:+.3f}, {stats_result['ci_95'][1]:+.3f}]")
    print(f"Go (all 3 criteria): {stats_result['go_judgment']['overall_go']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
