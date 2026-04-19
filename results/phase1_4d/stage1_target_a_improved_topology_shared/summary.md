# Phase 1.4d Stage 1 Experiment 5a — shared weight, improved topology

Same rule as Experiment 1 (shared scalar weight per topology, sdnd-proof 
rule ×0.7, threshold 0.5). The difference is the topology set:

    Experiment 1: Phase 1.3 extended A / B / C
    Experiment 5a: Phase 1.3 A + Phase 1.4a B_v3 + Phase 1.4a C_v3

The Fixed baseline on the improved topology set is recomputed (Fixed_new); the Adaptive vs Fixed gate applies to Fixed_new, not to Fixed_old.

## Per-trial macro F1

| Trial | Seed | Fixed_old (Exp 1) | Fixed_new (Exp 5a) | Exp 1 Adaptive | **Exp 5a Adaptive** | Exp 1 Δ | **Exp 5a Δ (vs Fixed_new)** |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.817 | 0.871 | **0.871** | -0.038 | **+0.055** |
| 2 | 137 | 0.906 | 0.906 | 0.906 | **0.906** | +0.000 | **+0.000** |
| 3 | 256 | 0.861 | 0.764 | 0.871 | **0.871** | +0.010 | **+0.108** |
| 4 | 512 | 0.771 | 0.723 | 0.723 | **0.723** | -0.048 | **+0.000** |
| 5 | 1024 | 0.861 | 0.909 | 0.817 | **0.909** | -0.044 | **+0.000** |

## Fixed baseline comparison (mean across 5 trials)

- Fixed_old (Phase 1.3 A/B/C): **0.862** (trials: ['0.909', '0.906', '0.861', '0.771', '0.861'])
- Fixed_new (Phase 1.3 A + B_v3 + C_v3): **0.824** (trials: ['0.817', '0.906', '0.764', '0.723', '0.909'])
- ΔFixed = **-0.038**

## Experiment 5a final Adaptive weights (per trial)

| Trial | Seed | w_A | w_B | w_C |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.150 | 0.188 | 0.539 |
| 2 | 137 | 0.097 | 0.034 | 0.593 |
| 3 | 256 | 0.301 | 0.106 | 0.525 |
| 4 | 512 | 0.102 | 0.188 | 0.545 |
| 5 | 1024 | 0.157 | 0.192 | 0.695 |
| mean | - | 0.162 | 0.142 | 0.579 |

## Statistical analysis (Exp 5a vs Fixed_new)

- Mean Δ: **+0.032**
- Std Δ: 0.048
- Paired t-test: t = 1.504, p = 0.2069
- Cohen's d: 0.673
- 95% CI: [-0.027, +0.092]

## Go judgment vs Experiment 1 (shared-weight comparison)

| Criterion | Threshold | Exp 1 | **Exp 5a** | Exp 5a pass |
|---|---|---:|---:|:-:|
| p-value | < 0.05 | 0.1177 | **0.2069** | N |
| Cohen's d | >= 0.8 | -0.889 | **0.673** | N |
| 95% CI lower | > 0 | -0.057 | **-0.027** | N |
| **Overall** | all pass | **No-Go** | **No-Go** | |

## Caveats

- Fixed_new uses the improved topology predictions with equal weights. Every shift in Fixed reflects the B_v3 + C_v3 upgrade, not the weight-learning rule.
- n=5 trials over shuffle-only variation; the paired t-test does not generalise to dataset sampling.

## Output files

- `trials_summary.json`
- `statistical_analysis.json`
- `graphs/weight_trajectory.png`
- `graphs/f1_comparison_vs_exp1.png`
