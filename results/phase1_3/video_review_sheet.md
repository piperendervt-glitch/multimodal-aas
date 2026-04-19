# Phase 1.3 Video Review Sheet

## 使い方

各動画を実際に視聴し、「人間レビュー欄」に記入してください。
動画ファイルは `data/raw/balcony_videos/` にあります (gitignored)。

## 全体サマリ (参考)

| Topology | macro F1 | sparrow F1 | bulbul F1 | fallback |
|---|---:|---:|---:|---:|
| A | 0.143 | 0.000 | 0.286 | 10 / 11 |
| B | 0.819 | 0.714 | 0.923 |  0 / 11 |
| C | 0.733 | 0.800 | 0.667 |  0 / 11 |

## レビュー優先度

以下の動画は特に注意して視聴することを推奨:

- **C が B より勝った fold**: `balcony_001`, `balcony_008` (B が sparrow 偽陽性、C が正しく抑えた)
- **C が B より負けた fold**: `balcony_004` (B 正答、C が bulbul を sparrow と誤判定)
- **両方失敗**: `balcony_003`, `balcony_005`, `balcony_010` (特に 005, 010 は 'both' ラベル)
- **Topology A が唯一 LLM 到達**: `balcony_005`

---

## balcony_001

### 動画情報

- ファイル名: `Bird watching (chats_) 02.mp4`
- 再生時間: 361.8 s
- 解像度: 480x360
- FPS: 30
- ファイルサイズ: 13.90 MB
- **優先レビュー理由**: C が B より勝った fold (B sparrow 偽陽性, C が抑制)

### Ground Truth (phase1_labels.json より)

- primary_label: `bulbul`
- sparrow: 0
- bulbul: 1
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - _No target species detected_
- BirdNET 誤検出 top 3 (対象種以外, 参考):
  - Northern Fulmar: max_conf=0.156, num=1
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ○, bulbul ✗

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 1, bulbul: 1}
- confidence: {sparrow: 0.76, bulbul: 0.54}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 362
  - frames_with_bird: 8
  - max_bbox_size_relative: 0.183
  - avg_bbox_size_relative: 0.116
  - std_bbox_size: 0.032
  - avg_detection_confidence: 0.317
- LLM reasoning: "最大 bbox サイズが 0.1833 で 0.1 を超え、検出数も複数存在。"
- 正誤: sparrow ✗, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 0, bulbul: 1}
- confidence: {sparrow: 0.80, bulbul: 0.70}
- fallback_triggered: false
- modality_used: visual
- LLM reasoning: "視覚情報より中型の bbox サイズが多いため。"
- 正誤: sparrow ○, bulbul ○

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_002

### 動画情報

- ファイル名: `Bird watching (chats_) 03.mp4`
- 再生時間: 41.4 s
- 解像度: 480x360
- FPS: 30
- ファイルサイズ: 1.73 MB

### Ground Truth (phase1_labels.json より)

- primary_label: `bulbul`
- sparrow: 0
- bulbul: 1
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - _No target species detected_
- BirdNET 誤検出 top 3 (対象種以外): _なし_
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ○, bulbul ✗

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 0, bulbul: 1}
- confidence: {sparrow: 0.85, bulbul: 0.92}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 41
  - frames_with_bird: 10
  - max_bbox_size_relative: 0.151
  - avg_bbox_size_relative: 0.125
  - std_bbox_size: 0.017
  - avg_detection_confidence: 0.612
- LLM reasoning: "最大 bbox サイズがヒヨドリの範囲内であり、検出数も主に中型鳥"
- 正誤: sparrow ○, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 0, bulbul: 1}
- confidence: {sparrow: 0.85, bulbul: 0.92}
- fallback_triggered: false
- modality_used: visual
- LLM reasoning: "中型の bbox サイズが多いため"
- 正誤: sparrow ○, bulbul ○

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_003

### 動画情報

- ファイル名: `Bird watching (chats_).mp4`
- 再生時間: 167.3 s
- 解像度: 480x360
- FPS: 30
- ファイルサイズ: 6.66 MB
- **優先レビュー理由**: A/B/C すべて失敗 (視覚が bulbul を sparrow に誤分類する傾向)

