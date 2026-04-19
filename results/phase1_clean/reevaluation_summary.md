# Phase 1.4a clean-dataset re-evaluation

Every Phase 1.3-extended and Phase 1.4a experiment is re-aggregated on the
22-fold clean subset (11 self-recorded + 11 YouTube Tier A/B/B'). Robosheep's
tier review (2026-04-19) drops 20 unusable YouTube clips (BGM / human voice /
text-dominant overlays / heavy noise).

**Simplification**: Tier B's 30 s intro trim is not re-applied here; we reuse
each experiment's original fold JSON (computed on the untrimmed clip). Tier B
clips therefore receive the same bias as in the 42-fold run. Trimmed re-runs
can be scheduled via `src/phase1_4a_common/video_trimmer.py` in Phase 1.4b+.

## Tier review summary

| tier | count | notes |
|---|---:|---|
| A (fully usable) | 4 | 1 sparrow, 3 bulbul |
| B (usable with 30 s intro trim) | 6 | 1 sparrow, 5 bulbul |
| B' (noisy but usable) | 1 | sparrow |
| C (unusable, excluded) | 20 | 8 sparrow, 4 bulbul, 8 mixed |
| not tiered (download failed) | 1 | yt_Ji1jooZwBSo |

Clean dataset = 11 self-recorded + 11 YouTube = **22 folds**.

## 4.1 Macro F1: full 42-fold vs clean 22-fold

| experiment | 42-fold n/scored | 42-fold macro F1 | 22-fold n/scored | 22-fold macro F1 | Δ |
|---|---|---:|---|---:|---:|
| Phase 1.3 A | 42/42 | 0.611 | 22/22 | 0.482 | -0.129 |
| Phase 1.3 B | 42/42 | 0.610 | 22/22 | 0.669 | +0.059 |
| Phase 1.3 C | 42/42 | 0.840 | 22/22 | 0.823 | -0.017 |
| Phase 1.4a C_v2 | 42/42 | 0.826 | 22/22 | 0.791 | -0.035 |
| Phase 1.4a C_v3 | 42/42 | 0.819 | 22/22 | 0.869 | +0.050 |
| Phase 1.4a B_v3 | 42/42 | 0.769 | 22/22 | 0.718 | -0.051 |
| Phase 1.4a C_v4 | 42/42 | 0.760 | 22/22 | 0.635 | -0.125 |

## 4.2 Category breakdown (clean 22-fold)

| category | n | Phase 1.3 A | Phase 1.3 B | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Phase 1.4a B_v3 | Phase 1.4a C_v4 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sparrow | 8 | 0.111 | 0.429 | 0.467 | 0.429 | 0.500 | 0.500 | 0.333 |
| bulbul | 12 | 0.400 | 0.478 | 0.455 | 0.455 | 0.455 | 0.478 | 0.429 |
| both | 2 | 0.333 | 0.500 | 0.667 | 0.667 | 0.667 | 0.833 | 0.333 |

## 4.3 Source breakdown (clean 22-fold)

| source | n | Phase 1.3 A | Phase 1.3 B | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Phase 1.4a B_v3 | Phase 1.4a C_v4 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| self (self-recorded) | 11 | 0.143 | 0.795 | 0.733 | 0.733 | 0.733 | 0.688 | 0.558 |
| YouTube (Tier A only) | 4 | 0.500 | 0.333 | 0.429 | 0.429 | 1.000 | 0.679 | 0.429 |
| YouTube (Tier A+B+B') | 11 | 0.750 | 0.500 | 0.871 | 0.721 | 1.000 | 0.721 | 0.444 |

## 4.4 Go judgment re-evaluation (clean 22-fold)

| objective | gate | clean value | verdict |
|---|---|---:|:-:|
| Obj B (C_v2 macro F1 >= 0.86) | vs Phase 1.3 C clean (0.823) | 0.791 | No-Go |
| Obj D (C_v3 macro F1 >= 0.86) | vs Phase 1.3 C clean (0.823) | 0.869 | Go |
| bbox v3 (B_v3 YouTube clean >= Phase 1.3 B YouTube clean + 0.10) | Phase 1.3 B YT clean 0.500 -> 0.721 (Δ +0.221) | 0.721 | Go |
| bbox v3 (C_v4 full clean >= Phase 1.3 C full clean + 0.02) | Phase 1.3 C clean 0.823 -> 0.635 (Δ -0.188) | 0.635 | No-Go |

## 4.5 Bootstrap 95% CI for macro F1 (clean 22-fold)

1000-resample bootstrap with seed=42. Paired deltas are indicative only; 
do not substitute for a proper paired statistical test.

| experiment | point | 95% CI (low, high) | CI width |
|---|---:|---|---:|
| Phase 1.3 A | 0.482 | (0.318, 0.659) | 0.341 |
| Phase 1.3 B | 0.669 | (0.534, 0.782) | 0.249 |
| Phase 1.3 C | 0.823 | (0.656, 0.954) | 0.297 |
| Phase 1.4a C_v2 | 0.791 | (0.613, 0.920) | 0.307 |
| Phase 1.4a C_v3 | 0.869 | (0.718, 0.978) | 0.260 |
| Phase 1.4a B_v3 | 0.718 | (0.630, 0.795) | 0.165 |
| Phase 1.4a C_v4 | 0.635 | (0.405, 0.810) | 0.405 |

## 4.6 Mixed-category evaluation is statistically limited

The clean subset contains only 2 `mixed` ("both") folds — both self-recorded (balcony_005, balcony_010). Any per-category macro F1 for `mixed` therefore covers at most 2 independent predictions; the number is reported for completeness but should not be interpreted as model-level behaviour. Grok's suggestion (Macaulay Library / external verified-both clips) remains the primary route to a statistically meaningful `mixed` evaluation.

## Caveats

- Tier B clips contribute the same fold JSONs as in the 42-fold run; the 30 s intro trim is **not** applied here. If Tier B intros dominate the prompt signal on a clip, the clean number still inherits that bias.
- n=22 produces wide unpaired bootstrap CIs (half-widths roughly ±0.08 to ±0.20 across experiments). Single-topology point estimates are loose. A paired bootstrap on (C, C_v3) over the same 22 folds would be tighter because errors are correlated across topologies.
- Robosheep's review is categorical (Tier A/B/B'/C) rather than per-clip scored; within-tier variance is not captured.

## Headline changes vs the 42-fold report

- **Objective D (C_v3 temporal_sync) flips No-Go -> Go** on the clean set (0.869 >= 0.86). The 42-fold No-Go (0.819) was dragged down by Tier C clips whose audio was mostly BGM / text overlays — exactly the situation where a modality-sync signal cannot help.
- **Objective B (C_v2 frame_extractor) stays No-Go** (0.791 < 0.86). Removing no-bird frames does not recover the missing accuracy even on clean data.
- **bbox v3 B_v3 YouTube gate stays Go** (0.721 vs Phase 1.3 B YouTube clean 0.500, +0.221). The relative-distribution prompt continues to beat the absolute-threshold baseline on verified-clean YouTube clips.
- **bbox v3 C_v4 full gate stays No-Go and regresses further** (0.635 vs Phase 1.3 C clean 0.823, −0.188). Combining the relative-distribution prompt with audio fusion is strictly worse than either in isolation.
