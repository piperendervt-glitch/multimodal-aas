# Phase 1.4a bbox prompt v3 summary (B_v3, C_v4)

Replaces Phase 1.3 Topology B/C absolute bbox thresholds (sparrow < 0.08, 
bulbul >= 0.13) with relative distribution features (dominant_range, 
size_variation_type).

- B_v3: Visual-Only with prompt v3.
- C_v4: Parallel Fusion with prompt v3 (no temporal_sync, no frame pre-filter).

## Metric deltas (B / B_v3, C / C_v4)

### Full (self + YouTube)

| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |
|---|---:|---:|---:|---:|---:|---:|
| macro F1 | 0.610 | 0.769 | +0.158 | 0.840 | 0.760 | -0.080 |
| sparrow F1 | 0.542 | 0.828 | +0.286 | 0.880 | 0.809 | -0.071 |
| bulbul F1 | 0.679 | 0.710 | +0.030 | 0.800 | 0.711 | -0.089 |
| fallback | 4 | 4 | +0 | 0 | 0 | +0 |
| scored | 42/42 | 42/42 | | 42/42 | 42/42 | |

### Self-recorded only

| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |
|---|---:|---:|---:|---:|---:|---:|
| macro F1 | 0.795 | 0.688 | -0.107 | 0.733 | 0.558 | -0.176 |
| sparrow F1 | 0.667 | 0.750 | +0.083 | 0.800 | 0.615 | -0.185 |
| bulbul F1 | 0.923 | 0.625 | -0.298 | 0.667 | 0.500 | -0.167 |
| fallback | 0 | 0 | +0 | 0 | 0 | +0 |
| scored | 11/11 | 11/11 | | 11/11 | 11/11 | |

### YouTube only

| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |
|---|---:|---:|---:|---:|---:|---:|
| macro F1 | 0.542 | 0.798 | +0.256 | 0.874 | 0.820 | -0.054 |
| sparrow F1 | 0.485 | 0.857 | +0.372 | 0.914 | 0.882 | -0.032 |
| bulbul F1 | 0.600 | 0.739 | +0.139 | 0.833 | 0.757 | -0.077 |
| fallback | 4 | 4 | +0 | 0 | 0 | +0 |
| scored | 31/31 | 31/31 | | 31/31 | 31/31 | |

### YouTube-grok

| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |
|---|---:|---:|---:|---:|---:|---:|
| macro F1 | 0.535 | 0.778 | +0.243 | 0.912 | 0.826 | -0.085 |
| sparrow F1 | 0.625 | 0.889 | +0.264 | 1.000 | 0.875 | -0.125 |
| bulbul F1 | 0.444 | 0.667 | +0.222 | 0.824 | 0.778 | -0.046 |
| fallback | 4 | 4 | +0 | 0 | 0 | +0 |
| scored | 16/16 | 16/16 | | 16/16 | 16/16 | |

### YouTube-claude

| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |
|---|---:|---:|---:|---:|---:|---:|
| macro F1 | 0.540 | 0.817 | +0.277 | 0.833 | 0.813 | -0.020 |
| sparrow F1 | 0.353 | 0.833 | +0.480 | 0.824 | 0.889 | +0.065 |
| bulbul F1 | 0.727 | 0.800 | +0.073 | 0.842 | 0.737 | -0.105 |
| fallback | 0 | 0 | +0 | 0 | 0 | +0 |
| scored | 15/15 | 15/15 | | 15/15 | 15/15 | |

### Category = both

| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |
|---|---:|---:|---:|---:|---:|---:|
| macro F1 | 0.500 | 0.833 | +0.333 | 0.667 | 0.333 | -0.333 |
| sparrow F1 | 0.000 | 0.667 | +0.667 | 0.667 | 0.000 | -0.667 |
| bulbul F1 | 1.000 | 1.000 | +0.000 | 0.667 | 0.667 | +0.000 |
| fallback | 0 | 0 | +0 | 0 | 0 | +0 |
| scored | 2/2 | 2/2 | | 2/2 | 2/2 | |

### Category = bulbul

| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |
|---|---:|---:|---:|---:|---:|---:|
| macro F1 | 0.429 | 0.429 | +0.000 | 0.467 | 0.429 | -0.038 |
| sparrow F1 | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | +0.000 |
| bulbul F1 | 0.857 | 0.857 | +0.000 | 0.933 | 0.857 | -0.076 |
| fallback | 3 | 3 | +0 | 0 | 0 | +0 |
| scored | 16/16 | 16/16 | | 16/16 | 16/16 | |

### Category = mixed

| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |
|---|---:|---:|---:|---:|---:|---:|
| macro F1 | 0.667 | 1.000 | +0.333 | 0.701 | 0.739 | +0.038 |
| sparrow F1 | 0.667 | 1.000 | +0.333 | 0.857 | 0.933 | +0.076 |
| bulbul F1 | 0.667 | 1.000 | +0.333 | 0.545 | 0.545 | +0.000 |
| fallback | 0 | 0 | +0 | 0 | 0 | +0 |
| scored | 8/8 | 8/8 | | 8/8 | 8/8 | |

### Category = sparrow

