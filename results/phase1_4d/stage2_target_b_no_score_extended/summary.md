# Phase 1.4d Stage 2 Experiment 2 extended — n=220 paired fold bootstrap

Exp 2 (commit 2dd8756) cleared |d| ≥ 0.8 and p < 0.05 under 55-fold paired bootstrap (commit 0d0903c) but its 95% CI lower edge landed at +0.000 — the Statistical Go gate missed by a hairline. This extension keeps every Exp 2 setting unchanged and only enlarges the trial set from 5 seeds to 20.

Seeds: [42, 137, 256, 512, 1024] (existing) + [2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432] (new).
Fixed baseline: Exp 2's `fixed_cache` is reused (22 unique per-video predictions). The 5 existing Adaptive trials are reused verbatim (no re-inference). The 15 new seeds contribute 15 × 22 = 330 fresh Adaptive LLM calls.

## Per-trial macro F1 (all 20 trials)

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 (existing) | 42 | 0.667 | 0.667 | +0.000 |
| 2 (existing) | 137 | 0.625 | 0.708 | +0.083 |
| 3 (existing) | 256 | 0.649 | 0.649 | +0.000 |
| 4 (existing) | 512 | 0.650 | 0.650 | +0.000 |
| 5 (existing) | 1024 | 0.686 | 0.686 | +0.000 |
| 6 (new) | 2048 | 0.718 | 0.670 | -0.048 |
| 7 (new) | 4096 | 0.333 | 0.333 | +0.000 |
| 8 (new) | 8192 | 0.595 | 0.571 | -0.024 |
| 9 (new) | 16384 | 0.273 | 0.439 | +0.167 |
| 10 (new) | 32768 | 0.788 | 0.705 | -0.083 |
| 11 (new) | 65536 | 0.733 | 0.733 | +0.000 |
| 12 (new) | 131072 | 0.619 | 0.583 | -0.036 |
| 13 (new) | 262144 | 0.585 | 0.585 | +0.000 |
| 14 (new) | 524288 | 0.467 | 0.443 | -0.024 |
| 15 (new) | 1048576 | 0.473 | 0.473 | +0.000 |
| 16 (new) | 2097152 | 0.686 | 0.686 | +0.000 |
| 17 (new) | 4194304 | 0.670 | 0.670 | +0.000 |
| 18 (new) | 8388608 | 0.649 | 0.649 | +0.000 |
| 19 (new) | 16777216 | 0.438 | 0.438 | +0.000 |
| 20 (new) | 33554432 | 0.476 | 0.476 | +0.000 |

## Adaptive final weights (mean across 20 trials)

| weight | Exp 2 (n=5) | Exp 2 extended (n=20) |
|---|---:|---:|
| visual.sparrow | 0.458 | 0.433 |
| visual.bulbul | 0.596 | 0.613 |
| audio.sparrow | 0.382 | 0.410 |
| audio.bulbul | 0.816 | 0.811 |

## Detail-level frequencies (20 trials × 22 = 440 decisions)

| level | visual | audio |
|---|---:|---:|
| brief | 2 | 0 |
| medium | 420 | 349 |
| full | 18 | 91 |

## Statistical methods compared

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| trial t-test (Exp 2 original) | 5 | +0.017 | +0.447 | 0.3739 | [-0.030, +0.063] | No-Go |
| **trial t-test (extended)** | **20** | +0.002 | **+0.036** | **0.8732** | [-0.021, +0.025] | **No-Go** |
| paired fold bootstrap (Exp 2 original) | 55 | +0.020 | +0.978 | 0.0001 | [+0.000, +0.068] | No-Go |
| **paired fold bootstrap (extended)** | **220** | -0.001 | **-0.115** | **0.8768** | [-0.023, +0.022] | **No-Go** |

## Go criteria breakdown

| method | n | p < 0.05 | |d| ≥ 0.8 | CI excl. 0 | direction | Overall |
|---|---:|:-:|:-:|:-:|:-:|---|
| bootstrap (original) | 55 | Y | Y | N | positive | No-Go |
| **bootstrap (extended)** | **220** | N | N | N | negative | **No-Go** |

## Discussion

**Not-Go** at extended n. Failing criterion/criteria: p<0.05, |d|≥0.8, CI excludes 0. CI edges [-0.023, +0.022], d=-0.115, p=0.8768. 
The extra 15 trials change the balance between effect and variance. Reading off the table: how did Cohen's d move from n=55 to n=220? Did the effect size shrink (variance-dominated) or grow (more signal)?

## Weight-trajectory observations (n=20 mean)

- visual.sparrow: 0.458 → 0.433 (-0.025)
- visual.bulbul: 0.596 → 0.613 (+0.017)
- audio.sparrow: 0.382 → 0.410 (+0.028)
- audio.bulbul: 0.816 → 0.811 (-0.005)

## Output files

- `trials_summary_extended.json`
- `bootstrap_analysis_extended.json`
- `graphs/weight_trajectory_20trials.png`
- `graphs/ci_n_comparison.png`
- `graphs/cohens_d_final.png`
- `graphs/go_criteria_visualization.png`
