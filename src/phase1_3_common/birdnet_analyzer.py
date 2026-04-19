"""birdnetlib wrapper that separates target-species evidence from noise.

The analyzer is initialised once (loads the TFLite model) and reused
across folds. Detections are split into:

  * ``all_detections``       — everything BirdNET returned above
    ``min_conf`` (kept for diagnostics / histograms).
  * ``filtered_target_species`` — sparrow / bulbul hits at or above
    ``target_min_conf``, collapsed to one record per species with the
    max confidence and the total number of 3-second windows.
  * ``other_birds``          — species names that did not match either
    target, sorted and de-duplicated.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

SPARROW_SCI = "Passer montanus"
BULBUL_SCI = "Hypsipetes amaurotis"
SPARROW_COMMON = "Eurasian Tree Sparrow"
BULBUL_COMMON = "Brown-eared Bulbul"

DEFAULT_LAT = 35.68
DEFAULT_LON = 139.65
DEFAULT_MIN_CONF = 0.1
DEFAULT_TARGET_MIN_CONF = 0.3


class BirdNetAnalyzer:
    def __init__(
        self,
        lat: float = DEFAULT_LAT,
        lon: float = DEFAULT_LON,
        min_conf: float = DEFAULT_MIN_CONF,
    ) -> None:
        try:
            from birdnetlib.analyzer import Analyzer
        except ImportError as e:
            raise RuntimeError(
                "birdnetlib is not installed. Run: pip install birdnetlib"
            ) from e
        self.analyzer = Analyzer()
        self.lat = lat
        self.lon = lon
        self.min_conf = min_conf

    def analyze(
        self,
        audio_path: Path,
        target_min_conf: float = DEFAULT_TARGET_MIN_CONF,
    ) -> dict[str, Any]:
        from birdnetlib import Recording

        rec = Recording(
            self.analyzer,
            str(audio_path),
            lat=self.lat,
            lon=self.lon,
            date=datetime.now(),
            min_conf=self.min_conf,
        )
        rec.analyze()

        all_detections: list[dict[str, Any]] = []
        for d in rec.detections:
            all_detections.append({
                "species": d.get("common_name", ""),
                "scientific_name": d.get("scientific_name", ""),
                "confidence": round(float(d.get("confidence", 0.0)), 4),
                "time_range": [
                    float(d.get("start_time", 0.0)),
                    float(d.get("end_time", 0.0)),
                ],
            })

        sparrow_hits: list[dict[str, Any]] = []
        bulbul_hits: list[dict[str, Any]] = []
        other_set: set[str] = set()
        for d in all_detections:
            sci = d["scientific_name"]
            com = d["species"]
            is_sparrow = SPARROW_SCI in sci or SPARROW_COMMON in com
            is_bulbul = BULBUL_SCI in sci or BULBUL_COMMON in com
            if is_sparrow and d["confidence"] >= target_min_conf:
                sparrow_hits.append(d)
            elif is_bulbul and d["confidence"] >= target_min_conf:
                bulbul_hits.append(d)
            elif not is_sparrow and not is_bulbul:
                other_set.add(com or "(unknown)")

        filtered: list[dict[str, Any]] = []
        if sparrow_hits:
            filtered.append({
                "species_code": "sparrow",
                "scientific_name": SPARROW_SCI,
                "confidence": round(max(h["confidence"] for h in sparrow_hits), 4),
                "num_detections": len(sparrow_hits),
            })
        if bulbul_hits:
            filtered.append({
                "species_code": "bulbul",
                "scientific_name": BULBUL_SCI,
                "confidence": round(max(h["confidence"] for h in bulbul_hits), 4),
                "num_detections": len(bulbul_hits),
            })

        return {
            "all_detections": all_detections,
            "filtered_target_species": filtered,
            "other_birds": sorted(other_set),
        }
