# Phase 1.3 Topology C (Parallel Fusion) Summary

- Pipeline: ffmpeg (audio 16 kHz + frames @ 1 fps CFR) -> BirdNET + YOLOv8n -> `qwen2.5:7b` fusion
- Folds:   11
- Scored:  11
- Fallback triggered: 0 / 11
- LLM parse failures (non-fallback): 0 / 11
- Errors:  0 / 11
- Macro F1: 0.733
- Sparrow F1: 0.800 | Bulbul F1: 0.667
- Sparrow accuracy: 0.727 | Bulbul accuracy: 0.727
- Total wall time: 117.2 s

## Modality used (from LLM response)

| modality | count |
|---|---:|
| visual    | 9 |
| audio     | 0 |
| both      | 2 |
| none      | 0 |
| unparsed  | 0 |

## Per-fold results

| fold | video_id | frames_with_bird | max_rel | audio_det | target_audio | modality | pred (S/B) | GT (S/B) | S OK | B OK | fallback | t_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | balcony_001 | 8 | 0.183 | 1 | - | visual | 0/1 | 0/1 | OK | OK | - | 21.73 |
| 02 | balcony_002 | 10 | 0.151 | 0 | - | visual | 0/1 | 0/1 | OK | OK | - | 6.06 |
| 03 | balcony_003 | 19 | 0.139 | 0 | - | visual | 1/0 | 0/1 | X | X | - | 10.93 |
| 04 | balcony_004 | 113 | 0.238 | 9 | - | visual | 1/0 | 0/1 | X | X | - | 10.03 |
| 05 | balcony_005 | 115 | 0.212 | 15 | Y | both | 0/1 | 1/1 | X | OK | - | 12.29 |
| 06 | balcony_006 | 24 | 0.083 | 0 | - | visual | 1/0 | 1/0 | OK | OK | - | 10.55 |
| 07 | balcony_007 | 16 | 0.083 | 0 | - | visual | 1/0 | 1/0 | OK | OK | - | 13.07 |
| 08 | balcony_008 | 21 | 0.206 | 2 | Y | both | 1/0 | 1/0 | OK | OK | - | 7.45 |
| 09 | balcony_009 | 18 | 0.069 | 0 | - | visual | 1/0 | 1/0 | OK | OK | - | 10.68 |
| 10 | balcony_010 | 64 | 0.402 | 6 | - | visual | 1/0 | 1/1 | OK | X | - | 8.12 |
| 11 | balcony_011 | 3 | 0.006 | 2 | - | visual | 1/0 | 1/0 | OK | OK | - | 5.96 |

## Confusion matrices

### sparrow

| | pred=1 | pred=0 |
|---|---|---|
| gt=1 | TP=6 | FN=1 |
| gt=0 | FP=2 | TN=2 |

### bulbul

| | pred=1 | pred=0 |
|---|---|---|
| gt=1 | TP=3 | FN=3 |
| gt=0 | FP=0 | TN=5 |

## Model reasoning

- **fold_01 balcony_001**: 視覚情報より中型の bbox サイズが多いため。
- **fold_02 balcony_002**: 中型の bbox サイズが多いため
- **fold_03 balcony_003**: 視覚情報でスズメの bbox サイズが小さい
- **fold_04 balcony_004**: 視覚情報より小型鳥多数でスズメの可能性が高い
- **fold_05 balcony_005**: 視覚情報でヒヨドリの bbox サイズが大きい。音声でもヒヨドリ検出。
- **fold_06 balcony_006**: 視覚情報から小型の bbox サイズが多いため
- **fold_07 balcony_007**: 視覚情報から小型の鳥が多く、音声情報はなし。
- **fold_08 balcony_008**: 視覚でスズメの bbox サイズが小さい。音声は対象種検出あり。
- **fold_09 balcony_009**: 視覚情報から小型の鳥が多く、音声情報は補強なし。
- **fold_10 balcony_010**: 視覚情報から中型の bbox サイズが多いため
- **fold_11 balcony_011**: 視覚で小型鳥多数、音声無し

## Mean stage times (non-error folds)

- audio_extraction  : 0.00 s
- frame_extraction  : 0.00 s
- birdnet           : 2.01 s
- yolo              : 3.60 s
- llm               : 5.01 s
- total             : 10.62 s
