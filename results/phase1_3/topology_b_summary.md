# Phase 1.3 Topology B (Visual-Only) Summary

- Pipeline: ffmpeg @ 1 fps (CFR) -> YOLOv8n (bird class) -> `qwen2.5:7b`
- Folds:   11
- Scored:  11
- Fallback triggered: 0 / 11
- LLM parse failures (non-fallback): 0 / 11
- Errors:  0 / 11
- Macro F1: 0.819
- Sparrow F1: 0.714 | Bulbul F1: 0.923
- Sparrow accuracy: 0.636 | Bulbul accuracy: 0.909
- Total wall time: 97.7 s

## Per-fold results

| fold | video_id | frames | with_bird | max_rel | avg_rel | std | max_conf | pred (S/B) | GT (S/B) | S OK | B OK | fallback | t_extract | t_yolo | t_llm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | 362 | 8 | 0.183 | 0.116 | 0.032 | 0.381 | 1/1 | 0/1 | X | OK | - | 0.00 | 10.54 | 7.14 |
| 02 | balcony_002 | 41 | 10 | 0.151 | 0.125 | 0.017 | 0.961 | 0/1 | 0/1 | OK | OK | - | 0.00 | 1.02 | 5.24 |
| 03 | balcony_003 | 167 | 19 | 0.139 | 0.072 | 0.021 | 0.831 | 1/1 | 0/1 | X | OK | - | 0.00 | 4.30 | 5.19 |
| 04 | balcony_004 | 145 | 113 | 0.238 | 0.150 | 0.047 | 0.909 | 0/1 | 0/1 | OK | OK | - | 0.00 | 3.57 | 4.88 |
| 05 | balcony_005 | 197 | 115 | 0.212 | 0.106 | 0.055 | 0.919 | 0/1 | 1/1 | X | OK | - | 0.00 | 4.60 | 4.91 |
| 06 | balcony_006 | 160 | 24 | 0.083 | 0.047 | 0.016 | 0.911 | 1/0 | 1/0 | OK | OK | - | 0.00 | 3.61 | 4.91 |
| 07 | balcony_007 | 242 | 16 | 0.083 | 0.050 | 0.023 | 0.830 | 1/0 | 1/0 | OK | OK | - | 0.00 | 5.41 | 5.04 |
| 08 | balcony_008 | 62 | 21 | 0.206 | 0.067 | 0.048 | 0.872 | 1/1 | 1/0 | OK | X | - | 0.00 | 1.58 | 4.74 |
| 09 | balcony_009 | 155 | 18 | 0.069 | 0.034 | 0.011 | 0.734 | 1/0 | 1/0 | OK | OK | - | 0.00 | 4.06 | 4.64 |
| 10 | balcony_010 | 89 | 64 | 0.402 | 0.169 | 0.047 | 0.943 | 0/1 | 1/1 | X | OK | - | 0.00 | 2.27 | 4.77 |
| 11 | balcony_011 | 43 | 3 | 0.006 | 0.004 | 0.002 | 0.496 | 1/0 | 1/0 | OK | OK | - | 0.00 | 0.91 | 4.33 |

## Confusion matrices

### sparrow

| | pred=1 | pred=0 |
|---|---|---|
| gt=1 | TP=5 | FN=2 |
| gt=0 | FP=2 | TN=2 |

### bulbul

| | pred=1 | pred=0 |
|---|---|---|
| gt=1 | TP=6 | FN=0 |
| gt=0 | FP=1 | TN=4 |

## Model reasoning

- **fold_01 balcony_001**: 最大 bbox サイズが 0.1833 で 0.1 を超え、検出数も複数存在。
- **fold_02 balcony_002**: 最大 bbox サイズがヒヨドリの範囲内であり、検出数も主に中型鳥
- **fold_03 balcony_003**: 最大 bbox サイズが 0.1391で 0.08以上、検出数も複数存在。
- **fold_04 balcony_004**: 最大 bbox サイズがヒヨドリの範囲であり、検出数も主に中型鳥
- **fold_05 balcony_005**: 最大 bbox サイズがヒヨドリの範囲内であり、検出数も主に中型鳥
- **fold_06 balcony_006**: 最大 bbox サイズが 0.0833 でスズメの範囲内。検出数も少ない。
- **fold_07 balcony_007**: 最大 bbox サイズが 0.0832でスズメ未満、平均 bbox サイズも小さい
- **fold_08 balcony_008**: 最大 bbox サイズが 0.2064で基準を上回り、検出数も複数
- **fold_09 balcony_009**: 最大 bbox サイズが 0.0685で 0.08未満。
- **fold_10 balcony_010**: 最大 bbox サイズが大きい値で、平均も中型以上。検出数もヒヨドリのパターン。
- **fold_11 balcony_011**: 最大 bbox サイズが非常に小さいためスズメと判定

## Mean stage times (across all folds)

- Frame extraction:    0.00 s
- YOLOv8n inference:   3.81 s
- LLM call (non-fallback avg): 5.07 s
