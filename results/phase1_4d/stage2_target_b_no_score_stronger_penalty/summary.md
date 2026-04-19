# Phase 1.4d Stage 2 Experiment 3 — stronger penalties, scores still hidden

Single-variable change vs Experiment 2 (commit 2dd8756): each of the four label-specific failure multipliers is made more aggressive. Everything else (no-score prompt, detail thresholds 0.4/0.6, 5 seeds, clean 22 folds, warm-up 11 / eval 11, Topology A & B_v3 single-modality updates) is carried over verbatim.

Penalty change:

| modality-label | Exp 2 | **Exp 3** |
|---|---:|---:|
| visual.sparrow | 0.80 | **0.7** |
| visual.bulbul  | 0.90 | **0.85** |
| audio.sparrow  | 0.75 | **0.6** |
| audio.bulbul   | 0.95 | **0.9** |

Objective: pull at least one weight below the 0.4 `brief` threshold so the detail knob finally sees all three tiers, and push Cohen's d past 0.8.

## Per-trial macro F1

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.667 | 0.697 | +0.030 |
| 2 | 137 | 0.625 | 0.650 | +0.025 |
| 3 | 256 | 0.649 | 0.614 | -0.036 |
| 4 | 512 | 0.650 | 0.800 | +0.150 |
| 5 | 1024 | 0.686 | 0.717 | +0.031 |

## Per-trial F1 breakdown

| Trial | Seed | Fixed sparrow | Fixed bulbul | Adaptive sparrow | Adaptive bulbul |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.667 | 0.667 | 0.667 | 0.727 |
| 2 | 137 | 0.500 | 0.750 | 0.500 | 0.800 |
| 3 | 256 | 0.571 | 0.727 | 0.500 | 0.727 |
| 4 | 512 | 0.500 | 0.800 | 0.800 | 0.800 |
| 5 | 1024 | 0.571 | 0.800 | 0.600 | 0.833 |

## Adaptive final weights per trial

| Trial | Seed | v_sparrow | v_bulbul | a_sparrow | a_bulbul |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.435 | 0.490 | 0.338 | 0.707 |
| 2 | 137 | 0.364 | 0.408 | 0.200 | 0.758 |
| 3 | 256 | 0.183 | 0.574 | 0.332 | 0.715 |
| 4 | 512 | 0.415 | 0.577 | 0.220 | 0.727 |
| 5 | 1024 | 0.411 | 0.497 | 0.320 | 0.723 |
| mean | - | 0.362 | 0.509 | 0.282 | 0.726 |

- Minimum final weight observed across 5 trials × 4 slots: **0.183** (reached brief tier (<0.4)).
- Final-weight brief-tier hits per slot (out of 5 trials):
  - visual.sparrow: 2 / 5
  - visual.bulbul: 0 / 5
  - audio.sparrow: 5 / 5
  - audio.bulbul: 0 / 5

## Adaptive detail-level frequencies (5 × 22 = 110 decisions)

| level | visual | audio |
|---|---:|---:|
| brief | 36 | 6 |
| medium | 70 | 101 |
| full | 4 | 3 |

Trajectory excursions where the modality average fell at or below 0.4 (regardless of final tier): visual = 36, audio = 6.

## Statistical analysis (Adaptive vs Fixed)

- Mean Δ: **+0.040**
- Std Δ: 0.068
- Paired t-test: t = 1.328, p = 0.2548
- Cohen's d: 0.594
- 95% CI: [-0.044, +0.124]

## Go judgment (sdnd-proof 3 criteria)

| Criterion | Threshold | Value | Pass |
|---|---|---:|:-:|
| p-value | < 0.05 | 0.2548 | N |
| Cohen's d | >= 0.8 | 0.594 | N |
| 95% CI lower | > 0 | -0.044 | N |
| **Overall** | all pass | | **No-Go** |

## Stage 2 three-experiment comparison

| Exp | prompt | penalty | Fixed mean | Adaptive mean | mean Δ | d | p | CI | verdict |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| Exp 1 | scores shown | ×0.9 uniform | 0.632 | 0.551 | -0.081 | -1.320 | 0.042 | [-0.156, -0.005] | **No-Go** |
| Exp 2 | scores hidden | 0.80/0.90/0.75/0.95 | 0.655 | 0.672 | +0.017 | +0.447 | 0.374 | [-0.030, +0.063] | **No-Go** |
| **Exp 3** | **scores hidden** | **0.70/0.85/0.60/0.90** | 0.655 | 0.695 | +0.040 | +0.594 | 0.255 | [-0.044, +0.124] | **No-Go** |

## Hypothesis check

- **Hypothesis A — brief-tier reach**: Exp 2 audio.sparrow mean was 0.382 (just above 0.4). Exp 3 penalty for audio.sparrow is 0.60; final mean is **0.282** (below the 0.4 brief boundary). Brief-tier decisions in adaptive trajectory: audio = 6, visual = 36.
- **Hypothesis B — diversity collapse**: if Cohen's d drops below Exp 2's +0.447, the stronger penalties over-concentrated evidence. Measured d = 0.594 (vs Exp 2's +0.447).
- **Hypothesis C — Go via penalty strength**: target d ≥ 0.8. Measured d = 0.594. Go gate crossed? No.

## Stage 1 Exp 5b anchor (reminder)

Stage 1 Exp 5b (ensemble-voting architecture): Δ=+0.011, d=+0.447, p=0.374. Stage 2 tests the same weight-learning machinery on a single-LLM substrate, so absolute F1 values are not directly comparable — only the Δ sign and effect-size magnitude are.

## Output files

- `trials_summary.json`
- `statistical_analysis.json`
- `graphs/weight_trajectory_exp3.png`
- `graphs/detail_level_evolution_exp3.png`
- `graphs/stage2_comparison.png`
- `graphs/cohens_d_progression.png`
