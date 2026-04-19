# Phase 1.4d Stage 1 Experiment 1 — target A with sdnd-proof flow_weight

Controlled comparison: Fixed equal weights vs Adaptive sdnd-proof flow_weight 
over the three Phase 1.3-extended topologies (A = Audio-Only, B = Visual-Only, 
C = Parallel Fusion). Clean 22-fold set (11 self + 11 YouTube Tier A/B/B'); 
first 11 folds = warm-up, last 11 folds = evaluation. 
Predictions come from the committed fold JSONs (no re-inference).

## Per-trial results

| Trial | Seed | Fixed macro F1 | Adaptive macro F1 | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.871 | -0.038 |
| 2 | 137 | 0.906 | 0.906 | +0.000 |
| 3 | 256 | 0.861 | 0.871 | +0.010 |
| 4 | 512 | 0.771 | 0.723 | -0.048 |
| 5 | 1024 | 0.861 | 0.817 | -0.044 |

## Per-trial F1 breakdown

| Trial | Seed | Fixed sparrow F1 | Fixed bulbul F1 | Adaptive sparrow F1 | Adaptive bulbul F1 |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.909 | 0.833 | 0.909 |
| 2 | 137 | 0.923 | 0.889 | 0.923 | 0.889 |
| 3 | 256 | 0.889 | 0.833 | 0.909 | 0.833 |
| 4 | 512 | 0.667 | 0.875 | 0.571 | 0.875 |
| 5 | 1024 | 0.889 | 0.833 | 0.800 | 0.833 |

## Adaptive final weights per trial

| Trial | Seed | w_A | w_B | w_C |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.150 | 0.281 | 0.516 |
| 2 | 137 | 0.097 | 0.219 | 0.563 |
| 3 | 256 | 0.301 | 0.179 | 0.517 |
| 4 | 512 | 0.102 | 0.088 | 0.510 |
| 5 | 1024 | 0.157 | 0.193 | 0.566 |
| mean | - | 0.162 | 0.192 | 0.534 |

## Statistical analysis

- Mean Δ: **-0.024**
- Std Δ: 0.027
- Paired t-test: t = -1.988, p = 0.1177
- Cohen's d (paired): -0.889
- 95% CI (paired): [-0.057, +0.010]

## Go judgment (sdnd-proof 3 criteria)

| Criterion | Threshold | Value | Pass |
|---|---|---:|:-:|
| p-value  | < 0.05 | 0.1177 | N |
| Cohen's d | >= 0.8 | -0.889 | N |
| 95% CI lower | > 0 | -0.057 | N |
| **Overall** | all pass | | **No-Go** |

## Weight trajectory discussion

- Mean final weights across 5 trials: A = 0.162, B = 0.192, C = 0.534
- Topology C carries the highest mean weight, matching Phase 1.3-extended clean performance where its point F1 is the strongest.
- Topology A starts and stays low because its label-level success rate is much worse than B and C on the clean set (many fallback-induced 0/0 predictions).
- The sdnd-proof asymmetry (additive success, multiplicative failure) is visible: once a topology loses a fold it drops fast (× 0.7), then crawls back at +0.1·(1−w) per correct fold.

## Caveats

- n = 5 trials; the t-test has 4 degrees of freedom, so Cohen's d >= 0.8 needs a mean-to-std ratio near 0.8+. With variance across seeds this bar is genuinely hard.
- Trials differ only in the shuffle order of the same 22 folds; trials are NOT independent dataset draws. The paired t-test here measures sensitivity to fold ordering, not to dataset sampling. For the latter we need bootstrap of the fold set.
- All three topologies draw predictions from the same pool of fold JSONs, so the ensemble's correlation structure is fixed. Independent LLM re-runs would give a different answer.

## Output files

- `trials_summary.json` — all 5 trials with per-fold decisions
- `statistical_analysis.json` — paired stats + Go judgment
- `graphs/weight_trajectory.png`
- `graphs/f1_comparison.png`
- `graphs/diff_distribution.png`
