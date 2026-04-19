"""Optional Tier B video trimmer.

Phase 1.4a Robosheep review marks six YouTube clips as Tier B — usable
after the first 30 seconds are removed (typically to skip a branded
intro or a BGM cold open). This module wraps ffmpeg to produce a
trimmed copy under ``data/processed/youtube_videos_trimmed/`` so the
full pipeline can re-run on the trimmed clip without touching the
original download.

In Phase 1.4a the clean-dataset re-evaluation reuses the existing
fold JSONs (computed on the untrimmed clip) because re-extracting
audio + frames and replaying YOLO / BirdNET / LLM for six clips would
double the disk footprint. The module exists so that Phase 1.4b+
(or any future run that cares about the first 30 s) can opt in.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TRIMMED_CACHE = REPO_ROOT / "data" / "processed" / "youtube_videos_trimmed"


def trim_video(source_path: Path, video_id: str, start_sec: int, force: bool = False) -> Path:
    """Trim ``start_sec`` seconds off the front of ``source_path`` via ffmpeg.

    Output is cached under ``data/processed/youtube_videos_trimmed/``;
    a subsequent call returns the cached path unless ``force=True``.
    """
    TRIMMED_CACHE.mkdir(parents=True, exist_ok=True)
    out = TRIMMED_CACHE / f"{video_id}.mp4"
    if out.is_file() and not force:
        return out
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-ss", str(int(start_sec)),
        "-i", str(source_path),
        "-c", "copy",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out
