# Phase 1.2 Cross-Modal Comparison

Side-by-side record of the visual (YOLOv8n) and audio (BirdNET) pipelines.
Phase 1.2 only confirms both pipelines run; Mirror Effect analysis is deferred to Phase 1.3.

- Visual JSONs: 11
- Audio JSONs:  11
- Videos in both: 11

## Per-video comparison

| video_id | GT (S/B) | V pred (S/B) | A pred (S/B) | S match V=A | B match V=A | V elapsed | A elapsed |
|---|---|---|---|---|---|---|---|
| balcony_001 | 0/1 | 1/0 | 0/0 | X | OK | 21.35s | 11.56s |
| balcony_002 | 0/1 | 1/0 | 0/0 | X | OK | 5.97s | 4.83s |
| balcony_003 | 0/1 | 1/0 | 0/0 | X | OK | 9.09s | 6.47s |
| balcony_004 | 0/1 | 1/0 | 0/0 | X | OK | 8.87s | 6.45s |
| balcony_005 | 1/1 | 1/0 | 0/1 | X | X | 10.51s | 7.36s |
| balcony_006 | 1/0 | 1/0 | 0/0 | X | OK | 9.33s | 6.32s |
| balcony_007 | 1/0 | 1/0 | 0/0 | X | OK | 10.72s | 7.38s |
| balcony_008 | 1/0 | 1/0 | 1/0 | OK | OK | 6.10s | 5.28s |
| balcony_009 | 1/0 | 1/0 | 0/0 | X | OK | 9.58s | 6.47s |
| balcony_010 | 1/1 | 1/0 | 0/0 | X | OK | 7.96s | 5.63s |
| balcony_011 | 1/0 | 1/0 | 0/0 | X | OK | 5.41s | 4.95s |

## Agreement (both modalities parsed a response)

- Videos with predictions on both sides: 11
- Agree on sparrow: 1 / 11
- Agree on bulbul:  10 / 11
- Agree on both labels: 1 / 11

## Processing time totals

- Visual total elapsed: 104.9 s over 11 videos
- Audio total elapsed:  72.7 s over 11 videos
