# Phase 1.4d Stage 3 Ablation F-1 — 2-topology subset (A + B_v3 (pure audio + pure visual, fusion excluded))

Drops **C_v3 (temporal-sync fusion)** from Target C's ensemble and re-runs the weight + consensus-gate + multiplicative-integration pipeline on A + B_v3 (pure audio + pure visual, fusion excluded). Identical seeds, warm-up, and bootstrap to Target C so d falls on the same axis.

Topology subset in vote: A, B_v3 (n_topologies = 2).
Seeds: [42, 137, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432]. 20 trials × 11 second-half folds = n_pooled = 220.

## Per-trial macro F1

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.713 | 0.713 | +0.000 |
| 2 | 137 | 0.741 | 0.455 | -0.286 |
| 3 | 256 | 0.639 | 0.639 | +0.000 |
| 4 | 512 | 0.723 | 0.723 | +0.000 |
| 5 | 1024 | 0.710 | 0.710 | +0.000 |
| 6 | 2048 | 0.639 | 0.639 | +0.000 |
| 7 | 4096 | 0.697 | 0.697 | +0.000 |
| 8 | 8192 | 0.729 | 0.729 | +0.000 |
| 9 | 16384 | 0.697 | 0.697 | +0.000 |
| 10 | 32768 | 0.713 | 0.670 | -0.043 |
| 11 | 65536 | 0.643 | 0.643 | +0.000 |
| 12 | 131072 | 0.697 | 0.697 | +0.000 |
| 13 | 262144 | 0.722 | 0.722 | +0.000 |
| 14 | 524288 | 0.717 | 0.717 | +0.000 |
| 15 | 1048576 | 0.662 | 0.662 | +0.000 |
| 16 | 2097152 | 0.710 | 0.710 | +0.000 |
| 17 | 4194304 | 0.697 | 0.697 | +0.000 |
| 18 | 8388608 | 0.774 | 0.774 | +0.000 |
| 19 | 16777216 | 0.750 | 0.750 | +0.000 |
| 20 | 33554432 | 0.753 | 0.333 | -0.420 |

## Δ sign distribution across 20 trials

| direction | count |
|---|---:|
| Δ > 0 | 0 |
| Δ = 0 | 17 |
| Δ < 0 | 3 |

## Statistical analysis

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| This experiment — trial t-test | 20 | -0.037 | -0.339 | 0.1461 | [-0.089, +0.014] | No-Go |
| **This experiment — paired fold bootstrap** | **220** | -0.026 | **-3.052** | **0.0004** | [-0.045, -0.011] | **Go (negative)** |
| Exp 5b extended (3-topology, weight only) (ref) | 220 | +0.013 | +2.041 | 0.0001 | [+0.003, +0.026] | Go (positive) |
| Target C (3-topology, weight + consensus gate) (ref) | 220 | +0.044 | +4.014 | 0.0001 | [+0.024, +0.067] | Go (positive) |

## Bootstrap Go criteria (n=220)

| Criterion | Value | Pass |
|---|---:|:-:|
| p-value < 0.05 | 0.0004 | Y |
| |Cohen's d| ≥ 0.8 | -3.052 | Y |
| 95% CI excludes 0 | [-0.045, -0.011] | Y |
| direction | negative | — |
| **Overall** | — | **Go (negative)** |

## Final weights and gates (mean across 20 trials)

| label | topology | weight | gate | w × g |
|---|---|---:|---:|---:|
| sparrow | A | 0.370 | 0.244 | 0.090 |
| sparrow | B_v3 | 0.327 | 0.851 | 0.279 |
| bulbul | A | 0.455 | 0.268 | 0.122 |
| bulbul | B_v3 | 0.373 | 0.911 | 0.340 |

## Routing analysis — mean effective contribution per label

| label | top topology | share | runner-up | share |
|---|---|---:|---|---:|
| sparrow | B_v3 | 75.59% | A | 24.41% |
| bulbul | B_v3 | 73.59% | A | 26.41% |

## Interpretation

**Case: removed topology was critical.** Dropping C_v3 (temporal-sync fusion) collapses d to -3.052 (Target C = +4.014; loss ≈ +7.067). The two remaining topologies alone cannot carry the consensus-gate lift.

## Output files

- `trials_summary.json`
- `bootstrap_analysis.json`
