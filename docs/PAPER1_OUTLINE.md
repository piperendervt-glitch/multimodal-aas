# Paper 1 — draft outline

Working title (candidates):

- **"Where sdnd-proof transfers and where it does not: an architecture
  boundary for `flow_weight` learning in multimodal LLM ensembles"**
- alt: "Outside the model, not inside it: transferring single-node AAS
  learning to a three-topology bird-identification ensemble"

Intended venue: workshop / short-paper track on AI safety + empirical
ML, with deterrence-oriented framing (matching the sdnd-proof
philosophy). Length target: 8–12 pages.

## Abstract (skeleton)

- Background: sdnd-proof demonstrated a single-node `flow_weight`
  learning rule (success: `w + 0.1·(1 − w)`; failure: `w × 0.7`) that
  beat fixed weights at Cohen's d = 4.29 on a toy LLM task.
- Question: does this rule still work when the "node" is replaced by
  a heterogeneous ensemble of visual-only, audio-only, and multimodal
  LLM topologies over a real task (Japanese backyard bird
  identification)?
- Method: four Phase 1.4d experiments (a negative control, a
  null-result diagnosis, a weak positive, a strong positive) all
  evaluated with the same 3-criterion paired-fold-bootstrap protocol
  on a Robosheep-reviewed 22-fold dataset.
