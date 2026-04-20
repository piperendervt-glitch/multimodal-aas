# Phase 1.4d — comprehensive experiment summary

Scope: every Stage 1 / 2 / 3 experiment run under Phase 1.4d, one
table per stage plus a short interpretation. Numbers are reproduced
from the committed `summary.md` of each experiment; see the commits
listed inline for the per-fold data.

All experiments use:

- Clean 22-fold dataset (11 self-recorded + 11 Robosheep-reviewed
  YouTube Tier A/B/B′).
- Warm-up on the first 11 folds of each shuffle, evaluation on the
  last 11.
- sdnd-proof update rule — success: `w + 0.1·(1 − w)`; failure:
  `w × p` (p defaults to 0.7 unless noted).
- sdnd-proof 3-criterion Go gate: `p < 0.05` AND `|Cohen's d| ≥ 0.8`
  AND 95% CI excludes 0. Direction (positive / negative) reported
  separately so `negative Go` does not masquerade as success.

---

## Stage 1 — Target A: topology weights

Stage 1 asks whether sdnd-proof's `flow_weight` rule transfers to a
3-topology weighted-vote ensemble.

| Exp | topology set | weight structure | penalty | threshold | Cohen's d (trial n=5) | Go? | commit |
|---|---|---|---|---:|---:|---|---|
| 1   | Phase 1.3 A/B/C | shared scalar | ×0.7 | 0.5 | **−0.889** | No-Go | `45f5b9c` |
| 2   | Phase 1.3 A/B/C | shared scalar | ×0.9 | 0.5 | −0.447 | No-Go | `89548c0` |
| 3   | Phase 1.3 A/B/C | label-specific | ×0.7 | 0.5 | −0.340 | No-Go | `e951457` |
| 4   | Phase 1.3 A/B/C | label-specific | ×0.7 | 0.4 | −0.697 | No-Go | `200e6fa` |
| 5a  | A + B_v3 + C_v3 | shared scalar | ×0.7 | 0.5 | **+0.673** | No-Go | `b546022` |
| 5b  | A + B_v3 + C_v3 | label-specific | ×0.7 | 0.5 | +0.447 | No-Go | `b069d7c` |

Headlines:

- **Phase 1.3 topology set is the wrong substrate.** On A/B/C the
  Cohen's d is stuck in the negative quadrant, irrespective of
  penalty strength, weight structure, or threshold. Stage 1 Exp 4
  (threshold=0.4) shows the Fixed value is literally unchanged (equal
  weights make the 3-node vote invariant to threshold in {0.5, 0.4}),
  so the threshold knob cannot rescue Adaptive.
- **Upgraded topology set flips the sign.** Replacing B with `B_v3`
  (Phase 1.4a bbox relative-distribution prompt) and C with `C_v3`
  (temporal sync signal) pushes Cohen's d from −0.889 (Exp 1) to
  +0.673 (Exp 5a). The base nodes, not the learning rule, were the
  bottleneck.
- **Label-specific weights also carry interpretability value.** Exp 3
  surfaced Topology B's `sparrow / bulbul` bias (w_bulbul = 0.525 vs
  w_sparrow = 0.255); Exp 5b showed that B_v3 had erased that bias
  (0.363 vs 0.362) as the prompt engineering intended.

### Stage 1 Exp 5b extended (commit `2db9ca2`)

n=5 trial → n=220 paired fold bootstrap to check whether the +0.447 is
real or an n=5 artefact.

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| trial t-test (original) | 5 | +0.011 | +0.447 | 0.374 | [−0.019, +0.041] | No-Go |
| paired bootstrap (n=55) | 55 | +0.011 | +0.986 | 0.0001 | [+0.000, +0.038] | No-Go (CI touches 0) |
| trial t-test (extended) | 20 | +0.013 | +0.485 | 0.043 | [+0.000, +0.025] | No-Go |
| **paired bootstrap (extended)** | **220** | **+0.013** | **+2.041** | **0.0001** | **[+0.003, +0.026]** | **Go (positive)** |

- Δ-sign distribution at n=20: **4 positive / 16 zero / 0 negative** —
  not a single trial flipped negative, so the stronger n=220 bootstrap
  is reading a genuine mean shift.
- This is the first positive Statistical Go in Phase 1.4d and the
  anchor for Stage 3.

---

## Stage 2 — Target B: modality weights

Stage 2 moves the learning one level deeper: the weights now live
inside a single-LLM substrate. Each fold, the LLM sees filtered
detection data; the experimenter controls how much of that data the
prompt exposes (via a 3-tier detail knob) and whether the numerical
weights are shown.