### Ground Truth (phase1_labels.json より)

- primary_label: `bulbul`
- sparrow: 0
- bulbul: 1
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - _No target species detected_
- BirdNET 誤検出 top 3 (対象種以外): _なし_
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ○, bulbul ✗

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 1, bulbul: 1}
- confidence: {sparrow: 0.76, bulbul: 0.58}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 167
  - frames_with_bird: 19
  - max_bbox_size_relative: 0.139
  - avg_bbox_size_relative: 0.072
  - std_bbox_size: 0.021
  - avg_detection_confidence: 0.588
- LLM reasoning: "最大 bbox サイズが 0.1391で 0.08以上、検出数も複数存在。"
- 正誤: sparrow ✗, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.85, bulbul: 0.15}
- fallback_triggered: false
- modality_used: visual
- LLM reasoning: "視覚情報でスズメの bbox サイズが小さい"
- 正誤: sparrow ✗, bulbul ✗

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_004

### 動画情報

- ファイル名: `Bird watching (Hypsipetes amaurotis).mp4`
- 再生時間: 144.9 s
- 解像度: 480x360
- FPS: 30
- ファイルサイズ: 6.04 MB
- **優先レビュー理由**: C が B より負けた fold (B 正答、C が bulbul を sparrow に誤分類)

### Ground Truth (phase1_labels.json より)

- primary_label: `bulbul`
- sparrow: 0
- bulbul: 1
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - _No target species detected_
- BirdNET 誤検出 top 3 (対象種以外, 参考):
  - Great Bittern: max_conf=0.256, num=1
  - Rock Pigeon: max_conf=0.145, num=7
  - Whooper Swan: max_conf=0.101, num=1
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ○, bulbul ✗

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 0, bulbul: 1}
- confidence: {sparrow: 0.85, bulbul: 0.92}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 145
  - frames_with_bird: 113
  - max_bbox_size_relative: 0.238
  - avg_bbox_size_relative: 0.150
  - std_bbox_size: 0.047
  - avg_detection_confidence: 0.630
- LLM reasoning: "最大 bbox サイズがヒヨドリの範囲であり、検出数も主に中型鳥"
- 正誤: sparrow ○, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.85, bulbul: 0.15}
- fallback_triggered: false
- modality_used: visual
- LLM reasoning: "視覚情報より小型鳥多数でスズメの可能性が高い"
- 正誤: sparrow ✗, bulbul ✗

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_005

### 動画情報

- ファイル名: `Bird watching (sparrow & Hypsipetes amaurotis).mp4`
- 再生時間: 197.3 s
- 解像度: 480x360
- FPS: 30
- ファイルサイズ: 7.51 MB
- **優先レビュー理由**: 両方失敗 / 'both' ラベル / A が唯一 LLM に到達した fold

### Ground Truth (phase1_labels.json より)

- primary_label: `both`
- sparrow: 1
- bulbul: 1
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 1}
- confidence: {sparrow: 0.96, bulbul: 0.96}
- fallback_triggered: false
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - Passer montanus: _not detected_
  - Hypsipetes amaurotis: max_conf=0.963, num_detections=8
- BirdNET 誤検出 top 3 (対象種以外, 参考):
  - Rock Pigeon: max_conf=0.214, num=7
- LLM reasoning: "BirdNETがbulbulを高確信で検出"
- 正誤: sparrow ✗, bulbul ○

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 0, bulbul: 1}
- confidence: {sparrow: 0.85, bulbul: 0.92}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 197
  - frames_with_bird: 115
  - max_bbox_size_relative: 0.212
  - avg_bbox_size_relative: 0.106
  - std_bbox_size: 0.055
  - avg_detection_confidence: 0.569
- LLM reasoning: "最大 bbox サイズがヒヨドリの範囲内であり、検出数も主に中型鳥"
- 正誤: sparrow ✗, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 0, bulbul: 1}
- confidence: {sparrow: 0.85, bulbul: 0.92}
- fallback_triggered: false
- modality_used: both
- LLM reasoning: "視覚情報でヒヨドリの bbox サイズが大きい。音声でもヒヨドリ検出。"
- 正誤: sparrow ✗, bulbul ○

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_006

