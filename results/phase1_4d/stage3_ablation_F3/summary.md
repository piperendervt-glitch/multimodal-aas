# Phase 1.4d Stage 3 Ablation F-3 — 2-topology subset (B_v3 + C_v3 (pure visual + temporal-sync fusion, pure-audio excluded))

Drops **A (pure-audio, BirdNET → LLM)** from Target C's ensemble and re-runs the weight + consensus-gate + multiplicative-integration pipeline on B_v3 + C_v3 (pure visual + temporal-sync fusion, pure-audio excluded). Identical seeds, warm-up, and bootstrap to Target C so d falls on the same axis.

Topology subset in vote: B_v3, C_v3 (n_topologies = 2).
Seeds: [42, 137, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432]. 20 trials × 11 second-half folds = n_pooled = 220.

## Per-trial macro F1

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.753 | 0.729 | -0.024 |
| 2 | 137 | 0.741 | 0.774 | +0.033 |
| 3 | 256 | 0.722 | 0.639 | -0.084 |
| 4 | 512 | 0.723 | 0.736 | +0.013 |
| 5 | 1024 | 0.710 | 0.710 | +0.000 |
| 6 | 2048 | 0.729 | 0.639 | -0.090 |
| 7 | 4096 | 0.778 | 0.753 | -0.026 |
| 8 | 8192 | 0.778 | 0.729 | -0.049 |
| 9 | 16384 | 0.778 | 0.753 | -0.026 |
| 10 | 32768 | 0.753 | 0.767 | +0.014 |
| 11 | 65536 | 0.672 | 0.754 | +0.082 |
| 12 | 131072 | 0.778 | 0.722 | -0.056 |
| 13 | 262144 | 0.754 | 0.764 | +0.010 |
| 14 | 524288 | 0.806 | 0.807 | +0.002 |
| 15 | 1048576 | 0.754 | 0.689 | -0.065 |
| 16 | 2097152 | 0.710 | 0.807 | +0.097 |
| 17 | 4194304 | 0.778 | 0.789 | +0.011 |
| 18 | 8388608 | 0.774 | 0.753 | -0.021 |
| 19 | 16777216 | 0.750 | 0.783 | +0.033 |
| 20 | 33554432 | 0.753 | 0.785 | +0.032 |

## Δ sign distribution across 20 trials

| direction | count |
|---|---:|
| Δ > 0 | 10 |
| Δ = 0 | 1 |
| Δ < 0 | 9 |

## Statistical analysis

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| This experiment — trial t-test | 20 | -0.006 | -0.115 | 0.6137 | [-0.029, +0.017] | No-Go |
| **This experiment — paired fold bootstrap** | **220** | -0.008 | **-0.575** | **0.5718** | [-0.037, +0.019] | **No-Go** |
| Exp 5b extended (3-topology, weight only) (ref) | 220 | +0.013 | +2.041 | 0.0001 | [+0.003, +0.026] | Go (positive) |
| Target C (3-topology, weight + consensus gate) (ref) | 220 | +0.044 | +4.014 | 0.0001 | [+0.024, +0.067] | Go (positive) |

## Bootstrap Go criteria (n=220)

| Criterion | Value | Pass |
|---|---:|:-:|
| p-value < 0.05 | 0.5718 | N |
| |Cohen's d| ≥ 0.8 | -0.575 | N |
| 95% CI excludes 0 | [-0.037, +0.019] | N |
| direction | negative | — |
| **Overall** | — | **No-Go** |

## Final weights and gates (mean across 20 trials)

| label | topology | weight | gate | w × g |
|---|---|---:|---:|---:|
| sparrow | B_v3 | 0.327 | 0.551 | 0.181 |
| sparrow | C_v3 | 0.625 | 0.762 | 0.476 |
| bulbul | B_v3 | 0.373 | 0.911 | 0.340 |
| bulbul | C_v3 | 0.627 | 0.281 | 0.176 |

## Routing analysis — mean effective contribution per label

| label | top topology | share | runner-up | share |
|---|---|---:|---|---:|
| sparrow | C_v3 | 72.49% | B_v3 | 27.51% |
| bulbul | B_v3 | 65.84% | C_v3 | 34.16% |

## Interpretation

**Case: removed topology was critical.** Dropping A (pure-audio, BirdNET → LLM) collapses d to -0.575 (Target C = +4.014; loss ≈ +4.589).

## Output files

- `trials_summary.json`
- `bootstrap_analysis.json`
