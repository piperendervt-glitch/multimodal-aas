# Phase 1.4d Stage 1 Experiment 2 — relaxed-penalty flow_weight

Single-knob change vs Experiment 1 (commit 45f5b9c):

    Exp 1: success = w + 0.1 · (1 − w), failure = w × **0.7** (sdnd-proof)
    Exp 2: success = w + 0.1 · (1 − w), failure = w × **0.9** (relaxed)

All other design choices are identical — 5 trials over seeds [42, 137, 256, 512, 1024], clean 22 folds (11 self + 11 YouTube Tier A/B/B'), first 11 folds warm-up, last 11 folds evaluation, predictions reused from `results/phase1_3_extended/`.

## Per-trial results (Fixed / Adaptive Exp 1 / Adaptive Exp 2)

| Trial | Seed | Fixed | Adaptive Exp 1 | Adaptive Exp 2 | Exp 1 Δ | Exp 2 Δ |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.871 | 0.871 | -0.038 | -0.038 |
| 2 | 137 | 0.906 | 0.906 | 0.906 | +0.000 | +0.000 |
| 3 | 256 | 0.861 | 0.871 | 0.861 | +0.010 | +0.000 |
| 4 | 512 | 0.771 | 0.723 | 0.771 | -0.048 | +0.000 |
| 5 | 1024 | 0.861 | 0.817 | 0.861 | -0.044 | +0.000 |

## Per-trial F1 breakdown (Experiment 2)

| Trial | Seed | Fixed sparrow | Fixed bulbul | Adaptive sparrow | Adaptive bulbul |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.909 | 0.833 | 0.909 |
| 2 | 137 | 0.923 | 0.889 | 0.923 | 0.889 |
| 3 | 256 | 0.889 | 0.833 | 0.889 | 0.833 |
| 4 | 512 | 0.667 | 0.875 | 0.667 | 0.875 |
| 5 | 1024 | 0.889 | 0.833 | 0.889 | 0.833 |

## Final weights comparison (Experiment 1 vs 2)

| Trial | Seed | Exp 1 w_A | Exp 1 w_B | Exp 1 w_C | Exp 2 w_A | Exp 2 w_B | Exp 2 w_C |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 42 | 0.150 | 0.281 | 0.516 | 0.383 | 0.451 | 0.757 |
| 2 | 137 | 0.097 | 0.219 | 0.563 | 0.364 | 0.458 | 0.782 |
| 3 | 256 | 0.301 | 0.179 | 0.517 | 0.487 | 0.403 | 0.751 |
| 4 | 512 | 0.102 | 0.088 | 0.510 | 0.392 | 0.339 | 0.740 |
| 5 | 1024 | 0.157 | 0.193 | 0.566 | 0.388 | 0.437 | 0.769 |
| mean | - | 0.162 | 0.192 | 0.534 | 0.403 | 0.418 | 0.760 |

## Experiment 2 statistical analysis

- Mean Δ: **-0.008**
- Std Δ: 0.017
- Paired t-test: t = -1.000, p = 0.3739
- Cohen's d (paired): -0.447
- 95% CI (paired): [-0.029, +0.013]

## Go judgment (sdnd-proof 3 criteria)

| Criterion | Threshold | Exp 1 value | Exp 2 value | Exp 2 pass |
|---|---|---:|---:|:-:|
| p-value | < 0.05 | 0.1177 | 0.3739 | N |
| Cohen's d | >= 0.8 | -0.889 | -0.447 | N |
| 95% CI lower | > 0 | -0.057 | -0.029 | N |
| **Overall** | all pass | **No-Go** | **No-Go** | |

## Weight-trajectory discussion

- Exp 1 mean final weights: A = 0.162, B = 0.192, C = 0.534
- Exp 2 mean final weights: A = 0.403, B = 0.418, C = 0.760
- Weight spread (max − min) across topologies: Exp 1 = 0.373, Exp 2 = 0.357
- Exp 2's smaller spread confirms the relaxed penalty preserves more ensemble diversity than Exp 1.

## Caveats

- n = 5 trials with non-independent shuffles (same 22 folds, different permutations). The t-test measures sensitivity to ordering, not to dataset sampling.
- Fixed macro F1 is already 0.861 ± 0.051 across trials; there is little headroom for Adaptive to show a large positive Δ. Improving Fixed is only realistic with a higher-capacity topology set.

## Output files

- `trials_summary.json`
- `statistical_analysis.json`
- `graphs/weight_trajectory_comparison.png` (Exp 1 vs Exp 2)
- `graphs/f1_comparison.png` (Fixed vs Adaptive Exp 2)
- `graphs/diff_distribution_comparison.png` (Exp 1 vs Exp 2 Δ)
