# Phase 1.4a Topology variants comparison (C / C_v2 / C_v3)

- Phase 1.3 C: Parallel Fusion, no frame pre-filter, no temporal alignment
- Phase 1.4a C_v2: + frame_extractor pre-filter (objective B)
- Phase 1.4a C_v3: + temporal_sampler (2s windows, sync_summary) -- objective D

- Folds: C=42  C_v2=42  C_v3=42

## Metric deltas

### Full (self + YouTube)

| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |
|---|---:|---:|---:|---:|
| n (scored) | 42 (42) | 42 (42) | 42 (42) | - |
| fallback | 0 | 0 | 0 | +0 |
| macro F1 | 0.840 | 0.826 | 0.819 | -0.021 |
| sparrow F1 | 0.880 | 0.880 | 0.906 | +0.026 |
| bulbul F1 | 0.800 | 0.773 | 0.732 | -0.068 |

### Self-recorded only

| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |
|---|---:|---:|---:|---:|
| n (scored) | 11 (11) | 11 (11) | 11 (11) | - |
| fallback | 0 | 0 | 0 | +0 |
| macro F1 | 0.733 | 0.733 | 0.733 | +0.000 |
| sparrow F1 | 0.800 | 0.800 | 0.800 | +0.000 |
| bulbul F1 | 0.667 | 0.667 | 0.667 | +0.000 |

### YouTube only

| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |
|---|---:|---:|---:|---:|
| n (scored) | 31 (31) | 31 (31) | 31 (31) | - |
| fallback | 0 | 0 | 0 | +0 |
| macro F1 | 0.874 | 0.857 | 0.849 | -0.025 |
| sparrow F1 | 0.914 | 0.914 | 0.947 | +0.033 |
| bulbul F1 | 0.833 | 0.800 | 0.750 | -0.083 |

### YouTube-grok

| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |
|---|---:|---:|---:|---:|
| n (scored) | 16 (16) | 16 (16) | 16 (16) | - |
| fallback | 0 | 0 | 0 | +0 |
| macro F1 | 0.912 | 0.882 | 0.875 | -0.037 |
| sparrow F1 | 1.000 | 0.941 | 1.000 | +0.000 |
| bulbul F1 | 0.824 | 0.824 | 0.750 | -0.074 |

### YouTube-claude

| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |
|---|---:|---:|---:|---:|
| n (scored) | 15 (15) | 15 (15) | 15 (15) | - |
| fallback | 0 | 0 | 0 | +0 |
| macro F1 | 0.833 | 0.833 | 0.825 | -0.008 |
| sparrow F1 | 0.824 | 0.889 | 0.900 | +0.076 |
| bulbul F1 | 0.842 | 0.778 | 0.750 | -0.092 |

### Category = both

| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |
|---|---:|---:|---:|---:|
| n (scored) | 2 (2) | 2 (2) | 2 (2) | - |
| fallback | 0 | 0 | 0 | +0 |
| macro F1 | 0.667 | 0.667 | 0.667 | +0.000 |
| sparrow F1 | 0.667 | 0.667 | 0.667 | +0.000 |
| bulbul F1 | 0.667 | 0.667 | 0.667 | +0.000 |

### Category = bulbul

| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |
|---|---:|---:|---:|---:|
| n (scored) | 16 (16) | 16 (16) | 16 (16) | - |
| fallback | 0 | 0 | 0 | +0 |
| macro F1 | 0.467 | 0.467 | 0.429 | -0.038 |
| sparrow F1 | 0.000 | 0.000 | 0.000 | +0.000 |
| bulbul F1 | 0.933 | 0.933 | 0.857 | -0.076 |

### Category = mixed

| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |
|---|---:|---:|---:|---:|
| n (scored) | 8 (8) | 8 (8) | 8 (8) | - |
| fallback | 0 | 0 | 0 | +0 |
| macro F1 | 0.701 | 0.667 | 0.667 | -0.035 |
| sparrow F1 | 0.857 | 0.933 | 0.933 | +0.076 |
| bulbul F1 | 0.545 | 0.400 | 0.400 | -0.145 |

