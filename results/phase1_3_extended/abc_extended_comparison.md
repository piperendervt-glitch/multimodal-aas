# Phase 1.3 extended — Topology A vs B vs C (43 folds)

- A = Audio-Only (BirdNET -> LLM)
- B = Visual-Only (YOLOv8n -> LLM)
- C = Parallel Fusion (BirdNET + YOLOv8n -> LLM, target_threshold=None)

- Folds with A result: 42 | B: 42 | C: 42

## Topology-level metric breakdowns

### Topology A

| scope | n / scored | fallback | errors | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|---:|
| full | 42 / 42 | 19 | 0 | 0.611 | 0.556 | 0.667 |
| self-recorded | 11 / 11 | 10 | 0 | 0.143 | 0.000 | 0.286 |
| youtube (all) | 31 / 31 | 9 | 0 | 0.720 | 0.690 | 0.750 |
| youtube-grok | 16 / 16 | 2 | 0 | 0.812 | 0.800 | 0.824 |
| youtube-claude | 15 / 15 | 7 | 0 | 0.619 | 0.571 | 0.667 |
| category=both | 2 / 2 | 1 | 0 | 0.333 | 0.000 | 0.667 |
| category=bulbul | 16 / 16 | 5 | 0 | 0.407 | 0.000 | 0.815 |
| category=mixed | 8 / 8 | 4 | 0 | 0.444 | 0.667 | 0.222 |
| category=sparrow | 16 / 16 | 9 | 0 | 0.273 | 0.545 | 0.000 |

### Topology B

| scope | n / scored | fallback | errors | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|---:|
| full | 42 / 42 | 4 | 0 | 0.610 | 0.542 | 0.679 |
| self-recorded | 11 / 11 | 0 | 0 | 0.795 | 0.667 | 0.923 |
| youtube (all) | 31 / 31 | 4 | 0 | 0.542 | 0.485 | 0.600 |
| youtube-grok | 16 / 16 | 4 | 0 | 0.535 | 0.625 | 0.444 |
| youtube-claude | 15 / 15 | 0 | 0 | 0.540 | 0.353 | 0.727 |
| category=both | 2 / 2 | 0 | 0 | 0.500 | 0.000 | 1.000 |
| category=bulbul | 16 / 16 | 3 | 0 | 0.429 | 0.000 | 0.857 |
| category=mixed | 8 / 8 | 0 | 0 | 0.667 | 0.667 | 0.667 |
| category=sparrow | 16 / 16 | 1 | 0 | 0.360 | 0.720 | 0.000 |

### Topology C

| scope | n / scored | fallback | errors | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|---:|
| full | 42 / 42 | 0 | 0 | 0.840 | 0.880 | 0.800 |
| self-recorded | 11 / 11 | 0 | 0 | 0.733 | 0.800 | 0.667 |
| youtube (all) | 31 / 31 | 0 | 0 | 0.874 | 0.914 | 0.833 |
| youtube-grok | 16 / 16 | 0 | 0 | 0.912 | 1.000 | 0.824 |
| youtube-claude | 15 / 15 | 0 | 0 | 0.833 | 0.824 | 0.842 |
| category=both | 2 / 2 | 0 | 0 | 0.667 | 0.667 | 0.667 |
| category=bulbul | 16 / 16 | 0 | 0 | 0.467 | 0.000 | 0.933 |
| category=mixed | 8 / 8 | 0 | 0 | 0.701 | 0.857 | 0.545 |
| category=sparrow | 16 / 16 | 0 | 0 | 0.484 | 0.968 | 0.000 |

## Per-video comparison

| fold | video_id | source | category | GT S/B | A pred | B pred | C pred | A full-ok | B full-ok | C full-ok |
|---:|---|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 01 | balcony_001 | self | bulbul | 0/1 | 0/0 | 1/1 | 0/1 | X | X | OK |
| 02 | balcony_002 | self | bulbul | 0/1 | 0/0 | 1/1 | 0/1 | X | X | OK |
| 03 | balcony_003 | self | bulbul | 0/1 | 0/0 | 1/1 | 1/0 | X | X | X |
| 04 | balcony_004 | self | bulbul | 0/1 | 0/0 | 0/1 | 1/0 | X | OK | X |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | 0/1 | 0/1 | X | X | X |
| 06 | balcony_006 | self | sparrow | 1/0 | 0/0 | 1/0 | 1/0 | X | OK | OK |
| 07 | balcony_007 | self | sparrow | 1/0 | 0/0 | 1/0 | 1/0 | X | OK | OK |
| 08 | balcony_008 | self | sparrow | 1/0 | 0/0 | 1/1 | 1/0 | X | X | OK |
| 09 | balcony_009 | self | sparrow | 1/0 | 0/0 | 1/0 | 1/0 | X | OK | OK |
| 10 | balcony_010 | self | both | 1/1 | 0/0 | 0/1 | 1/0 | X | X | X |
| 11 | balcony_011 | self | sparrow | 1/0 | 0/0 | 1/0 | 1/0 | X | OK | OK |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 0/0 | 1/1 | 1/0 | X | X | OK |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 1/0 | 0/0 | 1/0 | OK | X | OK |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 1/0 | 0/1 | 1/0 | OK | X | OK |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | OK | OK | OK |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 0/0 | 0/1 | 1/0 | X | X | OK |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 1/0 | 0/1 | 1/0 | OK | X | OK |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 0/0 | 0/1 | 1/0 | X | X | OK |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 1/0 | 0/1 | 1/0 | OK | X | OK |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/0 | 0/1 | 0/1 | X | X | X |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/0 | 1/1 | 1/0 | OK | X | OK |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 0/0 | 1/0 | 1/0 | X | OK | OK |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/1 | 0/0 | 0/1 | OK | X | OK |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/1 | 0/0 | 0/1 | OK | X | OK |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/1 | 0/0 | 0/1 | OK | X | OK |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 0/1 | 1/1 | 0/1 | OK | X | OK |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | OK | OK | OK |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 0/1 | 1/1 | 0/1 | OK | X | OK |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | OK | OK | OK |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | OK | OK | OK |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 0/1 | 1/1 | 0/1 | OK | X | OK |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 0/1 | 1/1 | 0/1 | OK | X | OK |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 0/1 | 1/0 | 0/1 | OK | X | OK |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 0/0 | 1/1 | 0/1 | X | X | OK |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | 1/0 | 1/0 | X | X | X |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 0/0 | 1/0 | 1/0 | X | X | X |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | 1/0 | 1/0 | X | X | X |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 0/0 | 0/1 | 1/0 | X | X | X |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 1/1 | 0/1 | 0/1 | OK | X | X |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 0/0 | 0/1 | 1/1 | X | X | OK |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 0/0 | 0/1 | 0/1 | X | X | X |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | 1/0 | 1/0 | X | X | X |

## Pairwise agreement (both sides scored)

| pair | comparable | sparrow agree | bulbul agree | full match |
|---|---:|---:|---:|---:|
| A vs B | 42 | 20/42 | 20/42 | 8/42 |
| A vs C | 42 | 26/42 | 36/42 | 21/42 |
| B vs C | 42 | 24/42 | 26/42 | 17/42 |
