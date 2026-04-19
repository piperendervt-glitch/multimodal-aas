"""sdnd-proof flow_weight update rule for Phase 1.4d.

Asymmetric online update inherited from the single-node AAS:
    * success: w <- w + 0.1 * (1 - w)    (bounded by 1.0, never overshoots)
    * failure: w <- w * 0.7              (bounded by 0.0, never undershoots)

The rule is label-agnostic — the caller decides what counts as success
or failure. In Phase 1.4d Stage 1 a topology is declared successful on
a fold when its binary prediction matches ground truth for **both**
sparrow and bulbul labels.
"""

from __future__ import annotations

INITIAL_WEIGHT = 0.5
SUCCESS_STEP = 0.1
FAILURE_MULTIPLIER = 0.7


def update_weight_sdnd_proof(w: float, success: bool) -> float:
    """Apply the sdnd-proof flow_weight update in place of value w."""
    if success:
        return w + SUCCESS_STEP * (1.0 - w)
    return w * FAILURE_MULTIPLIER


def is_topology_success(topology_pred: dict[str, int], ground_truth: dict[str, int]) -> bool:
    """Label-level correctness: success iff both sparrow and bulbul match."""
    return (
        topology_pred.get("sparrow") == ground_truth.get("sparrow")
        and topology_pred.get("bulbul") == ground_truth.get("bulbul")
    )
