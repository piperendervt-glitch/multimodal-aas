"""Temporal window sampler for Phase 1.4a Topology C_v3 (objective D).

Splits a video's visual (per-frame YOLO) and audio (BirdNET detections)
outputs into fixed-size time windows so the LLM can see *when* each
modality saw evidence. Each window carries visual aggregates computed
over the frames falling inside it and the audio detections overlapping
it; the ``sync_summary`` names the four disjoint sets

    both_present / visual_only / audio_only / neither

plus a ``sync_rate`` = both_present / (windows - neither). A high
sync_rate means visual and audio evidence co-occur, which should raise
the LLM's confidence; a low one means the modalities disagree on *when*
a bird is present.
"""

from __future__ import annotations

import math
from typing import Any

DEFAULT_WINDOW_SEC = 2.0

SPARROW_SCI = "Passer montanus"
BULBUL_SCI = "Hypsipetes amaurotis"
SPARROW_COMMON = "Eurasian Tree Sparrow"
BULBUL_COMMON = "Brown-eared Bulbul"


def _is_sparrow(sci: str, common: str) -> bool:
    return SPARROW_SCI in (sci or "") or SPARROW_COMMON in (common or "")


def _is_bulbul(sci: str, common: str) -> bool:
    return BULBUL_SCI in (sci or "") or BULBUL_COMMON in (common or "")


def _window_visual(frames_in_window: list[dict[str, Any]]) -> dict[str, Any]:
    bbox_rels: list[float] = []
    confs: list[float] = []
    counts: list[int] = []
    with_bird = 0
    for f in frames_in_window:
        counts.append(f["num_detections"])
        if f["num_detections"] > 0:
            with_bird += 1
        for d in f["detections"]:
            bbox_rels.append(float(d["bbox_rel"]))
            confs.append(float(d["confidence"]))
    return {
        "num_frames": len(frames_in_window),
        "frames_with_bird": with_bird,
        "max_bbox_size_relative": round(max(bbox_rels), 4) if bbox_rels else 0.0,
        "avg_bbox_size_relative": (
            round(sum(bbox_rels) / len(bbox_rels), 4) if bbox_rels else 0.0
        ),
        "avg_detection_confidence": (
            round(sum(confs) / len(confs), 4) if confs else 0.0
        ),
        "detection_counts": counts,
        "total_detections": sum(counts),
    }


def _window_audio(
    detections: list[dict[str, Any]], w_start: float, w_end: float
) -> dict[str, Any]:
    overlapping: list[dict[str, Any]] = []
    target_found = False
    for d in detections:
        start, end = d["time_range"]
        # [start, end) vs [w_start, w_end) open-right overlap
        if end <= w_start or start >= w_end:
            continue
        overlapping.append(d)
        if _is_sparrow(d.get("scientific_name", ""), d.get("species", "")):
            target_found = True
        elif _is_bulbul(d.get("scientific_name", ""), d.get("species", "")):
            target_found = True

    dominant = None
    if overlapping:
        top = max(overlapping, key=lambda d: float(d.get("confidence", 0.0)))
        dominant = top.get("species") or top.get("scientific_name") or ""

    audio_entries = []
    for d in overlapping:
        start, end = d["time_range"]
        audio_entries.append({
            "species": d.get("species", ""),
            "scientific_name": d.get("scientific_name", ""),
            "confidence": round(float(d.get("confidence", 0.0)), 4),
            "start_sec": round(float(start), 2),
            "end_sec": round(float(end), 2),
        })
    return {
        "detections": audio_entries,
        "target_species_found": target_found,
        "dominant_species": dominant,
    }


