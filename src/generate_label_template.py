"""Generate data/labels/phase1_labels.json from data/metadata.json.

Reads the metadata produced by generate_metadata.py and emits a label
template with a pre-filled primary_label inferred from the filename:

- filename contains "(sparrow"  marker AND a bulbul marker -> "both"
- filename contains "(sparrow"  marker only                 -> "sparrow"
- filename contains "(chats_"  or "hypsipetes" (bulbul)     -> "bulbul"
- otherwise -> null (review required, reason recorded in notes)

review_needed is always True and manual review by the researcher is
expected. location_detail defaults to "balcony" unless the filename
contains "hokkaido".

Usage:
    python src/generate_label_template.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_PATH = REPO_ROOT / "data" / "metadata.json"
LABELS_PATH = REPO_ROOT / "data" / "labels" / "phase1_labels.json"

SPECIES_CODES = {
    "sparrow": {
        "jp": "スズメ",
        "scientific": "Passer montanus",
        "english": "Eurasian Tree Sparrow",
    },
    "bulbul": {
        "jp": "ヒヨドリ",
        "scientific": "Hypsipetes amaurotis",
        "english": "Brown-eared Bulbul",
    },
}


def infer_label(filename: str) -> str | None:
    lower = filename.lower()
    has_sparrow = "(sparrow" in lower or "sparrow(" in lower
    has_bulbul = "(chats_" in lower or "hypsipetes" in lower
    if has_sparrow and has_bulbul:
        return "both"
    if has_sparrow:
        return "sparrow"
    if has_bulbul:
        return "bulbul"
    return None


def infer_location(filename: str) -> str:
    return "hokkaido" if "hokkaido" in filename.lower() else "balcony"


def main() -> int:
    if not METADATA_PATH.is_file():
        print(f"metadata not found: {METADATA_PATH}", file=sys.stderr)
        print("Run src/generate_metadata.py first.", file=sys.stderr)
        return 1

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    videos = metadata.get("videos", [])
    if not videos:
        print("metadata.json has no videos", file=sys.stderr)
        return 1

    labels: list[dict[str, Any]] = []
    for v in videos:
        filename = v["filename"]
        label = infer_label(filename)
        notes = "" if label is not None else "label could not be inferred from filename"
        labels.append({
            "video_id": v["video_id"],
            "filename": filename,
            "primary_label": label,
            "has_audio_call": None,
            "num_individuals": None,
            "notes": notes,
            "location_detail": infer_location(filename),
            "review_needed": True,
        })

    output = {
        "schema_version": "1.0",
        "phase": "phase1",
        "task": "binary_classification_with_both",
        "species_codes": SPECIES_CODES,
        "labels": labels,
    }

    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LABELS_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    counts: dict[str, int] = {"sparrow": 0, "bulbul": 0, "both": 0, "None": 0}
    for entry in labels:
        key = entry["primary_label"] if entry["primary_label"] is not None else "None"
        counts[key] = counts.get(key, 0) + 1
    print(f"wrote {LABELS_PATH} ({len(labels)} entries)")
    print(f"  primary_label counts: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
