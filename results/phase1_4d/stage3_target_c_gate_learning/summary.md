# Phase 1.4d Stage 3 Target C — per-label routing with gate learning

Ensemble voting over Topology A + B_v3 + C_v3 with **six weights** (sparrow / bulbul × A / B_v3 / C_v3) AND **six gates** on top. Effective contribution of each topology-label pair is `w × g`. Weights are updated against ground truth (like Exp 5b); gates are updated against the ensemble's own final prediction, i.e. they reward topologies that agree with the current consensus.

Seeds: [42, 137, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432]. 20 trials × 11 second-half folds = n_pooled = 220.
No new LLM inference: every per-topology per-fold prediction comes from the committed Phase 1.3 / Phase 1.4a fold JSONs.

## Per-trial macro F1

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.817 | 0.817 | +0.000 |
| 2 | 137 | 0.906 | 0.906 | +0.000 |
| 3 | 256 | 0.764 | 0.871 | +0.108 |
| 4 | 512 | 0.723 | 0.723 | +0.000 |
| 5 | 1024 | 0.909 | 0.909 | +0.000 |
| 6 | 2048 | 0.857 | 0.929 | +0.071 |
| 7 | 4096 | 0.633 | 0.748 | +0.115 |
| 8 | 8192 | 0.762 | 0.829 | +0.067 |
| 9 | 16384 | 0.633 | 0.697 | +0.064 |
| 10 | 32768 | 0.909 | 0.909 | +0.000 |
| 11 | 65536 | 0.733 | 0.771 | +0.037 |
| 12 | 131072 | 0.718 | 0.829 | +0.111 |
| 13 | 262144 | 0.804 | 0.804 | +0.000 |
| 14 | 524288 | 0.764 | 0.871 | +0.108 |
| 15 | 1048576 | 0.667 | 0.785 | +0.118 |
| 16 | 2097152 | 0.909 | 0.909 | +0.000 |
| 17 | 4194304 | 0.718 | 0.829 | +0.111 |
| 18 | 8388608 | 0.780 | 0.780 | +0.000 |
| 19 | 16777216 | 0.804 | 0.804 | +0.000 |
| 20 | 33554432 | 0.785 | 0.785 | +0.000 |

## Δ sign distribution across 20 trials

| direction | count |
|---|---:|
| Δ > 0 | 10 |
| Δ = 0 | 10 |
| Δ < 0 | 0 |

Exp 5b extended reference: 4 positive / 16 zero / 0 negative. Target C: **10 positive / 10 zero / 0 negative**.

## Statistical analysis

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| Target C trial t-test | 20 | +0.045 | +0.899 | 0.0007 | [+0.022, +0.069] | Go |
| **Target C paired fold bootstrap** | **220** | +0.044 | **+4.014** | **0.0001** | [+0.024, +0.067] | **Go (positive)** |
| Exp 5b extended trial t-test (ref) | 20 | +0.013 | +0.485 | 0.0432 | [+0.000, +0.025] | No-Go |
| Exp 5b extended paired fold bootstrap (ref) | 220 | +0.013 | +2.041 | 0.0001 | [+0.003, +0.026] | Go (positive) |

## Bootstrap Go criteria (extended n=220)

| Criterion | Value | Pass |
|---|---:|:-:|
| p-value < 0.05 | 0.0001 | Y |
| |Cohen's d| ≥ 0.8 | +4.014 | Y |
| 95% CI excludes 0 | [+0.024, +0.067] | Y |
| direction | positive | — |
| **Overall** | — | **Go (positive)** |

## Final weights and gates (mean across 20 trials)

| label | topology | weight | gate | w × g |
|---|---|---:|---:|---:|
| sparrow | A | 0.370 | 0.314 | 0.116 |
| sparrow | B_v3 | 0.327 | 0.396 | 0.130 |
| sparrow | C_v3 | 0.625 | 0.938 | 0.586 |
| bulbul | A | 0.455 | 0.746 | 0.339 |
| bulbul | B_v3 | 0.373 | 0.260 | 0.097 |
| bulbul | C_v3 | 0.627 | 0.887 | 0.557 |

## Routing analysis — mean effective contribution per label

| label | most-routed topology | effective share | second | third |
|---|---|---:|---|---|
| sparrow | C_v3 | 70.45% | B_v3 (15.59%) | A (13.96%) |
| bulbul | C_v3 | 56.07% | A (34.16%) | B_v3 (9.77%) |

## Comparison vs Stage 1 Exp 5b extended (ensemble voting without gates)

| experiment | weight structure | vote mixing | Cohen's d (n=220) | verdict |
|---|---|---|---:|---|
| Exp 5b extended | 6 weights (label-specific) | Σ(w · pred) / Σw | +2.041 | Go (positive) |
| **Target C** | **6 weights + 6 gates** | **Σ(w·g · pred) / Σ(w·g)** | **+4.014** | **Go (positive)** |

## Verdict

**Case A — gates helped.** Target C clears the 3-criterion gate and Cohen's d exceeds Exp 5b extended. Explicit routing is a genuine addition on top of label-specific weights.

## Output files

- `trials_summary.json`
- `bootstrap_analysis.json`
- `graphs/weight_gate_trajectory.png`
- `graphs/routing_visualization.png`
- `graphs/cohens_d_comparison.png`