### 動画情報

- ファイル名: `Bird watching (sparrow) 02.mp4`
- 再生時間: 159.7 s
- 解像度: 480x360
- FPS: 30
- ファイルサイズ: 5.83 MB

### Ground Truth (phase1_labels.json より)

- primary_label: `sparrow`
- sparrow: 1
- bulbul: 0
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - _No target species detected_
- BirdNET 誤検出 top 3 (対象種以外): _なし_
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ✗, bulbul ○

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.85, bulbul: 0.15}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 160
  - frames_with_bird: 24
  - max_bbox_size_relative: 0.083
  - avg_bbox_size_relative: 0.047
  - std_bbox_size: 0.016
  - avg_detection_confidence: 0.671
- LLM reasoning: "最大 bbox サイズが 0.0833 でスズメの範囲内。検出数も少ない。"
- 正誤: sparrow ○, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.85, bulbul: 0.15}
- fallback_triggered: false
- modality_used: visual
- LLM reasoning: "視覚情報から小型の bbox サイズが多いため"
- 正誤: sparrow ○, bulbul ○

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_007

### 動画情報

- ファイル名: `Bird watching (sparrow).mp4`
- 再生時間: 241.8 s
- 解像度: 540x360
- FPS: 20
- ファイルサイズ: 5.07 MB

### Ground Truth (phase1_labels.json より)

- primary_label: `sparrow`
- sparrow: 1
- bulbul: 0
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - _No target species detected_
- BirdNET 誤検出 top 3 (対象種以外): _なし_
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ✗, bulbul ○

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.85, bulbul: 0.15}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 242
  - frames_with_bird: 16
  - max_bbox_size_relative: 0.083
  - avg_bbox_size_relative: 0.050
  - std_bbox_size: 0.023
  - avg_detection_confidence: 0.569
- LLM reasoning: "最大 bbox サイズが 0.0832でスズメ未満、平均 bbox サイズも小さい"
- 正誤: sparrow ○, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.85, bulbul: 0.15}
- fallback_triggered: false
- modality_used: visual
- LLM reasoning: "視覚情報から小型の鳥が多く、音声情報はなし。"
- 正誤: sparrow ○, bulbul ○

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_008

### 動画情報

- ファイル名: `Bird watching 08 (sparrow).mp4`
- 再生時間: 62.2 s
- 解像度: 960x720
- FPS: 15
- ファイルサイズ: 12.68 MB
- **優先レビュー理由**: C が B より勝った fold (B が bulbul 誤付加, C が抑制)

### Ground Truth (phase1_labels.json より)

- primary_label: `sparrow`
- sparrow: 1
- bulbul: 0
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - Passer montanus: max_conf=0.218, num_detections=2
  - Hypsipetes amaurotis: _not detected_
- BirdNET 誤検出 top 3 (対象種以外): _なし_
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ✗, bulbul ○

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 1, bulbul: 1}
- confidence: {sparrow: 0.85, bulbul: 0.65}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 62
  - frames_with_bird: 21
  - max_bbox_size_relative: 0.206
  - avg_bbox_size_relative: 0.067
  - std_bbox_size: 0.048
  - avg_detection_confidence: 0.498
- LLM reasoning: "最大 bbox サイズが 0.2064で基準を上回り、検出数も複数"
- 正誤: sparrow ○, bulbul ✗

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.80, bulbul: 0.20}
- fallback_triggered: false
- modality_used: both
- LLM reasoning: "視覚でスズメの bbox サイズが小さい。音声は対象種検出あり。"
- 正誤: sparrow ○, bulbul ○

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_009

### 動画情報

- ファイル名: `Bird watching 09 (sparrow).mp4`
- 再生時間: 155.1 s
- 解像度: 960x720
- FPS: 15
- ファイルサイズ: 20.34 MB

### Ground Truth (phase1_labels.json より)

- primary_label: `sparrow`
- sparrow: 1
- bulbul: 0
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - _No target species detected_
- BirdNET 誤検出 top 3 (対象種以外): _なし_
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ✗, bulbul ○

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.95, bulbul: 0.05}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 155
  - frames_with_bird: 18
  - max_bbox_size_relative: 0.069
  - avg_bbox_size_relative: 0.034
  - std_bbox_size: 0.011
  - avg_detection_confidence: 0.507