def build_timeline(
    per_frame_yolo: list[dict[str, Any]],
    birdnet_detections: list[dict[str, Any]],
    video_duration_sec: float,
    window_sec: float = DEFAULT_WINDOW_SEC,
) -> dict[str, Any]:
    """Return timeline + sync_summary for Topology C_v3.

    ``per_frame_yolo`` is the list produced by
    :func:`phase1_4a_common.frame_extractor.run_yolo_per_frame` (each
    record has ``timestamp_sec`` and a ``detections`` list).
    ``birdnet_detections`` is ``birdnet_output.all_detections`` from the
    birdnet analyzer. ``video_duration_sec`` should be the actual audio
    length (we align windows to the audio span so every detection falls
    somewhere).
    """
    if video_duration_sec <= 0 and per_frame_yolo:
        video_duration_sec = max(
            float(f.get("timestamp_sec", 0.0)) for f in per_frame_yolo
        ) + 1.0
    if video_duration_sec <= 0:
        video_duration_sec = window_sec

    num_windows = max(1, math.ceil(video_duration_sec / window_sec))
    windows: list[dict[str, Any]] = []

    # Bucket frames into windows once (saves repeated scans).
    by_idx: dict[int, list[dict[str, Any]]] = {}
    for f in per_frame_yolo:
        ts = float(f.get("timestamp_sec", 0.0))
        idx = int(min(num_windows - 1, max(0, ts // window_sec)))
        by_idx.setdefault(idx, []).append(f)

    for idx in range(num_windows):
        w_start = idx * window_sec
        w_end = min((idx + 1) * window_sec, video_duration_sec)
        visual = _window_visual(by_idx.get(idx, []))
        audio = _window_audio(birdnet_detections, w_start, w_end)
        windows.append({
            "window_idx": idx,
            "time_range_sec": [round(w_start, 2), round(w_end, 2)],
            "visual": visual,
            "audio": audio,
        })

    both_present: list[int] = []
    visual_only: list[int] = []
    audio_only: list[int] = []
    neither: list[int] = []
    for w in windows:
        v_has = w["visual"]["frames_with_bird"] > 0
        a_has = w["audio"]["target_species_found"]
        if v_has and a_has:
            both_present.append(w["window_idx"])
        elif v_has:
            visual_only.append(w["window_idx"])
        elif a_has:
            audio_only.append(w["window_idx"])
        else:
            neither.append(w["window_idx"])

    active_total = len(windows) - len(neither)
    sync_rate = len(both_present) / active_total if active_total > 0 else 0.0

    return {
        "window_duration_sec": window_sec,
        "video_duration_sec": round(video_duration_sec, 3),
        "num_windows": len(windows),
        "windows": windows,
        "sync_summary": {
            "both_present_windows": both_present,
            "visual_only_windows": visual_only,
            "audio_only_windows": audio_only,
            "neither_windows": neither,
            "sync_rate": round(sync_rate, 4),
        },
    }


def summarise_timeline_for_llm(
    timeline: dict[str, Any],
    max_windows: int = 120,
) -> dict[str, Any]:
    """Reduce the timeline to a context-friendly size for the LLM.

    Strategy: keep every window with any signal (visual, audio, or
    both); if there are still more than ``max_windows`` of them, keep
    the ``both_present`` windows plus evenly spaced samples from the
    remainder. ``neither`` windows are summarised by a count.
    """
    all_windows = timeline["windows"]
    sync = timeline["sync_summary"]
    active_idx = set(sync["both_present_windows"] + sync["visual_only_windows"] + sync["audio_only_windows"])

    active = [w for w in all_windows if w["window_idx"] in active_idx]
    if len(active) <= max_windows:
        kept = active
        dropped = 0
    else:
        # Prioritise both_present, then sample evenly from visual_only and audio_only.
        both_idx = set(sync["both_present_windows"])
        both = [w for w in active if w["window_idx"] in both_idx]
        rest = [w for w in active if w["window_idx"] not in both_idx]
        budget = max_windows - len(both)
        if budget <= 0:
            kept = both[:max_windows]
            dropped = len(active) - max_windows
        else:
            if len(rest) <= budget:
                kept = both + rest
                dropped = 0
            else:
                step = len(rest) / budget
                sampled = [rest[int(i * step)] for i in range(budget)]
                kept = both + sampled
                dropped = len(rest) - budget

    kept.sort(key=lambda w: w["window_idx"])
    return {
        "window_duration_sec": timeline["window_duration_sec"],
        "num_windows": timeline["num_windows"],
        "windows_sampled_for_llm": kept,
        "windows_dropped_from_llm": dropped,
        "neither_windows_count": len(sync["neither_windows"]),
        "sync_summary": sync,
    }