| metric | Phase 1.3 B | B_v3 | Δ(B_v3-B) | Phase 1.3 C | C_v4 | Δ(C_v4-C) |
|---|---:|---:|---:|---:|---:|---:|
| macro F1 | 0.360 | 0.484 | +0.124 | 0.484 | 0.429 | -0.055 |
| sparrow F1 | 0.720 | 0.968 | +0.248 | 0.968 | 0.857 | -0.111 |
| bulbul F1 | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | +0.000 |
| fallback | 1 | 1 | +0 | 0 | 0 | +0 |
| scored | 16/16 | 16/16 | | 16/16 | 16/16 | |

## dominant_range distribution by ground-truth category (C_v4)

| category | small | medium | large | none |
|---|---:|---:|---:|---:|
| sparrow | 9 | 3 | 3 | 1 |
| bulbul | 2 | 6 | 5 | 3 |
| mixed | 0 | 7 | 1 | 0 |
| both | 0 | 1 | 1 | 0 |

## size_variation_type distribution (C_v4)

| variation_type | count |
|---|---:|
| uniform | 7 |
| mixed | 31 |
| none | 4 |

## Per-fold side-by-side

| fold | video_id | source | category | GT S/B | B | B_v3 | C | C_v4 | dom | var |
|---:|---|---|---|:-:|:-:|:-:|:-:|:-:|---|---|
| 01 | balcony_001 | self | bulbul | 0/1 | 1/1 | 0/1 | 0/1 | 0/0 | medium | uniform |
| 02 | balcony_002 | self | bulbul | 0/1 | 1/1 | 1/0 | 0/1 | 1/0 | medium | uniform |
| 03 | balcony_003 | self | bulbul | 0/1 | 1/1 | 1/1 | 1/0 | 1/0 | medium | uniform |
| 04 | balcony_004 | self | bulbul | 0/1 | 0/1 | 1/1 | 1/0 | 0/1 | large | mixed |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | 1/1 | 0/1 | 0/1 | medium | mixed |
| 06 | balcony_006 | self | sparrow | 1/0 | 1/0 | 1/1 | 1/0 | 1/0 | small | mixed |
| 07 | balcony_007 | self | sparrow | 1/0 | 1/0 | 1/1 | 1/0 | 1/0 | small | mixed |
| 08 | balcony_008 | self | sparrow | 1/0 | 1/1 | 1/1 | 1/0 | 1/0 | small | mixed |
| 09 | balcony_009 | self | sparrow | 1/0 | 1/0 | 1/1 | 1/0 | 1/0 | small | mixed |
| 10 | balcony_010 | self | both | 1/1 | 0/1 | 0/1 | 1/0 | 0/0 | large | uniform |
| 11 | balcony_011 | self | sparrow | 1/0 | 1/0 | 1/1 | 1/0 | 0/0 | small | mixed |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 1/1 | 1/1 | 1/0 | 0/0 | small | mixed |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 0/0 | 0/0 | 1/0 | 1/0 | none | none |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 0/1 | 1/0 | 1/0 | 1/0 | medium | uniform |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | 1/1 | 1/0 | 1/0 | small | mixed |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 0/1 | 1/1 | 1/0 | 1/0 | medium | mixed |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 0/1 | 1/1 | 1/0 | 0/1 | large | mixed |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 0/1 | 1/1 | 1/0 | 1/1 | medium | mixed |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 0/1 | 1/1 | 1/0 | 1/0 | small | mixed |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/1 | 1/1 | 0/1 | 0/1 | large | mixed |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/1 | 1/1 | 1/0 | 1/0 | large | mixed |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 1/0 | 1/1 | 1/0 | 1/0 | small | mixed |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/0 | 0/0 | 0/1 | 0/1 | none | none |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/0 | 0/0 | 0/1 | 0/1 | none | none |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/0 | 0/0 | 0/1 | 0/1 | none | none |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | small | mixed |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | large | uniform |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 | large | uniform |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | large | mixed |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | medium | mixed |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 | large | mixed |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | medium | mixed |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 1/0 | 1/1 | 0/1 | 0/1 | small | mixed |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 1/1 | 1/1 | 0/1 | 0/0 | medium | mixed |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | 1/1 | 1/0 | 1/0 | medium | mixed |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 1/0 | 1/1 | 1/0 | 1/0 | medium | mixed |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | 1/1 | 1/0 | 1/0 | medium | mixed |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 0/1 | 1/1 | 1/0 | 1/1 | medium | mixed |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 0/1 | 1/1 | 0/1 | 0/1 | large | mixed |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | medium | mixed |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 0/1 | 1/1 | 0/1 | 1/0 | medium | mixed |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | 1/1 | 1/0 | 1/0 | medium | mixed |

## Flip summary

| comparison | both correct | new wins | regressions | both wrong |
|---|---:|---:|---:|---:|
| B vs B_v3 | 2 | 13 | 8 | 19 |
| C vs C_v4 | 23 | 2 | 7 | 10 |

## Go / No-Go judgment

| gate | threshold | measured | pass? |
|---|---:|---:|:-:|
| B_v3 YouTube macro F1 | >= 0.642 | 0.798 | OK |
| C_v4 YouTube macro F1 | >= 0.894 | 0.820 | X |
| C_v4 full macro F1   | >= 0.860 | 0.760 | X |

**Go** (any of the three gates is sufficient).
