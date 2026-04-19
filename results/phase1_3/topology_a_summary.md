# Phase 1.3 Topology A (Audio-Only) Summary

- Pipeline: ffmpeg (16 kHz mono) -> BirdNET (birdnetlib) -> `qwen2.5:7b`
- Folds:   11
- Scored:  11
- Fallback triggered: 10 / 11
- LLM parse failures (non-fallback): 0 / 11
- Errors:  0 / 11
- Macro F1: 0.143
- Sparrow F1: 0.000 | Bulbul F1: 0.286
- Sparrow accuracy: 0.364 | Bulbul accuracy: 0.545
- Total wall time: 32.1 s

## Per-fold results

| fold | video_id | dur (s) | targets | other | pred (S/B) | GT (S/B) | S OK | B OK | fallback | t_audio | t_birdnet | t_llm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | 361.8 | - | 1 | 0/0 | 0/1 | OK | X | Y | 0.00 | 8.60 | 0.00 |
| 02 | balcony_002 | 41.4 | - | 0 | 0/0 | 0/1 | OK | X | Y | 0.00 | 0.68 | 0.00 |
| 03 | balcony_003 | 167.3 | - | 0 | 0/0 | 0/1 | OK | X | Y | 0.00 | 2.79 | 0.00 |
| 04 | balcony_004 | 144.9 | - | 3 | 0/0 | 0/1 | OK | X | Y | 0.00 | 1.90 | 0.00 |
| 05 | balcony_005 | 197.3 | bulbul | 1 | 0/1 | 1/1 | X | OK | - | 0.00 | 2.61 | 4.78 |
| 06 | balcony_006 | 159.7 | - | 0 | 0/0 | 1/0 | X | OK | Y | 0.00 | 2.11 | 0.00 |
| 07 | balcony_007 | 241.8 | - | 0 | 0/0 | 1/0 | X | OK | Y | 0.00 | 3.51 | 0.00 |
| 08 | balcony_008 | 62.2 | - | 0 | 0/0 | 1/0 | X | OK | Y | 0.00 | 0.96 | 0.00 |
| 09 | balcony_009 | 155.1 | - | 0 | 0/0 | 1/0 | X | OK | Y | 0.00 | 2.14 | 0.00 |
| 10 | balcony_010 | 89.2 | - | 4 | 0/0 | 1/1 | X | X | Y | 0.00 | 1.14 | 0.00 |
| 11 | balcony_011 | 42.8 | - | 1 | 0/0 | 1/0 | X | OK | Y | 0.00 | 0.56 | 0.00 |

## Confusion matrices

### sparrow

| | pred=1 | pred=0 |
|---|---|---|
| gt=1 | TP=0 | FN=7 |
| gt=0 | FP=0 | TN=4 |

### bulbul

| | pred=1 | pred=0 |
|---|---|---|
| gt=1 | TP=1 | FN=5 |
| gt=0 | FP=0 | TN=5 |

## Model reasoning

- **fold_01 balcony_001**: 対象種の検出なし (LLM スキップ)
- **fold_02 balcony_002**: 対象種の検出なし (LLM スキップ)
- **fold_03 balcony_003**: 対象種の検出なし (LLM スキップ)
- **fold_04 balcony_004**: 対象種の検出なし (LLM スキップ)
- **fold_05 balcony_005**: BirdNETがbulbulを高確信で検出
- **fold_06 balcony_006**: 対象種の検出なし (LLM スキップ)
- **fold_07 balcony_007**: 対象種の検出なし (LLM スキップ)
- **fold_08 balcony_008**: 対象種の検出なし (LLM スキップ)
- **fold_09 balcony_009**: 対象種の検出なし (LLM スキップ)
- **fold_10 balcony_010**: 対象種の検出なし (LLM スキップ)
- **fold_11 balcony_011**: 対象種の検出なし (LLM スキップ)

## Mean stage times (across all folds)

- Audio extraction:    0.00 s
- BirdNET inference:   2.46 s
- LLM call (non-fallback avg): 0.43 s
