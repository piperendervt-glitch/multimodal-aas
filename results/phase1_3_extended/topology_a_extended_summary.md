# Phase 1.3 Topology A extended summary (self + YouTube)

Pipeline: ffmpeg (16 kHz mono) -> BirdNET (birdnetlib) -> `qwen2.5:7b`

- Total folds executed: 42
- Skipped YouTube entries (download failed / missing): 1
- Total wall time: 180.9 s

## Aggregate metrics

| scope | n / scored | fallback | parse_fail | errors | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| **full (self + youtube)** | 42 / 42 | 19 | 0 | 0 | 0.611 | 0.556 | 0.667 |
| self-recorded | 11 / 11 | 10 | 0 | 0 | 0.143 | 0.000 | 0.286 |
| youtube (all) | 31 / 31 | 9 | 0 | 0 | 0.720 | 0.690 | 0.750 |
| youtube-grok | 16 / 16 | 2 | 0 | 0 | 0.812 | 0.800 | 0.824 |
| youtube-claude | 15 / 15 | 7 | 0 | 0 | 0.619 | 0.571 | 0.667 |

## Per-category metrics (full set)

| category | n / scored | fallback | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|
| both | 2 / 2 | 1 | 0.333 | 0.000 | 0.667 |
| bulbul | 16 / 16 | 5 | 0.407 | 0.000 | 0.815 |
| mixed | 8 / 8 | 4 | 0.444 | 0.667 | 0.222 |
| sparrow | 16 / 16 | 9 | 0.273 | 0.545 | 0.000 |

## Per-fold results

| fold | video_id | source | category | GT S/B | pred S/B | S OK | B OK | fallback | t_total |
|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | self | bulbul | 0/1 | 0/0 | OK | X | Y | 5.66 |
| 02 | balcony_002 | self | bulbul | 0/1 | 0/0 | OK | X | Y | 0.50 |
| 03 | balcony_003 | self | bulbul | 0/1 | 0/0 | OK | X | Y | 2.01 |
| 04 | balcony_004 | self | bulbul | 0/1 | 0/0 | OK | X | Y | 1.72 |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | X | OK | - | 8.51 |
| 06 | balcony_006 | self | sparrow | 1/0 | 0/0 | X | OK | Y | 1.95 |
| 07 | balcony_007 | self | sparrow | 1/0 | 0/0 | X | OK | Y | 2.98 |
| 08 | balcony_008 | self | sparrow | 1/0 | 0/0 | X | OK | Y | 0.75 |
| 09 | balcony_009 | self | sparrow | 1/0 | 0/0 | X | OK | Y | 1.87 |
| 10 | balcony_010 | self | both | 1/1 | 0/0 | X | X | Y | 1.08 |
| 11 | balcony_011 | self | sparrow | 1/0 | 0/0 | X | OK | Y | 0.51 |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 0/0 | X | OK | - | 6.03 |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 4.69 |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 4.77 |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 4.79 |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 0/0 | X | OK | Y | 0.85 |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 4.46 |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 0/0 | X | OK | Y | 2.48 |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 8.16 |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/0 | X | OK | Y | 0.26 |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 4.89 |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 0/0 | X | OK | Y | 1.15 |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 4.70 |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 4.79 |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 4.66 |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.48 |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.25 |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 4.69 |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.52 |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 6.21 |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 7.50 |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 8.07 |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 5.47 |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 0/0 | OK | X | Y | 1.96 |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 8.17 |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 0/0 | X | X | Y | 3.74 |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 7.04 |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 0/0 | X | X | Y | 3.74 |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 8.39 |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 0/0 | X | X | Y | 3.73 |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 0/0 | X | X | Y | 3.75 |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 6.80 |

## Skipped YouTube entries

| video_id | category | source | status | error |
|---|---|---|---|---|
| yt_Ji1jooZwBSo | sparrow | grok | failed | WARNING: [youtube] No supported JavaScript runtime could be found. Only deno is  |
