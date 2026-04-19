"""Build a compact timeline for the LLM prompt.

The full timeline can run to 150+ windows on a 5-minute clip; when passed
verbatim to qwen2.5:7b the prompt-processing time exceeds the Ollama
``/api/generate`` read timeout. This helper produces a trimmed view that
preserves the information the LLM actually needs:

    * Only active windows (visual bird or audio target).
    * Per window: time range, frames-with-bird count, max/avg bbox,
      avg visual confidence, audio species + confidence summary.
    * ``both_present`` windows are always kept; visual-only and
      audio-only windows are downsampled if the budget is exceeded.

The original full timeline is still persisted in the per-fold JSON so
downstream analysis (sync_rate vs correctness, temporal patterns) has
the full trace.
"""

from __future__ import annotations

from typing import Any

from phase1_4a_common.temporal_sampler import (
    BULBUL_COMMON,
    BULBUL_SCI,
    SPARROW_COMMON,
    SPARROW_SCI,
)


def _compact_audio(audio: dict[str, Any]) -> dict[str, Any]:
    sparrow_max = 0.0
    bulbul_max = 0.0
    other_max = 0.0
    other_species: set[str] = set()
    for d in audio.get("detections", []):
        sci = d.get("scientific_name", "")
        common = d.get("species", "")
        conf = float(d.get("confidence", 0.0))
        if SPARROW_SCI in sci or SPARROW_COMMON in common:
            sparrow_max = max(sparrow_max, conf)
        elif BULBUL_SCI in sci or BULBUL_COMMON in common:
            bulbul_max = max(bulbul_max, conf)
        else:
            other_max = max(other_max, conf)
            if common:
                other_species.add(common)
    out: dict[str, Any] = {"target_species_found": audio.get("target_species_found", False)}
    if sparrow_max > 0:
        out["sparrow_max_conf"] = round(sparrow_max, 3)
    if bulbul_max > 0:
        out["bulbul_max_conf"] = round(bulbul_max, 3)
    if other_species:
        out["other_species_top_conf"] = round(other_max, 3)
        # Keep at most 2 representative names to limit prompt size.
        out["other_species"] = sorted(other_species)[:2]
    dominant = audio.get("dominant_species")
    if dominant:
        out["dominant"] = dominant
    return out


def _compact_visual(visual: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "frames_with_bird",
        "max_bbox_size_relative",
        "avg_bbox_size_relative",
        "avg_detection_confidence",
    )
    out = {k: visual.get(k, 0) for k in keys}
    out["num_frames"] = visual.get("num_frames", 0)
    return out


def compact_timeline_for_llm(
    timeline: dict[str, Any],
    max_windows: int = 40,
) -> dict[str, Any]:
    """Return a prompt-friendly slice of ``timeline`` no larger than ``max_windows`` items."""
    windows = timeline["windows"]
    sync = timeline["sync_summary"]

    both_set = set(sync["both_present_windows"])
    visual_set = set(sync["visual_only_windows"])
    audio_set = set(sync["audio_only_windows"])
    active_set = both_set | visual_set | audio_set

    active = [w for w in windows if w["window_idx"] in active_set]
    # Always prioritise both_present windows.
    both = [w for w in active if w["window_idx"] in both_set]
    remainder = [w for w in active if w["window_idx"] not in both_set]

    if len(both) >= max_windows:
        kept = both[:max_windows]
        dropped = len(active) - max_windows
    else:
        budget = max_windows - len(both)
        if len(remainder) <= budget:
            kept = both + remainder
            dropped = 0
        else:
            step = len(remainder) / budget
            sampled = [remainder[int(i * step)] for i in range(budget)]
            kept = both + sampled
            dropped = len(remainder) - budget

    kept.sort(key=lambda w: w["window_idx"])

    compact_windows: list[dict[str, Any]] = []
    for w in kept:
        compact_windows.append({
            "window_idx": w["window_idx"],
            "time_range_sec": w["time_range_sec"],
            "visual": _compact_visual(w["visual"]),
            "audio": _compact_audio(w["audio"]),
        })

    return {
        "window_duration_sec": timeline["window_duration_sec"],
        "num_windows_total": timeline["num_windows"],
        "windows_sampled_for_llm": compact_windows,
        "windows_dropped_from_llm": dropped,
        "neither_windows_count": len(sync["neither_windows"]),
        "sync_summary": {
            "both_present_count": len(sync["both_present_windows"]),
            "visual_only_count": len(sync["visual_only_windows"]),
            "audio_only_count": len(sync["audio_only_windows"]),
            "neither_count": len(sync["neither_windows"]),
            "sync_rate": sync["sync_rate"],
        },
    }
