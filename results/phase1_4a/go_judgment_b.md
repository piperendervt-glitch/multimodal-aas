# Phase 1.4a Objective B — Go/No-Go judgment

## Criterion

- Go threshold: Topology C_v2 macro F1 >= **0.86** 
  (Phase 1.3 Topology C baseline was 0.840; target = +0.02).

## Measured values (42 folds, self + YouTube)

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| macro F1 | 0.840 | 0.826 | -0.014 |
| sparrow F1 | 0.880 | 0.880 | +0.000 |
| bulbul F1 | 0.800 | 0.773 | -0.027 |
| fallback | 0 | 0 | +0 |

## Verdict

**No-Go** (measured macro F1 = 0.826, threshold = 0.86).

Objective B is **not** satisfied by the frame_extractor alone.
Options:
- Revisit the bbox-size prompt thresholds (the YouTube regression in B 
  was the primary driver; C_v2 inherits the same prompt).
- Consider objective D (modality sync) even under No-Go, because 
  temporal alignment may unlock gains the frame-level aggregate hides.
- Measure uncertainty: with n=42 the F1 estimate has non-trivial 
  variance; a bootstrap CI on the delta may still clear the bar.
