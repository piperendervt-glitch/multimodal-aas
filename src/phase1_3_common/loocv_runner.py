"""Leave-one-out runner for Phase 1.3 topology experiments.

There is no actual learning in Phase 1.3 — every fold is independent —
but the LOOCV packaging is kept so that the result layout matches what
Phase 4 will need. Each fold gets its own directory so downstream code
can treat "fold_NN" as the atomic unit of analysis.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
METADATA_PATH = REPO_ROOT / "data" / "metadata.json"
LABELS_PATH = REPO_ROOT / "data" / "labels" / "phase1_labels.json"
VIDEO_DIR = REPO_ROOT / "data" / "raw" / "balcony_videos"

FoldFn = Callable[[int, dict[str, Any], dict[str, int]], dict[str, Any]]


def load_videos() -> list[dict[str, Any]]:
    """Return the 11 labelled videos as dicts with ``video_id``, ``filename``, ``video_path``, ``primary_label``."""
    md = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    lab = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    labels_by_id = {x["video_id"]: x["primary_label"] for x in lab.get("labels", [])}
    out: list[dict[str, Any]] = []
    for v in md.get("videos", []):
        vid = v["video_id"]
        if vid not in labels_by_id:
            continue
        out.append({
            "video_id": vid,
            "filename": v["filename"],
            "video_path": VIDEO_DIR / v["filename"],
            "primary_label": labels_by_id[vid],
        })
    return out


def ground_truth(primary_label: str) -> dict[str, int]:
    if primary_label == "sparrow":
        return {"sparrow": 1, "bulbul": 0}
    if primary_label == "bulbul":
        return {"sparrow": 0, "bulbul": 1}
    if primary_label == "both":
        return {"sparrow": 1, "bulbul": 1}
    return {"sparrow": 0, "bulbul": 0}


def run_loocv(
    topology: str,
    fold_fn: FoldFn,
    output_base: Path,
) -> list[dict[str, Any]]:
    videos = load_videos()
    output_base.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for i, v in enumerate(videos, start=1):
        fold_dir = output_base / f"fold_{i:02d}"
        fold_dir.mkdir(parents=True, exist_ok=True)
        out_path = fold_dir / f"{v['video_id']}.json"
        gt = ground_truth(v["primary_label"])
        print(f"[{topology} fold {i:02d}/{len(videos)}] {v['video_id']} ({v['filename']}) ...",
              flush=True)
        t0 = time.perf_counter()
        try:
            row = fold_fn(i, v, gt)
        except Exception as e:  # noqa: BLE001 - per-fold isolation
            print(f"  [error] {type(e).__name__}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            err_row = {
                "topology": topology,
                "fold": i,
                "video_id": v["video_id"],
                "error": f"{type(e).__name__}: {e}",
                "ground_truth": gt,
            }
            out_path.write_text(
                json.dumps(err_row, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            rows.append(err_row)
            continue

        row["topology"] = topology
        row["fold"] = i
        out_path.write_text(
            json.dumps(row, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rows.append(row)

        pred = row.get("final_prediction") or {}
        fb = row.get("fallback_triggered", False)
        dt = time.perf_counter() - t0
        print(
            f"  pred=(S:{pred.get('sparrow', '?')},B:{pred.get('bulbul', '?')}) "
            f"gt=(S:{gt['sparrow']},B:{gt['bulbul']}) fallback={fb} "
            f"({dt:.1f}s)"
        )
    return rows


def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Multi-label metrics over rows with ``final_prediction`` and ``ground_truth``.

    Rows whose final prediction is missing (e.g. an error row) are not
    counted in ``n_scored``, but still count toward ``parse_fail`` via
    ``llm_output.parsed is None``. Fallback rows are counted.
    """
    matrix = {
        "sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }
    n_scored = 0
    parse_fail = 0
    fallback = 0
    errors = 0
    for r in rows:
        if "error" in r:
            errors += 1
            continue
        if r.get("fallback_triggered"):
            fallback += 1
        llm_out = r.get("llm_output")
        if llm_out is not None and llm_out.get("parsed") is None and not r.get("fallback_triggered"):
            parse_fail += 1
        pred = r.get("final_prediction")
        if pred is None or pred.get("sparrow") not in (0, 1) or pred.get("bulbul") not in (0, 1):
            continue
        n_scored += 1
        gt = r["ground_truth"]
        for k in ("sparrow", "bulbul"):
            p, g = pred[k], gt[k]
            if p == 1 and g == 1:
                matrix[k]["tp"] += 1
            elif p == 1 and g == 0:
                matrix[k]["fp"] += 1
            elif p == 0 and g == 1:
                matrix[k]["fn"] += 1
            else:
                matrix[k]["tn"] += 1

    def f1_of(m: dict[str, int]) -> float:
        tp, fp, fn = m["tp"], m["fp"], m["fn"]
        if tp == 0:
            return 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    f1 = {k: f1_of(matrix[k]) for k in matrix}
    acc = {}
    for k, m in matrix.items():
        total = m["tp"] + m["fp"] + m["fn"] + m["tn"]
        acc[k] = (m["tp"] + m["tn"]) / total if total > 0 else 0.0
    return {
        "n_rows": len(rows),
        "n_scored": n_scored,
        "errors": errors,
        "parse_fail": parse_fail,
        "fallback_triggered": fallback,
        "confusion_matrix": matrix,
        "f1": f1,
        "accuracy": acc,
        "macro_f1": (f1["sparrow"] + f1["bulbul"]) / 2.0,
    }


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