### Trial-level results (n=5)

| Exp | prompt | penalty | Fixed mean | Adaptive mean | mean Δ | Cohen's d | p | verdict | commit |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | scores shown | ×0.9 uniform | 0.632 | 0.551 | **−0.081** | **−1.320** | 0.042 | No-Go (negative) | `2f247e0` |
| 2 | scores hidden | 0.80/0.90/0.75/0.95 | 0.655 | 0.672 | +0.017 | +0.447 | 0.374 | No-Go | `2dd8756` |
| 3 | scores hidden | 0.70/0.85/0.60/0.90 | 0.655 | 0.695 | +0.040 | +0.594 | 0.255 | No-Go | `3729f75` |

### Paired fold bootstrap (n=55, commit `0d0903c`)

| Exp | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| 1 | −0.084 | **−2.073** | 0.0001 | **[−0.171, −0.015]** | **Go (negative)** |
| 2 | +0.020 | +0.978 | 0.0001 | [+0.000, +0.068] | No-Go (CI touches 0) |
| 3 | +0.027 | +0.370 | 0.7036 | [−0.117, +0.170] | No-Go |

### Stage 2 Exp 2 extended (commit `d2fc14e`)

The n=55 Exp 2 bootstrap flirted with positive Go (d=+0.978, CI
[+0.000, +0.068]). Extending seeds from 5 to 20 (15 new LLM trials,
330 inferences) to see whether the effect holds:

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| trial t-test (original) | 5 | +0.017 | +0.447 | 0.374 | [−0.030, +0.063] | No-Go |
| paired bootstrap (n=55) | 55 | +0.020 | +0.978 | 0.0001 | [+0.000, +0.068] | No-Go |
| trial t-test (extended) | 20 | +0.002 | +0.036 | 0.873 | [−0.021, +0.025] | No-Go |
| **paired bootstrap (extended)** | **220** | **−0.001** | **−0.115** | 0.877 | **[−0.023, +0.022]** | **No-Go** |

