"""Unified video loader for Phase 1.3 extended runs.

Concatenates the 11 self-recorded balcony videos with the 32 YouTube
clips downloaded by ``youtube_video_downloader.py``. Downstream scripts
consume a single list; each entry is shaped like the original
``loocv_runner.load_videos()`` output plus extra ``source`` and
``category`` fields.

Videos whose download failed are dropped but counted in the returned
skipped list so the extended summaries can report them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
METADATA_PATH = REPO_ROOT / "data" / "metadata.json"
LABELS_PATH = REPO_ROOT / "data" / "labels" / "phase1_labels.json"
VIDEO_DIR = REPO_ROOT / "data" / "raw" / "balcony_videos"
YT_METADATA_PATH = REPO_ROOT / "data" / "youtube_metadata.json"


def _self_videos() -> list[dict[str, Any]]:
    md = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    labels_by_id = {
        x["video_id"]: x
        for x in json.loads(LABELS_PATH.read_text(encoding="utf-8")).get("labels", [])
    }
    out: list[dict[str, Any]] = []
    for v in md.get("videos", []):
        vid = v["video_id"]
        if vid not in labels_by_id:
            continue
        primary = labels_by_id[vid]["primary_label"]
        sp = 1 if primary in ("sparrow", "both") else 0
        bu = 1 if primary in ("bulbul", "both") else 0
        out.append({
            "video_id": vid,
            "filename": v["filename"],
            "video_path": VIDEO_DIR / v["filename"],
            "source": "self",
            "category": primary,
            "expected_sparrow": sp,
            "expected_bulbul": bu,
        })
    return out


def _youtube_videos() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not YT_METADATA_PATH.is_file():
        return [], []
    yt_md = json.loads(YT_METADATA_PATH.read_text(encoding="utf-8"))
    ok: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for v in yt_md.get("videos", []):
        if v.get("download_status") != "ok":
            skipped.append({
                "video_id": v.get("video_id"),
                "url": v.get("url"),
                "category": v.get("category"),
                "source": v.get("source"),
                "download_status": v.get("download_status"),
                "download_error": v.get("download_error"),
            })
            continue
        local = v.get("local_path")
        if not local:
            skipped.append({"video_id": v.get("video_id"), "reason": "no local_path"})
            continue
        video_path = REPO_ROOT / local
        if not video_path.is_file():
            skipped.append({"video_id": v.get("video_id"), "reason": "file missing"})
            continue
        ok.append({
            "video_id": v["video_id"],
            "filename": video_path.name,
            "video_path": video_path,
            "source": f"youtube-{v.get('source', 'unknown')}",
            "category": v.get("category", "unknown"),
            "expected_sparrow": int(v.get("expected_sparrow", 0)),
            "expected_bulbul": int(v.get("expected_bulbul", 0)),
            "youtube_title": v.get("youtube_title"),
            "youtube_id": v.get("youtube_id"),
            "url": v.get("url"),
        })
    return ok, skipped


def load_extended_videos() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (videos, skipped) with self-recorded videos first, YouTube second."""
    yt, skipped = _youtube_videos()
    return _self_videos() + yt, skipped


def ground_truth(video: dict[str, Any]) -> dict[str, int]:
    return {
        "sparrow": int(video.get("expected_sparrow", 0)),
        "bulbul":  int(video.get("expected_bulbul", 0)),
    }
