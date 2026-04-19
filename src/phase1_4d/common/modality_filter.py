"""Modality-conditioned prompt builder for Phase 1.4d Stage 2 Experiment 1.

Each modality (``visual``, ``audio``) owns a pair of reliability weights
(one per label), updated by the sdnd-proof rule against the matching
single-modality topology (Topology B_v3 for visual, Topology A for
audio). The per-modality *weight average* decides how much raw detail
is shown to the LLM for that modality:

    w_avg > 0.7      -> full   (everything the upstream node saw)
    0.4 < w_avg ≤ 0.7 -> medium (species-level aggregates)
    w_avg ≤ 0.4      -> brief  (binary "present / absent" only)

The prompt also passes the four reliability weights explicitly so the
LLM can weight its decision. Spec: Phase 1.4d Stage 2 Experiment 1.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


DETAIL_THRESHOLDS = (0.4, 0.7)  # <=0.4 -> brief, <=0.7 -> medium, else full
DETAIL_THRESHOLDS_V2 = (0.4, 0.6)  # Stage 2 Exp 2: tighter "full" band

SPARROW_MATCH = ("Passer montanus", "Eurasian Tree Sparrow")
BULBUL_MATCH = ("Hypsipetes amaurotis", "Brown-eared Bulbul")


def get_detail_level(w_avg: float, thresholds: tuple[float, float] = DETAIL_THRESHOLDS) -> str:
    """Map a modality's average weight to one of {``brief``, ``medium``, ``full``}."""
    lo, hi = thresholds
    if w_avg <= lo:
        return "brief"
    if w_avg <= hi:
        return "medium"
    return "full"


# ---------------------------------------------------------------------------
# Visual formatters (consume Topology B_v3 fold JSON: yolo_output + bbox_distribution)
# ---------------------------------------------------------------------------

def format_full_visual(yolo_output: dict[str, Any], bbox_dist: dict[str, Any]) -> str:
    bd = bbox_dist.get("bbox_size_distribution", {}) or {}
    rel_pos = bbox_dist.get("relative_position", {}) or {}
    counts = yolo_output.get("detection_counts_per_frame", [])
    counts_preview = counts[:30] + (["..."] if len(counts) > 30 else [])
    return (
        "- num_frames_analyzed: "
        f"{yolo_output.get('num_frames_analyzed', 0)}\n"
        "- frames_with_bird: "
        f"{yolo_output.get('frames_with_bird', 0)}\n"
        "- max_bbox_size_relative: "
        f"{yolo_output.get('max_bbox_size_relative', 0):.4f}\n"
        "- avg_bbox_size_relative: "
        f"{yolo_output.get('avg_bbox_size_relative', 0):.4f}\n"
        "- std_bbox_size: "
        f"{yolo_output.get('std_bbox_size', 0):.4f}\n"
        "- avg_detection_confidence: "
        f"{yolo_output.get('avg_detection_confidence', 0):.4f}\n"
        "- bbox_size_distribution:\n"
        f"    small (<0.05): {bd.get('small_count', 0)}, "
        f"medium (0.05-0.15): {bd.get('medium_count', 0)}, "
        f"large (>0.15): {bd.get('large_count', 0)}\n"
        f"    dominant_range: {bd.get('dominant_range', 'none')}, "
        f"dominant_ratio: {bd.get('dominant_ratio', 0):.3f}\n"
        "- size_variation_type: "
        f"{bbox_dist.get('size_variation_type', 'none')} "
        f"(size_consistency {bbox_dist.get('size_consistency', 0):.3f})\n"
        "- relative_position: "
        f"normalized_avg {rel_pos.get('normalized_avg', 0):.3f}, "
        f"normalized_min {rel_pos.get('normalized_min', 0):.3f}\n"
        f"- detection_counts_per_frame (first 30): {counts_preview}"
    )


def format_medium_visual(yolo_output: dict[str, Any], bbox_dist: dict[str, Any]) -> str:
    bd = bbox_dist.get("bbox_size_distribution", {}) or {}
    return (
        "- frames_with_bird: "
        f"{yolo_output.get('frames_with_bird', 0)} / "
        f"{yolo_output.get('num_frames_analyzed', 0)}\n"
        "- avg_bbox_size_relative: "
        f"{yolo_output.get('avg_bbox_size_relative', 0):.3f}\n"
        "- max_bbox_size_relative: "
        f"{yolo_output.get('max_bbox_size_relative', 0):.3f}\n"
        "- dominant_range: "
        f"{bd.get('dominant_range', 'none')} "
        f"(ratio {bd.get('dominant_ratio', 0):.2f})\n"
        "- size_variation_type: "
        f"{bbox_dist.get('size_variation_type', 'none')}"
    )


