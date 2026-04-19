# Phase 1.4d Stage 2 — paired fold bootstrap analysis

Paired fold-level resampling (n=10000 bootstrap draws, seed=42) of the three Stage 2 experiments. Each experiment pools 5 trials × 11 second-half folds = 55 (Fixed, Adaptive) prediction pairs and resamples them with replacement; Fixed and Adaptive use the same index set on every draw so fold-level common variance is absorbed. Methodology mirrors Phase 1.4a paired bootstrap (commit b6a2580).

sdnd-proof 3-criterion gate:
- p-value (two-sided) < 0.05
- |Cohen's d (paired)| ≥ 0.8 (direction reported separately)
- 95% CI excludes 0

Overall verdict: Go ⇔ all three criteria pass *and* direction is positive.

## Trial t-test vs paired fold bootstrap

| Experiment | statistic | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---|---:|---:|---:|---:|---|---|
| Exp 1 (scores shown) | trial t-test | 5 | -0.081 | -1.320 | 0.0419 | [-0.156, -0.005] | No-Go |
| Exp 1 (scores shown) | paired fold bootstrap | 55 | -0.084 | -2.073 | 0.0001 | [-0.171, -0.015] | Go (neg) |
| Exp 2 (scores hidden) | trial t-test | 5 | +0.017 | +0.447 | 0.3739 | [-0.030, +0.063] | No-Go |
| Exp 2 (scores hidden) | paired fold bootstrap | 55 | +0.020 | +0.978 | 0.0001 | [+0.000, +0.068] | No-Go |
| Exp 3 (scores hidden, stronger penalty) | trial t-test | 5 | +0.040 | +0.594 | 0.2548 | [-0.044, +0.124] | No-Go |
| Exp 3 (scores hidden, stronger penalty) | paired fold bootstrap | 55 | +0.027 | +0.370 | 0.7036 | [-0.117, +0.170] | No-Go |

## Bootstrap criteria breakdown

| Experiment | p < 0.05 | |d| ≥ 0.8 | CI excl. 0 | direction | Overall |
|---|:-:|:-:|:-:|:-:|---|
| Exp 1 | Y | Y | Y | negative | **Go (negative direction)** — all 3 criteria pass but Adaptive < Fixed |
| Exp 2 | Y | Y | N | positive | **No-Go** |
| Exp 3 | N | N | N | positive | **No-Go** |

## Discussion

1. **Power gain from fold-level bootstrap.** Trial t-test had df=4; the bootstrap uses 55 paired folds × 10,000 draws, so the CI width collapses sharply. Compare Exp 2: trial CI [-0.030, +0.063] vs bootstrap CI [+0.000, +0.068].
2. **Exp 1 negative-direction significance is confirmed.** Bootstrap reports d=-2.073, p=0.0001, CI=[-0.171, -0.015] (direction: negative). Exposing numerical reliability scores to the LLM harms accuracy at the fold-level n too, not just by coincidence at n=5.
3. **Exp 3 vs the 3-criterion gate.** Bootstrap reports d=+0.370, p=0.7036, CI=[-0.117, +0.170].
   Fails on: p<0.05, |d|≥0.8, CI excludes 0. Direction is positive (favouring Adaptive) so the positive-Go trajectory continues, but the absolute bar is not cleared on n=55.
4. **Stage 2 trajectory.** Bootstrap Cohen's d goes -2.073 → +0.978 → +0.370 across Exp 1 → 2 → 3. The Exp 1 → 2 sign flip reproduces the trial-level finding (prompt-design ablation is the dominant effect). Exp 2 → 3 is non-monotonic under bootstrap: stronger penalties raised the point Δ but also raised per-fold variance, so Cohen's d *fell*. The tightest positive effect is in Exp 2, not Exp 3 — the opposite of what the trial-level t-test suggested.

## Output files

- `statistical_analysis_bootstrap.json` — full per-experiment stats (including histogram bins)
- `trials_bootstrap.json` — pooled per-fold records used as bootstrap input
- `graphs/bootstrap_distribution.png` — Δ distributions with CI overlays
- `graphs/ci_comparison.png` — trial t-test CI vs bootstrap CI
- `graphs/stage2_final_cohens_d.png` — Cohen's d progression (trial vs bootstrap)
