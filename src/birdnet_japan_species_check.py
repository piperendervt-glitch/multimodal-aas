"""BirdNET sensitivity check for Japanese target species.

After the North American baseline confirmed that BirdNET itself is
functional (91 species / 423 detections on a 20-minute reference clip),
this script tests whether BirdNET can actually recognise our two target
species — *Passer montanus* (Eurasian Tree Sparrow / スズメ) and
*Hypsipetes amaurotis* (Brown-eared Bulbul / ヒヨドリ) — when given
clean audio where they are the named subject.

The Topology A pipeline uses Tokyo lat/lon (35.68, 139.65); this script
uses the same coordinates so the probable-species list matches the
deployment setup. The question is narrow: with clean audio and the right
location prior, does BirdNET emit high-confidence detections for each
target species?

Exit code 0 on a successful run regardless of detection count (the
verdict is the finding to report).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = REPO_ROOT / "data" / "raw" / "birdnet_japan"
RESULTS_DIR = REPO_ROOT / "results" / "phase1_3" / "birdnet_japan"
SUMMARY_PATH = RESULTS_DIR / "summary.md"

MIN_CONF = 0.1
SENSITIVITY = 1.0
SAMPLE_RATE = 16000
LAT = 35.68
LON = 139.65  # Tokyo — matches Topology A setup

# Each clip is configured with the YouTube URL, the output stem, and the
# target species we expect BirdNET to pick up.
CLIPS = [
    {
        "name": "sparrow",
        "url": "https://www.youtube.com/watch?v=Z6-WL8woFPk",
        "source_id": "Z6-WL8woFPk",
        "description": (
            "スズメの鳴き声01さえずりと地鳴き？Eurasian Tree Sparrow / "
            "Passer montanus (channel: 身近な生き物語)"
        ),
        "target_common": "Eurasian Tree Sparrow",
        "target_scientific": "Passer montanus",
    },
    {
        "name": "bulbul",
        "url": "https://www.youtube.com/watch?v=8zanYHHEpiw",
        "source_id": "8zanYHHEpiw",
        "description": "ヒヨドリの群れ 鳴き声 Hypsipetes amaurotis",
        "target_common": "Brown-eared Bulbul",
        "target_scientific": "Hypsipetes amaurotis",
    },
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


def download_audio(url: str, out_dir: Path, stem: str, sr: int) -> Path:
    """Download the full audio track of ``url`` as ``{stem}.wav`` at ``sr`` Hz mono."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.wav"
    if out_path.is_file() and out_path.stat().st_size > 100_000:
        print(f"[cache] {out_path} already exists, skipping download.")
        return out_path
    for leftover in out_dir.glob(f"{stem}.*"):
        leftover.unlink()
    yt_dlp = _resolve_yt_dlp()
    cmd = [
        yt_dlp,
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--postprocessor-args", f"ffmpeg:-ar {sr} -ac 1",
        "-o", str(out_dir / f"{stem}.%(ext)s"),
        url,
    ]
    print(f"[download] {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)
    return out_path


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


def run_birdnet(audio_path: Path) -> list[dict[str, Any]]:
    from birdnetlib import Recording
    from birdnetlib.analyzer import Analyzer
    analyzer = Analyzer()
    rec = Recording(
        analyzer,
        str(audio_path),
        lat=LAT,
        lon=LON,
        date=datetime.now(),
        min_conf=MIN_CONF,
        sensitivity=SENSITIVITY,
    )
    rec.analyze()
    return rec.detections


def summarise_clip(clip: dict[str, Any]) -> dict[str, Any]:
    audio_path = download_audio(clip["url"], AUDIO_DIR, clip["name"], SAMPLE_RATE)
    duration = probe_duration(audio_path)
    print(f"[{clip['name']}] duration={duration:.1f}s path={audio_path}")

    t0 = time.perf_counter()
    raw_detections = run_birdnet(audio_path)
    elapsed = time.perf_counter() - t0
    print(f"[{clip['name']}] birdnet done in {elapsed:.1f}s, {len(raw_detections)} detections")

    # Aggregate by species.
    by_species: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in raw_detections:
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

    target_sci = clip["target_scientific"]
    target_com = clip["target_common"]
    target_hits: list[dict[str, Any]] = []
    for d in sorted(raw_detections, key=lambda x: float(x.get("start_time", 0.0))):
        sci = d.get("scientific_name", "")
        com = d.get("common_name", "")
        if target_sci in sci or target_com in com:
            target_hits.append({
                "confidence": round(float(d.get("confidence", 0.0)), 4),
                "time_range": [
                    round(float(d.get("start_time", 0.0)), 1),
                    round(float(d.get("end_time", 0.0)), 1),
                ],
            })

    target_confs = [h["confidence"] for h in target_hits]
    target_stats = {
        "num_detections": len(target_hits),
        "max_confidence": round(max(target_confs), 4) if target_confs else 0.0,
        "avg_confidence": round(sum(target_confs) / len(target_confs), 4) if target_confs else 0.0,
    }

    detections_payload = {
        "source": f"YouTube {clip['source_id']}",
        "source_description": clip["description"],
        "source_url": clip["url"],
        "target_species": target_sci,
        "target_common_name": target_com,
        "audio_duration_sec": round(duration, 1),
        "audio_sample_rate": SAMPLE_RATE,
        "birdnet_config": {
            "min_conf": MIN_CONF,
            "sensitivity": SENSITIVITY,
            "lat": LAT,
            "lon": LON,
        },
        "total_detections": len(raw_detections),
        "unique_species": len(by_species),
        "target_species_detections": target_hits,
        "target_species_stats": target_stats,
        "top_species": species_rows[:10],
        "all_species_ranked": species_rows,
        "analysis_elapsed_sec": round(elapsed, 1),
    }

    out_path = RESULTS_DIR / f"{clip['name']}_detections.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(detections_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[{clip['name']}] wrote {out_path}")
    return detections_payload


