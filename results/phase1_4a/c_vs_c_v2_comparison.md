# Phase 1.4a C_v2 vs Phase 1.3 C

Side-by-side comparison of the Parallel Fusion topology with and without 
the frame_extractor pre-filter. Both runs use identical prompts, BirdNET 
configuration (`target_threshold=None`), and the same 42-fold video set.

- Phase 1.3 folds: 42
- Phase 1.4a folds: 42

## Metric deltas

### Full (self + YouTube)

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| n (scored) | 42 (42) | 42 (42) | - |
| fallback  | 0 | 0 | +0 |
| macro F1  | 0.840 | 0.826 | -0.014 |
| sparrow F1 | 0.880 | 0.880 | +0.000 |
| bulbul F1  | 0.800 | 0.773 | -0.027 |

### Self-recorded only

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| n (scored) | 11 (11) | 11 (11) | - |
| fallback  | 0 | 0 | +0 |
| macro F1  | 0.733 | 0.733 | +0.000 |
| sparrow F1 | 0.800 | 0.800 | +0.000 |
| bulbul F1  | 0.667 | 0.667 | +0.000 |

### YouTube only

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| n (scored) | 31 (31) | 31 (31) | - |
| fallback  | 0 | 0 | +0 |
| macro F1  | 0.874 | 0.857 | -0.017 |
| sparrow F1 | 0.914 | 0.914 | +0.000 |
| bulbul F1  | 0.833 | 0.800 | -0.033 |

### YouTube-grok

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| n (scored) | 16 (16) | 16 (16) | - |
| fallback  | 0 | 0 | +0 |
| macro F1  | 0.912 | 0.882 | -0.029 |
| sparrow F1 | 1.000 | 0.941 | -0.059 |
| bulbul F1  | 0.824 | 0.824 | +0.000 |

### YouTube-claude

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| n (scored) | 15 (15) | 15 (15) | - |
| fallback  | 0 | 0 | +0 |
| macro F1  | 0.833 | 0.833 | +0.001 |
| sparrow F1 | 0.824 | 0.889 | +0.065 |
| bulbul F1  | 0.842 | 0.778 | -0.064 |

### Category = both

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| n (scored) | 2 (2) | 2 (2) | - |
| fallback  | 0 | 0 | +0 |
| macro F1  | 0.667 | 0.667 | +0.000 |
| sparrow F1 | 0.667 | 0.667 | +0.000 |
| bulbul F1  | 0.667 | 0.667 | +0.000 |

### Category = bulbul

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| n (scored) | 16 (16) | 16 (16) | - |
| fallback  | 0 | 0 | +0 |
| macro F1  | 0.467 | 0.467 | +0.000 |
| sparrow F1 | 0.000 | 0.000 | +0.000 |
| bulbul F1  | 0.933 | 0.933 | +0.000 |

### Category = mixed

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| n (scored) | 8 (8) | 8 (8) | - |
| fallback  | 0 | 0 | +0 |
| macro F1  | 0.701 | 0.667 | -0.035 |
| sparrow F1 | 0.857 | 0.933 | +0.076 |
| bulbul F1  | 0.545 | 0.400 | -0.145 |

### Category = sparrow

| metric | Phase 1.3 C | Phase 1.4a C_v2 | delta |
|---|---:|---:|---:|
| n (scored) | 16 (16) | 16 (16) | - |
| fallback  | 0 | 0 | +0 |
| macro F1  | 0.484 | 0.467 | -0.017 |
| sparrow F1 | 0.968 | 0.933 | -0.034 |
| bulbul F1  | 0.000 | 0.000 | +0.000 |

## Per-video flip summary

- Both correct: 28
- C_v2 improved over C: 1
- C_v2 regressed from C: 2
- Both wrong: 11

### Flip details

| fold | video_id | source | category | GT S/B | C pred | C_v2 pred | sel_rate | kind |
|---:|---|---|---|:-:|:-:|:-:|---:|---|
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 1/0 | 0/0 | 0.722 | regression (C_v2 wrong) |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 0/1 | 1/1 | 0.700 | improvement (C_v2 right) |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 1/1 | 1/0 | 0.397 | regression (C_v2 wrong) |

## Per-video side-by-side (42 folds)