- LLM reasoning: "最大 bbox サイズが 0.0685で 0.08未満。"
- 正誤: sparrow ○, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.85, bulbul: 0.15}
- fallback_triggered: false
- modality_used: visual
- LLM reasoning: "視覚情報から小型の鳥が多く、音声情報は補強なし。"
- 正誤: sparrow ○, bulbul ○

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_010

### 動画情報

- ファイル名: `Bird watching 10 (sparrow & Hypsipetes amaurotis).mp4`
- 再生時間: 89.2 s
- 解像度: 960x720
- FPS: 15
- ファイルサイズ: 18.12 MB
- **優先レビュー理由**: 両方失敗 / 'both' ラベル

### Ground Truth (phase1_labels.json より)

- primary_label: `both`
- sparrow: 1
- bulbul: 1
- review_needed: true
- location_detail: balcony
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - _No target species detected_
- BirdNET 誤検出 top 3 (対象種以外, 参考):
  - Rock Pigeon: max_conf=0.920, num=1
  - Common Merganser: max_conf=0.221, num=2
  - Mallard: max_conf=0.125, num=2
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ✗, bulbul ✗

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 0, bulbul: 1}
- confidence: {sparrow: 0.85, bulbul: 0.92}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 89
  - frames_with_bird: 64
  - max_bbox_size_relative: 0.402
  - avg_bbox_size_relative: 0.169
  - std_bbox_size: 0.047
  - avg_detection_confidence: 0.737
- LLM reasoning: "最大 bbox サイズが大きい値で、平均も中型以上。検出数もヒヨドリのパターン。"
- 正誤: sparrow ✗, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.90, bulbul: 0.10}
- fallback_triggered: false
- modality_used: visual
- LLM reasoning: "視覚情報から中型の bbox サイズが多いため"
- 正誤: sparrow ○, bulbul ✗

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---

## balcony_011

### 動画情報

- ファイル名: `sparrow(Hokkaido).mp4`
- 再生時間: 42.8 s
- 解像度: 636x360
- FPS: 29.947
- ファイルサイズ: 1.93 MB

### Ground Truth (phase1_labels.json より)

- primary_label: `sparrow`
- sparrow: 1
- bulbul: 0
- review_needed: true
- location_detail: hokkaido
- notes: (なし)

### Topology A (Audio-Only) の結果

- 予測: {sparrow: 0, bulbul: 0}
- confidence: {sparrow: 0.00, bulbul: 0.00}
- fallback_triggered: true
- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):
  - _No target species detected_
- BirdNET 誤検出 top 3 (対象種以外, 参考):
  - Large-billed Crow: max_conf=0.143, num=2
- LLM reasoning: "対象種の検出なし (LLM スキップ)"
- 正誤: sparrow ✗, bulbul ○

### Topology B (Visual-Only) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.95, bulbul: 0.05}
- fallback_triggered: false
- YOLOv8n 結果:
  - num_frames_analyzed: 43
  - frames_with_bird: 3
  - max_bbox_size_relative: 0.006
  - avg_bbox_size_relative: 0.004
  - std_bbox_size: 0.002
  - avg_detection_confidence: 0.412
- LLM reasoning: "最大 bbox サイズが非常に小さいためスズメと判定"
- 正誤: sparrow ○, bulbul ○

### Topology C (Parallel Fusion) の結果

- 予測: {sparrow: 1, bulbul: 0}
- confidence: {sparrow: 0.95, bulbul: 0.05}
- fallback_triggered: false
- modality_used: visual
- LLM reasoning: "視覚で小型鳥多数、音声無し"
- 正誤: sparrow ○, bulbul ○

### 人間レビュー欄 (Robosheep が記入)

- [ ] 動画を視聴した
- ground_truth は正しいか: [yes / no / 修正案]
- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]
- 各トポロジの評価:
  - A: [妥当 / 誤り / 部分的]
  - B: [妥当 / 誤り / 部分的]
  - C: [妥当 / 誤り / 部分的]
- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]

---
