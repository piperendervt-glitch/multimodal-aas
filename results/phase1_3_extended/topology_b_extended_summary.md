# Phase 1.3 Topology B extended summary (self + YouTube)

Pipeline: ffmpeg @ 1 fps (CFR) -> YOLOv8n (bird class) -> `qwen2.5:7b`

- Total folds executed: 42
- Skipped YouTube entries: 1
- Total wall time: 320.6 s

## Aggregate metrics

| scope | n / scored | fallback | parse_fail | errors | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| **full (self + youtube)** | 42 / 42 | 4 | 0 | 0 | 0.610 | 0.542 | 0.679 |
| self-recorded | 11 / 11 | 0 | 0 | 0 | 0.795 | 0.667 | 0.923 |
| youtube (all) | 31 / 31 | 4 | 0 | 0 | 0.542 | 0.485 | 0.600 |
| youtube-grok | 16 / 16 | 4 | 0 | 0 | 0.535 | 0.625 | 0.444 |
| youtube-claude | 15 / 15 | 0 | 0 | 0 | 0.540 | 0.353 | 0.727 |

## Per-category metrics (full set)

| category | n / scored | fallback | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|
| both | 2 / 2 | 0 | 0.500 | 0.000 | 1.000 |
| bulbul | 16 / 16 | 3 | 0.429 | 0.000 | 0.857 |
| mixed | 8 / 8 | 0 | 0.667 | 0.667 | 0.667 |
| sparrow | 16 / 16 | 1 | 0.360 | 0.720 | 0.000 |

## Per-fold results

| fold | video_id | source | category | GT S/B | pred S/B | S OK | B OK | fallback | t_total | max_rel | with_bird |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | self | bulbul | 0/1 | 1/1 | X | OK | - | 14.20 | 0.183 | 8 |
| 02 | balcony_002 | self | bulbul | 0/1 | 1/1 | X | OK | - | 5.54 | 0.151 | 10 |
| 03 | balcony_003 | self | bulbul | 0/1 | 1/1 | X | OK | - | 8.75 | 0.139 | 19 |
| 04 | balcony_004 | self | bulbul | 0/1 | 0/1 | OK | OK | - | 8.31 | 0.238 | 113 |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | X | OK | - | 9.37 | 0.212 | 115 |
| 06 | balcony_006 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 8.64 | 0.083 | 24 |
| 07 | balcony_007 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 10.74 | 0.083 | 16 |
| 08 | balcony_008 | self | sparrow | 1/0 | 1/1 | OK | X | - | 6.05 | 0.206 | 21 |
| 09 | balcony_009 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 8.63 | 0.069 | 18 |
| 10 | balcony_010 | self | both | 1/1 | 0/1 | X | OK | - | 6.92 | 0.402 | 64 |
| 11 | balcony_011 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 5.19 | 0.006 | 3 |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 1/1 | OK | X | - | 7.66 | 0.160 | 91 |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 0/0 | X | OK | Y | 0.41 | 0.000 | 0 |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 0/1 | X | X | - | 5.24 | 0.104 | 28 |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.49 | 0.105 | 35 |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 0/1 | X | X | - | 5.98 | 0.356 | 37 |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 0/1 | X | X | - | 4.76 | 0.229 | 9 |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 0/1 | X | X | - | 9.54 | 0.351 | 175 |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 0/1 | X | X | - | 11.38 | 0.108 | 84 |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/1 | X | X | - | 5.18 | 0.558 | 19 |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/1 | OK | X | - | 5.22 | 0.974 | 28 |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 6.62 | 0.040 | 32 |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/0 | OK | X | Y | 0.54 | 0.000 | 0 |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/0 | OK | X | Y | 0.47 | 0.000 | 0 |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/0 | OK | X | Y | 0.37 | 0.000 | 0 |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 1/1 | X | OK | - | 6.69 | 0.333 | 37 |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 6.24 | 0.213 | 55 |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 1/1 | X | OK | - | 5.39 | 0.340 | 23 |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 6.46 | 0.466 | 89 |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 8.01 | 0.259 | 139 |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 1/1 | X | OK | - | 9.96 | 0.778 | 106 |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 1/1 | X | OK | - | 12.48 | 0.165 | 24 |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 1/0 | X | X | - | 6.58 | 0.137 | 60 |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 1/1 | X | OK | - | 7.84 | 0.344 | 148 |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 12.04 | 0.175 | 151 |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 11.81 | 0.287 | 78 |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 9.60 | 0.279 | 156 |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 0/1 | X | OK | - | 11.85 | 0.373 | 219 |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 0/1 | X | OK | - | 11.62 | 0.283 | 210 |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 0/1 | X | OK | - | 11.70 | 0.446 | 119 |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 0/1 | X | OK | - | 11.85 | 0.369 | 162 |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 9.25 | 0.539 | 130 |

## Skipped YouTube entries

| video_id | category | source | status | error |
|---|---|---|---|---|
| yt_Ji1jooZwBSo | sparrow | grok | failed | WARNING: [youtube] No supported JavaScript runtime could be found. Only deno is  |
