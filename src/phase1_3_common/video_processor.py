"""ffmpeg-based audio and frame extraction with a disk cache.

The cache lives under ``data/processed/`` (gitignored). A call with the
same ``video_id`` reuses existing output unless ``force=True``. Variable
frame-rate sources are normalised to CFR via ``-fps_mode cfr`` so the
1 fps sampling stays at a constant pace regardless of source timing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIO_CACHE = REPO_ROOT / "data" / "processed" / "audio"
FRAMES_CACHE = REPO_ROOT / "data" / "processed" / "frames"

DEFAULT_SR = 16000
DEFAULT_FPS = 1


def extract_audio(
    video_path: Path,
    video_id: str,
    sr: int = DEFAULT_SR,
    force: bool = False,
) -> Path:
    """Extract mono WAV at ``sr`` Hz into the audio cache and return its path."""
    out = AUDIO_CACHE / f"{video_id}.wav"
    if out.is_file() and not force:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sr),
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def extract_frames(
    video_path: Path,
    video_id: str,
    fps: int = DEFAULT_FPS,
    force: bool = False,
) -> list[Path]:
    """Extract CFR frames at ``fps`` Hz into the frames cache.

    Returns the sorted list of ``frame_*.jpg`` paths. If a previous run
    already populated the directory the existing frames are reused (unless
    ``force=True``).
    """
    out_dir = FRAMES_CACHE / video_id
    if out_dir.is_dir() and not force:
        existing = sorted(out_dir.glob("frame_*.jpg"))
        if existing:
            return existing
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("frame_*.jpg"):
        old.unlink()
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-fps_mode", "cfr",
        "-q:v", "2",
        str(out_dir / "frame_%03d.jpg"),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(out_dir.glob("frame_*.jpg"))


def probe_duration(media_path: Path) -> float:
    """Return ``format.duration`` (seconds) for any ffprobe-readable file."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    out = subprocess.run(cmd, capture_output=True, check=True)
    try:
        return float(out.stdout.decode("utf-8").strip())
    except ValueError:
        return 0.0
