# Phase 1.4a paired bootstrap results (Grok round-2 Q2)

Paired bootstrap resampling of fold indices across the clean subset. 
Each of the 10,000 resamples draws the same fold indices for both 
topologies, recomputes pooled F1 on each side independently, and records 
the difference. 

- seed = 42
- n_iter = 10000
- CI: 95% percentile (2.5, 97.5)
- Verdict rules: CI excludes 0 AND P(Δ>0) ≥ 0.95 → **statistical Go**; 
  CI includes 0 AND point Δ ≥ 0.02 → **practical Go (caveat)**; 
  otherwise → **No-Go**.

## Point estimates on the paired subsets

| comparison | n | baseline F1 | new F1 | point Δ |
|---|---:|---:|---:|---:|
| C vs C_v3 (macro, clean 22)  | 22 | 0.823 | 0.869 | +0.045 |
| C vs C_v3 (sparrow, clean 22) | 22 | 0.800 | 0.857 | +0.057 |
| C vs C_v3 (bulbul, clean 22)  | 22 | 0.846 | 0.880 | +0.034 |
| B vs B_v3 (macro, clean YT 11) | 11 | 0.500 | 0.721 | +0.221 |

## Paired bootstrap CI and verdict

| Comparison | n | point Δ | 95% CI (paired) | P(Δ>0) | 判定 |
|---|---:|---:|---|---:|---|
| C_v3 vs C (macro, clean 22) | 22 | +0.045 | [+0.000, +0.153] | 0.641 | practical Go (CI includes 0) |
| C_v3 vs C (sparrow F1) | 22 | +0.057 | [+0.000, +0.212] | 0.641 | practical Go (CI includes 0) |
| C_v3 vs C (bulbul F1) | 22 | +0.034 | [+0.000, +0.117] | 0.641 | practical Go (CI includes 0) |
| B_v3 vs B (macro, clean YouTube 11) | 11 | +0.221 | [+0.024, +0.417] | 0.983 | statistical Go |

## Histograms

- `graphs/bootstrap_C_vs_Cv3_overall.png`
- `graphs/bootstrap_B_vs_Bv3_youtube.png`

## Interpretation

- **C_v3 vs C (macro)** — practical Go (CI includes 0). Point Δ ≥ 0.02 so the improvement is practically relevant, but the 95% CI [+0.000, +0.153] crosses 0 so the delta is not statistically significant on this n.
- **C_v3 vs C (sparrow)** — practical Go (CI includes 0). Point Δ ≥ 0.02 so the improvement is practically relevant, but the 95% CI [+0.000, +0.212] crosses 0 so the delta is not statistically significant on this n.
- **C_v3 vs C (bulbul)** — practical Go (CI includes 0). Point Δ ≥ 0.02 so the improvement is practically relevant, but the 95% CI [+0.000, +0.117] crosses 0 so the delta is not statistically significant on this n.
- **B_v3 vs B (YouTube)** — statistical Go. The paired Δ distribution excludes 0 at α=0.05 (P(Δ>0)=0.983); the improvement is statistically supported on this subset.

## Caveats

- Paired bootstrap narrows the CI compared to the unpaired version used in 
  `reevaluation_summary.md`, but `n=22` (or `n=11`) is still small; the 
  interval endpoints themselves have non-negligible Monte-Carlo variance.
- Tier B clips contribute the pre-trim fold JSON; the first 30 s of their 
  content is still included in the prompt signal.
- `mixed` (n=2) is excluded from F1 splits; the paired Δ only reflects the 
  20 clean sparrow + bulbul folds for each sparrow/bulbul split view.
