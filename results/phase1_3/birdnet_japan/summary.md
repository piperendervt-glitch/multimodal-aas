# BirdNET Sensitivity Check — Japanese target species

- BirdNET config: `min_conf=0.1`, `sensitivity=1.0`, 
  lat/lon = (35.68, 139.65) (Tokyo, matches Topology A setup)

## Sources

- **Sparrow clip**: スズメの鳴き声01さえずりと地鳴き？Eurasian Tree Sparrow / Passer montanus (channel: 身近な生き物語)  
  URL: https://www.youtube.com/watch?v=Z6-WL8woFPk  
  Duration: 33.4 s
- **Bulbul clip**: ヒヨドリの群れ 鳴き声 Hypsipetes amaurotis  
  URL: https://www.youtube.com/watch?v=8zanYHHEpiw  
  Duration: 689.6 s

## Target-species detections

- *Passer montanus* (sparrow clip): target detections: **8**, max_conf: **0.839**, avg_conf: **0.291**
- *Hypsipetes amaurotis* (bulbul clip): target detections: **102**, max_conf: **0.981**, avg_conf: **0.496**

## Verdict

**Both target species are detected at high confidence (≥0.5) on
clean reference audio.** The Japanese-species coverage hypothesis (b)
is therefore **eliminated** as the main driver of Phase 1.3 Topology A's
low detection rate; the remaining primary suspect is (c) **balcony audio
quality** — webcam microphone bandwidth, distance from the feeder,
wind/traffic noise, or aliasing in the self-recorded clips.

## Phase 1.3 Topology A implication

Baseline cross-check (previous run, North American reference audio): 
BirdNET returned 423 detections / 91 species and picked up *Passer domesticus* 22 times. Passer genus is clearly within its recognition envelope, so the sparrow clip result should discriminate between species-specific sensitivity and recording quality directly.

## Top 10 species per clip (diagnostic)

### Sparrow clip

| rank | species | scientific_name | count | avg_conf | max_conf |
|---:|---|---|---:|---:|---:|
| 1 | Eurasian Tree Sparrow | Passer montanus | 8 | 0.291 | 0.839 |
| 2 | Common Redpoll | Acanthis flammea | 1 | 0.588 | 0.588 |

### Bulbul clip

| rank | species | scientific_name | count | avg_conf | max_conf |
|---:|---|---|---:|---:|---:|
| 1 | Brown-eared Bulbul | Hypsipetes amaurotis | 102 | 0.496 | 0.981 |
| 2 | Eurasian Siskin | Spinus spinus | 15 | 0.289 | 0.639 |
| 3 | Blue Rock-Thrush | Monticola solitarius | 3 | 0.243 | 0.360 |
| 4 | Rock Pigeon | Columba livia | 1 | 0.133 | 0.133 |
| 5 | Ashy Minivet | Pericrocotus divaricatus | 1 | 0.117 | 0.117 |

## Target-species detection timeline

### Sparrow clip — Passer montanus

| time (s) | confidence |
|---|---|
| 0.0 – 3.0 | 0.839 |
| 6.0 – 9.0 | 0.163 |
| 9.0 – 12.0 | 0.110 |
| 12.0 – 15.0 | 0.206 |
| 18.0 – 21.0 | 0.129 |
| 21.0 – 24.0 | 0.279 |
| 27.0 – 30.0 | 0.394 |
| 30.0 – 33.0 | 0.211 |

### Bulbul clip — Hypsipetes amaurotis

