# Phase 1.4a Topology C_v4 extended summary

Pipeline: per-frame YOLOv8n + bbox_normalizer + BirdNET (target_threshold=None) -> `qwen2.5:7b` (prompt v3, no temporal_sync)

- Total folds executed: 42
- Skipped YouTube entries: 1
- Total wall time: 491.7 s

## Modality used (from LLM response)

| modality | count |
|---|---:|
| both | 24 |
| visual | 12 |
| audio | 4 |
| none | 2 |

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
| **full (self + youtube)** | 42 / 42 | 0 | 0 | 0 | 0.760 | 0.809 | 0.711 |
| self-recorded | 11 / 11 | 0 | 0 | 0 | 0.558 | 0.615 | 0.500 |
| youtube (all) | 31 / 31 | 0 | 0 | 0 | 0.820 | 0.882 | 0.757 |
| youtube-grok | 16 / 16 | 0 | 0 | 0 | 0.826 | 0.875 | 0.778 |
| youtube-claude | 15 / 15 | 0 | 0 | 0 | 0.813 | 0.889 | 0.737 |

## Per-category metrics (full set)

| category | n / scored | fallback | macro F1 | sparrow F1 | bulbul F1 |
|---|---|---:|---:|---:|---:|
| both | 2 / 2 | 0 | 0.333 | 0.000 | 0.667 |
| bulbul | 16 / 16 | 0 | 0.429 | 0.000 | 0.857 |
| mixed | 8 / 8 | 0 | 0.739 | 0.933 | 0.545 |
| sparrow | 16 / 16 | 0 | 0.429 | 0.857 | 0.000 |

## Per-fold results

| fold | video_id | source | category | GT S/B | pred S/B | S OK | B OK | fallback | t_total | dominant_range | variation_type |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | self | bulbul | 0/1 | 0/0 | OK | X | - | 22.63 | medium | uniform |
| 02 | balcony_002 | self | bulbul | 0/1 | 1/0 | X | X | - | 7.51 | medium | uniform |
| 03 | balcony_003 | self | bulbul | 0/1 | 1/0 | X | X | - | 12.44 | medium | uniform |
| 04 | balcony_004 | self | bulbul | 0/1 | 0/1 | OK | OK | - | 11.93 | large | mixed |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | X | OK | - | 15.17 | medium | mixed |
| 06 | balcony_006 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 12.99 | small | mixed |
| 07 | balcony_007 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 15.65 | small | mixed |
| 08 | balcony_008 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 8.94 | small | mixed |
| 09 | balcony_009 | self | sparrow | 1/0 | 1/0 | OK | OK | - | 12.85 | small | mixed |
| 10 | balcony_010 | self | both | 1/1 | 0/0 | X | X | - | 8.37 | large | uniform |
| 11 | balcony_011 | self | sparrow | 1/0 | 0/0 | X | OK | - | 7.68 | small | mixed |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 0/0 | X | OK | - | 10.77 | small | mixed |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 6.67 | none | none |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 7.14 | medium | uniform |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 7.61 | small | mixed |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 1/0 | OK | OK | - | 9.23 | medium | mixed |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 0/1 | X | X | - | 6.67 | large | mixed |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 1/1 | OK | X | - | 13.17 | medium | mixed |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 17.12 | small | mixed |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/1 | X | X | - | 6.88 | large | mixed |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 7.73 | large | mixed |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 1/0 | OK | OK | - | 9.74 | small | mixed |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.23 | none | none |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 6.96 | none | none |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.08 | none | none |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 9.20 | small | mixed |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 9.45 | large | uniform |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 7.67 | large | uniform |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | OK | OK | - | 10.12 | large | mixed |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 12.08 | medium | mixed |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 15.05 | large | mixed |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 17.44 | medium | mixed |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 0/1 | OK | OK | - | 9.76 | small | mixed |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 0/0 | OK | X | - | 11.08 | medium | mixed |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 17.81 | medium | mixed |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 17.71 | medium | mixed |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | OK | X | - | 14.12 | medium | mixed |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 16.67 | medium | mixed |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 0/1 | X | OK | - | 16.77 | large | mixed |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 1/1 | OK | OK | - | 16.21 | medium | mixed |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 15.91 | medium | mixed |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | OK | X | - | 13.31 | medium | mixed |