def classify_result(payload: dict[str, Any]) -> str:
    max_c = payload["target_species_stats"]["max_confidence"]
    if max_c >= 0.5:
        return "high"
    if max_c >= 0.3:
        return "moderate"
    if max_c > 0.0:
        return "low"
    return "none"


def render_summary(sparrow: dict[str, Any], bulbul: dict[str, Any]) -> str:
    def fmt_stats(p: dict[str, Any]) -> str:
        s = p["target_species_stats"]
        return (
            f"target detections: **{s['num_detections']}**, "
            f"max_conf: **{s['max_confidence']:.3f}**, "
            f"avg_conf: **{s['avg_confidence']:.3f}**"
        )

    sp_cls = classify_result(sparrow)
    bu_cls = classify_result(bulbul)

    lines = [
        "# BirdNET Sensitivity Check — Japanese target species",
        "",
        f"- BirdNET config: `min_conf={MIN_CONF}`, `sensitivity={SENSITIVITY}`, ",
        f"  lat/lon = ({LAT}, {LON}) (Tokyo, matches Topology A setup)",
        "",
        "## Sources",
        "",
        f"- **Sparrow clip**: {sparrow['source_description']}  ",
        f"  URL: {sparrow['source_url']}  ",
        f"  Duration: {sparrow['audio_duration_sec']:.1f} s",
        f"- **Bulbul clip**: {bulbul['source_description']}  ",
        f"  URL: {bulbul['source_url']}  ",
        f"  Duration: {bulbul['audio_duration_sec']:.1f} s",
        "",
        "## Target-species detections",
        "",
        f"- *Passer montanus* (sparrow clip): {fmt_stats(sparrow)}",
        f"- *Hypsipetes amaurotis* (bulbul clip): {fmt_stats(bulbul)}",
        "",
        "## Verdict",
        "",
    ]

    if sp_cls == "high" and bu_cls == "high":
        lines.extend([
            "**Both target species are detected at high confidence (≥0.5) on",
            "clean reference audio.** The Japanese-species coverage hypothesis (b)",
            "is therefore **eliminated** as the main driver of Phase 1.3 Topology A's",
            "low detection rate; the remaining primary suspect is (c) **balcony audio",
            "quality** — webcam microphone bandwidth, distance from the feeder,",
            "wind/traffic noise, or aliasing in the self-recorded clips.",
        ])
    elif sp_cls == "none" and bu_cls == "none":
        lines.extend([
            "**Neither target species is detected on clean reference audio.** The",
            "Japanese-species coverage hypothesis (b) is **confirmed** as at least a",
            "major factor. Consider: a different acoustic model (e.g. BirdNET Analyzer",
            "with the Japan-trained head, if available), or replacing the audio node",
            "in Topology A with a Japan-specific classifier.",
        ])
    elif sp_cls != "none" and bu_cls != "none":
        lines.extend([
            "**Both target species are detected, but at mixed confidences** ",
            f"(sparrow: {sp_cls}, bulbul: {bu_cls}).",
            "BirdNET covers both species but the margin on the weaker side suggests a",
            "combination of (b) species-specific sensitivity and (c) audio quality;",
            "a separate test with Xeno-canto clean reference audio will help",
            "disentangle the two.",
        ])
    else:
        hits = "sparrow" if sp_cls != "none" else "bulbul"
        miss = "bulbul" if hits == "sparrow" else "sparrow"
        lines.extend([
            f"**Asymmetric result**: BirdNET detects the {hits} clip's target but not",
            f"the {miss} clip's target. Species-specific sensitivity is uneven; for",
            f"Topology A the {miss} class would benefit most from a replacement or",
            "augmentation node, while the other target can be kept on BirdNET.",
        ])
    lines.append("")

    lines.append("## Phase 1.3 Topology A implication")
    lines.append("")
    lines.append(
        "Baseline cross-check (previous run, North American reference audio): ",
    )
    lines.append(
        "BirdNET returned 423 detections / 91 species and picked up "
        "*Passer domesticus* 22 times. Passer genus is clearly within its recognition "
        "envelope, so the sparrow clip result should discriminate between "
        "species-specific sensitivity and recording quality directly."
    )
    lines.append("")

    lines.append("## Top 10 species per clip (diagnostic)")
    lines.append("")
    for label, payload in (("Sparrow clip", sparrow), ("Bulbul clip", bulbul)):
        lines.append(f"### {label}")
        lines.append("")
        rows = payload["top_species"]
        if not rows:
            lines.append("_No detections._")
            lines.append("")
            continue
        lines.append("| rank | species | scientific_name | count | avg_conf | max_conf |")
        lines.append("|---:|---|---|---:|---:|---:|")
        for i, r in enumerate(rows, 1):
            lines.append(
                f"| {i} | {r['species']} | {r['scientific_name']} | "
                f"{r['num_detections']} | {r['avg_confidence']:.3f} | {r['max_confidence']:.3f} |"
            )
        lines.append("")

    lines.append("## Target-species detection timeline")
    lines.append("")
    for label, payload in (("Sparrow clip — Passer montanus", sparrow),
                            ("Bulbul clip — Hypsipetes amaurotis", bulbul)):
        lines.append(f"### {label}")
        lines.append("")
        hits = payload["target_species_detections"]
        if not hits:
            lines.append("_No target-species detections above `min_conf=0.1`._")
            lines.append("")
            continue
        lines.append("| time (s) | confidence |")
        lines.append("|---|---|")
        for h in hits:
            start, end = h["time_range"]
            lines.append(f"| {start:.1f} – {end:.1f} | {h['confidence']:.3f} |")
        lines.append("")

    lines.append("Raw per-clip JSONs: `sparrow_detections.json`, `bulbul_detections.json`.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()
    sparrow = summarise_clip(CLIPS[0])
    bulbul = summarise_clip(CLIPS[1])

    SUMMARY_PATH.write_text(render_summary(sparrow, bulbul), encoding="utf-8")

    def cls_label(p: dict[str, Any]) -> str:
        return f"{classify_result(p)} (max_conf={p['target_species_stats']['max_confidence']:.3f}, n={p['target_species_stats']['num_detections']})"

    print()
    print(f"Sparrow clip     : {cls_label(sparrow)}")
    print(f"Bulbul clip      : {cls_label(bulbul)}")
    print(f"Summary          : {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
