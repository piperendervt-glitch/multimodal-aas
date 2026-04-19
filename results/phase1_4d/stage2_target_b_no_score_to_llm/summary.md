# Phase 1.4d Stage 2 Experiment 2 — info filtering without showing scores

Hypothesis: Experiment 1's collapse (d=−1.320, p=0.042) was caused by exposing the LLM to numerical reliability scores. This experiment keeps everything else constant and **removes those scores from the prompt**; the learned weights only drive *which detail tier* each modality's section is rendered at. Three small changes accompany the removal:

- Prompt: no `Reliability scores` block, no detail-tier label in the text.
- Detail thresholds: tightened from (0.4, 0.7) to (0.4, 0.6) so more folds can reach the `full` tier instead of getting stuck at `medium`.
- Label-specific failure penalties: visual_sparrow=0.8, visual_bulbul=0.9, audio_sparrow=0.75, audio_bulbul=0.95 (reflects the measured per-label difficulty).

Everything else matches Exp 1: clean 22 folds, 5 seeds, warm-up 11 / eval 11, single-modality updates through Topology A (audio) / Topology B_v3 (visual).

## Per-trial macro F1

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.667 | 0.667 | +0.000 |
| 2 | 137 | 0.625 | 0.708 | +0.083 |
| 3 | 256 | 0.649 | 0.649 | +0.000 |
| 4 | 512 | 0.650 | 0.650 | +0.000 |
| 5 | 1024 | 0.686 | 0.686 | +0.000 |

## Per-trial F1 breakdown

| Trial | Seed | Fixed sparrow | Fixed bulbul | Adaptive sparrow | Adaptive bulbul |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.667 | 0.667 | 0.667 | 0.667 |
| 2 | 137 | 0.500 | 0.750 | 0.667 | 0.750 |
| 3 | 256 | 0.571 | 0.727 | 0.571 | 0.727 |
| 4 | 512 | 0.500 | 0.800 | 0.500 | 0.800 |
| 5 | 1024 | 0.571 | 0.800 | 0.571 | 0.800 |

## Adaptive final weights per trial

| Trial | Seed | v_sparrow | v_bulbul | a_sparrow | a_bulbul |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.531 | 0.578 | 0.420 | 0.806 |
| 2 | 137 | 0.487 | 0.515 | 0.304 | 0.834 |
| 3 | 256 | 0.289 | 0.644 | 0.438 | 0.809 |
| 4 | 512 | 0.489 | 0.657 | 0.354 | 0.816 |
| 5 | 1024 | 0.496 | 0.585 | 0.397 | 0.814 |
| mean | - | 0.458 | 0.596 | 0.382 | 0.816 |

## Adaptive detail-level frequencies (5 × 22 = 110 decisions)

| level | visual | audio |
|---|---:|---:|
| brief | 0 | 0 |
| medium | 99 | 91 |
| full | 11 | 19 |

## Statistical analysis (Adaptive vs Fixed)

- Mean Δ: **+0.017**
- Std Δ: 0.037
- Paired t-test: t = 1.000, p = 0.3739
- Cohen's d: 0.447
- 95% CI: [-0.030, +0.063]

## Go judgment (sdnd-proof 3 criteria)

| Criterion | Threshold | Value | Pass |
|---|---|---:|:-:|
| p-value | < 0.05 | 0.3739 | N |
| Cohen's d | >= 0.8 | 0.447 | N |
| 95% CI lower | > 0 | -0.030 | N |
| **Overall** | all pass | | **No-Go** |

## Stage 2 Exp 1 vs Exp 2 comparison (prompt-design ablation)

| experiment | prompt | thresholds | penalty | Fixed mean | Adaptive mean | mean Δ | d | p | verdict |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| Exp 1 | shows scores | (0.4, 0.7) | ×0.9 uniform | 0.632 | 0.551 | -0.081 | -1.320 | 0.042 | **No-Go** |
| **Exp 2** | **no scores** | **(0.4, 0.6)** | **4× label-specific** | 0.655 | 0.672 | +0.017 | 0.447 | 0.374 | **No-Go** |

## Discussion

1. **Prompt design vs. weight learning**: with the scores removed from the prompt, the weight-learning machinery now acts only as an information gatekeeper — the LLM never sees that any weighting is happening. This is the cleanest test of the *information filtering* hypothesis we can run without rebuilding the ensemble.
2. **Detail-level utilisation** (vs Exp 1): threshold 0.4 / 0.6 lets more modality-averages escape the `medium` zone. The detail-frequency table above shows whether `full` and `brief` tiers actually got used this time.
3. **Label-specific penalties**: the four penalty values encode observed per-label difficulty (audio sparrow hardest at 0.75, audio bulbul easiest at 0.95). The final-weights table above shows whether those asymmetries survived 22 folds of learning.

## Stage 1 Exp 5b anchor

For reference, Stage 1 Exp 5b (ensemble voting, not single-LLM): Δ=+0.011, d=0.447, p=0.374. Stage 2 operates on a different architectural layer (single-LLM with modality-filtered input); the absolute F1 numbers are not directly comparable to Stage 1.

## Output files

- `trials_summary.json`
- `statistical_analysis.json`
- `graphs/weight_trajectory.png`
- `graphs/detail_level_evolution.png`
- `graphs/f1_comparison.png`
- `graphs/exp1_vs_exp2_comparison.png`
