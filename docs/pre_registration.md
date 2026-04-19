# Pre-Registration: Multimodal AAS Topology Comparison

**Status:** DRAFT. Freeze before running Phase 4b.
**Author:** Katsuma Murashita
**Project:** multimodal-aas-bird
**Prior work:** sdnd-proof (LLM-node AAS), 5/5 trials, p = 0.0007,
Cohen's d = 4.29.

This document follows the spirit of OSF pre-registration: hypotheses,
metrics, sample size, and analysis plan are fixed **before** any
experimental run in Phase 4b. Any deviation after freeze is reported
as a post-hoc exploratory analysis, not as a confirmatory result.

Motivation for pre-registration is explicit: the TRUSS Phase 5 review
showed that post-hoc metric and test selection can inflate apparent
effects. Freezing the protocol is the main defence.

---

## 1. Research Question

Does a heterogeneous (vision + audio + LLM) AAS topology outperform
single-modality baselines on bird species identification from
balcony-scale real-world data?

## 2. Hypotheses

- **H0 (null):** Mean species-level F1 of the best multimodal topology
  (C, D, E, or F) equals the mean F1 of the best single-modality
  baseline (A or B), on the held-out evaluation set.
- **H1 (alternative, one-sided):** Mean species-level F1 of the best
  multimodal topology is **greater** than the best single-modality
  baseline by at least Delta = 0.05 (absolute).

Secondary hypotheses (exploratory, not confirmatory):
- H2: Audio-First Gating (D) reduces compute cost per decision versus
  Parallel Fusion (C) without loss of F1.
- H3: Cross-Validation (F) reduces confident false positives (precision
  at high-confidence threshold) versus Parallel Fusion (C).

## 3. Topologies Under Test

| Code | Name | Inputs | Integration |
|------|------|--------|-------------|
| A | Audio-Only | BirdNET | - |
| B | Visual-Only | best detector + best classifier | - |
| C | Parallel Fusion | audio + vision | LLM integrator, both always run |
| D | Audio-First Gating | audio triggers vision | LLM integrator |
| E | Visual-Guided Audio | vision triggers audio window | LLM integrator |
| F | Cross-Validation | audio + vision, agreement required | LLM integrator |

Component choices for B/C/D/E/F are locked by Phase 4a results before
Phase 4b begins. Phase 4a outcome (which detector, which classifier)
is itself a frozen decision rule: pick the component with the higher
macro F1 on a separate Phase 4a evaluation set.

## 4. Primary Metric

Species-level macro F1 on the Phase 4b evaluation set.

- Evaluation set composition is fixed in Section 6 below.
- F1 is computed per species, then averaged (macro). Species with zero
  ground-truth instances are excluded before averaging.

## 5. Statistical Test

Primary test: **one-sided paired Welch's t-test** on per-trial F1,
with trials as the unit of analysis (matched by evaluation seed).
Alpha = 0.05. Effect size reported as Cohen's d.

Rationale: same approach as sdnd-proof Phase 5 (prior result d = 4.29),
keeping the test comparable. One-sided because H1 is directional.

If the Shapiro-Wilk test on paired differences rejects normality at
alpha = 0.05, the pre-registered fallback is a Wilcoxon signed-rank
test (one-sided). Effect size reported as rank-biserial correlation.

## 6. Sample Size / Trials

- **Number of trials:** 5 per topology (same as sdnd-proof).
- **Per-trial evaluation set:** 200 balanced samples (50% positive
  balcony clips with species label, 50% challenging negatives:
  background, wind, human voice, non-target birds).
- **Seeds:** trials 1-5 use seeds `{42, 137, 271, 314, 1618}`.
- **Power:** with d = 1.0 (far below prior d = 4.29), n = 5 paired
  trials, one-sided alpha = 0.05, post-hoc power estimate > 0.80.
  We accept this as sufficient given the prior effect size and the
  cost per trial. If pilot data suggest d < 0.8, trial count is
  increased to 10 **before** any confirmatory run.

## 7. Evaluation Set Construction

- Positive pool: balcony clips (Tier 4) with expert species label,
  augmented by Xeno-canto audio (Tier 1) cut to the same duration
  distribution.
- Negative pool: balcony clips confirmed bird-absent, plus
  urban-noise recordings (traffic, human voice, wind).
- The evaluation set is constructed **once**, hashed, and the hash
  recorded here before Phase 4b runs:

  `evaluation_set_sha256:` (to be filled in)

- After freeze, the set is read-only. Any change invalidates the
  pre-registration and requires a new, dated freeze.

## 8. Decision Rule

- Reject H0 in favour of H1 if and only if:
  1. one-sided p < 0.05 on the primary test,
  2. observed mean F1 difference >= Delta = 0.05,
  3. the winning topology is the one pre-specified by Phase 4a
     component selection plus Section 3 rules (i.e., not cherry-picked
     after seeing the numbers).

All three conditions must hold. Any two-out-of-three outcome is
reported as inconclusive, not as a positive result.

## 9. Deviations and Amendments

Any change to Sections 1-8 after the freeze date must be logged
below with date, reason, and whether it occurred before or after
seeing Phase 4b data. Changes after seeing data downgrade affected
claims to exploratory.

| Date | Section | Change | Before data? | Reason |
|------|---------|--------|--------------|--------|
|      |         |        |              |        |

## 10. Freeze

Freeze date: (to be filled in)
Freeze commit: (to be filled in)
Signed by: (to be filled in)
