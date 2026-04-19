"""Weighted-vote ensemble utilities for Phase 1.4d.

Each topology produces a binary ``{sparrow: 0/1, bulbul: 0/1}`` prediction.
The ensemble combines them with a weighted per-label score and a 0.5
threshold. Macro F1 is computed by pooling counts across the chosen
fold set (second half of the random trial order, per spec).
"""

from __future__ import annotations

from typing import Any


def weighted_vote(
    preds: dict[str, dict[str, int]],
    weights: dict[str, float],
    threshold: float = 0.5,
) -> dict[str, int]:
    """Combine per-topology binary predictions with ``weights``.

    ``preds`` maps topology key (e.g. "A", "B", "C") to a dict with
    0/1 ``sparrow`` and ``bulbul``. ``weights`` uses the same keys.
    """
    total = sum(weights[k] for k in preds.keys())
    if total <= 0:
        return {"sparrow": 0, "bulbul": 0}
    out: dict[str, int] = {}
    for cls in ("sparrow", "bulbul"):
        score = sum(weights[k] * preds[k][cls] for k in preds.keys()) / total
        out[cls] = 1 if score >= threshold else 0
    return out


def _f1(tp: int, fp: int, fn: int) -> float:
    if tp == 0:
        return 0.0
    pr = tp / (tp + fp) if (tp + fp) else 0.0
    rc = tp / (tp + fn) if (tp + fn) else 0.0
    if pr + rc == 0:
        return 0.0
    return 2 * pr * rc / (pr + rc)


def compute_f1_bundle(pairs: list[tuple[dict[str, int], dict[str, int]]]) -> dict[str, Any]:
    """Pooled sparrow / bulbul / macro F1 over a list of (pred, gt) pairs."""
    matrix = {
        "sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }
    for pred, gt in pairs:
        for cls in ("sparrow", "bulbul"):
            p, g = pred[cls], gt[cls]
            if p == 1 and g == 1:
                matrix[cls]["tp"] += 1
            elif p == 1 and g == 0:
                matrix[cls]["fp"] += 1
            elif p == 0 and g == 1:
                matrix[cls]["fn"] += 1
            else:
                matrix[cls]["tn"] += 1
    sp = _f1(matrix["sparrow"]["tp"], matrix["sparrow"]["fp"], matrix["sparrow"]["fn"])
    bu = _f1(matrix["bulbul"]["tp"],  matrix["bulbul"]["fp"],  matrix["bulbul"]["fn"])
    return {
        "sparrow_f1": sp,
        "bulbul_f1":  bu,
        "macro_f1":   (sp + bu) / 2.0,
        "confusion":  matrix,
    }
