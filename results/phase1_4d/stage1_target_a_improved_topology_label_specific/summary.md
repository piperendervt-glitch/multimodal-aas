# Phase 1.4d Stage 1 Experiment 5b — label-specific, improved topology

Same rule as Experiment 3 (6 weights = 3 topologies × 2 labels, sdnd-proof 
rule ×0.7, threshold 0.5). The difference is the topology set:

    Experiment 3:  Phase 1.3 extended A / B / C
    Experiment 5b: Phase 1.3 A + Phase 1.4a B_v3 + Phase 1.4a C_v3

## Per-trial macro F1

| Trial | Seed | Fixed_old (Exp 3) | Fixed_new (Exp 5b) | Exp 3 Adaptive | **Exp 5b Adaptive** | Exp 3 Δ | **Exp 5b Δ (vs Fixed_new)** |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.817 | 0.871 | **0.817** | -0.038 | **+0.000** |
| 2 | 137 | 0.906 | 0.906 | 0.906 | **0.906** | +0.000 | **+0.000** |
| 3 | 256 | 0.861 | 0.764 | 0.917 | **0.818** | +0.056 | **+0.055** |
| 4 | 512 | 0.771 | 0.723 | 0.723 | **0.723** | -0.048 | **+0.000** |
| 5 | 1024 | 0.861 | 0.909 | 0.817 | **0.909** | -0.044 | **+0.000** |

## Fixed baseline comparison (mean across 5 trials)

- Fixed_old (Phase 1.3 A/B/C): **0.862**
- Fixed_new (Phase 1.3 A + B_v3 + C_v3): **0.824**
- ΔFixed = **-0.038**

## Experiment 5b final Adaptive weights (per trial)

| Trial | Seed | A.s | A.b | B.s | B.b | C.s | C.b |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 42 | 0.385 | 0.410 | 0.435 | 0.350 | 0.558 | 0.643 |
| 2 | 137 | 0.259 | 0.510 | 0.364 | 0.239 | 0.603 | 0.614 |
| 3 | 256 | 0.396 | 0.445 | 0.183 | 0.462 | 0.736 | 0.559 |
| 4 | 512 | 0.300 | 0.461 | 0.415 | 0.404 | 0.563 | 0.727 |
| 5 | 1024 | 0.363 | 0.447 | 0.411 | 0.357 | 0.722 | 0.709 |
| mean | - | 0.341 | 0.455 | 0.362 | 0.363 | 0.637 | 0.651 |

## Mean label-specific weight comparison (Exp 3 vs Exp 5b)

| Topology | Exp 3 sparrow | Exp 3 bulbul | Exp 5b sparrow | Exp 5b bulbul | Exp 3 \|Δ\| | Exp 5b \|Δ\| |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.341 | 0.455 | 0.341 | 0.455 | 0.114 | 0.114 |
| B (→B_v3) | 0.255 | 0.525 | 0.362 | 0.363 | 0.270 | 0.001 |
| C (→C_v3) | 0.588 | 0.600 | 0.637 | 0.651 | 0.013 | 0.014 |

## Statistical analysis (Exp 5b vs Fixed_new)

- Mean Δ: **+0.011**
- Std Δ: 0.024
- Paired t-test: t = 1.000, p = 0.3739
- Cohen's d: 0.447
- 95% CI: [-0.019, +0.041]

## Go judgment vs Experiment 3 (label-specific comparison)

| Criterion | Threshold | Exp 3 | **Exp 5b** | Exp 5b pass |
|---|---|---:|---:|:-:|
| p-value | < 0.05 | 0.4894 | **0.3739** | N |
| Cohen's d | >= 0.8 | -0.340 | **0.447** | N |
| 95% CI lower | > 0 | -0.069 | **-0.019** | N |
| **Overall** | all pass | **No-Go** | **No-Go** | |

## Caveats

- B_v3 was specifically designed to reduce the sparrow / bulbul split. Any residual split in Exp 5b is what the flow_weight learning still finds on top of that engineering change.
- n=5 trials (shuffle-only variation).

## Output files

- `trials_summary.json`
- `statistical_analysis.json`
- `graphs/weight_trajectory_label_specific.png`
- `graphs/label_weight_comparison_exp3_exp5b.png`
