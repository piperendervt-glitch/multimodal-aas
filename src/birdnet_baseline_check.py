"""BirdNET baseline sanity check with a North American bird-song reference.

Phase 1.3 Topology A showed that BirdNET detected Passer montanus only
twice (both below 0.25 confidence) and Hypsipetes amaurotis 8 times
across 11 self-recorded balcony videos. This script isolates whether
BirdNET itself is working by pointing it at a clean, high-quality public
reference recording.

Steps:
    1. Download the first 20 minutes of the reference YouTube video with
       yt-dlp (audio only, 16 kHz mono WAV).
    2. Run birdnetlib's ``Analyzer`` with ``min_conf=0.1`` and
       ``sensitivity=1.0``. No lat/lon is passed, so BirdNET considers
       its full species list.
    3. Write a JSON summary and a Markdown verdict.

Exit code 0 on a successful run (even if zero detections — that is the
finding to report). The script is idempotent: the downloaded WAV is
cached under data/raw/birdnet_baseline/ (gitignored).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = REPO_ROOT / "data" / "raw" / "birdnet_baseline"
AUDIO_PATH = AUDIO_DIR / "north_america_birds.wav"
RESULTS_DIR = REPO_ROOT / "results" / "phase1_3" / "birdnet_baseline"
DETECTIONS_PATH = RESULTS_DIR / "detections.json"
SUMMARY_PATH = RESULTS_DIR / "summary.md"

SOURCE_URL = "https://www.youtube.com/watch?v=JvfFRAP6qG8"
SOURCE_ID = "JvfFRAP6qG8"
SOURCE_DESC = "10 Hours of North American Bird Songs (Badgerland Birding Extras)"
SOURCE_LICENSE = "CC BY 4.0 (per video description)"

SAMPLE_RATE = 16000
CLIP_SECONDS = 20 * 60  # 20 minutes
MIN_CONF = 0.1
SENSITIVITY = 1.0


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def _resolve_yt_dlp() -> str:
    """Return the path of yt-dlp, preferring the venv executable."""
    venv_bin = Path(sys.executable).parent / "yt-dlp.exe"
    if venv_bin.is_file():
        return str(venv_bin)
    found = shutil.which("yt-dlp")
    if found:
        return found
    raise RuntimeError(
        "yt-dlp が見つかりません。pip install yt-dlp を実行してください。"
    )


def download_audio(url: str, out_dir: Path, clip_sec: int, sr: int) -> None:
    """Download the first ``clip_sec`` seconds of ``url`` as mono WAV at ``sr`` Hz.

    Uses ``yt-dlp --download-sections`` so only the segment is fetched,
    not the full 10 hours. ``--postprocessor-args`` with the ``ffmpeg:``
    scope ensures the resample is applied during extraction.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if AUDIO_PATH.is_file() and AUDIO_PATH.stat().st_size > 1_000_000:
        print(f"[cache] {AUDIO_PATH} already exists, skipping download.")
        return
    for leftover in out_dir.glob("north_america_birds.*"):
        leftover.unlink()
    yt_dlp = _resolve_yt_dlp()
    cmd = [
        yt_dlp,
        "--download-sections", f"*0-{clip_sec}",
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--postprocessor-args", f"ffmpeg:-ar {sr} -ac 1",
        "-o", str(out_dir / "north_america_birds.%(ext)s"),
        url,
    ]
    print(f"[download] {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.run(cmd, capture_output=True, check=True)
    try:
        return float(out.stdout.decode("utf-8").strip())
    except ValueError:
        return 0.0


def run_birdnet(audio_path: Path, min_conf: float, sensitivity: float):
    from birdnetlib import Recording
    from birdnetlib.analyzer import Analyzer
    analyzer = Analyzer()
    rec = Recording(
        analyzer,
        str(audio_path),
        min_conf=min_conf,
        sensitivity=sensitivity,
    )
    rec.analyze()
    return rec.detections


def aggregate(detections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, int]]:
    by_species: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in detections:
        name = d.get("common_name", "") or "(unknown)"
        by_species[name].append(d)

    species_rows: list[dict[str, Any]] = []
    for name, items in sorted(by_species.items(), key=lambda kv: -len(kv[1])):
        confs = [float(i.get("confidence", 0.0)) for i in items]
        species_rows.append({
            "species": name,
            "scientific_name": items[0].get("scientific_name", ""),
            "num_detections": len(items),
            "avg_confidence": round(sum(confs) / len(confs), 4) if confs else 0.0,
            "max_confidence": round(max(confs), 4) if confs else 0.0,
        })

    time_sorted = sorted(detections, key=lambda d: float(d.get("start_time", 0.0)))
    sample = [{
        "species": d.get("common_name", ""),
        "scientific_name": d.get("scientific_name", ""),
        "confidence": round(float(d.get("confidence", 0.0)), 4),
        "time_range": [
            round(float(d.get("start_time", 0.0)), 1),
            round(float(d.get("end_time", 0.0)), 1),
        ],
    } for d in time_sorted[:50]]

    bins: dict[int, int] = defaultdict(int)
    for d in detections:
        minute = int(float(d.get("start_time", 0.0)) // 60)
        bins[minute] += 1

    return species_rows, sample, dict(bins)


def render_summary(
    detections: list[dict[str, Any]],
    species_rows: list[dict[str, Any]],
    bins: dict[int, int],
    duration_sec: float,
    elapsed_sec: float,
) -> str:
    total = len(detections)
    unique = len(species_rows)
    lines = [
        "# BirdNET Baseline Sanity Check",
        "",
        f"- Source: {SOURCE_DESC}",
        f"- URL:    {SOURCE_URL}",
        f"- License: {SOURCE_LICENSE}",
        f"- Analyzed clip: {duration_sec:.1f} s ({duration_sec/60:.1f} min) @ {SAMPLE_RATE} Hz",
        f"- BirdNET config: `min_conf={MIN_CONF}`, `sensitivity={SENSITIVITY}`, no lat/lon",
        f"- Total detections: **{total}**",
        f"- Unique species:   **{unique}**",
        f"- Analysis wall time: {elapsed_sec:.1f} s",
        "",
        "## Verdict",
        "",
    ]
    if total > 0 and unique >= 5:
        lines.extend([
            "**BirdNET is functioning correctly.** The clean North-American",
            "reference recording produced many detections with meaningful species",
            "diversity. Therefore the Phase 1.3 Topology A low-detection result is",
            "**not** caused by a BirdNET setup problem; the remaining hypotheses are:",
            "",
            "- (b) Japanese species coverage or model sensitivity to *Passer montanus*",
            "  / *Hypsipetes amaurotis* vocalisations.",
            "- (c) Balcony webcam audio quality (microphone bandwidth, SNR, distance",
            "  from feeder, ambient traffic/wind).",
            "",
            "Follow-up experiments should target (b) and (c) separately — e.g.,",
            "running BirdNET against a Xeno-canto sparrow/bulbul clip (tests b) and",
            "against balcony audio captured via a dedicated mic (tests c).",
        ])
    elif total == 0:
        lines.extend([
            "**BirdNET returned zero detections on a clean reference.**",
            "This indicates a setup issue (a). Verify:",
            "",
            "- `birdnetlib` / `tensorflow` / `tflite_runtime` installation",
            "- model files were loaded (check the analyzer init logs)",
            "- the WAV sample rate and channel count match expectations",
            "- the WAV contains actual audio (not silence) — e.g. run `ffplay` or check",
            "  the file size.",
        ])
    else:
        lines.extend([
            "**BirdNET partially operational.** Detections exist but species diversity",
            f"is low ({unique} species). Check sensitivity, confidence threshold, and the",
            "downloaded clip content before drawing conclusions about Topology A.",
        ])
    lines.append("")

    lines.append("## Top 10 detected species")
    lines.append("")
    if species_rows:
        lines.append("| rank | species | scientific_name | count | avg_conf | max_conf |")
        lines.append("|---:|---|---|---:|---:|---:|")
        for i, s in enumerate(species_rows[:10], 1):
            lines.append(
                f"| {i} | {s['species']} | {s['scientific_name']} | "
                f"{s['num_detections']} | {s['avg_confidence']:.3f} | {s['max_confidence']:.3f} |"
            )
    else:
        lines.append("_No species detected._")
    lines.append("")

    lines.append("## Detection density per minute")
    lines.append("")
    if bins:
        lines.append("| minute | detections |")
        lines.append("|---:|---:|")
        for m in sorted(bins):
            lines.append(f"| {m} | {bins[m]} |")
    else:
        lines.append("_No detections to bin._")
    lines.append("")

    lines.append(
        "Full top-species table and the first 50 time-sorted detections are in "
        "`detections.json`."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()

    download_audio(SOURCE_URL, AUDIO_DIR, CLIP_SECONDS, SAMPLE_RATE)
    duration = probe_duration(AUDIO_PATH)
    print(f"[audio] duration={duration:.1f}s sample_rate={SAMPLE_RATE}Hz path={AUDIO_PATH}")

    print("[birdnet] analyzing ...", flush=True)
    t0 = time.perf_counter()
    detections = run_birdnet(AUDIO_PATH, MIN_CONF, SENSITIVITY)
    elapsed = time.perf_counter() - t0
    print(f"[birdnet] done in {elapsed:.1f}s, {len(detections)} detections")

    species_rows, sample, bins = aggregate(detections)
    unique = len(species_rows)

    out = {
        "source": f"YouTube {SOURCE_ID}",
        "source_description": SOURCE_DESC,
        "source_url": SOURCE_URL,
        "source_license": SOURCE_LICENSE,
        "audio_duration_sec": round(duration, 1),
        "audio_sample_rate": SAMPLE_RATE,
        "birdnet_config": {
            "min_conf": MIN_CONF,
            "sensitivity": SENSITIVITY,
            "lat": None,
            "lon": None,
        },
        "total_detections": len(detections),
        "unique_species": unique,
        "top_10_species": species_rows[:10],
        "all_species_ranked": species_rows,
        "all_detections_sample": sample,
        "analysis_elapsed_sec": round(elapsed, 1),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DETECTIONS_PATH.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(
        render_summary(detections, species_rows, bins, duration, elapsed),
        encoding="utf-8",
    )

    print()
    print(f"Total detections : {len(detections)}")
    print(f"Unique species   : {unique}")
    verdict = (
        "BirdNET functional" if len(detections) > 0 and unique >= 5
        else "BirdNET setup problem" if len(detections) == 0
        else "BirdNET partial"
    )
    print(f"Verdict          : {verdict}")
    print(f"Detections JSON  : {DETECTIONS_PATH}")
    print(f"Summary          : {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