### Category = sparrow

| metric | Phase 1.3 C | Phase 1.4a C_v2 | Phase 1.4a C_v3 | Δ(v3 - C) |
|---|---:|---:|---:|---:|
| n (scored) | 16 (16) | 16 (16) | 16 (16) | - |
| fallback | 0 | 0 | 0 | +0 |
| macro F1 | 0.484 | 0.467 | 0.500 | +0.016 |
| sparrow F1 | 0.968 | 0.933 | 1.000 | +0.032 |
| bulbul F1 | 0.000 | 0.000 | 0.000 | +0.000 |

## Per-video flip summary (C vs C_v3)

- Both correct: 27
- C_v3 improved over C: 2
- C_v3 regressed from C: 3
- Both wrong: 10

### Flip details

| fold | video_id | source | category | GT S/B | C pred | C_v3 pred | sync_rate | kind |
|---:|---|---|---|:-:|:-:|:-:|---:|---|
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/1 | 1/0 | 0.000 | v3 improvement |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/1 | 0/0 | 0.000 | v3 regression |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 0/1 | 1/0 | 0.000 | v3 regression |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 1/1 | 1/0 | 0.000 | v3 regression |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | 1/1 | 0.107 | v3 improvement |

## Per-fold side-by-side (42 folds)

| fold | video_id | source | category | GT S/B | C | C_v2 | C_v3 | sync_rate | sel_rate |
|---:|---|---|---|:-:|:-:|:-:|:-:|---:|---:|
| 01 | balcony_001 | self | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.000 | 0.022 |
| 02 | balcony_002 | self | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.000 | 0.244 |
| 03 | balcony_003 | self | bulbul | 0/1 | 1/0 | 1/0 | 1/0 | 0.000 | 0.114 |
| 04 | balcony_004 | self | bulbul | 0/1 | 1/0 | 1/0 | 1/0 | 0.000 | 0.779 |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | 0/1 | 0/1 | 0.026 | 0.584 |
| 06 | balcony_006 | self | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.000 | 0.150 |
| 07 | balcony_007 | self | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.000 | 0.066 |
| 08 | balcony_008 | self | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.250 | 0.339 |
| 09 | balcony_009 | self | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.000 | 0.116 |
| 10 | balcony_010 | self | both | 1/1 | 1/0 | 1/0 | 1/0 | 0.000 | 0.719 |
| 11 | balcony_011 | self | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.000 | 0.070 |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 1/0 | 0/0 | 1/0 | 0.231 | 0.722 |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.000 | 0.000 |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 1.000 | 1.000 |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 1.000 | 1.000 |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.286 | 0.561 |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.400 | 0.900 |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.000 | 0.897 |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.149 | 0.280 |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/1 | 0/1 | 1/0 | 0.000 | 1.000 |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.647 | 0.849 |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 1/0 | 1/0 | 1/0 | 0.000 | 0.352 |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/0 | 0.000 | 0.000 |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.000 | 0.000 |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.000 | 0.000 |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.464 | 0.457 |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.457 | 0.775 |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.929 | 0.742 |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.391 | 0.937 |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.597 | 0.952 |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.457 | 0.447 |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.118 | 0.080 |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0/1 | 0.727 | 0.690 |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 1/0 | 0.000 | 0.955 |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | 1/0 | 1/0 | 0.076 | 0.503 |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 1/0 | 1/0 | 1/0 | 0.000 | 0.260 |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | 1/0 | 1/0 | 0.232 | 0.746 |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 1/0 | 1/0 | 1/0 | 0.000 | 0.730 |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 0/1 | 1/1 | 0/1 | 0.054 | 0.700 |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 1/1 | 1/0 | 1/0 | 0.000 | 0.397 |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 0/1 | 0/1 | 1/0 | 0.000 | 0.540 |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | 1/0 | 1/1 | 0.107 | 0.718 |

## C_v3 sync_rate vs correctness

| subset | n | mean sync_rate |
|---|---:|---:|
| C_v3 fully correct | 29 | 0.283 |
| C_v3 at least one class wrong | 13 | 0.030 |
