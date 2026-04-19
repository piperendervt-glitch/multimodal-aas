# Phase 1.3 Topology A vs B

- Topology A = Audio-Only (BirdNET -> LLM)
- Topology B = Visual-Only (YOLOv8n -> LLM)

- Folds with A result: 11
- Folds with B result: 11
- Common folds: 11

## Per-video comparison

| fold | video_id | GT (S/B) | A pred | B pred | S match A=B | B match A=B | A fb | B fb | A t | B t |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | 0/1 | 0/0 | 1/1 | X | X | Y | - | 8.60s | 17.69s |
| 02 | balcony_002 | 0/1 | 0/0 | 0/1 | OK | X | Y | - | 0.68s | 6.26s |
| 03 | balcony_003 | 0/1 | 0/0 | 1/1 | X | X | Y | - | 2.79s | 9.50s |
| 04 | balcony_004 | 0/1 | 0/0 | 0/1 | OK | X | Y | - | 1.90s | 8.45s |
| 05 | balcony_005 | 1/1 | 0/1 | 0/1 | OK | OK | - | - | 7.39s | 9.51s |
| 06 | balcony_006 | 1/0 | 0/0 | 1/0 | X | OK | Y | - | 2.11s | 8.52s |
| 07 | balcony_007 | 1/0 | 0/0 | 1/0 | X | OK | Y | - | 3.51s | 10.45s |
| 08 | balcony_008 | 1/0 | 0/0 | 1/1 | X | X | Y | - | 0.96s | 6.32s |
| 09 | balcony_009 | 1/0 | 0/0 | 1/0 | X | OK | Y | - | 2.14s | 8.70s |
| 10 | balcony_010 | 1/1 | 0/0 | 0/1 | OK | X | Y | - | 1.14s | 7.05s |
| 11 | balcony_011 | 1/0 | 0/0 | 1/0 | X | OK | Y | - | 0.56s | 5.24s |

## Agreement (folds comparable on both sides)

- Comparable folds: 11
- Agree on sparrow:  4 / 11
- Agree on bulbul:   5 / 11
- Agree on both labels (full match): 1 / 11

## Correctness split (diagnostic for Mirror Effect candidate A)

- Both correct:      0 / 11
- Only A correct:    0 / 11
- Only B correct:    6 / 11
- Both wrong:        5 / 11

Ground-truth pattern distribution (comparable folds):
- `1/0`: 5
- `0/1`: 4
- `1/1`: 2

Phase 1.2 only ran end-to-end smoke tests; these counts are retained for Phase 1.3+ analysis and should not be interpreted as a Mirror Effect result.
