# Phase 1.4d Stage 1 Experiment 4 — label-specific + threshold 0.4

Same 6-weight label-specific structure as Experiment 3, same sdnd-proof update rule (×0.7), same 5 trials, same clean 22 folds, same second-half evaluation. **Only change**: the decision threshold for the per-label weighted score is lowered from 0.5 to **0.4**, so a single confident topology can trigger `label=1` even when the majority disagrees.

To make the A/B comparison fair, we also compute **Fixed_0.4** (equal weights at threshold 0.4) on the same shuffles. The primary Go gate is Adaptive_0.4 vs Fixed_0.4; a reference comparison against Fixed_0.5 (Exp 3's Fixed, same as Exp 1/2 Fixed) is shown for intuition.

## Per-trial macro F1 across 4 experiments

| Trial | Seed | Fixed 0.5 | Fixed 0.4 | Exp 1 | Exp 2 | Exp 3 | **Exp 4** | Δ(Exp 4 − Fixed 0.4) | Δ(Exp 4 − Fixed 0.5) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.909 | 0.871 | 0.871 | 0.871 | **0.871** | -0.038 | -0.038 |
| 2 | 137 | 0.906 | 0.906 | 0.906 | 0.906 | 0.906 | **0.906** | +0.000 | +0.000 |
| 3 | 256 | 0.861 | 0.861 | 0.871 | 0.861 | 0.917 | **0.883** | +0.022 | +0.022 |
| 4 | 512 | 0.771 | 0.771 | 0.723 | 0.771 | 0.723 | **0.723** | -0.048 | -0.048 |
| 5 | 1024 | 0.861 | 0.861 | 0.817 | 0.861 | 0.817 | **0.817** | -0.044 | -0.044 |

## Per-trial F1 breakdown (Experiment 4)

| Trial | Seed | Fixed 0.4 sparrow | Fixed 0.4 bulbul | Adaptive 0.4 sparrow | Adaptive 0.4 bulbul |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.909 | 0.833 | 0.909 |
| 2 | 137 | 0.923 | 0.889 | 0.923 | 0.889 |
| 3 | 256 | 0.889 | 0.833 | 0.909 | 0.857 |
| 4 | 512 | 0.667 | 0.875 | 0.571 | 0.875 |
| 5 | 1024 | 0.889 | 0.833 | 0.800 | 0.833 |

## Experiment 4 final weights (per trial)

| Trial | Seed | A.s | A.b | B.s | B.b | C.s | C.b |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 42 | 0.385 | 0.410 | 0.357 | 0.539 | 0.532 | 0.615 |
| 2 | 137 | 0.259 | 0.510 | 0.288 | 0.597 | 0.571 | 0.580 |
| 3 | 256 | 0.396 | 0.445 | 0.210 | 0.549 | 0.726 | 0.549 |
| 4 | 512 | 0.300 | 0.461 | 0.188 | 0.486 | 0.524 | 0.682 |
| 5 | 1024 | 0.363 | 0.447 | 0.234 | 0.455 | 0.587 | 0.577 |
| mean | - | 0.341 | 0.455 | 0.255 | 0.525 | 0.588 | 0.600 |

## Mean final weights (5-trial average)

|          | sparrow | bulbul | \|Δ\| |
|---|---:|---:|---:|
| Topology A | 0.341 | 0.455 | 0.114 |
| Topology B | 0.255 | 0.525 | 0.270 |
| Topology C | 0.588 | 0.600 | 0.013 |

## Experiment 4 statistical analysis (primary: vs Fixed_0.4)

- Mean Δ: **-0.022**
- Std Δ: 0.031
- Paired t-test: t = -1.560, p = 0.1939
- Cohen's d (paired): -0.697
- 95% CI (paired): [-0.060, +0.017]

## Reference: Experiment 4 vs Fixed_0.5 (threshold change + weight learning combined)

- Mean Δ: -0.022  | p = 0.1939  | d = -0.697  | CI [-0.060, +0.017]

## Go judgment (sdnd-proof 3 criteria, primary baseline = Fixed_0.4)

| Criterion | Threshold | Exp 1 | Exp 2 | Exp 3 | **Exp 4** | Exp 4 pass |
|---|---|---:|---:|---:|---:|:-:|
| p-value | < 0.05 | 0.1177 | 0.3739 | 0.4894 | **0.1939** | N |
| Cohen's d | >= 0.8 | -0.889 | -0.447 | -0.340 | **-0.697** | N |
| 95% CI lower | > 0 | -0.057 | -0.029 | -0.069 | **-0.060** | N |
| **Overall** | all pass | **No-Go** | **No-Go** | **No-Go** | **No-Go** | |

## Trial 3 breakthrough analysis

- Exp 3 Trial 3 (seed 256): Fixed_0.5 = 0.861, Adaptive_0.5 = 0.917 (Δ = +0.056).
- Exp 4 Trial 3 (seed 256): Fixed_0.4 = 0.861, Adaptive_0.4 = 0.883 (Δ = +0.022).
- Exp 4 trial-level split vs Fixed_0.4: 1 better, 1 equal, 3 worse.

## False Positive / False Negative analysis (pooled across 5 × 11 = 55 eval folds)

| pool | sparrow TP | sparrow FP | sparrow FN | sparrow TN | bulbul TP | bulbul FP | bulbul FN | bulbul TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed_0.5 | 21 | 2 | 4 | 28 | 26 | 1 | 7 | 21 |
| Fixed_0.4 | 21 | 2 | 4 | 28 | 26 | 1 | 7 | 21 |
| Adaptive_0.5 (Exp 3) | 22 | 5 | 3 | 25 | 26 | 1 | 7 | 21 |
| Adaptive_0.4 (Exp 4) | 22 | 6 | 3 | 24 | 27 | 2 | 6 | 20 |

### Threshold-change effect on FP/FN

- Fixed side (0.5 → 0.4): total FP change = +0, total FN change = +0.
- Adaptive side (0.5 → 0.4): total FP change = +2, total FN change = -1.

## Caveats

- n=5 trials on shuffle-only variation; the t-test does not generalise to dataset sampling. Bootstrap over the fold set is the next step.
- Lowering the threshold to 0.4 makes `mixed` (both-label) predictions mechanically more likely; with only 2 `mixed` clips in the clean set, the positive F1 gain is fragile and tightly coupled to those two folds.
- Fixed_0.4 is a stronger baseline than Fixed_0.5 whenever the 0.4 threshold recovers TPs that 0.5 missed; this is exactly the headroom Adaptive_0.4 has to beat.

## Output files

- `trials_summary.json`
- `statistical_analysis.json` (primary: Exp 4 vs Fixed_0.4)
- `graphs/threshold_comparison.png`
- `graphs/f1_comparison_4exp.png`
- `graphs/fp_fn_analysis.png`
- `graphs/weight_trajectory_exp4.png`
