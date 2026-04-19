"""Generate data/metadata.json from balcony_videos/*.mp4 using ffprobe.

Scans data/raw/balcony_videos/ for .mp4 files (sorted alphabetically),
probes each with ffprobe, computes a SHA-256 of the file contents, and
writes the combined result to data/metadata.json.

Usage:
    python src/generate_metadata.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = REPO_ROOT / "data" / "raw" / "balcony_videos"
OUTPUT_PATH = REPO_ROOT / "data" / "metadata.json"
HASH_CHUNK_BYTES = 1024 * 1024


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(HASH_CHUNK_BYTES), b""):
            h.update(chunk)
    return h.hexdigest()


def ffprobe_json(path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    return json.loads(result.stdout.decode("utf-8"))


def parse_fps(rate_str: str | None) -> float | int | None:
    if not rate_str or rate_str == "0/0":
        return None
    try:
        num_str, den_str = rate_str.split("/")
        num, den = int(num_str), int(den_str)
    except (ValueError, AttributeError):
        return None
    if den == 0:
        return None
    value = num / den
    return int(value) if value.is_integer() else round(value, 3)


def build_entry(video_id: str, path: Path) -> dict[str, Any]:
    probe = ffprobe_json(path)
    streams = probe.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = probe.get("format", {})

    if video_stream is None:
        raise RuntimeError(f"no video stream in {path}")

    width = video_stream.get("width")
    height = video_stream.get("height")
    duration_raw = fmt.get("duration") or video_stream.get("duration")
    duration_sec = round(float(duration_raw), 3) if duration_raw is not None else None
    fps = parse_fps(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))

    return {
        "video_id": video_id,
        "filename": path.name,
        "file_size_bytes": path.stat().st_size,
        "sha256": sha256_of(path),
        "duration_sec": duration_sec,
        "resolution": f"{width}x{height}" if width and height else None,
        "fps": fps,
        "codec_video": video_stream.get("codec_name"),
        "codec_audio": audio_stream.get("codec_name") if audio_stream else None,
        "has_audio": audio_stream is not None,
    }


def main() -> int:
    if not VIDEO_DIR.is_dir():
        print(f"video dir not found: {VIDEO_DIR}", file=sys.stderr)
        return 1

    files = sorted(VIDEO_DIR.glob("*.mp4"))
    if not files:
        print(f"no .mp4 files in {VIDEO_DIR}", file=sys.stderr)
        return 1

    videos: list[dict[str, Any]] = []
    for i, path in enumerate(files, start=1):
        video_id = f"balcony_{i:03d}"
        print(f"[{i:>2}/{len(files)}] {video_id} <- {path.name}")
        videos.append(build_entry(video_id, path))

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "self_recorded",
        "device": "webcam",
        "location": "balcony",
        "videos": videos,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT_PATH} ({len(videos)} videos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
