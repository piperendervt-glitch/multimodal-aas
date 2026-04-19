# Phase 1.3 Topology C extended summary (self + YouTube)

Pipeline: ffmpeg (audio 16 kHz + frames @ 1 fps CFR) -> BirdNET + YOLOv8n -> `qwen2.5:7b` fusion (BirdNET target_threshold=None, all detections forwarded to LLM)

- Total folds executed: 42
- Skipped YouTube entries: 1
- Total wall time: 411.6 s

## Modality used (from LLM response)

| modality | count |
|---|---:|
| visual | 19 |
| both | 19 |
| audio | 4 |

## Aggregate metrics

| scope | n / scored | fallback | parse_fail | errors | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| **full (self + youtube)** | 42 / 42 | 0 | 0 | 0 | 0.840 | 0.880 | 0.800 |
| self-recorded | 11 / 11 | 0 | 0 | 0 | 0.733 | 0.800 | 0.667 |
| youtube (all) | 31 / 31 | 0 | 0 | 0 | 0.874 | 0.914 | 0.833 |
| youtube-grok | 16 / 16 | 0 | 0 | 0 | 0.912 | 1.000 | 0.824 |
| youtube-claude | 15 / 15 | 0 | 0 | 0 | 0.833 | 0.824 | 0.842 |

## Per-category metrics (full set)

| category | n / scored | fallback | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|
| both | 2 / 2 | 0 | 0.667 | 0.667 | 0.667 |
| bulbul | 16 / 16 | 0 | 0.467 | 0.000 | 0.933 |
| mixed | 8 / 8 | 0 | 0.701 | 0.857 | 0.545 |
| sparrow | 16 / 16 | 0 | 0.484 | 0.968 | 0.000 |

## Per-fold results

| fold | video_id | source | category | GT S/B | pred S/B | S OK | B OK | fallback | t_total | modality |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | self | bulbul | 0/1 | 0/1 | OK | OK | - | 20.41 | visual |
| 02 | balcony_002 | self | bulbul | 0/1 | 0/1 | OK | OK | - | 6.05 | visual |
| 03 | balcony_003 | self | bulbul | 0/1 | 1/0 | X | X | - | 10.76 | visual |
| 04 | balcony_004 | self | bulbul | 0/1 | 1/0 | X | X | - | 10.07 | visual |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | X | OK | - | 12.35 | both |
| 06 | balcony_006 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 10.54 | visual |
| 07 | balcony_007 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 13.38 | visual |
| 08 | balcony_008 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 7.14 | visual |
| 09 | balcony_009 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 10.52 | visual |
| 10 | balcony_010 | self | both | 1/1 | 1/0 | OK | X | - | 8.28 | visual |
| 11 | balcony_011 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 5.98 | visual |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 9.04 | visual |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.14 | audio |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 5.62 | both |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 6.13 | both |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 7.07 | both |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 4.98 | both |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 11.17 | visual |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 15.00 | both |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/1 | X | X | - | 5.37 | visual |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 5.85 | both |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 7.61 | visual |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.58 | audio |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.25 | audio |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.20 | audio |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.57 | both |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.08 | both |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 5.72 | both |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.92 | both |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 9.84 | both |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 12.67 | both |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 15.12 | both |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 7.83 | both |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 10.09 | both |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 15.03 | both |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 14.70 | visual |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 12.03 | both |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 14.81 | visual |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 0/1 | X | OK | - | 15.19 | both |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 14.70 | visual |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 0/1 | X | OK | - | 14.71 | visual |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 10.91 | visual |

## Skipped YouTube entries

| video_id | category | source | status | error |
|---|---|---|---|---|
| yt_Ji1jooZwBSo | sparrow | grok | failed | WARNING: [youtube] No supported JavaScript runtime could be found. Only deno is  |
