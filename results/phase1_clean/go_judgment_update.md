# Phase 1.4a Go judgment update (post paired bootstrap)

This finalises Phase 1.4a's Go/No-Go calls by combining the clean-dataset 
re-evaluation (`reevaluation_summary.md`) with the paired-bootstrap results 
in `paired_bootstrap_results.md`.

| objective | clean point | clean CI (paired) | P(Δ>0) | final verdict |
|---|---:|---|---:|---|
| Obj D: C_v3 vs C (macro) (0.823 → 0.869) | +0.045 | [+0.000, +0.153] | 0.641 | practical Go (CI includes 0) |
| bbox v3 gate: B_v3 vs B (YouTube) (0.500 → 0.721) | +0.221 | [+0.024, +0.417] | 0.983 | statistical Go |

## Unchanged verdicts from the 42-fold run (no bootstrap needed)

- **Obj B (C_v2 macro F1 ≥ 0.86)** — clean point 0.791 below the gate; **No-Go**.
- **bbox v3 + fusion (C_v4 macro F1 ≥ Phase 1.3 C + 0.02)** — clean point 0.635 
  vs baseline 0.823 (Δ = −0.188); **No-Go** (regression, not improvement).

## Summary of Phase 1.4a Go state

| intervention | final verdict | notes |
|---|---|---|
| Obj B (frame_extractor) | No-Go | point 0.791 < 0.86 on clean data |
| Obj D (temporal_sync) | practical Go (CI includes 0) | paired Δ = +0.045 [+0.000, +0.153], P(Δ>0)=0.641 |
| bbox v3 on B (Grok Q2) | statistical Go | paired Δ = +0.221 [+0.024, +0.417], P(Δ>0)=0.983 on 11 clean YouTube folds |
| bbox v3 on C (C_v4) | No-Go | Δ = −0.188 on clean data (regression) |

## Recommendation

At least one intervention shows a statistically-significant paired Δ; 
Phase 1.4a can exit with that result as the headline improvement. 
