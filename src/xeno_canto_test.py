"""Minimal Xeno-canto API v3 connectivity check.

Queries the Xeno-canto v3 recordings endpoint for Parus major, quality A,
prints the total number of recordings and the first three results'
metadata. Intended as a Phase 0 smoke test only.

Xeno-canto API v3 requires an API key. Register at
https://xeno-canto.org/account and export the key:

    # PowerShell
    $env:XENO_CANTO_API_KEY = "<your key>"
    # bash / WSL
    export XENO_CANTO_API_KEY=<your key>

Usage:
    python src/xeno_canto_test.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests

API_URL = "https://xeno-canto.org/api/3/recordings"
QUERY = "Parus major q:A"
PER_PAGE = 3
TIMEOUT_SECONDS = 30


def fetch(query: str, api_key: str) -> dict[str, Any]:
    params = {"query": query, "key": api_key, "per_page": str(PER_PAGE)}
    response = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def summarise(payload: dict[str, Any]) -> None:
    num_recordings = payload.get("numRecordings", "?")
    num_species = payload.get("numSpecies", "?")
    recordings = payload.get("recordings", []) or []

    print(f"query            : {QUERY}")
    print(f"numRecordings    : {num_recordings}")
    print(f"numSpecies       : {num_species}")
    print(f"recordings shown : {len(recordings)}")
    print("-" * 60)

    for i, rec in enumerate(recordings[:3], start=1):
        meta = {
            "id": rec.get("id"),
            "gen": rec.get("gen"),
            "sp": rec.get("sp"),
            "en": rec.get("en"),
            "cnt": rec.get("cnt"),
            "loc": rec.get("loc"),
            "q": rec.get("q"),
            "lic": rec.get("lic"),
            "rec": rec.get("rec"),
            "url": rec.get("url"),
        }
        print(f"[{i}] {json.dumps(meta, ensure_ascii=False, indent=2)}")


def main() -> int:
    api_key = os.environ.get("XENO_CANTO_API_KEY")
    if not api_key:
        print(
            "XENO_CANTO_API_KEY is not set. Xeno-canto API v3 requires a key.\n"
            "Register at https://xeno-canto.org/account and set the env var "
            "before retrying.",
            file=sys.stderr,
        )
        return 2

    try:
        payload = fetch(QUERY, api_key)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        body = e.response.text[:200] if e.response is not None else ""
        print(f"HTTP error {status}: {e}", file=sys.stderr)
        if body:
            print(f"body: {body}", file=sys.stderr)
        return 1
    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1

    summarise(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
