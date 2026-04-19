# Phase 1.4a Topology C_v2 extended summary (self + YouTube)

Pipeline: ffmpeg (audio 16 kHz + frames @ 1 fps CFR) -> frame_extractor (YOLOv8n bird pre-filter) -> BirdNET (target_threshold=None) -> `qwen2.5:7b` fusion

- Total folds executed: 42
- Skipped YouTube entries: 1
- Total wall time: 407.1 s

## Modality used (from LLM response)

| modality | count |
|---|---:|
| visual | 22 |
| both | 16 |
| audio | 4 |

## Frame selection rate (bird-detected frames / total sampled)

- mean: 0.509
- min:  0.000
- max:  1.000
- folds with 0% selection (all no-bird): 4

## Aggregate metrics

| scope | n / scored | fallback | parse_fail | errors | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| **full (self + youtube)** | 42 / 42 | 0 | 0 | 0 | 0.826 | 0.880 | 0.773 |
| self-recorded | 11 / 11 | 0 | 0 | 0 | 0.733 | 0.800 | 0.667 |
| youtube (all) | 31 / 31 | 0 | 0 | 0 | 0.857 | 0.914 | 0.800 |
| youtube-grok | 16 / 16 | 0 | 0 | 0 | 0.882 | 0.941 | 0.824 |
| youtube-claude | 15 / 15 | 0 | 0 | 0 | 0.833 | 0.889 | 0.778 |

## Per-category metrics (full set)

| category | n / scored | fallback | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|
| both | 2 / 2 | 0 | 0.667 | 0.667 | 0.667 |
| bulbul | 16 / 16 | 0 | 0.467 | 0.000 | 0.933 |
| mixed | 8 / 8 | 0 | 0.667 | 0.933 | 0.400 |
| sparrow | 16 / 16 | 0 | 0.467 | 0.933 | 0.000 |

## Per-fold results

| fold | video_id | source | category | GT S/B | pred S/B | S OK | B OK | fallback | t_total | modality | sel_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | self | bulbul | 0/1 | 0/1 | OK | OK | - | 20.91 | visual | 0.022 |
| 02 | balcony_002 | self | bulbul | 0/1 | 0/1 | OK | OK | - | 6.04 | visual | 0.244 |
| 03 | balcony_003 | self | bulbul | 0/1 | 1/0 | X | X | - | 10.55 | visual | 0.114 |
| 04 | balcony_004 | self | bulbul | 0/1 | 1/0 | X | X | - | 10.34 | visual | 0.779 |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | X | OK | - | 12.03 | both | 0.584 |
| 06 | balcony_006 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 10.13 | visual | 0.150 |
| 07 | balcony_007 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 12.92 | visual | 0.066 |
| 08 | balcony_008 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 6.97 | visual | 0.339 |
| 09 | balcony_009 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 10.40 | visual | 0.116 |
| 10 | balcony_010 | self | both | 1/1 | 1/0 | OK | X | - | 8.19 | visual | 0.719 |
| 11 | balcony_011 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 6.00 | visual | 0.070 |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 0/0 | X | OK | - | 8.74 | visual | 0.722 |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.17 | audio | 0.000 |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.63 | both | 1.000 |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 6.11 | both | 1.000 |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 6.99 | visual | 0.561 |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.04 | both | 0.900 |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 11.19 | visual | 0.897 |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 14.52 | visual | 0.280 |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/1 | X | X | - | 5.12 | visual | 1.000 |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 5.98 | both | 0.849 |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 7.35 | visual | 0.352 |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.45 | audio | 0.000 |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.25 | audio | 0.000 |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.24 | audio | 0.000 |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.38 | both | 0.457 |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.42 | both | 0.775 |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.71 | both | 0.742 |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 8.05 | both | 0.937 |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 9.54 | both | 0.952 |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 12.91 | both | 0.447 |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 14.58 | both | 0.080 |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 7.69 | both | 0.690 |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 10.11 | visual | 0.955 |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 14.52 | both | 0.503 |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 14.50 | visual | 0.260 |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 11.78 | both | 0.746 |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 14.59 | visual | 0.730 |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 14.91 | both | 0.700 |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 14.43 | visual | 0.397 |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 0/1 | X | OK | - | 14.72 | visual | 0.540 |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 10.71 | visual | 0.718 |

## Skipped YouTube entries

| video_id | category | source | status | error |
|---|---|---|---|---|
| yt_Ji1jooZwBSo | sparrow | grok | failed | WARNING: [youtube] No supported JavaScript runtime could be found. Only deno is  |
