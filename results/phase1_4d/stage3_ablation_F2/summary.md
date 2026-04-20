# Phase 1.4d Stage 3 Ablation F-2 — 2-topology subset (A + C_v3 (pure audio + temporal-sync fusion, pure-visual excluded))

Drops **B_v3 (pure-visual, bbox v3 prompt)** from Target C's ensemble and re-runs the weight + consensus-gate + multiplicative-integration pipeline on A + C_v3 (pure audio + temporal-sync fusion, pure-visual excluded). Identical seeds, warm-up, and bootstrap to Target C so d falls on the same axis.

Topology subset in vote: A, C_v3 (n_topologies = 2).
Seeds: [42, 137, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432]. 20 trials × 11 second-half folds = n_pooled = 220.

## Per-trial macro F1

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.871 | 0.871 | +0.000 |
| 2 | 137 | 0.906 | 0.906 | +0.000 |
| 3 | 256 | 0.871 | 0.871 | +0.000 |
| 4 | 512 | 0.723 | 0.723 | +0.000 |
| 5 | 1024 | 0.909 | 0.909 | +0.000 |
| 6 | 2048 | 0.967 | 0.967 | +0.000 |
| 7 | 4096 | 0.748 | 0.748 | +0.000 |
| 8 | 8192 | 0.829 | 0.829 | +0.000 |
| 9 | 16384 | 0.748 | 0.748 | +0.000 |
| 10 | 32768 | 0.955 | 0.955 | +0.000 |
| 11 | 65536 | 0.771 | 0.771 | +0.000 |
| 12 | 131072 | 0.829 | 0.829 | +0.000 |
| 13 | 262144 | 0.842 | 0.842 | +0.000 |
| 14 | 524288 | 0.871 | 0.871 | +0.000 |
| 15 | 1048576 | 0.785 | 0.785 | +0.000 |
| 16 | 2097152 | 0.909 | 0.909 | +0.000 |
| 17 | 4194304 | 0.829 | 0.829 | +0.000 |
| 18 | 8388608 | 0.780 | 0.780 | +0.000 |
| 19 | 16777216 | 0.804 | 0.804 | +0.000 |
| 20 | 33554432 | 0.785 | 0.785 | +0.000 |

## Δ sign distribution across 20 trials

| direction | count |
|---|---:|
| Δ > 0 | 0 |
| Δ = 0 | 20 |
| Δ < 0 | 0 |

## Statistical analysis

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| This experiment — trial t-test | 20 | +0.000 | +0.000 | nan | [+0.000, +0.000] | No-Go |
| **This experiment — paired fold bootstrap** | **220** | +0.000 | **+0.000** | **0.0001** | [+0.000, +0.000] | **No-Go** |
| Exp 5b extended (3-topology, weight only) (ref) | 220 | +0.013 | +2.041 | 0.0001 | [+0.003, +0.026] | Go (positive) |
| Target C (3-topology, weight + consensus gate) (ref) | 220 | +0.044 | +4.014 | 0.0001 | [+0.024, +0.067] | Go (positive) |

## Bootstrap Go criteria (n=220)

| Criterion | Value | Pass |
|---|---:|:-:|
| p-value < 0.05 | 0.0001 | Y |
| |Cohen's d| ≥ 0.8 | +0.000 | N |
| 95% CI excludes 0 | [+0.000, +0.000] | N |
| direction | zero | — |
| **Overall** | — | **No-Go** |

## Final weights and gates (mean across 20 trials)

| label | topology | weight | gate | w × g |
|---|---|---:|---:|---:|
| sparrow | A | 0.370 | 0.312 | 0.115 |
| sparrow | C_v3 | 0.625 | 0.951 | 0.594 |
| bulbul | A | 0.455 | 0.695 | 0.316 |
| bulbul | C_v3 | 0.627 | 0.951 | 0.596 |

## Routing analysis — mean effective contribution per label

| label | top topology | share | runner-up | share |
|---|---|---:|---|---:|
| sparrow | C_v3 | 83.72% | A | 16.28% |
| bulbul | C_v3 | 65.37% | A | 34.63% |

## Interpretation

**Case: removed topology was critical.** Dropping B_v3 (pure-visual, bbox v3 prompt) collapses d to +0.000 (Target C = +4.014; loss ≈ +4.014).

## Output files

- `trials_summary.json`
- `bootstrap_analysis.json`
