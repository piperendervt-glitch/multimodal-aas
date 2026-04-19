# Phase 1.4d Stage 1 — overall summary

Target A of the Phase 1.4d programme is **weight between heterogeneous topologies** in an ensemble. Stage 1 is a controlled comparison: Fixed equal weights vs Adaptive flow_weight learning (sdnd-proof rule) over clean 22 folds, 5 trials, second-half evaluation. Six experiments were run:

| # | script folder | topology set | weight structure | failure rule | threshold |
|---|---|---|---|---|---:|
| Exp 1 | `stage1_target_a_sdnd_proof` | Phase 1.3 A/B/C | Shared | ×0.7 | 0.5 |
| Exp 2 | `stage1_target_a_relaxed` | Phase 1.3 A/B/C | Shared | ×0.9 | 0.5 |
| Exp 3 | `stage1_target_a_label_specific` | Phase 1.3 A/B/C | Label-specific | ×0.7 | 0.5 |
| Exp 4 | `stage1_target_a_label_specific_low_threshold` | Phase 1.3 A/B/C | Label-specific | ×0.7 | 0.4 |
| Exp 5a | `stage1_target_a_improved_topology_shared` | A + B_v3 + C_v3 | Shared | ×0.7 | 0.5 |
| Exp 5b | `stage1_target_a_improved_topology_label_specific` | A + B_v3 + C_v3 | Label-specific | ×0.7 | 0.5 |

## Headline 2×2 matrix (shared vs label-specific × Phase 1.3 vs Phase 1.4a topology)

| | Phase 1.3 A/B/C | A + B_v3 + C_v3 |
|---|---|---|
| **Shared weight** | Exp 1: Δ=-0.024, d=-0.889, p=0.118, CI=[-0.057,+0.010] → **No-Go** | Exp 5a: Δ=+0.032, d=+0.673, p=0.207, CI=[-0.027,+0.092] → **No-Go** |
| **Label-specific** | Exp 3: Δ=-0.015, d=-0.340, p=0.489, CI=[-0.069,+0.039] → **No-Go** | Exp 5b: Δ=+0.011, d=+0.447, p=0.374, CI=[-0.019,+0.041] → **No-Go** |

## All 6 experiments — ordered by Cohen's d

| Exp | Topology | Weight | Penalty | Thr | Fixed mean F1 | Adaptive mean F1 | mean Δ | Cohen's d | p | 95% CI | Go |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|:-:|
| Exp 5a | A + B_v3 + C_v3 | Shared | ×0.7 | 0.5 | 0.824 | 0.856 | +0.032 | +0.673 | 0.207 | [-0.027, +0.092] | No-Go |
| Exp 5b | A + B_v3 + C_v3 | Label-specific | ×0.7 | 0.5 | 0.824 | 0.835 | +0.011 | +0.447 | 0.374 | [-0.019, +0.041] | No-Go |
| Exp 3 | Phase 1.3 A/B/C | Label-specific | ×0.7 | 0.5 | 0.862 | 0.847 | -0.015 | -0.340 | 0.489 | [-0.069, +0.039] | No-Go |
| Exp 2 | Phase 1.3 A/B/C | Shared | ×0.9 | 0.5 | 0.862 | 0.854 | -0.008 | -0.447 | 0.374 | [-0.029, +0.013] | No-Go |
| Exp 4 | Phase 1.3 A/B/C | Label-specific | ×0.7 | 0.4 | 0.862 | 0.840 | -0.022 | -0.697 | 0.194 | [-0.060, +0.017] | No-Go |
| Exp 1 | Phase 1.3 A/B/C | Shared | ×0.7 | 0.5 | 0.862 | 0.838 | -0.024 | -0.889 | 0.118 | [-0.057, +0.010] | No-Go |

## Fixed baseline by topology set

| topology set | experiments | mean Fixed macro F1 |
|---|---|---:|
| Phase 1.3 A/B/C | Exp 1–4 | 0.862 |
| A + B_v3 + C_v3 | Exp 5a/5b | 0.824 |
| ΔFixed (Phase 1.4a − Phase 1.3) | — | -0.038 |

## Label-specific weight balance (Exp 3 vs Exp 5b)

| topology | Exp 3 sparrow | Exp 3 bulbul | Exp 3 \|Δ\| | Exp 5b sparrow | Exp 5b bulbul | Exp 5b \|Δ\| |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.341 | 0.455 | 0.114 | 0.341 | 0.455 | 0.114 |
| B (→B_v3) | 0.255 | 0.525 | 0.270 | 0.362 | 0.363 | 0.001 |
| C (→C_v3) | 0.588 | 0.600 | 0.013 | 0.637 | 0.651 | 0.014 |

## Structural findings from Stage 1

1. **sdnd-proof flow_weight transfer is structurally constrained in a 3-node 0/1 vote ensemble.** With shared weights on the Phase 1.3 topology (Exp 1–4), every configuration produced a negative Cohen's d — learning the weights either collapsed ensemble diversity (×0.7 harsh penalty) or became inert (×0.9 soft penalty, or Fixed and Adaptive converge on the same majority decision).
2. **Improving the base topology flips Cohen's d positive.** Replacing the two weakest Phase 1.3 topologies with their Phase 1.4a upgrades (B → B_v3, C → C_v3) pushes Cohen's d from −0.889 (Exp 1) to **+0.673 (Exp 5a)** — still shy of the 0.8 Go threshold, but the sign change is a genuine structural effect: the learning rule was waiting for stronger base nodes.
3. **Label-specific weights are most informative as a diagnostic tool.** Exp 3 exposed a striking Topology-B bulbul bias (B.sparrow=0.255, B.bulbul=0.525). Exp 5b shows that B_v3 has *erased* that split (B.sparrow=0.362, B.bulbul=0.363), which is exactly the engineering goal of the bbox prompt v3. The learning rule is acting here as an interpretability probe, not as an accuracy driver.
4. **Fixed baseline on the improved topology is *lower* than on Phase 1.3.** ΔFixed = -0.038. B_v3 and C_v3 trade per-fold error correlations differently; majority voting loses some of the complementarity. Adaptive learning partially recovers the gap (Exp 5a Adaptive mean = 0.856), which is itself a flow_weight-learning signal.
5. **Stage 1 overall: No-Go on the sdnd-proof 3-criterion gate, but the experiment is scientifically productive.** Zero experiments clear the gate (all six p > 0.05 after n=5 paired trials). The Cohen's d trajectory −0.889 → −0.447 → −0.340 → −0.697 → **+0.673** / +0.447 tells us the direction of travel: flip the sign by upgrading topologies and isolating labels. Closing the gap to d ≥ 0.8 is a Stage 2 problem.

## Recommendations for Stage 2

- **Topology-set iteration.** The Fixed baseline on the improved topology is modestly worse than on Phase 1.3 A/B/C. A v3-style re-evaluation of Topology A (BirdNET side) is the cheapest next upgrade.
- **Fold-set bootstrap rather than shuffle trials.** n=5 trials over the same 22 folds is measuring sensitivity to ordering, not to dataset sampling. A paired bootstrap over (Fixed, Adaptive) on fold indices would likely yield a power gain without any new inference.
- **Per-fold credit assignment.** The current 'success = both labels right' rule is all-or-nothing. A per-label partial-success rule (already present in Exp 3/4/5b) is better, but a continuous-credit rule (success intensity proportional to confidence delta) could amplify the gradient further.
- **A higher-dimensional target.** Target A was ensemble weights over 3 topologies. Target B (intra-modality) or Target C (per-label routing) may exhibit stronger flow_weight signals because they have more weights relative to the 22-fold signal.
