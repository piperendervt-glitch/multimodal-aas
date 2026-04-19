# Phase 1.4a Topology C_v3 extended summary (self + YouTube)

Pipeline: ffmpeg -> per-frame YOLOv8n + BirdNET (target_threshold=None) -> temporal_sampler (2s windows, sync_summary) -> `qwen2.5:7b` fusion

- Total folds executed: 42
- Skipped YouTube entries: 1
- Total wall time: 417.2 s

## Modality used (from LLM response)

| modality | count |
|---|---:|
| both | 20 |
| visual | 18 |
| audio | 3 |
| none | 1 |

## sync_rate distribution

- mean: 0.205
- min:  0.000
- max:  1.000
- folds with sync_rate = 0: 21

## sync_rate vs correctness

| subset | n | mean sync_rate |
|---|---:|---:|
| fully correct | 29 | 0.283 |
| at least one class wrong | 13 | 0.030 |

## Aggregate metrics

| scope | n / scored | fallback | parse_fail | errors | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| **full (self + youtube)** | 42 / 42 | 0 | 0 | 0 | 0.819 | 0.906 | 0.732 |
| self-recorded | 11 / 11 | 0 | 0 | 0 | 0.733 | 0.800 | 0.667 |
| youtube (all) | 31 / 31 | 0 | 0 | 0 | 0.849 | 0.947 | 0.750 |
| youtube-grok | 16 / 16 | 0 | 0 | 0 | 0.875 | 1.000 | 0.750 |
| youtube-claude | 15 / 15 | 0 | 0 | 0 | 0.825 | 0.900 | 0.750 |

## Per-category metrics (full set)

| category | n / scored | fallback | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|
| both | 2 / 2 | 0 | 0.667 | 0.667 | 0.667 |
| bulbul | 16 / 16 | 0 | 0.429 | 0.000 | 0.857 |
| mixed | 8 / 8 | 0 | 0.667 | 0.933 | 0.400 |
| sparrow | 16 / 16 | 0 | 0.500 | 1.000 | 0.000 |

## Per-fold results

| fold | video_id | source | category | GT S/B | pred S/B | S OK | B OK | fallback | t_total | modality | sync_rate | num_windows |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | self | bulbul | 0/1 | 0/1 | OK | OK | - | 20.48 | visual | 0.000 | 181 |
| 02 | balcony_002 | self | bulbul | 0/1 | 0/1 | OK | OK | - | 6.21 | visual | 0.000 | 21 |
| 03 | balcony_003 | self | bulbul | 0/1 | 1/0 | X | X | - | 10.83 | visual | 0.000 | 84 |
| 04 | balcony_004 | self | bulbul | 0/1 | 1/0 | X | X | - | 10.54 | visual | 0.000 | 73 |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | X | OK | - | 12.13 | both | 0.026 | 99 |
| 06 | balcony_006 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 10.59 | visual | 0.000 | 80 |
| 07 | balcony_007 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 13.23 | visual | 0.000 | 121 |
| 08 | balcony_008 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 7.23 | both | 0.250 | 32 |
| 09 | balcony_009 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 10.65 | visual | 0.000 | 78 |
| 10 | balcony_010 | self | both | 1/1 | 1/0 | OK | X | - | 8.23 | visual | 0.000 | 45 |
| 11 | balcony_011 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 6.23 | visual | 0.000 | 22 |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 9.21 | visual | 0.231 | 64 |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.21 | audio | 0.000 | 9 |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.80 | both | 1.000 | 15 |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.95 | both | 1.000 | 18 |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 7.20 | both | 0.286 | 34 |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.06 | both | 0.400 | 6 |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 11.47 | visual | 0.000 | 98 |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 15.04 | both | 0.149 | 151 |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 5.52 | visual | 0.000 | 10 |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 6.18 | both | 0.647 | 17 |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 7.81 | visual | 0.000 | 46 |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/0 | OK | X | - | 5.49 | none | 0.000 | 12 |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.45 | audio | 0.000 | 11 |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.26 | audio | 0.000 | 9 |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.52 | both | 0.464 | 41 |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.12 | both | 0.457 | 36 |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.96 | both | 0.929 | 16 |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 8.21 | both | 0.391 | 48 |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 10.01 | both | 0.597 | 74 |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 13.38 | both | 0.457 | 119 |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 14.96 | both | 0.118 | 151 |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 7.69 | both | 0.727 | 44 |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 1/0 | X | X | - | 10.32 | visual | 0.000 | 78 |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 15.37 | both | 0.076 | 151 |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 14.64 | visual | 0.000 | 151 |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 12.25 | both | 0.232 | 105 |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 15.25 | visual | 0.000 | 151 |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 0/1 | X | OK | - | 14.88 | both | 0.054 | 151 |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 15.10 | visual | 0.000 | 151 |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 15.10 | visual | 0.000 | 151 |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 11.07 | both | 0.107 | 91 |

## Skipped YouTube entries

| video_id | category | source | status | error |
|---|---|---|---|---|
| yt_Ji1jooZwBSo | sparrow | grok | failed | WARNING: [youtube] No supported JavaScript runtime could be found. Only deno is  |
