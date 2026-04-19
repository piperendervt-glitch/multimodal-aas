# Phase 1.4d Stage 1 Exp 5b extended validation

**Question**: is Exp 5b's n=5 Cohen's d = +0.447 a true positive (ensemble voting over the Phase 1.4a improved topology transfers sdnd-proof) or the same small-sample artifact that Stage 2 Exp 2 extended diagnosed?

Methodology mirrors Stage 2 Exp 2 extended (commit d2fc14e): add 15 new seeds (powers of two after 1024), re-run Adaptive + Fixed using the same recipe (label-specific 6-weight update, sdnd-proof ×0.7 penalty, label-independent credit assignment, 0.5 threshold). No new LLM inference is required — every trial's predictions come from the committed Topology A / B_v3 / C_v3 fold JSONs and differ only in shuffle order and learned weights.

Seeds: [42, 137, 256, 512, 1024] (existing) + [2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432] (new).
Pool size for bootstrap: 20 trials × 11 second-half folds = 220 paired (Fixed, Adaptive) prediction pairs.

## Per-trial macro F1 (all 20 trials)

| Trial | Seed | origin | Fixed | Adaptive | Δ |
|---|---:|---|---:|---:|---:|
| 1 | 42 | existing | 0.817 | 0.817 | +0.000 |
| 2 | 137 | existing | 0.906 | 0.906 | +0.000 |
| 3 | 256 | existing | 0.764 | 0.818 | +0.055 |
| 4 | 512 | existing | 0.723 | 0.723 | +0.000 |
| 5 | 1024 | existing | 0.909 | 0.909 | +0.000 |
| 6 | 2048 | new | 0.857 | 0.929 | +0.071 |
| 7 | 4096 | new | 0.633 | 0.633 | +0.000 |
| 8 | 8192 | new | 0.762 | 0.829 | +0.067 |
| 9 | 16384 | new | 0.633 | 0.633 | +0.000 |
| 10 | 32768 | new | 0.909 | 0.909 | +0.000 |
| 11 | 65536 | new | 0.733 | 0.733 | +0.000 |
| 12 | 131072 | new | 0.718 | 0.718 | +0.000 |
| 13 | 262144 | new | 0.804 | 0.804 | +0.000 |
| 14 | 524288 | new | 0.764 | 0.764 | +0.000 |
| 15 | 1048576 | new | 0.667 | 0.667 | +0.000 |
| 16 | 2097152 | new | 0.909 | 0.909 | +0.000 |
| 17 | 4194304 | new | 0.718 | 0.785 | +0.067 |
| 18 | 8388608 | new | 0.780 | 0.780 | +0.000 |
| 19 | 16777216 | new | 0.804 | 0.804 | +0.000 |
| 20 | 33554432 | new | 0.785 | 0.785 | +0.000 |

## Δ sign distribution across 20 trials

| direction | count |
|---|---:|
| Δ > 0 | 4 |
| Δ = 0 | 16 |
| Δ < 0 | 0 |

Stage 2 Exp 2 extended reference: 2 positive / 12 zero / 6 negative. Exp 5b extended: **4 positive / 16 zero / 0 negative**.

## Statistical methods compared

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| trial t-test (Exp 5b original) | 5 | +0.011 | +0.447 | 0.3739 | [-0.019, +0.041] | No-Go |
| paired fold bootstrap (n=55) | 55 | +0.011 | +0.986 | 0.0001 | [+0.000, +0.038] | No-Go |
| **trial t-test (extended)** | **20** | +0.013 | **+0.485** | **0.0432** | [+0.000, +0.025] | **No-Go** |
| **paired fold bootstrap (extended)** | **220** | +0.013 | **+2.041** | **0.0001** | [+0.003, +0.026] | **Go (positive)** |

## Bootstrap Go criteria (extended n=220)

| Criterion | Value | Pass |
|---|---:|:-:|
| p-value < 0.05 | 0.0001 | Y |
| |Cohen's d| ≥ 0.8 | +2.041 | Y |
| 95% CI excludes 0 | [+0.003, +0.026] | Y |
| direction | positive | — |
| **Overall** | — | **Go (positive)** |

## Side-by-side with Stage 2 Exp 2 extended (same methodology)

| experiment | architecture | n=5 d (trial) | n=55 d (boot) | n=220 d (boot) | interpretation |
|---|---|---:|---:|---:|---|
| Stage 2 Exp 2 extended | single-LLM + info filter | +0.447 | +0.978 | -0.115 | small-sample artifact confirmed |
| **Stage 1 Exp 5b extended** | **ensemble voting (A + B_v3 + C_v3)** | +0.447 | +0.986 | **+2.041** | possible true-positive (different trajectory) |

## Adaptive final weights (mean across 20 trials)

| weight | Exp 5b (n=5) | Exp 5b extended (n=20) |
|---|---:|---:|
| A.sparrow | 0.341 | 0.370 |
| A.bulbul | 0.455 | 0.455 |
| B_v3.sparrow | 0.362 | 0.327 |
| B_v3.bulbul | 0.363 | 0.373 |
| C_v3.sparrow | 0.637 | 0.625 |
| C_v3.bulbul | 0.651 | 0.627 |

## Verdict

**Case B — possible true positive.** The extended bootstrap clears the full sdnd-proof 3-criterion gate in the positive direction, i.e. ensemble voting across A + B_v3 + C_v3 does transfer the sdnd-proof learning rule in a way the single-LLM substrate did not. Target C per-label routing is a defensible next step.

## Paper 1 implications

- Paper 1 can report a mixed-result story: **prompt-injection harms (Exp 1 negative Go)** + **ensemble-voting transfers weakly (Exp 5b extended positive Go)** + **single-LLM filter fails (Exp 2 extended No-Go)**. Target C still warranted.

## Output files

- `trials_summary_extended.json`
- `bootstrap_analysis.json`
- `graphs/delta_distribution.png`
- `graphs/cohens_d_comparison.png`
- `graphs/ci_across_n.png`
