# Phase 1.4d Stage 3 Ablation 5 — Ground-truth based gate update

Same substrate as Target C (ensemble voting over A + B_v3 + C_v3, 6 weights + 6 gates, effective vote = w × g), same weight update (GT-driven sdnd-proof), but the **gate update signal is swapped** from consensus-agreement to ground truth:

    Target C:   g_ok = (topology_pred == ensemble_final_pred)
    Ablation 5: g_ok = (topology_pred == ground_truth)      ← same as the weight

Because both variables now share identical update rule and signal starting from w = g = 0.5, the gate collapses onto the weight trajectory (w ≡ g along every run) and the effective vote reduces to w² · pred. This is the explicit test of whether Target C's novelty lives in the *consensus signal* or merely in having a second multiplicative knob.

Seeds: [42, 137, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432]. 20 trials × 11 second-half folds = n_pooled = 220.

## Per-trial macro F1

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.817 | 0.817 | +0.000 |
| 2 | 137 | 0.906 | 0.906 | +0.000 |
| 3 | 256 | 0.764 | 0.833 | +0.070 |
| 4 | 512 | 0.723 | 0.604 | -0.119 |
| 5 | 1024 | 0.909 | 0.909 | +0.000 |
| 6 | 2048 | 0.857 | 0.929 | +0.071 |
| 7 | 4096 | 0.633 | 0.697 | +0.064 |
| 8 | 8192 | 0.762 | 0.829 | +0.067 |
| 9 | 16384 | 0.633 | 0.633 | +0.000 |
| 10 | 32768 | 0.909 | 0.871 | -0.038 |
| 11 | 65536 | 0.733 | 0.771 | +0.037 |
| 12 | 131072 | 0.718 | 0.718 | +0.000 |
| 13 | 262144 | 0.804 | 0.804 | +0.000 |
| 14 | 524288 | 0.764 | 0.871 | +0.108 |
| 15 | 1048576 | 0.667 | 0.718 | +0.051 |
| 16 | 2097152 | 0.909 | 0.909 | +0.000 |
| 17 | 4194304 | 0.718 | 0.785 | +0.067 |
| 18 | 8388608 | 0.780 | 0.780 | +0.000 |
| 19 | 16777216 | 0.804 | 0.804 | +0.000 |
| 20 | 33554432 | 0.785 | 0.785 | +0.000 |

## Δ sign distribution across 20 trials

| direction | count |
|---|---:|
| Δ > 0 | 8 |
| Δ = 0 | 10 |
| Δ < 0 | 2 |

## Statistical analysis

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| Ablation 5 trial t-test | 20 | +0.019 | +0.380 | 0.1059 | [-0.004, +0.042] | No-Go |
| **Ablation 5 paired fold bootstrap** | **220** | +0.021 | **+2.042** | **0.0350** | [+0.001, +0.042] | **Go (positive)** |
| Target C paired fold bootstrap (ref) | 220 | +0.044 | +4.014 | 0.0001 | [+0.024, +0.067] | Go (positive) |
| Ablation 1 paired fold bootstrap (ref) | 220 | +0.022 | +2.217 | 0.0174 | [+0.004, +0.044] | Go (positive) |
| Exp 5b extended paired fold bootstrap (ref) | 220 | +0.013 | +2.041 | 0.0001 | [+0.003, +0.026] | Go (positive) |

## Bootstrap Go criteria (n=220)

| Criterion | Value | Pass |
|---|---:|:-:|
| p-value < 0.05 | 0.0350 | Y |
| |Cohen's d| ≥ 0.8 | +2.042 | Y |
| 95% CI excludes 0 | [+0.001, +0.042] | Y |
| direction | positive | — |
| **Overall** | — | **Go (positive)** |

## Final weights and gates (mean across 20 trials)

| label | topology | weight | gate | w × g | |w − g| check |
|---|---|---:|---:|---:|---:|
| sparrow | A | 0.370 | 0.370 | 0.137 | 0 |
| sparrow | B_v3 | 0.327 | 0.327 | 0.107 | 0 |
| sparrow | C_v3 | 0.625 | 0.625 | 0.390 | 0 |
| bulbul | A | 0.455 | 0.455 | 0.207 | 0 |
| bulbul | B_v3 | 0.373 | 0.373 | 0.139 | 0 |
| bulbul | C_v3 | 0.627 | 0.627 | 0.393 | 0 |

Max |w − g| across all (trial, topology, label) cells: **0**. With identical initialisation and identical update signal this should be numerically zero — the gate collapses onto the weight trajectory.

## Interpretation

**Case A — consensus signal IS the novelty.** Swapping the gate to a ground-truth signal drops Cohen's d from Target C's +4.014 down to +2.042, comparable to or below Exp 5b extended (+2.041). The consensus-agreement reward is load-bearing; a second GT-driven variable is redundant with the weight and the w × g sharpening only helps when the second variable encodes a *different* signal. This is the primary novelty to claim in Paper 1 Chapter 5.

## Output files

- `trials_summary.json`
- `bootstrap_analysis.json`
- `graphs/weight_gate_trajectory.png`
- `graphs/cohens_d_comparison.png`
