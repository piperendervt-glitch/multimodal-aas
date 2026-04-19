# multimodal-aas-bird: TASKS.md

## プロジェクト概要

**プロジェクト名**: multimodal-aas-bird
**リポジトリ**: https://github.com/piperendervt-glitch/multimodal-aas
**開始日**: 2026-04-19

**研究目的**: AAS (Adaptive Artificial Synapse) v1 (sdnd-proof, Cohen's d = 4.29) の多モーダル拡張による、AI 安全性研究への貢献。Heterogeneous-node マルチモーダル AAS の実証と、統制可能な AI 設計の探求。

**哲学**: Deterrence-oriented AI development — AI 能力の追求ではなく、制御不能な AI を抑止するための研究。

**対象**:
- スズメ (Passer montanus, Eurasian Tree Sparrow)
- ヒヨドリ (Hypsipetes amaurotis, Brown-eared Bulbul)
- 撮影環境: 自前ベランダ + バードケーキ

**技術スタック**:
- YOLOv8n (視覚、COCO bird class)
- BirdNET (音声、Japanese species model)
- qwen2.5:7b (LLM、Ollama 経由)
- GPU: RTX 5060 Ti 16GB VRAM

**判定者プロセス (sdnd-proof スタイル)**:
- 判定者 I: Claude (設計相談役)
- 判定者 II: Claude Code (実装)
- 判定者 III: Grok + ChatGPT + 人間 (独立評価)

---

## Phase 別の進捗と Go/No-Go 判定

### Phase 0: 環境構築 [完了]

- 11 自前動画取得 (sparrow 5, bulbul 4, mixed 2)
- Python 3.12 venv, ffmpeg, Ollama
- 合計 27.7 分
- data/metadata.json, data/labels/phase1_labels.json

### Phase 1.1: qwen2.5:7b 単独 [Go]

- 5 プロンプト、スコア 3.0/5.0
- ゲート基準 β (3.0 以上) を最小限達成
- commit: 3a5ffc3

### Phase 1.2: 両モダリティ [両方 Go]

- Visual (YOLOv8n + LLM): 11/11 パース成功、macro F1 = 0.389
- Audio (BirdNET + LLM): 11/11 パース成功、macro F1 = 0.268
- Topology B の "always sparrow" collapse 発生
- commit: 031d2a8

### Phase 1.3: Topology A/B/C 実装 [Go]

- Topology A (Audio-Only): macro F1 = 0.143, fallback 10/11
- Topology B (Visual-Only): macro F1 = 0.819
- Topology C (Parallel Fusion): macro F1 = 0.733
- Human review で正誤判定の妥当性を確認
- commits: 16c77b1, 8ad78a9

#### BirdNET 音質問題の切り分け [確定]
- (a) BirdNET セットアップ: 北米鳥 423 検出で OK (commit: 998287f)
- (b) 日本種モデル感度: スズメ 0.839, ヒヨドリ 0.981 で OK (commit: 5c36e3d)
- (c) 自前動画 Web カメラマイク音質: **確定的な原因**

### Phase 1.3 拡張: 42 fold 評価 [強い Go]

- 自前 11 + YouTube 31 = 42 fold
- Topology A: self=0.143, YouTube=0.720, 全体=0.611 (音質問題の 5 倍改善)
- Topology B: self=0.795, YouTube=0.542, 全体=0.610 (YouTube 退化 -0.253)
- Topology C: self=0.733, YouTube=0.874, 全体=0.840
- commit: 2a19fe5

#### 判明した事実
- 音質仮説完全確定: Topology A は clean audio でマルチモーダル統合を有効化
- Topology B の YouTube 退化: bbox プロンプト自前動画への過適合
- Topology C の環境依存性: 両モダリティがクリーンな時に真価を発揮
- Mirror Effect 初期観察: A vs C 一致率 > B vs C 一致率 (C が A の影響を強く受ける)

### Phase 1.4a: frame_extractor 追加実験

#### 当初設計
frame_extractor をノード化し、マルチモーダル統合を前処理レベルから改善。目的 A (処理効率), B (精度), C (時系列活用), D (モダリティ同期) の 4 つの目的。

#### Robosheep の優先順位
1. 目的 B: macro F1 向上 (主)
2. 目的 D: モダリティ同期度 (副)
3. 目的 C: 時系列情報活用度 (副)
4. 目的 A: 処理時間 (余力)

#### 実装結果

##### 目的 B (C_v2, frame_extractor): No-Go [42 fold 基準]
- YOLOv8n 事前検出で bird フレームのみを LLM に渡す
- macro F1 = 0.826 (Phase 1.3 C より -0.014)
- Clean 22-fold 再評価でも 0.791 < 0.86 → No-Go 確定
- **含意**: density 情報の喪失による LLM 誤判断
- commit: 4e402d1

##### 目的 D (C_v3, temporal_sync): Go [clean 22-fold で逆転]
- 2 秒時間窓で visual と audio の対応関係を LLM に提供
- 全 42 fold: 0.819 → **No-Go 判定**
- **Clean 22 fold: 0.869 > 0.86 → Go 逆転**
- 実装試行錯誤: full timeline 150 → ReadTimeout、compact 40 → hallucinate、集計のみ (6 フィールド) → 成功
- sync_rate と正誤の強い相関: 正答 0.283 vs 誤答 0.030 (約 9 倍)
- commit: 3dcbac4

##### bbox プロンプト v3 (B_v3, C_v4): B_v3 Go / C_v4 No-Go
- Grok 判定第 1 ラウンド最優先項目への対応
- bbox 絶対閾値 → 相対分布 (small/medium/large) + size_consistency
- B_v3: YouTube clean で 0.500 → 0.721 (+0.221) → **Go (YouTube gate)**
- C_v4 (bbox v3 + fusion): clean で 0.823 → 0.635 (-0.188) → **No-Go 確定**
- **含意**: bbox 改良は visual-only で機能、fusion で干渉
- commit: 4113107

#### Phase 1.4a Go 判定 [完了]

| 目的 | 判定 | 根拠 |
|---|---|---|
| 目的 B (frame_extractor) | **No-Go** | 情報削減が本質的に不利 |
| 目的 D (temporal_sync) | **Go** (clean) | C_v3 clean 0.869 > 0.86 |
| bbox v3 (B_v3) | **Go** (YouTube gate) | +0.221 on YouTube clean |
| bbox v3 + fusion (C_v4) | **No-Go** | fusion で干渉 |
| 目的 C (時系列活用) | **スキップ** | Grok 判定 Q4: sync_rate で既に活用済み、ROI 低い |
| 目的 A (処理時間) | **スキップ** | 優先度最低、余力時のみ |

**統計的確認**: paired bootstrap (進行中)
- C_v3 vs C (clean 22 fold) Δ=0.046
- B_v3 vs B (YouTube clean 11 fold) Δ=0.221

### Phase 1.4b-e: 今後のタスク

#### Phase 1.4b: YOLOv8n 並列化
- 異なる閾値での multi-head YOLOv8n
- adaptive routing
- **優先度: 中** (Grok 判定 Q4: Phase 2 hardware 改善後に回せる)

#### Phase 1.4c: LLM 並列化
- qwen2.5:7b + llama3 + mistral の 3 LLM 多数決
- VRAM 16GB 制約への対応
- **優先度: 中** (Grok 判定 Q6 盲点: 複数モデル検証は重要)

#### Phase 1.4d: 重み更新機構 [最優先]
- AAS 学習ルールの実装
- Mirror Effect の本格観察
- topology 間 adaptive synapse
- **優先度: 最高** (Grok 判定 Q4: AAS の本質)
- C_v5 実験 (Phase 1.3 C プロンプト + bbox_distribution を純情報として追加) を 1.4d に吸収可能

#### Phase 1.4e: 合議モード
- Escape hatch として、多数決による判定
- **優先度: 低**

---

## データ品質の学び

### データソース階層

**Tier A (完全に使える)**: 4 本
- sparrow (1): yt_ZRQLsbGEVG8
- bulbul (3): yt_8HhsjaqFITQ, yt_8zanYHHEpiw, yt_vmrbbEe9R6M

**Tier B (冒頭除外、トリミング要)**: 6 本
- sparrow (1): yt_JCGgh5zvEeE
- bulbul (5): yt_-DYmOCTDWc0, yt_jk15DbXQV6A, yt_kMWUQOW-bTM, yt_lnyw5TOMea8, yt_QxKLx__Nzn4

**Tier B' (音ノイズ多いが使える)**: 1 本
- sparrow (1): yt_evVHoDIv1hE

**Tier C (使えない、除外)**: 20 本
- sparrow (8): 多くは科学的編集が施された動画 (声紋解析、効果音等)
- bulbul (4): 日本野鳥の会の声紋解析シリーズ等
- mixed (8): **全滅** — 編集動画の性質上、テキスト・ナレーション過多

### データ品質ゲートの教訓

- **YouTube 検索ではタイトルのみで判断すると 65% が不適切**
- 日本野鳥の会等の権威あるソースほど科学的編集が施されており、rawデータには向かない
- **mixed カテゴリの取得が特に困難** — 「複数種を見せる」動画は編集必須
- **Robosheep の「疲労時レビュー回避」判断は研究の誠実性の勝利** (Grok round 2 Q5)

### 新ルール (TASKS.md に追加)

- **Review Gate**: データレビューは疲労時を避け、集中力のある状態で実施
- **Scope Limitation**: Phase 1 の mixed 評価は self-recorded 2 例に限定
- **Data Quality Audit**: 新データソース追加時は全件事前レビュー

---

## データセット仕様

### Clean 22 fold (Phase 1 評価基準)

| カテゴリ | 自前 | YouTube (Tier A+B+B') | 合計 |
|---|---|---|---|
| sparrow | 5 | 3 | 8 |
| bulbul | 4 | 8 | 12 |
| mixed | 2 | 0 | **2** (統計的制限あり) |
| **合計** | **11** | **11** | **22** |

### Phase 2 への持ち越し

- Macaulay Library 申請 (Cornell Lab of Ornithology) — 研究利用無料、リクエスト制
  - 優先度: 中 (Phase 1 完了後)
  - Grok 判定: Phase 1 を止めずに並行検討
- 外部マイク調達 (RODE VideoMicro / Zoom H1n 等) — Web カメラ音質問題の根本解決
  - 優先度: 中 (Phase 2 hardware として)
- 自前動画の長期蓄積 (外部マイク導入後)

---

## 研究的発見のカタログ

### Phase 1 で得られた知見

1. **音質がマルチモーダル統合の価値を決定する**
   - Clean audio (YouTube): C - B = +0.332
   - Webcam audio (self): C ≈ B
   - 含意: ハードウェア選定が AAS 設計と不可分

2. **情報追加は non-monotonic**
   - C_v2 (objective B): 情報削減 → -0.014
   - C_v3 (objective D): 情報追加 → +0.050 (clean) / -0.021 (full)
   - LLM プロンプトの均衡が壊れると性能が退化

3. **sync_rate が正答の強力な予測因子** (新発見)
   - 正答 fold 平均 sync_rate = 0.283
   - 誤答 fold 平均 sync_rate = 0.030
   - 約 9 倍の差

4. **エラー方向のトポロジ依存性**
   - 各 topology が異なるエラーパターン
   - sparrow と bulbul で F1 の trade-off

5. **bbox プロンプトの環境依存性**
   - 絶対閾値は自前動画に過適合
   - 相対分布 (B_v3) で YouTube に対応可能
   - ただし fusion への統合は逆効果

6. **Phase 1.3 C の性能上限**
   - 0.823 (clean) が qwen2.5:7b × 現 prompt の近傍最適
   - 単純改良では超えられず、根本的アプローチ必要

7. **データ品質がゲートとして機能**
   - Full 42 fold: C_v3 No-Go
   - Clean 22 fold: C_v3 Go
   - **同じ実験結果の解釈が、データ品質で逆転する**

### 論文化候補

**Paper 1 (副次的、即時)**: "Negative results in multimodal LLM fusion: when adding information hurts"
- Phase 1.4a の No-Go 群 (objective B, C_v4)
- データ品質 gate の定量化 (65% unusable)
- arXiv preprint 候補

**Paper 2 (メイン、Phase 1.4d 完了後)**: AAS v2 — Heterogeneous-node adaptive synapse for multimodal classification
- Mirror Effect の実証
- 重み更新機構
- sdnd-proof AAS v1 からの拡張

---

## 外部判定者プロセス

### Grok 判定第 1 ラウンド (2026-04-19, 午前)
- レポート: results/reports/session_summary_for_grok.md
- 主要推奨:
  - Q1: Phase 1.4a Objective C 限定継続 (コンパクト版)
  - Q2: bbox v3 最優先 ← 実施、B_v3 Go
  - Q3: 1.4d に全力移行
  - Q5: YouTube GT review 盲点 ← Robosheep の判断で延期 (結果的に正解)

### Grok 判定第 2 ラウンド (2026-04-19, 午後)
- レポート: results/reports/session_summary_for_grok_v2.md
- 主要推奨:
  - Q1: Phase 1.4a 完了宣言 OK (条件付き Go として記録)
  - Q2: paired bootstrap 今日中実施
  - Q3: mixed は Phase 1 で drop、scope 限定明記
  - Q4: 1.4d 直行
  - Q5: Robosheep の review 延期判断は称賛、新ルール明文化推奨
  - Q6: 論文化価値あり (arXiv preprint 候補)

### ChatGPT 判定 (未実施)
- Phase 1 完了時にまとめて依頼予定
- Claude + Grok + ChatGPT + 人間の 4 者判定

---

## コミット履歴 (主要)

| Commit | 内容 |
|---|---|
| 7c82b1f | Bootstrap リポジトリ、TASKS.md 初版 |
| 3a5ffc3 | Phase 1.1 単独 LLM |
| 031d2a8 | Phase 1.2 両モダリティ |
| 16c77b1 | Phase 1.3 Topology A, B |
| 9300f37 | raw_analysis.md |
| 998287f | BirdNET 北米 baseline |
| 5c36e3d | BirdNET 日本種感度 |
| 8ad78a9 | Phase 1.3 Topology C |
| 6544295 | Video review sheet |
| 2a19fe5 | Phase 1.3 extended (42 fold) |
| 4e402d1 | Phase 1.4a C_v2 (objective B) |
| 3dcbac4 | Phase 1.4a C_v3 (objective D) |
| 4113107 | Phase 1.4a B_v3/C_v4 (bbox v3) |
| 46770df | Clean dataset reevaluation |
| e63162f | Session summary v2 for Grok |

---

## 次のマイルストーン

### 今日中
- [x] Paired bootstrap CI 計算 (進行中)
- [ ] TASKS.md 更新 (このファイル)

### 今週中
- [ ] Phase 1.4d (Mirror Effect + weight update) 設計開始
- [ ] C_v5 最小実験 (bbox_distribution 純情報として追加)
- [ ] ChatGPT 判定取得 (Phase 1 完了時)

### 今月中
- [ ] Phase 1 complete 宣言
- [ ] Paper 1 (negative results) arXiv preprint 準備
- [ ] Phase 2 hardware (外部マイク) 調達計画

### 長期 (2-3 ヶ月)
- [ ] Phase 1.4d (Mirror Effect 本格観察)
- [ ] Macaulay Library データ取得 (Phase 2)
- [ ] Paper 2 メイン論文準備
- [ ] Zenodo DOI リリース

---

## Future Research セクション

### 未解決課題
- qwen2.5:7b 単一依存 (llama3.2:3b での再現確認 — Grok 指摘)
- Mixed カテゴリの評価 (Macaulay Library 申請 or Phase 2 自前データ)
- bootstrap paired CI の統計的厳密化
- Phase 2 hardware (外部マイク) 具体的スケジュール

### 研究的深化の候補
- C_v5 (bbox_distribution 情報としてのみ追加)
- 時系列情報の更なる活用 (目的 C を 1.4d の中で)
- 異種 LLM での Mirror Effect 観察 (1.4c + 1.4d)
- Tier A-only データでの極限性能測定 (n=4 で C_v3 が perfect 1.000 の示唆)

### 研究哲学の発展
- Deterrence-oriented AI development の具体化
- AI 能力追求 vs AI 制御の設計原理
- Heterogeneous-node AAS の社会実装への含意

---

**Last Updated**: 2026-04-19 (Phase 1.4a 完了、paired bootstrap 実行中)
