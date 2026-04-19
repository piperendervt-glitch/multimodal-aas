"""Download the 32 YouTube videos used for Phase 1.3 extended evaluation.

Each video is capped at the first 5 minutes via ``yt-dlp --download-sections``
so we never pay for more than what the evaluation pipeline will use
(frames @ 1 fps + BirdNET 3s windows). Files land under
``data/raw/youtube_videos/{category}/{youtube_id}.mp4`` and their
metadata is appended to ``data/youtube_metadata.json`` with a per-entry
``download_status`` so downstream scripts can skip failed videos.

The script is idempotent: files already on disk are reused; metadata for
existing files is refreshed from ffprobe. Per-video failures are logged
and recorded in the metadata — the run never aborts on a single failure.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_ROOT = REPO_ROOT / "data" / "raw" / "youtube_videos"
METADATA_PATH = REPO_ROOT / "data" / "youtube_metadata.json"

CLIP_SECONDS = 300  # 5 minutes
MAX_HEIGHT = 720


# Video specification. Each entry records:
#   - url: YouTube URL (watch?v=... or /shorts/...)
#   - category: "sparrow" (solo), "bulbul" (solo), or "mixed"
#   - source: "grok" or "claude" (who selected the clip)
#   - hint: short human-readable description
#
# Ground-truth expectation follows category:
#   sparrow -> (S=1, B=0), bulbul -> (S=0, B=1), mixed -> (S=1, B=1)
#
# review_needed is set to True on all entries because these expectations
# are based on titles/descriptions, not on actual viewing. Robosheep is
# expected to reconcile after the extended run.

VIDEO_SPECS: list[dict[str, str]] = [
    # sparrow (12) — Grok 7
    {"url": "https://www.youtube.com/watch?v=JCGgh5zvEeE", "category": "sparrow", "source": "grok",
     "hint": "Japanese Birder Miki スズメ地鳴き"},
    {"url": "https://www.youtube.com/watch?v=HFN1MX3D4yM", "category": "sparrow", "source": "grok",
     "hint": "日本野鳥の会 声紋分析"},
    {"url": "https://www.youtube.com/watch?v=ToG_e-OQWwI", "category": "sparrow", "source": "grok",
     "hint": "こんにちはスズメ さえずり"},
    {"url": "https://www.youtube.com/watch?v=sljwOG3KU2g", "category": "sparrow", "source": "grok",
     "hint": "こんにちはスズメ 地鳴き"},
    {"url": "https://www.youtube.com/watch?v=b12Fb3C7LcY", "category": "sparrow", "source": "grok",
     "hint": "スズメ幼鳥2羽 朝のさえずり"},
    {"url": "https://www.youtube.com/watch?v=evVHoDIv1hE", "category": "sparrow", "source": "grok",
     "hint": "スズメ HD画質"},
    {"url": "https://www.youtube.com/watch?v=Ji1jooZwBSo", "category": "sparrow", "source": "grok",
     "hint": "スズメ群れの日常"},
    # sparrow — Claude 5
    {"url": "https://www.youtube.com/watch?v=RbGhZOyR7Pg", "category": "sparrow", "source": "claude",
     "hint": "効果音系 朝のスズメ"},
    {"url": "https://www.youtube.com/watch?v=YFdbUv65QIw", "category": "sparrow", "source": "claude",
     "hint": "神戸大卒業研究 夜明けのスズメ"},
    {"url": "https://www.youtube.com/shorts/ZRQLsbGEVG8", "category": "sparrow", "source": "claude",
     "hint": "スズメのなる木 Shorts"},
    {"url": "https://www.youtube.com/watch?v=Z6-WL8woFPk", "category": "sparrow", "source": "claude",
     "hint": "今日の検証で使用したスズメ音源"},
    {"url": "https://www.youtube.com/watch?v=xhvf73wRJVM", "category": "sparrow", "source": "claude",
     "hint": "スズメ Tree Sparrow 狩猟鳥"},

    # bulbul (12) — Grok 7
    {"url": "https://www.youtube.com/watch?v=TPgyTtnlYak", "category": "bulbul", "source": "grok",
     "hint": "日本野鳥の会 ヒヨドリ地鳴き"},
    {"url": "https://www.youtube.com/watch?v=p-te4rfSFlo", "category": "bulbul", "source": "grok",
     "hint": "日本野鳥の会 飛翔の声"},
    {"url": "https://www.youtube.com/watch?v=4QdQnWqiekY", "category": "bulbul", "source": "grok",
     "hint": "日本野鳥の会 夕方の鳴き合い"},
    {"url": "https://www.youtube.com/watch?v=kMWUQOW-bTM", "category": "bulbul", "source": "grok",
     "hint": "Japanese Birder Miki 6種解説"},
    {"url": "https://www.youtube.com/watch?v=QxKLx__Nzn4", "category": "bulbul", "source": "grok",
     "hint": "歌うヒヨドリ 独唱"},
    {"url": "https://www.youtube.com/watch?v=jk15DbXQV6A", "category": "bulbul", "source": "grok",
     "hint": "Hidekawa0627 さえずり"},
    {"url": "https://www.youtube.com/watch?v=lnyw5TOMea8", "category": "bulbul", "source": "grok",
     "hint": "Hidekawa0627 地鳴き"},
    # bulbul — Claude 5
    {"url": "https://www.youtube.com/watch?v=-DYmOCTDWc0", "category": "bulbul", "source": "claude",
     "hint": "Japanese Birder Miki ヒヨドリ地鳴き"},
    {"url": "https://www.youtube.com/watch?v=vmrbbEe9R6M", "category": "bulbul", "source": "claude",
     "hint": "今日の検証で使用したヒヨドリ音源"},
    {"url": "https://www.youtube.com/watch?v=8zanYHHEpiw", "category": "bulbul", "source": "claude",
     "hint": "ヒヨドリの群れ 鳴き声"},
    {"url": "https://www.youtube.com/watch?v=8HhsjaqFITQ", "category": "bulbul", "source": "claude",
     "hint": "ヒヨドリ さえずり ソ・ラ・シ"},
    {"url": "https://www.youtube.com/watch?v=zYvgirz9KMo", "category": "bulbul", "source": "claude",
     "hint": "参考: イソヒヨドリの可能性あり、混入したら除外"},

    # mixed (8) — Grok 3
    {"url": "https://www.youtube.com/watch?v=bhp8AhQ2cvw", "category": "mixed", "source": "grok",
     "hint": "ヒヨドリ対スズメ 餌台"},
    {"url": "https://www.youtube.com/watch?v=ruTTT9OdI9Q", "category": "mixed", "source": "grok",
     "hint": "庭でヒヨドリがスズメ追う"},
    {"url": "https://www.youtube.com/watch?v=RC3ELjgkUCQ", "category": "mixed", "source": "grok",
     "hint": "バードバス 水浴び"},
    # mixed — Claude 5 (植木鉢シリーズ)
    {"url": "https://www.youtube.com/watch?v=bGk6vto6JxM", "category": "mixed", "source": "claude",
     "hint": "リンゴ編 メジロ/スズメ/ヒヨドリ"},
    {"url": "https://www.youtube.com/watch?v=_K7JMyeOnjw", "category": "mixed", "source": "claude",
     "hint": "イチゴ編 メジロ/ヒヨドリ/スズメ"},
    {"url": "https://www.youtube.com/watch?v=IjHCLUmBqJE", "category": "mixed", "source": "claude",
     "hint": "カキ編 複数種"},
    {"url": "https://www.youtube.com/watch?v=6FQnY2jYNjM", "category": "mixed", "source": "claude",
     "hint": "焼き芋編2 複数種"},
    {"url": "https://www.youtube.com/watch?v=I1XmEHGO19A", "category": "mixed", "source": "claude",
     "hint": "特別編 メジロ/スズメ"},
]


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def _resolve_yt_dlp() -> str:
    venv_bin = Path(sys.executable).parent / "yt-dlp.exe"
    if venv_bin.is_file():
        return str(venv_bin)
    found = shutil.which("yt-dlp")
    if found:
        return found
    raise RuntimeError(
        "yt-dlp が見つかりません。pip install yt-dlp を実行してください。"
    )


_YT_ID_RE = re.compile(r"(?:v=|/shorts/)([A-Za-z0-9_-]{11})")


def extract_youtube_id(url: str) -> str:
    m = _YT_ID_RE.search(url)
    if not m:
        raise ValueError(f"Can't extract YouTube ID from URL: {url}")
    return m.group(1)


def expected_labels(category: str) -> tuple[int, int]:
    if category == "sparrow":
        return 1, 0
    if category == "bulbul":
        return 0, 1
    if category == "mixed":
        return 1, 1
    return 0, 0


def probe_metadata(path: Path) -> dict[str, Any]:
    """Run ffprobe and return duration / resolution / fps / size."""
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    probe = json.loads(result.stdout.decode("utf-8"))
    streams = probe.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    fmt = probe.get("format", {})
    duration_raw = fmt.get("duration") or (video_stream or {}).get("duration")
    duration_sec = round(float(duration_raw), 3) if duration_raw is not None else None
    width = (video_stream or {}).get("width")
    height = (video_stream or {}).get("height")
    resolution = f"{width}x{height}" if width and height else None

    fps_str = (video_stream or {}).get("avg_frame_rate") or (video_stream or {}).get("r_frame_rate")
    fps: float | int | None = None
    if fps_str and fps_str != "0/0":
        try:
            num_str, den_str = fps_str.split("/")
            num, den = int(num_str), int(den_str)
            if den != 0:
                value = num / den
                fps = int(value) if value.is_integer() else round(value, 3)
        except (ValueError, AttributeError):
            pass

    return {
        "duration_sec": duration_sec,
        "resolution": resolution,
        "fps": fps,
        "file_size_bytes": path.stat().st_size,
    }


def download_one(
    spec: dict[str, str],
    yt_dlp: str,
) -> dict[str, Any]:
    youtube_id = extract_youtube_id(spec["url"])
    video_id = f"yt_{youtube_id}"
    category = spec["category"]
    exp_s, exp_b = expected_labels(category)

    category_dir = OUT_ROOT / category
    category_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = category_dir / f"{youtube_id}.mp4"

    entry: dict[str, Any] = {
        "video_id": video_id,
        "youtube_id": youtube_id,
        "url": spec["url"],
        "title_hint": spec["hint"],
        "category": category,
        "source": spec["source"],
        "expected_sparrow": exp_s,
        "expected_bulbul": exp_b,
        "review_needed": True,
        "local_path": str(out_mp4.relative_to(REPO_ROOT)).replace("\\", "/"),
        "download_status": "pending",
        "download_error": None,
        "downloaded_at": None,
        "duration_sec": None,
        "resolution": None,
        "fps": None,
        "file_size_bytes": None,
        "youtube_title": None,
    }

    if out_mp4.is_file() and out_mp4.stat().st_size > 100_000:
        print(f"[cache] {out_mp4} exists, reusing.")
        entry["download_status"] = "ok"
        entry["downloaded_at"] = datetime.fromtimestamp(
            out_mp4.stat().st_mtime, tz=timezone.utc
        ).isoformat(timespec="seconds")
    else:
        cmd = [
            yt_dlp,
            "--no-playlist",
            "--no-overwrites",
            "--download-sections", f"*0-{CLIP_SECONDS}",
            "--force-keyframes-at-cuts",
            "-f", f"best[ext=mp4][height<={MAX_HEIGHT}]/best[height<={MAX_HEIGHT}]/best",
            "--merge-output-format", "mp4",
            "--print-to-file", "title:%(title)s", str(category_dir / f"{youtube_id}.title.txt"),
            "-o", str(category_dir / f"{youtube_id}.%(ext)s"),
            spec["url"],
        ]
        print(f"[download] {video_id} ({category}/{spec['source']}): {spec['url']}", flush=True)
        start = time.perf_counter()
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            entry["download_status"] = "failed"
            entry["download_error"] = stderr.strip()[:500]
            print(f"  [error] yt-dlp exit {e.returncode}: {stderr.strip()[:300]}", file=sys.stderr)
            return entry
        elapsed = time.perf_counter() - start
        print(f"  [ok] downloaded in {elapsed:.1f}s")
        entry["download_status"] = "ok"
        entry["downloaded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Read the title sidecar file if present
    title_sidecar = category_dir / f"{youtube_id}.title.txt"
    if title_sidecar.is_file():
        try:
            entry["youtube_title"] = title_sidecar.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            pass

    # Probe the downloaded file for metadata
    if out_mp4.is_file():
        try:
            meta = probe_metadata(out_mp4)
            entry.update({k: meta[k] for k in ("duration_sec", "resolution", "fps", "file_size_bytes")})
        except subprocess.CalledProcessError as e:
            entry["download_status"] = "probe_failed"
            entry["download_error"] = (
                e.stderr.decode("utf-8", errors="replace") if e.stderr else "ffprobe failure"
            )[:500]
    else:
        entry["download_status"] = "missing_after_download"

    return entry


def main() -> int:
    ensure_utf8_streams()
    yt_dlp = _resolve_yt_dlp()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    existing: dict[str, dict[str, Any]] = {}
    if METADATA_PATH.is_file():
        try:
            prior = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
            for v in prior.get("videos", []):
                existing[v["video_id"]] = v
        except json.JSONDecodeError:
            pass

    entries: list[dict[str, Any]] = []
    for i, spec in enumerate(VIDEO_SPECS, start=1):
        print(f"\n[{i:02d}/{len(VIDEO_SPECS)}] {spec['category']:7s} {spec['source']:6s} {spec['url']}")
        try:
            entry = download_one(spec, yt_dlp)
        except Exception as e:  # noqa: BLE001 - per-video isolation
            youtube_id = (
                extract_youtube_id(spec["url"]) if _YT_ID_RE.search(spec["url"]) else f"bad_url_{i}"
            )
            entry = {
                "video_id": f"yt_{youtube_id}",
                "youtube_id": youtube_id,
                "url": spec["url"],
                "category": spec["category"],
                "source": spec["source"],
                "title_hint": spec["hint"],
                "download_status": "exception",
                "download_error": f"{type(e).__name__}: {e}",
            }
            print(f"  [exception] {type(e).__name__}: {e}", file=sys.stderr)
        entries.append(entry)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "clip_seconds_cap": CLIP_SECONDS,
        "max_height": MAX_HEIGHT,
        "total_videos": len(entries),
        "ok_videos": sum(1 for e in entries if e.get("download_status") == "ok"),
        "failed_videos": sum(1 for e in entries if e.get("download_status") not in ("ok",)),
        "videos": entries,
    }
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print()
    print(f"Total attempted : {len(entries)}")
    print(f"Downloaded OK   : {output['ok_videos']}")
    print(f"Failed          : {output['failed_videos']}")
    print(f"Metadata        : {METADATA_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
