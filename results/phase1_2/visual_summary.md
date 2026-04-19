# Phase 1.2 Visual Node Summary

- Pipeline: ffmpeg @ 1 fps -> YOLOv8n (bird class) -> `qwen2.5:7b`
- Videos:   11
- Parsed:   11 / 11
- Go / No-Go: Go (β)  (11/11 videos parsed)
- Macro F1: 0.389
- Accuracy: sparrow=0.636, bulbul=0.455
- Total wall time: 104.9 s

## Per-video results

| video_id | frames | with_bird | max_rel | avg_conf | pred (S/B) | GT (S/B) | S OK | B OK | t_extract | t_yolo | t_llm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| balcony_001 | 362 | 8 | 0.183 | 0.317 | 1/0 | 0/1 | X | X | 0.52 | 13.89 | 6.94 |
| balcony_002 | 41 | 10 | 0.151 | 0.612 | 1/0 | 0/1 | X | X | 0.10 | 0.99 | 4.88 |
| balcony_003 | 167 | 19 | 0.139 | 0.588 | 1/0 | 0/1 | X | X | 0.26 | 4.25 | 4.58 |
| balcony_004 | 145 | 113 | 0.238 | 0.630 | 1/0 | 0/1 | X | X | 0.28 | 3.73 | 4.86 |
| balcony_005 | 197 | 115 | 0.212 | 0.569 | 1/0 | 1/1 | OK | X | 0.30 | 4.97 | 5.23 |
| balcony_006 | 160 | 24 | 0.083 | 0.671 | 1/0 | 1/0 | OK | OK | 0.25 | 3.95 | 5.13 |
| balcony_007 | 242 | 16 | 0.083 | 0.569 | 1/0 | 1/0 | OK | OK | 0.22 | 5.77 | 4.73 |
| balcony_008 | 62 | 21 | 0.206 | 0.498 | 1/0 | 1/0 | OK | OK | 0.33 | 1.63 | 4.13 |
| balcony_009 | 155 | 18 | 0.069 | 0.507 | 1/0 | 1/0 | OK | OK | 0.69 | 3.92 | 4.97 |
| balcony_010 | 89 | 64 | 0.402 | 0.737 | 1/0 | 1/1 | OK | X | 0.53 | 2.49 | 4.95 |
| balcony_011 | 43 | 3 | 0.006 | 0.412 | 1/0 | 1/0 | OK | OK | 0.12 | 0.97 | 4.32 |

## Model reasoning

- **balcony_001**: 最大のbboxサイズがスズメに近い値であり、ヒヨドリは見られなかった。
- **balcony_002**: 最大サイズがスズメの範囲で、ヒヨドリは見当たらない。
- **balcony_003**: 最大サイズが小さい方でスズメが多い
- **balcony_004**: 最大のbboxサイズがヒヨドリより小さいためスズメ
- **balcony_005**: ヒヨドリが最大のbboxサイズでスズメの方が頻繁に検出されました。
- **balcony_006**: 最大のbboxサイズがスズメ未満で、ヒヨドリは見当たらない。
- **balcony_007**: 最大のbboxサイズが小さいためスズメ
- **balcony_008**: ヒヨドリが大きい鳥で最多
- **balcony_009**: 最大サイズが小さいスズメの範囲内であり、ヒヨドリは検出されていない。
- **balcony_010**: 最大サイズがヒヨドリより小さいし、スズメが多い
- **balcony_011**: 最大サイズが小さいのでスズメ

## Mean stage times

- Frame extraction: 0.33 s
- YOLOv8n inference: 4.23 s
- LLM call:         4.97 s