- Δ-sign distribution at n=20: **2 positive / 12 zero / 6 negative**
  (contrast with Exp 5b extended's 4 / 16 / 0). The extra 15 trials
  deliver no systematic improvement; the apparent effect at n=5 / n=55
  was small-sample noise.
- This is the methodological lesson of Phase 1.4d: n=5 paired t-test
  and n=55 fold-level bootstrap are both underpowered enough that a
  positive-looking effect can dissolve at n=220. Every small-n Go
  claim in this project was re-audited.

Headlines:

- **Exp 1 — Negative Go is robust** at bootstrap n=55:
  d = **−2.073**, CI **[−0.171, −0.015]**, direction negative. Showing
  the LLM numerical reliability scores harms accuracy significantly.
- **Exp 2 extended — No transfer at scale.** The single-LLM +
  silent-filter recipe produces no detectable effect on n=220.
- **Exp 3 — penalty strength does not rescue.** Stronger penalties
  activate the `brief` tier for the first time (audio.sparrow crosses
  below 0.4) but bootstrap Cohen's d at n=55 actually *drops* to
  +0.370 because the extra weight variance outruns the signal.

---

## Stage 3 — Target C: per-label routing with gate learning

Given Stage 1's positive Go on the ensemble-voting substrate, Stage 3
adds an explicit routing gate on top of the label-specific weights:

- 6 weights `w[topology][label]` — updated against ground truth
  (same as Exp 5b).
- 6 gates `g[topology][label]` — updated against the ensemble's own
  final prediction, so topologies that agree with the majority grow
  their gate and topologies that disagree shrink it.
- Effective contribution per topology-label pair = `w × g`.

### Target C results (commit `bfd840d`)

| method | n | point Δ | Cohen's d | p | 95% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| trial t-test | 20 | +0.045 | **+0.899** | 0.0007 | [+0.022, +0.069] | Go |
| **paired fold bootstrap** | **220** | **+0.044** | **+4.014** | **0.0001** | **[+0.024, +0.067]** | **Go (positive)** |

Both the trial-level test AND the fold-level bootstrap clear all
three sdnd-proof criteria in the positive direction — Phase 1.4d's
gold-standard Statistical Go.

### Head-to-head: Exp 5b extended vs Target C

| quantity | Exp 5b extended | Target C | multiplier |
|---|---:|---:|---:|
| bootstrap Cohen's d (n=220) | +2.041 | **+4.014** | ~1.97× |
| trial t-test Cohen's d (n=20) | +0.485 | +0.899 | ~1.85× |
| 95% CI lower (bootstrap) | +0.003 | +0.024 | ~8× further from 0 |
| positive trials / 20 | 4 | **10** | +6 trials |
| negative trials / 20 | 0 | 0 | — |

### Routing structure at n=20 (mean final `w × g` share per label)

| label | C_v3 | A | B_v3 |
|---|---:|---:|---:|
| sparrow | **70.45%** | 13.96% | 15.59% |
| bulbul  | **56.07%** | 34.16% | 9.77%  |

- `sparrow` routing concentrates on `C_v3` (audio-aware fusion), with
  Topology A (audio-only) de-weighted because BirdNET's sparrow
  sensitivity is low.
- `bulbul` routing shares between `C_v3` and `A`, reflecting
  BirdNET's higher confidence on the bulbul vocalisation.

These are exactly the per-label strengths the project measured
upstream (Phase 1.3 BirdNET sensitivity check, Phase 1.4a bbox prompt
v3). The learning rule re-derived them online.

### Target C ablation study (commits `49d4273`, `49615c4`, `38933b1`)

Target C stacks four design elements (second online variable,
distinct update signal, multiplicative integration, per-label
routing). Two ablations — each a minimal edit to Target C's update
rule — localise which of those is load-bearing. Same 20 seeds, same
11-fold eval, same n=220 paired-fold bootstrap.

| experiment | Weight learned | Gate learned | Gate signal | Integration | bootstrap d (n=220) | 95% CI | bootstrap p | Go |
|---|---|---|---|---|---:|:---:|---:|:---:|
| Exp 5b extended | Yes (GT) | — | — | additive | +2.041 | [+0.003, +0.026] | 0.0001 | ✓ |
| **Ablation 1** — gate only | **No (frozen 0.5)** | Yes | consensus | multiplicative | **+2.217** | [+0.004, +0.044] | 0.0174 | ✓ |
| **Ablation 5** — GT gate | Yes (GT) | Yes | **ground truth** | multiplicative | **+2.042** | [+0.001, +0.042] | 0.0350 | ✓ |
| Target C | Yes (GT) | Yes | consensus | multiplicative | **+4.014** | [+0.024, +0.067] | 0.0001 | ✓ |

Three findings:

1. **Gate contributes independently** — Ablation 1 (d=+2.217) ≈
   Exp 5b extended (d=+2.041). Gate alone and weight alone sit on the
   same tier.
2. **Consensus signal is the essential novelty** — Ablation 5
   (d=+2.042) collapses to the Exp 5b extended level when the gate
   is fed ground truth instead of consensus. With matched signals the
   gate trajectory collapses onto the weight and `w × g` degenerates
   to `w² · pred`.
3. **Near-additive combination** — Target C (+4.014) ≈ Ablation 1
   (+2.217) + Exp 5b extended (+2.041). Two differently-informed
   variables carry complementary signal dimensions.

Load-bearing novelty for Paper 1 Chapter 5: the **gate's
consensus-agreement update rule** (reward topologies that agree with
the emerging majority). Multiplicative `w × g` integration is an
engineering choice that only pays off when its two factors encode
different signals. See `results/phase1_4d/stage3_ablation_summary.md`
for the full write-up.

---

## Big picture — the architecture boundary

Putting Stage 1 / 2 / 3 together:

| substrate | weight signal | representative experiment | Cohen's d (n=220) | verdict |
|---|---|---|---:|---|
| single-LLM, reliability scores injected | prompt-visible | Stage 2 Exp 1 (n=55) | **−2.073** | **Negative Go** |
| single-LLM, silent info filter | prompt-invisible | Stage 2 Exp 2 extended | −0.115 | No transfer |
| ensemble vote, label weights | outside LLM | Stage 1 Exp 5b extended | +2.041 | Positive Go (weak) |
| ensemble vote, `w × g` gated routing | outside LLM | Stage 3 Target C | **+4.014** | **Positive Go (strong)** |

One sentence: **sdnd-proof's `flow_weight` rule transfers cleanly to a
mixing layer that lives outside the LLM; the moment the learned
weights are fed into the LLM's context, the same rule stops helping
and can actively harm.** The paper follows from this boundary.

## Methodological lesson, carried into Paper 1

Phase 1.4d's "detect the n=5 artifact" episode (Stage 2 Exp 2 n=5 →
n=220) is itself a reportable finding. Every positive-Go claim in
this project was re-audited with a paired fold bootstrap at n=220
before being treated as a paper result. The Paper 1 methodology
section names this pattern explicitly so a reader can repeat it on
their own small-sample experiments.
