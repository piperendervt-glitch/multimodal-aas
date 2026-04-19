"""YOLOv8n wrapper: per-frame bird detection -> aggregate statistics.

The aggregate is intentionally flat so it can be dropped straight into an
LLM prompt. bbox sizes are reported relative to the frame area so they
are comparable across videos with different resolutions.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any


BIRD_CLASS_ID = 14  # COCO "bird"
DEFAULT_WEIGHTS = "yolov8n.pt"


class YoloDetector:
    def __init__(self, weights: str = DEFAULT_WEIGHTS) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise RuntimeError(
                "ultralytics is not installed. Run: pip install ultralytics"
            ) from e
        self.model = YOLO(weights)

    def aggregate(self, frame_paths: list[Path]) -> dict[str, Any]:
        frames_with_bird = 0
        bbox_rels: list[float] = []
        confs: list[float] = []
        detection_counts: list[int] = []

        for fp in frame_paths:
            results = self.model.predict(
                source=str(fp),
                classes=[BIRD_CLASS_ID],
                verbose=False,
            )
            r = results[0]
            boxes = r.boxes
            count = 0 if boxes is None else len(boxes)
            detection_counts.append(count)
            if count == 0:
                continue
            frames_with_bird += 1
            h, w = r.orig_shape
            area = float(h) * float(w)
            xyxy = boxes.xyxy.cpu().numpy()
            cc = boxes.conf.cpu().numpy()
            for (x1, y1, x2, y2), c in zip(xyxy, cc):
                bbox_area = float((x2 - x1) * (y2 - y1))
                rel = bbox_area / area if area > 0 else 0.0
                bbox_rels.append(rel)
                confs.append(float(c))

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
            "num_frames_analyzed": len(frame_paths),
            "frames_with_bird": frames_with_bird,
            "max_bbox_size_relative": round(max_rel, 4),
            "avg_bbox_size_relative": round(avg_rel, 4),
            "std_bbox_size": round(std_rel, 4),
            "max_detection_confidence": round(max_conf, 4),
            "avg_detection_confidence": round(avg_conf, 4),
            "detection_counts_per_frame": detection_counts,
        }
