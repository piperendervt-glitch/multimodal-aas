# Phase 1.4d Stage 1 Experiment 3 — label-specific flow_weight

Weight structure changed from 3 scalars (one per topology) to 6 scalars 
(one per **topology × label** pair). The sdnd-proof update rule is restored to 
its original form (×0.7 penalty) but applied *per label*, so a topology that 
is strong on bulbul but weak on sparrow can lose its sparrow-weight without 
giving up its bulbul-weight.

Same design as Exp 1 / Exp 2 otherwise: 5 trials on seeds [42, 137, 256, 512, 1024], clean 22 folds (11 self + 11 YouTube Tier A/B/B'), first 11 folds warm-up, last 11 folds evaluation. Predictions reused from `results/phase1_3_extended/`.

## Per-trial macro F1 across 3 experiments

| Trial | Seed | Fixed | Adaptive Exp 1 | Adaptive Exp 2 | Adaptive Exp 3 | Exp 1 Δ | Exp 2 Δ | Exp 3 Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.871 | 0.871 | 0.871 | -0.038 | -0.038 | -0.038 |
| 2 | 137 | 0.906 | 0.906 | 0.906 | 0.906 | +0.000 | +0.000 | +0.000 |
| 3 | 256 | 0.861 | 0.871 | 0.861 | 0.917 | +0.010 | +0.000 | +0.056 |
| 4 | 512 | 0.771 | 0.723 | 0.771 | 0.723 | -0.048 | +0.000 | -0.048 |
| 5 | 1024 | 0.861 | 0.817 | 0.861 | 0.817 | -0.044 | +0.000 | -0.044 |

## Per-trial F1 breakdown (Experiment 3)

| Trial | Seed | Fixed sparrow | Fixed bulbul | Adaptive sparrow | Adaptive bulbul |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.909 | 0.909 | 0.833 | 0.909 |
| 2 | 137 | 0.923 | 0.889 | 0.923 | 0.889 |
| 3 | 256 | 0.889 | 0.833 | 1.000 | 0.833 |
| 4 | 512 | 0.667 | 0.875 | 0.571 | 0.875 |
| 5 | 1024 | 0.889 | 0.833 | 0.800 | 0.833 |

## Experiment 3 final weights (per trial)

| Trial | Seed | A.sparrow | A.bulbul | B.sparrow | B.bulbul | C.sparrow | C.bulbul |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 42 | 0.385 | 0.410 | 0.357 | 0.539 | 0.532 | 0.615 |
| 2 | 137 | 0.259 | 0.510 | 0.288 | 0.597 | 0.571 | 0.580 |
| 3 | 256 | 0.396 | 0.445 | 0.210 | 0.549 | 0.726 | 0.549 |
| 4 | 512 | 0.300 | 0.461 | 0.188 | 0.486 | 0.524 | 0.682 |
| 5 | 1024 | 0.363 | 0.447 | 0.234 | 0.455 | 0.587 | 0.577 |
| mean | - | 0.341 | 0.455 | 0.255 | 0.525 | 0.588 | 0.600 |

## Mean final weights (5-trial average)

|          | sparrow | bulbul |
|---|---:|---:|
| Topology A | 0.341 | 0.455 |
| Topology B | 0.255 | 0.525 |
| Topology C | 0.588 | 0.600 |

## Experiment 3 statistical analysis

- Mean Δ: **-0.015**
- Std Δ: 0.044
- Paired t-test: t = -0.760, p = 0.4894
- Cohen's d (paired): -0.340
- 95% CI (paired): [-0.069, +0.039]

## Go judgment (sdnd-proof 3 criteria)

| Criterion | Threshold | Exp 1 | Exp 2 | Exp 3 | Exp 3 pass |
|---|---|---:|---:|---:|:-:|
| p-value | < 0.05 | 0.1177 | 0.3739 | 0.4894 | N |
| Cohen's d | >= 0.8 | -0.889 | -0.447 | -0.340 | N |
| 95% CI lower | > 0 | -0.057 | -0.029 | -0.069 | N |
| **Overall** | all pass | **No-Go** | **No-Go** | **No-Go** | |

## Label-specific weight discussion

- Topology A: sparrow=0.341 vs bulbul=0.455 — meaningful split favouring **bulbul** (|Δ|=0.114). Label independence detected a per-label strength difference that the shared-weight rule could not express.
- Topology B: sparrow=0.255 vs bulbul=0.525 — meaningful split favouring **bulbul** (|Δ|=0.270). Label independence detected a per-label strength difference that the shared-weight rule could not express.
- Topology C: sparrow=0.588 vs bulbul=0.600 — no meaningful per-label split (|Δ|<0.10).

**No-Go**: label independence preserves per-label weight structure but does not cross the 3-criterion bar on n=5 trials. The label-specific split may still be a meaningful diagnostic — see the weight table above for which topologies gain a per-label identity.

## Caveats

- 5 trials over the same 22 folds measure sensitivity to ordering, not dataset sampling. Bootstrap of the fold set is needed for a broader claim.
- Per-label independence doubles the number of updates per fold (6 updates vs 3). With ×0.7 on failures, the 6-weight system decays faster toward zero on whatever label the topology gets wrong frequently.
- The 0.5 decision threshold still applies. If none of the 6 weights grow ≈ >0.5·total for their own label, the per-label majority is purely decided by the count of 1s — same as Fixed.

## Output files

- `trials_summary.json`
- `statistical_analysis.json`
- `graphs/weight_trajectory_label_specific.png`
- `graphs/label_specific_comparison.png`
- `graphs/f1_comparison_3exp.png`
