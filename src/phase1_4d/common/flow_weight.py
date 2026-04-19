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


RELAXED_FAILURE_MULTIPLIER = 0.9


def update_weight_relaxed(w: float, success: bool, failure_rate: float = RELAXED_FAILURE_MULTIPLIER) -> float:
    """Phase 1.4d Stage 1 Experiment 2 rule: softer penalty.

    The Experiment 1 evaluation showed that the sdnd-proof asymmetry
    (0.7 multiplicative penalty) collapsed the adaptive ensemble onto
    Topology C and lost the diversity benefit of the fixed equal-weight
    vote. Experiment 2 tests a single change — keep the same success
    step (+0.1 * (1 - w)) but raise the failure multiplier toward 1
    (default 0.9) so weaker topologies decay more slowly and stay in
    the vote.
    """
    if success:
        return w + SUCCESS_STEP * (1.0 - w)
    return w * failure_rate


def is_topology_success(topology_pred: dict[str, int], ground_truth: dict[str, int]) -> bool:
    """Label-level correctness: success iff both sparrow and bulbul match."""
    return (
        topology_pred.get("sparrow") == ground_truth.get("sparrow")
        and topology_pred.get("bulbul") == ground_truth.get("bulbul")
    )
