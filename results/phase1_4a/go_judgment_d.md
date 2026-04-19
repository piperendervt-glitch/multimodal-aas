# Phase 1.4a Objective D — Go/No-Go judgment

## Criterion

- Go threshold: C_v3 macro F1 >= **0.86** 
  (Phase 1.3 C baseline 0.840; C_v2 was 0.826)

## Measured values (42 folds, self + YouTube)

| metric | Phase 1.3 C | C_v2 | C_v3 | Δ(C_v3 - C) |
|---|---:|---:|---:|---:|
| macro F1 | 0.840 | 0.826 | 0.819 | -0.021 |
| sparrow F1 | 0.880 | 0.880 | 0.906 | +0.026 |
| bulbul F1 | 0.800 | 0.773 | 0.732 | -0.068 |
| fallback | 0 | 0 | 0 | +0 |

## Verdict

**No-Go** (C_v3 macro F1 = 0.819, threshold = 0.86).

Objective D is **not** satisfied on its own. Candidate next steps:

- Tighten the temporal prompt: explicit rules for sparrow/bulbul 
  co-occurrence in different windows (mixed category).
- Combine with objective B (frame_extractor) and see if the two 
  interventions are additive.
- Extend the 42-fold set; n=42 leaves a non-trivial uncertainty 
  on the macro F1 delta (one-fold noise ≈ ±0.02).