- Result: **sdnd-proof transfers cleanly to an external mixing layer
  (Cohen's d = +4.014 on n=220) and fails — with statistically
  significant harm — when the learned weights are shown to the LLM as
  numerical advice (Cohen's d = −2.073)**. The boundary is
  architectural, not parametric.
- Methodological contribution: every small-n positive in this project
  (n=5 trial t-test) was re-audited at n=220 paired fold bootstrap.
  One positive result dissolved; one survived and strengthened. The
  paper names this re-audit as a standing requirement.

## Chapter 1 — The architecture boundary

- Present the four pillars side-by-side (Stage 2 Exp 1, Stage 2 Exp 2
  extended, Stage 1 Exp 5b extended, Stage 3 Target C).
- Show the Cohen's d table from `PHASE_1_4D_SUMMARY.md` as the
  headline figure.
- Argue the boundary is where the learned weight meets the LLM's
  attention: outside → fine, inside → harmful.

## Chapter 2 — Negative Go: prompt injection harms

- Experiment: Stage 2 Exp 1 (commit `2f247e0`, bootstrap `0d0903c`).
- Protocol: four per-modality reliability scores inserted as numeric
  values into the LLM prompt; 5 trials; paired fold bootstrap n=55.
- Result: d = −2.073, p = 0.0001, CI [−0.171, −0.015].
- Mechanism (hypothesis, to be argued): when the LLM sees a scalar
  that looks like "trust this modality at 0.72", it tends to
  over-weight that modality and lose the complementarity that made
  the ensemble work at equal weights.
- Take-away: do not let a learned-weight layer leak into the prompt
  surface.

## Chapter 3 — No transfer: silent info filtering

- Experiment: Stage 2 Exp 2 and its extension (commits `2dd8756`,
  `3729f75`, `d2fc14e`).
- Protocol: same prompt template for Fixed and Adaptive, but the
  Adaptive arm uses the learned weight to select a 3-tier detail
  level (brief / medium / full) for each modality.
- Result at n=5: d = +0.447 (looks positive). At n=55 bootstrap:
  d = +0.978, CI lower = +0.000 (touches zero). At n=220:
  d = −0.115 — effect dissolves.
- Interpretation: the detail knob is coarse, the weight motion is
  small, and the LLM's behaviour is largely invariant to which tier
  it sees. What reads as a positive at small n is variance.
- Key figure: Cohen's d trajectory across n ∈ {5, 55, 220} for Exp 2,
  next to the Exp 5b trajectory (which goes the other way).

## Chapter 4 — Positive Go weak: ensemble voting over label-specific weights

- Experiment: Stage 1 Exp 5b extended (commit `2db9ca2`).
- Protocol: six weights (3 topologies × 2 labels), sdnd-proof rule
  ×0.7 penalty, label-independent credit assignment, weighted binary
  vote over A + B_v3 + C_v3. 20 trials, n=220 paired fold bootstrap.
- Result: bootstrap d = +2.041, p = 0.0001, CI [+0.003, +0.026].
- Δ-sign: 4 positive / 16 zero / 0 negative across 20 trials. The
  ensemble never goes backwards.
- Diagnostic: the learned weight-balance surfaces Topology B_v3's
  measured per-label balance (bbox prompt v3 was specifically
  engineered to remove the sparrow/bulbul split) — weight learning
  recovers the engineering effect.

## Chapter 5 — Positive Go strong: gate routing

- Experiment: Stage 3 Target C (commit `bfd840d`).
- Protocol: on top of the 6 weights, add 6 gates — one per topology
  per label. Weight updates against GT; **gate updates against the
  ensemble's own final prediction**, so topologies that agree with
  the emerging consensus are rewarded. Effective contribution =
  `w × g`.
- Result: trial t-test d = +0.899 (p = 0.0007), bootstrap d = +4.014
  (p = 0.0001), CI [+0.024, +0.067]. All three criteria on both
  analyses.
- Routing structure (mean n=20):
  - `sparrow` ends up 70% on `C_v3` (the audio-aware fusion topology)
  - `bulbul` splits 56% on `C_v3` and 34% on `A` (audio-only) — the
    BirdNET bulbul signal is strong enough to deserve its own route.
- Take-away: adding an explicit routing gate on top of the weight
  nearly doubles Cohen's d (+2.041 → +4.014) by driving positive
  trials from 4/20 to 10/20. The ensemble *learns to specialise*.

## Chapter 6 — Methodological contribution: re-audit at n=220

- Framing: "small-n Go claims need to be stress-tested before they
  become paper claims."
- The Exp 2 trajectory (+0.447 → +0.978 → −0.115 as n grows) is the
  motivating example. The Exp 5b trajectory (+0.447 → +0.986 → +2.041)
  is the contrast.
- Recipe:
  1. Run the small-n experiment (sdnd-proof style 5 trials).
  2. If the trial t-test looks like Go, extend to ≥20 seeds.
  3. Pool trial × fold predictions and run 10k paired fold bootstrap.
  4. Check CI excludes zero cleanly (not "touches zero"); a CI lower
     bound of exactly +0.000 is the signal the effect is a
     bootstrap-duplication artefact.
  5. Report the full trajectory in the paper, not just the best
     number. Honest reporting prevents small-n artefacts from
     propagating through the literature.

## Conclusion

- sdnd-proof's `flow_weight` rule does transfer to a multimodal
  ensemble, but only when the weight lives *outside* the LLM.
- Showing the same weight to the LLM produces a statistically
  significant *harm*, not a null result.
- Adding a routing gate on top of the weight nearly doubles the
  effect size. Paper 1's strongest positive is built from three
  layers: ensemble voting (substrate), label-specific weights
  (direction), and explicit gates (routing).
- Phase 1.4d's most portable contribution is procedural: pair every
  small-n result with an n=220 bootstrap before believing it.

## Figures (planned)

1. **Architecture boundary table** — the 4-row table from
   `PHASE_1_4D_SUMMARY.md` "Big picture" section.
2. **Cohen's d vs n** — two-line plot (Exp 2 extended collapses, Exp
   5b extended grows) with the Go threshold line.
3. **Routing share per label** — `stage3_target_c_gate_learning/graphs/
   routing_visualization.png`.
4. **Δ-sign distribution** — stacked bar of positive / zero /
   negative trials across Stage 2 Exp 2 extended, Stage 1 Exp 5b
   extended, Stage 3 Target C.

## Supplementary / reproduction

- `src/phase1_4d/stage{1,2,3}_*.py` — all experiment scripts.
- `results/phase1_4d/*/summary.md` — committed per-experiment
  summaries (the paper numbers come from these files).
- `docs/PHASE_1_4D_SUMMARY.md` — the one-page index of every
  experiment and its verdict.

## Open items before submission

- Decide whether Phase 1.4b / 1.4c / 1.4e are in scope. Target C
  already clears the Go gate by a wide margin; additional topology or
  LLM parallelism is interesting but not required for the paper.
- Prepare the balcony-audio hardware caveat for a limitations
  paragraph (Phase 1.3 BirdNET sensitivity check is the source).
- Final Grok / ChatGPT / human review of the full draft before
  submission (judge III round 3).
