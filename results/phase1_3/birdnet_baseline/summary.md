# BirdNET Baseline Sanity Check

- Source: 10 Hours of North American Bird Songs (Badgerland Birding Extras)
- URL:    https://www.youtube.com/watch?v=JvfFRAP6qG8
- License: CC BY 4.0 (per video description)
- Analyzed clip: 1200.0 s (20.0 min) @ 16000 Hz
- BirdNET config: `min_conf=0.1`, `sensitivity=1.0`, no lat/lon
- Total detections: **423**
- Unique species:   **91**
- Analysis wall time: 18.1 s

## Verdict

**BirdNET is functioning correctly.** The clean North-American
reference recording produced many detections with meaningful species
diversity. Therefore the Phase 1.3 Topology A low-detection result is
**not** caused by a BirdNET setup problem; the remaining hypotheses are:

- (b) Japanese species coverage or model sensitivity to *Passer montanus*
  / *Hypsipetes amaurotis* vocalisations.
- (c) Balcony webcam audio quality (microphone bandwidth, SNR, distance
  from feeder, ambient traffic/wind).

Follow-up experiments should target (b) and (c) separately — e.g.,
running BirdNET against a Xeno-canto sparrow/bulbul clip (tests b) and
against balcony audio captured via a dedicated mic (tests c).

## Top 10 detected species

| rank | species | scientific_name | count | avg_conf | max_conf |
|---:|---|---|---:|---:|---:|
| 1 | American Robin | Turdus migratorius | 39 | 0.660 | 0.998 |
| 2 | Brown Thrasher | Toxostoma rufum | 38 | 0.505 | 0.970 |
| 3 | American Goldfinch | Spinus tristis | 29 | 0.816 | 0.993 |
| 4 | Gray Catbird | Dumetella carolinensis | 24 | 0.449 | 0.911 |
| 5 | Northern Cardinal | Cardinalis cardinalis | 22 | 0.807 | 0.981 |
| 6 | House Sparrow | Passer domesticus | 22 | 0.338 | 0.748 |
| 7 | Song Sparrow | Melospiza melodia | 22 | 0.835 | 0.980 |
| 8 | House Finch | Haemorhous mexicanus | 20 | 0.699 | 0.990 |
| 9 | Red-winged Blackbird | Agelaius phoeniceus | 15 | 0.369 | 0.678 |
| 10 | Eastern Towhee | Pipilo erythrophthalmus | 14 | 0.895 | 0.995 |

## Detection density per minute

| minute | detections |
|---:|---:|
| 0 | 22 |
| 1 | 22 |
| 2 | 21 |
| 3 | 24 |
| 4 | 19 |
| 5 | 22 |
| 6 | 20 |
| 7 | 13 |
| 8 | 14 |
| 9 | 18 |
| 10 | 25 |
| 11 | 23 |
| 12 | 15 |
| 13 | 26 |
| 14 | 29 |
| 15 | 28 |
| 16 | 24 |
| 17 | 28 |
| 18 | 16 |
| 19 | 14 |

Full top-species table and the first 50 time-sorted detections are in `detections.json`.
