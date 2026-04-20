# Phase 1.4d Stage 3 Ablation E — single-node degenerate ensemble (C_v3)

Ensemble-voting framework applied to a **single topology** (C_v3 only). With one node in the vote the multiplicative `w × g` mixing reduces to `pred` identically, so fixed and adaptive arms emit the same prediction on every fold by construction. The observation is whether the actual bootstrap behaves as the analytic prediction demands — d ≈ 0, CI tight around 0.

Topology subset in vote: C_v3 (n_topologies = 1).
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
| Stage 2 Exp 2 extended (single-LLM, silent filter) (ref) | 220 | -0.001 | -0.115 | 0.8768 | [-0.023, +0.022] | No-Go |
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

## Interpretation

**Case A — architecture boundary confirmed.** With one topology in the vote, Fixed and Adaptive arms produce identical predictions on every fold (Δ = 0 exactly, Cohen's d ≈ 0, CI clamped to zero). The ensemble code framework alone — weight + gate + consensus signal + multiplicative integration — carries zero lift when topology diversity is absent. Target C's d=+4.014 therefore lives in the diversity across A / B_v3 / C_v3, not in the code structure that mixes them. Paper 1 Chapter 1's 'Ensemble voting works, Single-LLM does not' claim survives the strongest null check available.

## Diagnostic — Fixed vs Adaptive prediction equality

Across 440 (trial, fold) pairs, Fixed and Adaptive emitted **different** predictions in **0** cases.

## Output files

- `trials_summary.json`
- `bootstrap_analysis.json`
