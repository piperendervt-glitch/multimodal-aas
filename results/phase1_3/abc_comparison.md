# Phase 1.3 Topology A vs B vs C

- A = Audio-Only (BirdNET -> LLM)
- B = Visual-Only (YOLOv8n -> LLM)
- C = Parallel Fusion (BirdNET + YOLOv8n -> LLM, no BirdNET target threshold)

- Folds with A result: 11 | B: 11 | C: 11

## Overall metrics

| topology | macro F1 | sparrow F1 | bulbul F1 | fallback | mean total (s) |
|---|---:|---:|---:|---:|---:|
| A | 0.143 | 0.000 | 0.286 | 10 / 11 | 2.89 |
| B | 0.819 | 0.714 | 0.923 | 0 / 11 | 8.88 |
| C | 0.733 | 0.800 | 0.667 | 0 / 11 | 10.62 |

## Per-video comparison

| fold | video_id | GT S/B | A pred | B pred | C pred | A full-ok | B full-ok | C full-ok |
|---:|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 01 | balcony_001 | 0/1 | 0/0 | 1/1 | 0/1 | X | X | OK |
| 02 | balcony_002 | 0/1 | 0/0 | 0/1 | 0/1 | X | OK | OK |
| 03 | balcony_003 | 0/1 | 0/0 | 1/1 | 1/0 | X | X | X |
| 04 | balcony_004 | 0/1 | 0/0 | 0/1 | 1/0 | X | OK | X |
| 05 | balcony_005 | 1/1 | 0/1 | 0/1 | 0/1 | X | X | X |
| 06 | balcony_006 | 1/0 | 0/0 | 1/0 | 1/0 | X | OK | OK |
| 07 | balcony_007 | 1/0 | 0/0 | 1/0 | 1/0 | X | OK | OK |
| 08 | balcony_008 | 1/0 | 0/0 | 1/1 | 1/0 | X | X | OK |
| 09 | balcony_009 | 1/0 | 0/0 | 1/0 | 1/0 | X | OK | OK |
| 10 | balcony_010 | 1/1 | 0/0 | 0/1 | 1/0 | X | X | X |
| 11 | balcony_011 | 1/0 | 0/0 | 1/0 | 1/0 | X | OK | OK |

## Pairwise agreement (both sides comparable)

| pair | comparable | sparrow agree | bulbul agree | full match |
|---|---:|---:|---:|---:|
| A vs B | 11 | 4/11 | 5/11 | 1/11 |
| A vs C | 11 | 3/11 | 9/11 | 1/11 |
| B vs C | 11 | 8/11 | 7/11 | 6/11 |

## Correctness split (B vs C)

- Both correct: 5
- Only B correct: 1
- Only C correct: 2
- Both wrong: 3

## Mirror Effect candidate A (pairwise agreement interpretation)

Pairwise agreement is the direct observable for Phase 1.3+ Mirror-Effect analysis. A pipeline that 'mirrors' another will show high agreement even when accuracy differs; a genuinely independent pipeline will show agreement bounded by the bird-distribution prior.

Phase 1.2 / 1.3 runs so far have not been large enough to declare Mirror Effect presence or absence — these counts are recorded as the baseline.