def format_brief_visual(yolo_output: dict[str, Any], bbox_dist: dict[str, Any]) -> str:
    bd = bbox_dist.get("bbox_size_distribution", {}) or {}
    small = bd.get("small_count", 0)
    medium = bd.get("medium_count", 0)
    large = bd.get("large_count", 0)
    has_bird = yolo_output.get("frames_with_bird", 0) > 0
    sparrow_like = has_bird and small > max(medium, large)
    bulbul_like = has_bird and (medium + large) > small
    return (
        "- has_bird: "
        f"{'yes' if has_bird else 'no'}\n"
        "- sparrow_like (small bbox dominant): "
        f"{'yes' if sparrow_like else 'no'}\n"
        "- bulbul_like (medium/large bbox dominant): "
        f"{'yes' if bulbul_like else 'no'}"
    )


def format_visual(yolo_output: dict[str, Any], bbox_dist: dict[str, Any], level: str) -> str:
    if level == "full":
        return format_full_visual(yolo_output, bbox_dist)
    if level == "medium":
        return format_medium_visual(yolo_output, bbox_dist)
    return format_brief_visual(yolo_output, bbox_dist)


# ---------------------------------------------------------------------------
# Audio formatters (consume Topology A fold JSON: birdnet_output.all_detections)
# ---------------------------------------------------------------------------

def _is_sparrow(sci: str, com: str) -> bool:
    return any(t in (sci or "") or t in (com or "") for t in SPARROW_MATCH)


def _is_bulbul(sci: str, com: str) -> bool:
    return any(t in (sci or "") or t in (com or "") for t in BULBUL_MATCH)


def _aggregate_audio(detections: list[dict[str, Any]]) -> dict[str, Any]:
    by_species: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in detections:
        name = d.get("species") or d.get("scientific_name") or "(unknown)"
        by_species[name].append(d)
    rows: list[dict[str, Any]] = []
    for name, items in sorted(by_species.items(), key=lambda kv: -len(kv[1])):
        confs = [float(i.get("confidence", 0.0)) for i in items]
        rows.append({
            "species": name,
            "scientific_name": items[0].get("scientific_name", ""),
            "count": len(items),
            "max_conf": round(max(confs), 3) if confs else 0.0,
        })
    return {"by_species": rows}


def format_full_audio(birdnet_output: dict[str, Any]) -> str:
    dets = birdnet_output.get("all_detections", []) or []
    if not dets:
        return "- no BirdNET detections above min_conf=0.1"
    lines = [f"- total detections: {len(dets)}"]
    # First 20 detections in time order
    items = sorted(dets, key=lambda d: float(d.get("time_range", [0, 0])[0]))[:20]
    for d in items:
        t = d.get("time_range", [0, 0])
        lines.append(
            f"  {float(t[0]):.1f}-{float(t[1]):.1f}s  {d.get('species','')}  "
            f"(conf {float(d.get('confidence', 0)):.3f}, {d.get('scientific_name','')})"
        )
    if len(dets) > 20:
        lines.append(f"  ... plus {len(dets) - 20} more detections")
    return "\n".join(lines)


def format_medium_audio(birdnet_output: dict[str, Any]) -> str:
    dets = birdnet_output.get("all_detections", []) or []
    if not dets:
        return "- no BirdNET detections above min_conf=0.1"
    agg = _aggregate_audio(dets)
    lines = [f"- total detections: {len(dets)}"]
    for row in agg["by_species"][:8]:
        lines.append(
            f"  {row['species']} ({row['scientific_name']}): {row['count']} detections, "
            f"max confidence {row['max_conf']:.3f}"
        )
    return "\n".join(lines)


def format_brief_audio(birdnet_output: dict[str, Any]) -> str:
    dets = birdnet_output.get("all_detections", []) or []
    has_sp = any(_is_sparrow(d.get("scientific_name", ""), d.get("species", ""))
                 for d in dets)
    has_bu = any(_is_bulbul(d.get("scientific_name", ""), d.get("species", ""))
                 for d in dets)
    return (
        "- sparrow_audio (Passer montanus): "
        f"{'yes' if has_sp else 'no'}\n"
        "- bulbul_audio (Hypsipetes amaurotis): "
        f"{'yes' if has_bu else 'no'}"
    )


def format_audio(birdnet_output: dict[str, Any], level: str) -> str:
    if level == "full":
        return format_full_audio(birdnet_output)
    if level == "medium":
        return format_medium_audio(birdnet_output)
    return format_brief_audio(birdnet_output)


# ---------------------------------------------------------------------------
# Prompt composer
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an expert at Japanese backyard bird identification. "
    "Bird candidates are Eurasian Tree Sparrow (Passer montanus, `sparrow`) "
    "and Brown-eared Bulbul (Hypsipetes amaurotis, `bulbul`). "
    "Determine whether each species is present given the detection evidence "
    "and the reliability weights supplied by the operator. "
    "Respond strictly in JSON with keys `sparrow` and `bulbul`, each 0 or 1."
)


