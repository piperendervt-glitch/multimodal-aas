"""Video-internal bbox size distribution for Phase 1.4a prompt v3.

Phase 1.3 Topology B used fixed absolute thresholds (0.08 / 0.13) for
sparrow vs bulbul; that overfits to the self-recorded balcony framing
and regressed from macro F1 0.795 (self) to 0.542 (YouTube) under
Phase 1.3 extended. This module replaces the absolute decision with
*relative* distribution features:

    * ``bbox_size_distribution`` — counts by coarse bucket
      (small/medium/large) and which bucket dominates.
    * ``size_consistency`` — std / mean of bbox relative sizes. Low
      means "one body-size on screen"; high means mixed sizes.
    * ``size_variation_type`` — categorical wrapper around
      ``size_consistency`` with threshold 0.3.
    * ``relative_position`` — each bbox scaled against the clip's
      own max so the LLM can reason without needing calibration to
      absolute frame area.

The thresholds for bucketing are still global (small < 0.05, medium
0.05–0.15, large > 0.15) because YOLO's bbox_rel is itself
frame-area-normalised; what changes is that the LLM prompt now works
with proportions and consistency labels rather than raw thresholds.
"""

from __future__ import annotations

import math
from typing import Any

SMALL_MAX = 0.05
MEDIUM_MAX = 0.15
CONSISTENCY_UNIFORM_MAX = 0.3


def analyze_bbox_distribution(per_frame_yolo: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the bbox distribution features for a clip.

    ``per_frame_yolo`` is the list produced by
    :func:`phase1_4a_common.frame_extractor.run_yolo_per_frame` — each
    frame has zero or more detections, each with ``bbox_rel`` and
    ``confidence``. We flatten across frames because the distribution
    question is clip-level ("what does this clip's bird population look
    like"), not per-frame.
    """
    bbox_rels: list[float] = []
    for f in per_frame_yolo:
        for d in f.get("detections", []):
            bbox_rels.append(float(d.get("bbox_rel", 0.0)))

    if not bbox_rels:
        return {
            "bbox_size_distribution": {
                "small_count": 0,
                "medium_count": 0,
                "large_count": 0,
                "total_detections": 0,
                "dominant_range": "none",
                "dominant_ratio": 0.0,
            },
            "size_consistency": 0.0,
            "size_variation_type": "none",
            "relative_position": {
                "normalized_avg": 0.0,
                "normalized_min": 0.0,
                "normalized_max": 0.0,
            },
        }

    small = sum(1 for r in bbox_rels if r < SMALL_MAX)
    medium = sum(1 for r in bbox_rels if SMALL_MAX <= r <= MEDIUM_MAX)
    large = sum(1 for r in bbox_rels if r > MEDIUM_MAX)
    total = len(bbox_rels)

    counts = {"small": small, "medium": medium, "large": large}
    dominant = max(counts.items(), key=lambda kv: kv[1])[0]
    dominant_ratio = counts[dominant] / total if total > 0 else 0.0

    mean = sum(bbox_rels) / len(bbox_rels)
    if len(bbox_rels) > 1:
        var = sum((x - mean) ** 2 for x in bbox_rels) / (len(bbox_rels) - 1)
        std = math.sqrt(var)
    else:
        std = 0.0
    size_consistency = std / mean if mean > 0 else 0.0
    variation_type = "uniform" if size_consistency < CONSISTENCY_UNIFORM_MAX else "mixed"

    max_rel = max(bbox_rels)
    min_rel = min(bbox_rels)
    normalized_avg = mean / max_rel if max_rel > 0 else 0.0
    normalized_min = min_rel / max_rel if max_rel > 0 else 0.0

    return {
        "bbox_size_distribution": {
            "small_count": small,
            "medium_count": medium,
            "large_count": large,
            "total_detections": total,
            "dominant_range": dominant,
            "dominant_ratio": round(dominant_ratio, 4),
        },
        "size_consistency": round(size_consistency, 4),
        "size_variation_type": variation_type,
        "relative_position": {
            "normalized_avg": round(normalized_avg, 4),
            "normalized_min": round(normalized_min, 4),
            "normalized_max": 1.0,
        },
    }
