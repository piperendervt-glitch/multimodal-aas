"""Robosheep-reviewed tier assignments for the Phase 1.3-extended YouTube set.

31 YouTube videos were downloaded; 20 are Tier C (unusable — BGM, human
voice, text-dominant overlays, or heavy acoustic noise). The remaining
11 are split into:

  * Tier A  — fully usable, no pre-processing required (4 videos).
  * Tier B  — usable once the first 30 seconds are trimmed (6 videos).
  * Tier B' — noisy audio but still usable for model evaluation
              (1 video).

Self-recorded balcony clips (11) are always treated as trusted and
included unconditionally in the "clean" subset.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

REVIEW_DATE = "2026-04-19"
REVIEWER = "robosheep"


TIER_A = [
    "yt_ZRQLsbGEVG8",  # sparrow
    "yt_8HhsjaqFITQ",  # bulbul
    "yt_8zanYHHEpiw",  # bulbul
    "yt_vmrbbEe9R6M",  # bulbul
]

TIER_B = [  # trim 30 s intro
    "yt_JCGgh5zvEeE",  # sparrow
    "yt_-DYmOCTDWc0",  # bulbul
    "yt_jk15DbXQV6A",  # bulbul
    "yt_kMWUQOW-bTM",  # bulbul
    "yt_lnyw5TOMea8",  # bulbul
    "yt_QxKLx__Nzn4",  # bulbul
]

TIER_B_PRIME = [
    "yt_evVHoDIv1hE",  # sparrow (noisy but usable)
]

TIER_C = [
    # sparrow (8)
    "yt_b12Fb3C7LcY", "yt_HFN1MX3D4yM", "yt_RbGhZOyR7Pg", "yt_sljwOG3KU2g",
    "yt_ToG_e-OQWwI", "yt_xhvf73wRJVM", "yt_YFdbUv65QIw", "yt_Z6-WL8woFPk",
    # bulbul (4)
    "yt_4QdQnWqiekY", "yt_p-te4rfSFlo", "yt_TPgyTtnlYak", "yt_zYvgirz9KMo",
    # mixed (8)
    "yt__K7JMyeOnjw", "yt_6FQnY2jYNjM", "yt_bGk6vto6JxM", "yt_bhp8AhQ2cvw",
    "yt_I1XmEHGO19A", "yt_IjHCLUmBqJE", "yt_RC3ELjgkUCQ", "yt_ruTTT9OdI9Q",
]

DEFAULT_TRIM_START_SEC = 30


def tier_of(video_id: str) -> str | None:
    if video_id in TIER_A:
        return "A"
    if video_id in TIER_B:
        return "B"
    if video_id in TIER_B_PRIME:
        return "B'"
    if video_id in TIER_C:
        return "C"
    return None


def is_usable(video_id: str | None, source: str | None = None) -> bool:
    """Return True for self-recorded and Tier A/B/B' YouTube clips."""
    if source == "self":
        return True
    if video_id is None:
        return False
    t = tier_of(video_id)
    if t is None:
        # No tier assignment (e.g. download-failed entry) → exclude.
        return False
    return t in ("A", "B", "B'")


def apply_tiers_to_metadata(metadata_path: Path) -> dict[str, int]:
    """Merge Robosheep's tier review into ``youtube_metadata.json``.

    Safe to call repeatedly. Returns counts by tier for logging.
    """
    import json

    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {"A": 0, "B": 0, "B'": 0, "C": 0, "unknown": 0}
    for v in data.get("videos", []):
        vid = v.get("video_id")
        tier = tier_of(vid)
        if tier is None:
            v["tier"] = None
            v["usable"] = False
            v["exclusion_reason"] = v.get("download_status") if v.get("download_status") != "ok" else None
            v["requires_trim"] = False
            v["trim_start_sec"] = None
            counts["unknown"] += 1
            continue
        v["tier"] = tier
        v["usable"] = tier in ("A", "B", "B'")
        if tier == "C":
            v["exclusion_reason"] = "tier_c_unusable"
            v["requires_trim"] = False
            v["trim_start_sec"] = None
        elif tier == "B":
            v["exclusion_reason"] = None
            v["requires_trim"] = True
            v["trim_start_sec"] = DEFAULT_TRIM_START_SEC
        else:
            v["exclusion_reason"] = None
            v["requires_trim"] = False
            v["trim_start_sec"] = None
        v["reviewed_by"] = REVIEWER
        v["reviewed_at"] = REVIEW_DATE
        v["review_needed"] = False
        counts[tier] += 1
    data["tier_review_summary"] = counts
    data["tier_reviewed_by"] = REVIEWER
    data["tier_reviewed_at"] = REVIEW_DATE
    metadata_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return counts


def load_usable_video_ids(metadata_path: Path) -> set[str]:
    import json
    if not metadata_path.is_file():
        return set()
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    return {v["video_id"] for v in data.get("videos", []) if v.get("usable")}