def build_prompt(
    yolo_output: dict[str, Any],
    bbox_dist: dict[str, Any],
    birdnet_output: dict[str, Any],
    weights: dict[str, dict[str, float]],
) -> tuple[str, dict[str, str]]:
    """Return (prompt_text, metadata) for the LLM call.

    ``weights`` shape: ``{"visual": {"sparrow": w, "bulbul": w}, "audio": ...}``.
    ``metadata`` reports the chosen detail levels so the caller can log them.
    """
    w_v_avg = (weights["visual"]["sparrow"] + weights["visual"]["bulbul"]) / 2.0
    w_a_avg = (weights["audio"]["sparrow"] + weights["audio"]["bulbul"]) / 2.0
    vis_level = get_detail_level(w_v_avg)
    aud_level = get_detail_level(w_a_avg)

    visual_section = format_visual(yolo_output, bbox_dist, vis_level)
    audio_section = format_audio(birdnet_output, aud_level)

    w_v_s = weights["visual"]["sparrow"]
    w_v_b = weights["visual"]["bulbul"]
    w_a_s = weights["audio"]["sparrow"]
    w_a_b = weights["audio"]["bulbul"]

    prompt = (
        "Analyze the following detection data for bird identification.\n"
        "\n"
        "Reliability scores (learned from past decisions):\n"
        f"- Visual reliability for sparrow: {w_v_s:.2f}\n"
        f"- Visual reliability for bulbul:  {w_v_b:.2f}\n"
        f"- Audio  reliability for sparrow: {w_a_s:.2f}\n"
        f"- Audio  reliability for bulbul:  {w_a_b:.2f}\n"
        "\n"
        "Higher scores indicate more reliable evidence for that species.\n"
        "Weight your decision according to these scores — if one modality's "
        "reliability is low, rely more on the other for that label.\n"
        "\n"
        f"Visual Detection ({vis_level} detail):\n"
        f"{visual_section}\n"
        "\n"
        f"Audio Detection ({aud_level} detail):\n"
        f"{audio_section}\n"
        "\n"
        "Environment context: feeder is on a balcony in Japan; only sparrow "
        "and bulbul can visit. 'No evidence' on both modalities should map "
        "to `{\"sparrow\": 0, \"bulbul\": 0}`.\n"
        "\n"
        "Determine whether sparrow and/or bulbul are present.\n"
        "Respond strictly in JSON: {\"sparrow\": 0 or 1, \"bulbul\": 0 or 1}"
    )
    return prompt, {"visual_level": vis_level, "audio_level": aud_level}


SYSTEM_PROMPT_NO_SCORE = (
    "You are an expert at Japanese backyard bird identification. "
    "Bird candidates are Eurasian Tree Sparrow (Passer montanus, `sparrow`) "
    "and Brown-eared Bulbul (Hypsipetes amaurotis, `bulbul`). "
    "Determine whether each species is present given the detection evidence. "
    "Respond strictly in JSON with keys `sparrow` and `bulbul`, each 0 or 1."
)


def build_prompt_no_score(
    yolo_output: dict[str, Any],
    bbox_dist: dict[str, Any],
    birdnet_output: dict[str, Any],
    weights: dict[str, dict[str, float]],
    thresholds: tuple[float, float] = DETAIL_THRESHOLDS_V2,
) -> tuple[str, dict[str, str]]:
    """Stage 2 Experiment 2 prompt: hide weights, only vary detail level.

    The prompt looks like a normal bird-ID request — the LLM never sees
    the four reliability scores — but the detail sections are still
    filtered by the modality-average weight behind the scenes.
    ``metadata`` records which detail tier was chosen for audit.
    """
    w_v_avg = (weights["visual"]["sparrow"] + weights["visual"]["bulbul"]) / 2.0
    w_a_avg = (weights["audio"]["sparrow"] + weights["audio"]["bulbul"]) / 2.0
    vis_level = get_detail_level(w_v_avg, thresholds)
    aud_level = get_detail_level(w_a_avg, thresholds)

    visual_section = format_visual(yolo_output, bbox_dist, vis_level)
    audio_section = format_audio(birdnet_output, aud_level)

    prompt = (
        "Analyze the following detection data for bird identification.\n"
        "\n"
        f"Visual Detection:\n{visual_section}\n"
        "\n"
        f"Audio Detection:\n{audio_section}\n"
        "\n"
        "Environment context: feeder is on a balcony in Japan; only sparrow "
        "and bulbul can visit. 'No evidence' on both modalities should map "
        "to `{\"sparrow\": 0, \"bulbul\": 0}`.\n"
        "\n"
        "Determine whether sparrow and/or bulbul are present.\n"
        "Respond strictly in JSON: {\"sparrow\": 0 or 1, \"bulbul\": 0 or 1}"
    )
    return prompt, {"visual_level": vis_level, "audio_level": aud_level}


def parse_prediction(raw: str) -> dict[str, int] | None:
    """Permissive parser for the Stage 2 response format."""
    import json as _json
    try:
        obj = _json.loads(raw)
    except _json.JSONDecodeError:
        return None
    if isinstance(obj, dict) and "predictions" in obj and isinstance(obj["predictions"], dict):
        obj = obj["predictions"]
    if not isinstance(obj, dict):
        return None
    sp = obj.get("sparrow")
    bu = obj.get("bulbul")
    if sp not in (0, 1) or bu not in (0, 1):
        return None
    return {"sparrow": int(sp), "bulbul": int(bu)}
