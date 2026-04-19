# Phase 1.2 Audio Node Summary

- Pipeline: ffmpeg (16 kHz mono WAV) -> BirdNET (birdnetlib, min_conf=0.1) -> `qwen2.5:7b`
- Videos:   11
- Parsed:   11 / 11
- Go / No-Go: Go (β)  (11/11 videos parsed)
- Macro F1: 0.268
- Accuracy: sparrow=0.455, bulbul=0.545
- Total wall time: 72.7 s

## Per-video results

| video_id | dur (s) | all_det | sparrow_det | bulbul_det | pred (S/B) | GT (S/B) | S OK | B OK | t_extract | t_birdnet | t_llm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| balcony_001 | 361.8 | 1 | 0 | 0 | 0/0 | 0/1 | OK | X | 0.18 | 6.97 | 4.41 |
| balcony_002 | 41.4 | 0 | 0 | 0 | 0/0 | 0/1 | OK | X | 0.07 | 0.53 | 4.22 |
| balcony_003 | 167.3 | 0 | 0 | 0 | 0/0 | 0/1 | OK | X | 0.11 | 2.13 | 4.22 |
| balcony_004 | 144.9 | 9 | 0 | 0 | 0/0 | 0/1 | OK | X | 0.11 | 1.83 | 4.51 |
| balcony_005 | 197.3 | 15 | 0 | 8 | 0/1 | 1/1 | X | OK | 0.13 | 2.52 | 4.71 |
| balcony_006 | 159.7 | 0 | 0 | 0 | 0/0 | 1/0 | X | OK | 0.11 | 2.01 | 4.20 |
| balcony_007 | 241.8 | 0 | 0 | 0 | 0/0 | 1/0 | X | OK | 0.14 | 3.03 | 4.22 |
| balcony_008 | 62.2 | 2 | 2 | 0 | 1/0 | 1/0 | OK | OK | 0.08 | 0.79 | 4.40 |
| balcony_009 | 155.1 | 0 | 0 | 0 | 0/0 | 1/0 | X | OK | 0.12 | 1.97 | 4.39 |
| balcony_010 | 89.2 | 6 | 0 | 0 | 0/0 | 1/1 | X | X | 0.10 | 1.14 | 4.40 |
| balcony_011 | 42.8 | 2 | 0 | 0 | 0/0 | 1/0 | X | OK | 0.08 | 0.54 | 4.34 |

## BirdNET species histogram (all videos)

| species | detections |
|---|---|
| Rock Pigeon | 15 |
| Brown-eared Bulbul | 8 |
| Eurasian Tree Sparrow | 2 |
| Mallard | 2 |
| Common Merganser | 2 |
| Large-billed Crow | 2 |
| Northern Fulmar | 1 |
| Whooper Swan | 1 |
| Great Bittern | 1 |
| Gray Heron | 1 |

## Model reasoning

- **balcony_001**: 関連する種が検出されなかった
- **balcony_002**: BirdNETが検出結果なし
- **balcony_003**: BirdNETが検出結果なし
- **balcony_004**: BirdNETが関連する種を検出しないため
- **balcony_005**: Brown-eared Bulbulの検出確信度が高い
- **balcony_006**: BirdNETが検出結果なし
- **balcony_007**: BirdNETが検出結果なし
- **balcony_008**: BirdNETがスズメを検出したため
- **balcony_009**: BirdNET が鳥を検出しないため
- **balcony_010**: 関連する鳥種が検出されなかった
- **balcony_011**: 関連する種が検出されなかった

## Mean stage times

- Audio extraction:    0.11 s
- BirdNET inference:   2.13 s
- LLM call:            4.37 s
