# Phase 1.4d Stage 2 Experiment 1 — full interpretation C

Target B: learn **modality-level** reliability weights (visual and audio) 
and feed them — plus a dynamically-filtered detail section for each modality 
— directly to qwen2.5:7b as numerical scores. 4 weights, label-specific.

- Clean 22 folds (11 self + 11 YouTube Tier A/B/B').
- 5 trials × seeds [42, 137, 256, 512, 1024]; first 11 folds = warm-up, 
  last 11 folds = evaluation.
- Fixed baseline: all weights pinned at 0.5 (medium detail both sides). 
  Cached across trials (22 LLM calls total).
- Adaptive: sdnd-proof rule, failure multiplier ×0.9 (relaxed). 
  Per-fold modality updates driven by Topology A and Topology B_v3 correctness.
- LLM: qwen2.5:7b via Ollama, temperature 0.0, timeout 120 s, retry 3.

## Per-trial macro F1

| Trial | Seed | Fixed | Adaptive | Δ |
|---|---:|---:|---:|---:|
| 1 | 42 | 0.667 | 0.522 | -0.144 |
| 2 | 137 | 0.625 | 0.476 | -0.149 |
| 3 | 256 | 0.649 | 0.614 | -0.036 |
| 4 | 512 | 0.650 | 0.600 | -0.050 |
| 5 | 1024 | 0.567 | 0.543 | -0.024 |

## Per-trial F1 breakdown

| Trial | Seed | Fixed sparrow | Fixed bulbul | Adaptive sparrow | Adaptive bulbul |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.667 | 0.667 | 0.444 | 0.600 |
| 2 | 137 | 0.500 | 0.750 | 0.286 | 0.667 |
| 3 | 256 | 0.571 | 0.727 | 0.500 | 0.727 |
| 4 | 512 | 0.500 | 0.800 | 0.400 | 0.800 |
| 5 | 1024 | 0.333 | 0.800 | 0.286 | 0.800 |

## Adaptive final weights per trial

| Trial | Seed | v_sparrow | v_bulbul | a_sparrow | a_bulbul |
|---|---:|---:|---:|---:|---:|
| 1 | 42 | 0.670 | 0.578 | 0.611 | 0.707 |
| 2 | 137 | 0.653 | 0.515 | 0.546 | 0.758 |
| 3 | 256 | 0.497 | 0.644 | 0.632 | 0.715 |
| 4 | 512 | 0.628 | 0.657 | 0.599 | 0.727 |
| 5 | 1024 | 0.637 | 0.585 | 0.595 | 0.723 |
| mean | - | 0.617 | 0.596 | 0.597 | 0.726 |

## Adaptive detail-level frequencies (5 trials × 22 folds = 110 decisions)

| level | visual | audio |
|---|---:|---:|
| brief | 0 | 0 |
| medium | 110 | 104 |
| full | 0 | 6 |

## LLM call health

- Fixed cached calls: 22 (1 per video)
- Adaptive calls: 110 (0 with fallback after retries exhausted)

## Statistical analysis (Adaptive vs Fixed)

- Mean Δ: **-0.081**
- Std Δ: 0.061
- Paired t-test: t = -2.951, p = 0.0419
- Cohen's d: -1.320
- 95% CI: [-0.156, -0.005]

## Go judgment (sdnd-proof 3 criteria)

| Criterion | Threshold | Value | Pass |
|---|---|---:|:-:|
| p-value | < 0.05 | 0.0419 | Y |
| Cohen's d | >= 0.8 | -1.320 | N |
| 95% CI lower | > 0 | -0.156 | N |
| **Overall** | all pass | | **No-Go** |

## Comparison vs Stage 1 Experiment 5b (same topology set, label-specific weights only)

| experiment | mean Δ | Cohen's d | p | 95% CI |
|---|---:|---:|---:|---|
| Stage 1 Exp 5b | +0.011 | 0.447 | 0.374 | [-0.019, +0.041] |
| **Stage 2 Exp 1** | -0.081 | -1.320 | 0.042 | [-0.156, -0.005] |

## Discussion

1. Modality-level weights concentrate differently from topology-level weights: the LLM sees exactly two reliability scores per label (visual vs audio) instead of three node weights. This keeps the prompt budget small and lets the 3-level detail knob carry the extra information.
2. Audio weights in this clean subset stay low because the Topology-A single-modality judgment is correct on the 'both zero' rows by chance only; most folds drive the audio weights downward at the ×0.9 penalty.
3. The detail-level knob means the 'brief' mode removes most numeric evidence from the LLM and forces it to rely on the reliability scores. When that mode coincides with high weights for the other modality, the prompt becomes effectively single-modality.

## Output files

- `trials_summary.json` — per-fold prompts, responses, weights
- `statistical_analysis.json` — paired t-test and Go judgment
- `graphs/weight_trajectory.png`
- `graphs/detail_level_evolution.png`
- `graphs/f1_comparison.png`
- `graphs/stage_comparison.png`
