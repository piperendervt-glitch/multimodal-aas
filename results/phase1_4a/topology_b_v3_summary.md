# Phase 1.4a Topology B_v3 extended summary

Pipeline: ffmpeg @ 1 fps (CFR) -> per-frame YOLOv8n -> bbox_normalizer -> `qwen2.5:7b` (prompt v3 with relative distribution)

- Total folds executed: 42
- Skipped YouTube entries: 1
- Total wall time: 386.3 s

## dominant_range distribution

| dominant_range | count |
|---|---:|
| small | 11 |
| medium | 17 |
| large | 10 |
| none | 4 |

## size_variation_type distribution

| variation_type | count |
|---|---:|
| uniform | 7 |
| mixed | 31 |
| none | 4 |

## Aggregate metrics

| scope | n / scored | fallback | parse_fail | errors | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| **full (self + youtube)** | 42 / 42 | 4 | 0 | 0 | 0.769 | 0.828 | 0.710 |
| self-recorded | 11 / 11 | 0 | 0 | 0 | 0.688 | 0.750 | 0.625 |
| youtube (all) | 31 / 31 | 4 | 0 | 0 | 0.798 | 0.857 | 0.739 |
| youtube-grok | 16 / 16 | 4 | 0 | 0 | 0.778 | 0.889 | 0.667 |
| youtube-claude | 15 / 15 | 0 | 0 | 0 | 0.817 | 0.833 | 0.800 |

## Per-category metrics (full set)

| category | n / scored | fallback | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|
| both | 2 / 2 | 0 | 0.833 | 0.667 | 1.000 |
| bulbul | 16 / 16 | 3 | 0.429 | 0.000 | 0.857 |
| mixed | 8 / 8 | 0 | 1.000 | 1.000 | 1.000 |
| sparrow | 16 / 16 | 1 | 0.484 | 0.968 | 0.000 |

## Per-fold results

| fold | video_id | source | category | GT S/B | pred S/B | S OK | B OK | fallback | t_total | dominant_range | variation_type |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | self | bulbul | 0/1 | 0/1 | OK | OK | - | 18.98 | medium | uniform |
| 02 | balcony_002 | self | bulbul | 0/1 | 1/0 | X | X | - | 7.49 | medium | uniform |
| 03 | balcony_003 | self | bulbul | 0/1 | 1/1 | X | OK | - | 11.00 | medium | uniform |
| 04 | balcony_004 | self | bulbul | 0/1 | 1/1 | X | OK | - | 10.43 | large | mixed |
| 05 | balcony_005 | self | both | 1/1 | 1/1 | OK | OK | - | 11.78 | medium | mixed |
| 06 | balcony_006 | self | sparrow | 1/0 | 1/1 | OK | X | - | 10.86 | small | mixed |
| 07 | balcony_007 | self | sparrow | 1/0 | 1/1 | OK | X | - | 12.93 | small | mixed |
| 08 | balcony_008 | self | sparrow | 1/0 | 1/1 | OK | X | - | 7.74 | small | mixed |
| 09 | balcony_009 | self | sparrow | 1/0 | 1/1 | OK | X | - | 11.01 | small | mixed |
| 10 | balcony_010 | self | both | 1/1 | 0/1 | X | OK | - | 9.24 | large | uniform |
| 11 | balcony_011 | self | sparrow | 1/0 | 1/1 | OK | X | - | 6.83 | small | mixed |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 1/1 | OK | X | - | 9.25 | small | mixed |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 0/0 | X | OK | Y | 0.39 | none | none |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 6.71 | medium | uniform |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/1 | OK | X | - | 6.71 | small | mixed |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 1/1 | OK | X | - | 7.54 | medium | mixed |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 1/1 | OK | X | - | 6.77 | large | mixed |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 1/1 | OK | X | - | 11.10 | medium | mixed |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 1/1 | OK | X | - | 12.77 | small | mixed |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 1/1 | OK | X | - | 6.43 | large | mixed |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/1 | OK | X | - | 6.93 | large | mixed |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 1/1 | OK | X | - | 7.94 | small | mixed |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/0 | OK | X | Y | 0.52 | none | none |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/0 | OK | X | Y | 0.44 | none | none |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/0 | OK | X | Y | 0.35 | none | none |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 1/1 | X | OK | - | 7.56 | small | mixed |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.55 | large | uniform |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 6.66 | large | uniform |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 8.08 | large | mixed |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 1/1 | X | OK | - | 9.60 | medium | mixed |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 12.17 | large | mixed |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 1/1 | X | OK | - | 12.99 | medium | mixed |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 1/1 | X | OK | - | 8.09 | small | mixed |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 1/1 | X | OK | - | 9.51 | medium | mixed |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/1 | OK | OK | - | 13.20 | medium | mixed |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 1/1 | OK | OK | - | 13.44 | medium | mixed |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/1 | OK | OK | - | 11.93 | medium | mixed |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 13.42 | medium | mixed |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 13.79 | large | mixed |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 12.79 | medium | mixed |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 12.96 | medium | mixed |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 10.43 | medium | mixed |