| fold | video_id | source | category | GT S/B | C pred | C_v2 pred | sel_rate | C ok | C_v2 ok |
|---:|---|---|---|:-:|:-:|:-:|---:|:-:|:-:|
| 01 | balcony_001 | self | bulbul | 0/1 | 0/1 | 0/1 | 0.022 | OK | OK |
| 02 | balcony_002 | self | bulbul | 0/1 | 0/1 | 0/1 | 0.244 | OK | OK |
| 03 | balcony_003 | self | bulbul | 0/1 | 1/0 | 1/0 | 0.114 | X | X |
| 04 | balcony_004 | self | bulbul | 0/1 | 1/0 | 1/0 | 0.779 | X | X |
| 05 | balcony_005 | self | both | 1/1 | 0/1 | 0/1 | 0.584 | X | X |
| 06 | balcony_006 | self | sparrow | 1/0 | 1/0 | 1/0 | 0.150 | OK | OK |
| 07 | balcony_007 | self | sparrow | 1/0 | 1/0 | 1/0 | 0.066 | OK | OK |
| 08 | balcony_008 | self | sparrow | 1/0 | 1/0 | 1/0 | 0.339 | OK | OK |
| 09 | balcony_009 | self | sparrow | 1/0 | 1/0 | 1/0 | 0.116 | OK | OK |
| 10 | balcony_010 | self | both | 1/1 | 1/0 | 1/0 | 0.719 | X | X |
| 11 | balcony_011 | self | sparrow | 1/0 | 1/0 | 1/0 | 0.070 | OK | OK |
| 12 | yt_JCGgh5zvEeE | youtube-grok | sparrow | 1/0 | 1/0 | 0/0 | 0.722 | OK | X |
| 13 | yt_HFN1MX3D4yM | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 0.000 | OK | OK |
| 14 | yt_ToG_e-OQWwI | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 1.000 | OK | OK |
| 15 | yt_sljwOG3KU2g | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 1.000 | OK | OK |
| 16 | yt_b12Fb3C7LcY | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 0.561 | OK | OK |
| 17 | yt_evVHoDIv1hE | youtube-grok | sparrow | 1/0 | 1/0 | 1/0 | 0.900 | OK | OK |
| 18 | yt_RbGhZOyR7Pg | youtube-claude | sparrow | 1/0 | 1/0 | 1/0 | 0.897 | OK | OK |
| 19 | yt_YFdbUv65QIw | youtube-claude | sparrow | 1/0 | 1/0 | 1/0 | 0.280 | OK | OK |
| 20 | yt_ZRQLsbGEVG8 | youtube-claude | sparrow | 1/0 | 0/1 | 0/1 | 1.000 | X | X |
| 21 | yt_Z6-WL8woFPk | youtube-claude | sparrow | 1/0 | 1/0 | 1/0 | 0.849 | OK | OK |
| 22 | yt_xhvf73wRJVM | youtube-claude | sparrow | 1/0 | 1/0 | 1/0 | 0.352 | OK | OK |
| 23 | yt_TPgyTtnlYak | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0.000 | OK | OK |
| 24 | yt_p-te4rfSFlo | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0.000 | OK | OK |
| 25 | yt_4QdQnWqiekY | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0.000 | OK | OK |
| 26 | yt_kMWUQOW-bTM | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0.457 | OK | OK |
| 27 | yt_QxKLx__Nzn4 | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0.775 | OK | OK |
| 28 | yt_jk15DbXQV6A | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0.742 | OK | OK |
| 29 | yt_lnyw5TOMea8 | youtube-grok | bulbul | 0/1 | 0/1 | 0/1 | 0.937 | OK | OK |
| 30 | yt_-DYmOCTDWc0 | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0.952 | OK | OK |
| 31 | yt_vmrbbEe9R6M | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0.447 | OK | OK |
| 32 | yt_8zanYHHEpiw | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0.080 | OK | OK |
| 33 | yt_8HhsjaqFITQ | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0.690 | OK | OK |
| 34 | yt_zYvgirz9KMo | youtube-claude | bulbul | 0/1 | 0/1 | 0/1 | 0.955 | OK | OK |
| 35 | yt_bhp8AhQ2cvw | youtube-grok | mixed | 1/1 | 1/0 | 1/0 | 0.503 | X | X |
| 36 | yt_ruTTT9OdI9Q | youtube-grok | mixed | 1/1 | 1/0 | 1/0 | 0.260 | X | X |
| 37 | yt_RC3ELjgkUCQ | youtube-grok | mixed | 1/1 | 1/0 | 1/0 | 0.746 | X | X |
| 38 | yt_bGk6vto6JxM | youtube-claude | mixed | 1/1 | 1/0 | 1/0 | 0.730 | X | X |
| 39 | yt__K7JMyeOnjw | youtube-claude | mixed | 1/1 | 0/1 | 1/1 | 0.700 | X | OK |
| 40 | yt_IjHCLUmBqJE | youtube-claude | mixed | 1/1 | 1/1 | 1/0 | 0.397 | OK | X |
| 41 | yt_6FQnY2jYNjM | youtube-claude | mixed | 1/1 | 0/1 | 0/1 | 0.540 | X | X |
| 42 | yt_I1XmEHGO19A | youtube-claude | mixed | 1/1 | 1/0 | 1/0 | 0.718 | X | X |

## Selection-rate vs correctness (C_v2)

| subset | n | mean selection rate |
|---|---:|---:|
| C_v2 fully correct | 29 | 0.468 |
| C_v2 at least one class wrong | 13 | 0.601 |
