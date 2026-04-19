"""Frame pre-filter for Phase 1.4a Topology C_v2 (objective B: accuracy).

Phase 1.3 Topology C aggregates YOLO statistics over every sampled frame.
No-bird frames contribute zero-counts to ``detection_counts_per_frame``
and add nothing to the bbox / confidence statistics — but they inflate
``num_frames_analyzed`` and drag ``frames_with_bird / num_frames_analyzed``
toward low density numbers that can mislead the LLM.

This module does one YOLO pass and returns:

  * ``extract_bird_frames(detector, frame_paths)`` — per-frame detection
    records plus the selected subset (frames with at least one bird).
  * ``aggregate_selected(extractor_out)`` — Phase-1.3-style aggregate
    statistics computed over the selected subset only, so the LLM never
    sees zero-count noise.

Keeping the two functions separate means the fold JSON can log *both*
the full per-frame trace (for audit / Phase 1.4a+ analysis) and the
filtered aggregate actually fed to the LLM.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from phase1_3_common.yolo_detector import BIRD_CLASS_ID, YoloDetector


def run_yolo_per_frame(
    detector: YoloDetector,
    frame_paths: list[Path],
    fps_sampling: float = 1.0,
) -> list[dict[str, Any]]:
    """Run YOLOv8n on each frame path and return a per-frame record.

    Each record has ``frame_idx``, ``timestamp_sec``, ``num_detections``
    (bird class only), and a list of ``detections`` with ``bbox_rel``
    (bbox area / frame area) and ``confidence``.
    """
    out: list[dict[str, Any]] = []
    for idx, fp in enumerate(frame_paths):
        results = detector.model.predict(
            source=str(fp), classes=[BIRD_CLASS_ID], verbose=False,
        )
        r = results[0]
        boxes = r.boxes
        count = 0 if boxes is None else len(boxes)
        h, w = r.orig_shape
        img_area = float(h) * float(w)

        detections: list[dict[str, float]] = []
        if count > 0 and img_area > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            for (x1, y1, x2, y2), c in zip(xyxy, confs):
                bbox_area = float((x2 - x1) * (y2 - y1))
                rel = bbox_area / img_area
                detections.append({
                    "bbox_rel": round(rel, 4),
                    "confidence": round(float(c), 4),
                })

        timestamp = float(idx) / float(fps_sampling) if fps_sampling > 0 else float(idx)
        out.append({
            "frame_idx": idx,
            "timestamp_sec": round(timestamp, 2),
            "num_detections": count,
            "detections": detections,
        })
    return out


def extract_bird_frames(
    detector: YoloDetector,
    frame_paths: list[Path],
    fps_sampling: float = 1.0,
) -> dict[str, Any]:
    """Run YOLO per frame and split into selected (bird-detected) / all."""
    per_frame = run_yolo_per_frame(detector, frame_paths, fps_sampling=fps_sampling)
    selected = [f for f in per_frame if f["num_detections"] > 0]
    total = len(per_frame)
    return {
        "total_frames_sampled": total,
        "frames_with_bird": len(selected),
        "frame_selection_rate": round(len(selected) / total, 4) if total > 0 else 0.0,
        "fps_sampling": fps_sampling,
        "selected_frames": selected,
        "all_frames_yolo_output": per_frame,
    }


def aggregate_selected(extractor_out: dict[str, Any]) -> dict[str, Any]:
    """Phase-1.3-style YOLO aggregate computed over selected frames only."""
    selected = extractor_out["selected_frames"]
    bbox_rels: list[float] = []
    confs: list[float] = []
    detection_counts: list[int] = []
    for fr in selected:
        detection_counts.append(fr["num_detections"])
        for d in fr["detections"]:
            bbox_rels.append(float(d["bbox_rel"]))
            confs.append(float(d["confidence"]))

    max_rel = max(bbox_rels) if bbox_rels else 0.0
    avg_rel = sum(bbox_rels) / len(bbox_rels) if bbox_rels else 0.0
    if len(bbox_rels) > 1:
        mean = sum(bbox_rels) / len(bbox_rels)
        var = sum((x - mean) ** 2 for x in bbox_rels) / (len(bbox_rels) - 1)
        std_rel = math.sqrt(var)
    else:
        std_rel = 0.0
    max_conf = max(confs) if confs else 0.0
    avg_conf = sum(confs) / len(confs) if confs else 0.0

    return {
        "num_frames_analyzed": len(selected),
        "frames_with_bird": len(selected),
        "max_bbox_size_relative": round(max_rel, 4),
        "avg_bbox_size_relative": round(avg_rel, 4),
        "std_bbox_size": round(std_rel, 4),
        "max_detection_confidence": round(max_conf, 4),
        "avg_detection_confidence": round(avg_conf, 4),
        "detection_counts_per_frame": detection_counts,
    }
