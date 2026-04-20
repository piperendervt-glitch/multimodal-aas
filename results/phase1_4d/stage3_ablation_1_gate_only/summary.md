# Phase 1.4d Stage 3 Ablation 1 — Gate only (Weight frozen at 0.5)

Isolates the gate mechanism's standalone effect. Same substrate as Target C (ensemble voting over A + B_v3 + C_v3, 6 weights + 6 gates, effective contribution = w × g), but **weights are held at 0.5** and only the six gates learn — using the same consensus-agreement reward as Target C (gate success iff topology prediction == ensemble final prediction). Under this configuration the effective vote is 0.5 × g, so the label-routing knob is entirely in the gate.

Seeds: [42, 137, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432]. 20 trials × 11 second-half folds = n_pooled = 220.

## Per-trial macro F1

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.817 | 0.750 | -0.067 |
| 2 | 137 | 0.906 | 0.906 | +0.000 |
| 3 | 256 | 0.764 | 0.871 | +0.108 |
| 4 | 512 | 0.723 | 0.723 | +0.000 |
| 5 | 1024 | 0.909 | 0.909 | +0.000 |
| 6 | 2048 | 0.857 | 0.929 | +0.071 |
| 7 | 4096 | 0.633 | 0.748 | +0.115 |
| 8 | 8192 | 0.762 | 0.829 | +0.067 |
| 9 | 16384 | 0.633 | 0.636 | +0.003 |
| 10 | 32768 | 0.909 | 0.909 | +0.000 |
| 11 | 65536 | 0.733 | 0.733 | +0.000 |
| 12 | 131072 | 0.718 | 0.785 | +0.067 |
| 13 | 262144 | 0.804 | 0.760 | -0.044 |
| 14 | 524288 | 0.764 | 0.818 | +0.055 |
| 15 | 1048576 | 0.667 | 0.667 | +0.000 |
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
| Ablation 1 trial t-test | 20 | +0.022 | +0.464 | 0.0517 | [-0.000, +0.044] | No-Go |
| **Ablation 1 paired fold bootstrap** | **220** | +0.022 | **+2.217** | **0.0174** | [+0.004, +0.044] | **Go (positive)** |
| Target C paired fold bootstrap (ref) | 220 | +0.044 | +4.014 | 0.0001 | [+0.024, +0.067] | Go (positive) |
| Exp 5b extended paired fold bootstrap (ref) | 220 | +0.013 | +2.041 | 0.0001 | [+0.003, +0.026] | Go (positive) |

## Bootstrap Go criteria (n=220)

| Criterion | Value | Pass |
|---|---:|:-:|
| p-value < 0.05 | 0.0174 | Y |
| |Cohen's d| ≥ 0.8 | +2.217 | Y |
| 95% CI excludes 0 | [+0.004, +0.044] | Y |
| direction | positive | — |
| **Overall** | — | **Go (positive)** |

## Final gates (mean across 20 trials)

| label | topology | gate | effective (0.5 × g) |
|---|---|---:|---:|
| sparrow | A | 0.316 | 0.158 |
| sparrow | B_v3 | 0.399 | 0.200 |
| sparrow | C_v3 | 0.927 | 0.463 |
| bulbul | A | 0.828 | 0.414 |
| bulbul | B_v3 | 0.263 | 0.132 |
| bulbul | C_v3 | 0.805 | 0.403 |

## Routing analysis — mean effective contribution per label

| label | most-routed topology | share | second | third |
|---|---|---:|---|---|
| sparrow | C_v3 | 56.43% | B_v3 (24.33%) | A (19.24%) |
| bulbul | A | 43.65% | C_v3 (42.47%) | B_v3 (13.87%) |

## Interpretation

**Case B-lower — weight carries more.** Gate-only d (+2.217) sits below Exp 5b extended d (+2.041), so the label-specific weight alone beats the gate alone. The gate's contribution on top of the weight (Target C d=+4.014) is real but additive, not the main driver.

## Output files

- `trials_summary.json`
- `bootstrap_analysis.json`
- `graphs/gate_trajectory.png`
- `graphs/cohens_d_comparison.png`