| time (s) | confidence |
|---|---|
| 18.0 – 21.0 | 0.864 |
| 21.0 – 24.0 | 0.234 |
| 24.0 – 27.0 | 0.413 |
| 30.0 – 33.0 | 0.240 |
| 33.0 – 36.0 | 0.433 |
| 36.0 – 39.0 | 0.403 |
| 39.0 – 42.0 | 0.904 |
| 42.0 – 45.0 | 0.301 |
| 45.0 – 48.0 | 0.693 |
| 48.0 – 51.0 | 0.763 |
| 51.0 – 54.0 | 0.949 |
| 57.0 – 60.0 | 0.236 |
| 60.0 – 63.0 | 0.144 |
| 63.0 – 66.0 | 0.103 |
| 66.0 – 69.0 | 0.679 |
| 72.0 – 75.0 | 0.163 |
| 75.0 – 78.0 | 0.268 |
| 90.0 – 93.0 | 0.167 |
| 93.0 – 96.0 | 0.665 |
| 96.0 – 99.0 | 0.640 |
| 99.0 – 102.0 | 0.202 |
| 105.0 – 108.0 | 0.781 |
| 108.0 – 111.0 | 0.954 |
| 117.0 – 120.0 | 0.303 |
| 147.0 – 150.0 | 0.822 |
| 153.0 – 156.0 | 0.437 |
| 174.0 – 177.0 | 0.555 |
| 219.0 – 222.0 | 0.516 |
| 222.0 – 225.0 | 0.181 |
| 234.0 – 237.0 | 0.398 |
| 237.0 – 240.0 | 0.606 |
| 240.0 – 243.0 | 0.517 |
| 255.0 – 258.0 | 0.873 |
| 261.0 – 264.0 | 0.549 |
| 264.0 – 267.0 | 0.957 |
| 267.0 – 270.0 | 0.625 |
| 270.0 – 273.0 | 0.231 |
| 279.0 – 282.0 | 0.402 |
| 282.0 – 285.0 | 0.513 |
| 303.0 – 306.0 | 0.719 |
| 306.0 – 309.0 | 0.615 |
| 309.0 – 312.0 | 0.304 |
| 312.0 – 315.0 | 0.703 |
| 315.0 – 318.0 | 0.909 |
| 318.0 – 321.0 | 0.367 |
| 321.0 – 324.0 | 0.118 |
| 324.0 – 327.0 | 0.192 |
| 327.0 – 330.0 | 0.358 |
| 333.0 – 336.0 | 0.679 |
| 348.0 – 351.0 | 0.782 |
| 351.0 – 354.0 | 0.848 |
| 354.0 – 357.0 | 0.842 |
| 363.0 – 366.0 | 0.705 |
| 366.0 – 369.0 | 0.671 |
| 369.0 – 372.0 | 0.138 |
| 372.0 – 375.0 | 0.200 |
| 378.0 – 381.0 | 0.196 |
| 384.0 – 387.0 | 0.124 |
| 387.0 – 390.0 | 0.761 |
| 390.0 – 393.0 | 0.303 |
| 396.0 – 399.0 | 0.571 |
| 405.0 – 408.0 | 0.213 |
| 420.0 – 423.0 | 0.416 |
| 426.0 – 429.0 | 0.706 |
| 429.0 – 432.0 | 0.530 |
| 432.0 – 435.0 | 0.461 |
| 447.0 – 450.0 | 0.105 |
| 459.0 – 462.0 | 0.406 |
| 474.0 – 477.0 | 0.659 |
| 477.0 – 480.0 | 0.540 |
| 480.0 – 483.0 | 0.462 |
| 489.0 – 492.0 | 0.179 |
| 492.0 – 495.0 | 0.355 |
| 495.0 – 498.0 | 0.105 |
| 498.0 – 501.0 | 0.739 |
| 501.0 – 504.0 | 0.966 |
| 504.0 – 507.0 | 0.973 |
| 507.0 – 510.0 | 0.336 |
| 510.0 – 513.0 | 0.250 |
| 513.0 – 516.0 | 0.614 |
| 516.0 – 519.0 | 0.158 |
| 519.0 – 522.0 | 0.431 |
| 525.0 – 528.0 | 0.384 |
| 531.0 – 534.0 | 0.386 |
| 552.0 – 555.0 | 0.712 |
| 555.0 – 558.0 | 0.981 |
| 561.0 – 564.0 | 0.976 |
| 564.0 – 567.0 | 0.214 |
| 567.0 – 570.0 | 0.128 |
| 576.0 – 579.0 | 0.122 |
| 579.0 – 582.0 | 0.380 |
| 582.0 – 585.0 | 0.102 |
| 588.0 – 591.0 | 0.946 |
| 597.0 – 600.0 | 0.187 |
| 603.0 – 606.0 | 0.900 |
| 645.0 – 648.0 | 0.162 |
| 648.0 – 651.0 | 0.460 |
| 660.0 – 663.0 | 0.175 |
| 663.0 – 666.0 | 0.813 |
| 672.0 – 675.0 | 0.644 |
| 681.0 – 684.0 | 0.914 |
| 684.0 – 687.0 | 0.571 |

Raw per-clip JSONs: `sparrow_detections.json`, `bulbul_detections.json`.
