# multimodal-aas-bird: TASKS.md

## プロジェクト概要

**プロジェクト名**: multimodal-aas-bird
**リポジトリ**: https://github.com/piperendervt-glitch/multimodal-aas
**開始日**: 2026-04-19

**研究目的**: sdnd-proof (AAS v1) で実証された「Adaptive 構造は Fixed 構造を上回る」効果を、マルチモーダル鳥識別タスクで応用し、AI 安全性研究に貢献する。

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

---

## sdnd-proof (AAS v1) との関係

### 参照研究
- **GitHub**: https://github.com/piperendervt-glitch/sdnd-proof
- **著者**: pipe_render (村下 勝真 / KATSUMA MURASHITA)
- **実績**: p=0.0007, Cohen's d=4.29, 5/5 trials

### sdnd-proof の実験設計 (継承対象)

| | Experiment A (Fixed) | Experiment B (Adaptive) |
|---|---|---|
| Structure | Node1 → Node2 → Node3 | flow_weight updated per result |
| Model | qwen2.5:3b | qwen2.5:3b |
| Hardware | identical | identical |

**flow_weight 更新式**:
```
success: new_weight = old_weight + 0.1 × (1.0 - old_weight)
failure: new_weight = old_weight × 0.7
```

**評価**: 問題 51-100 (flow_weight 蓄積後) の accuracy
**3 基準**: p < 0.05, Cohen's d ≥ 0.8, 95% CI が 0 を含まない

### 非スケール原則 (README より)

> 「本研究は 3 ノード PoC の結果をもって完結しました」
> 「これ以上のスケーリングは行いません」
> 「動的適応構造 (AAS) と安全設計は、原理的に両立しません」
> 「性能を上げるほど制約を超えようとする力が働きます」
> 「この矛盾に踏み込まないことが、今できる最大限の安全対策です」

**multimodal-aas-bird の立ち位置**:
- sdnd-proof の **拡張ではなく、手法の応用**
- 3-node scale 原則を超えない
- constitution.md の safety principles に従う

### constitution.md の safety principles (適用)

- **Human Override Authority** (Art. 3): Robosheep がいつでも停止可能
- **No Self-Modification** (Art. 8-2): エージェント自身のコード変更不可
- **Adaptation is bounded** (Art. 6): executor のみ適応、judge/watchdog/leader は固定
- **Automatic stopping conditions** (Art. 8-1): 事前定義
- **Autonomous startup restriction** (Art. 8-8): Leader のみが executor を起動
- **Internet connectivity warning** (Art. 9): ローカル・隔離環境前提

---

## 判定者プロセス (sdnd-proof スタイル)

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
- Topology A: self=0.143, YouTube=0.720, 全体=0.611
- Topology B: self=0.795, YouTube=0.542, 全体=0.610
- Topology C: self=0.733, YouTube=0.874, 全体=0.840
- commit: 2a19fe5

### Phase 1.4a: frame_extractor 追加実験 [完了]

#### Robosheep の優先順位
1. 目的 B: macro F1 向上 (主)
2. 目的 D: モダリティ同期度 (副)
3. 目的 C: 時系列情報活用度 (副)
4. 目的 A: 処理時間 (余力)

#### 実装結果

##### 目的 B (C_v2, frame_extractor): No-Go
- YOLOv8n 事前検出で bird フレームのみを LLM に渡す
- 全 42 fold: 0.826、Clean 22-fold: 0.791 → **No-Go 確定**
- commit: 4e402d1

##### 目的 D (C_v3, temporal_sync): Practical Go
- 2 秒時間窓で visual と audio の対応関係を LLM に提供
- 全 42 fold: 0.819、Clean 22 fold: 0.869 → **Go 逆転**
- sync_rate 相関: 正答 0.283 vs 誤答 0.030 (約 9 倍)
- commit: 3dcbac4

##### bbox プロンプト v3 (B_v3): Statistical Go
- Grok 判定第 1 ラウンド最優先項目への対応
- bbox 絶対閾値 → 相対分布 + size_consistency
- YouTube clean で 0.500 → 0.721 (+0.221) → **Statistical Go**
- commit: 4113107

##### bbox v3 + fusion (C_v4): No-Go
- clean で 0.823 → 0.635 (-0.188) → **No-Go 確定**
- commit: 4113107

#### Paired Bootstrap CI 結果 (commit b6a2580)

| Comparison | n | point Δ | 95% CI (paired) | P(Δ>0) | 判定 |
|---|---|---|---|---|---|
| C_v3 vs C (macro) | 22 | +0.045 | [+0.000, +0.153] | 0.641 | Practical Go |
| C_v3 vs C (sparrow F1) | 22 | +0.057 | [+0.000, +0.212] | 0.641 | Practical Go |
| C_v3 vs C (bulbul F1) | 22 | +0.034 | [+0.000, +0.117] | 0.641 | Practical Go |
| B_v3 vs B (YouTube) | 11 | +0.221 | [+0.024, +0.417] | 0.983 | **Statistical Go** |

#### Phase 1.4a 最終 Go 状態

| Intervention | 最終判定 |
|---|---|
| Obj B (frame_extractor) | No-Go |
| Obj D (temporal_sync) | Practical Go (CI touches 0) |
| bbox v3 on B (Grok Q2) | **Statistical Go** ← 論文化 headline |
| bbox v3 on C (C_v4) | No-Go (regression) |
| Obj C (時系列活用) | スキップ (sync_rate で既に活用済み) |
| Obj A (処理時間) | スキップ (優先度最低) |

**Phase 1.4a 結論**: 統計的に有意な改善 1 件 (B_v3)、実用的改善 1 件 (C_v3) 獲得。

#### C_v3 を Statistical Go に格上げするための候補
1. Clean データ拡張 (Macaulay Library)
2. 別ベースラインとのペア比較
3. Paired-Δ CI を狭める設計変更 (分散削減)

---

## Phase 1.4d: AAS v1 応用実験 [計画確定、実装次回]

### 設計方針: sdnd-proof 対照実験の継承

**sdnd-proof と同じ実験デザインパターン**:

| | Experiment A (Fixed) | Experiment B (Adaptive) |
|---|---|---|
| Structure | 固定重み (均等 or 学習なし) | flow_weight 更新 |
| Model | qwen2.5:7b | qwen2.5:7b |
| Hardware | identical | identical |
| Data | Clean 22 fold | Clean 22 fold |
| Update Rule | none | sdnd-proof 継承 |

### flow_weight 更新式 (sdnd-proof から継承)

```python
success: new_weight = old_weight + 0.1 × (1.0 - old_weight)
failure: new_weight = old_weight × 0.7
```

**数学的性質**:
- Success 則: 指数的な 1 への接近 (上限あり、max +0.1)
- Failure 則: 指数的減衰 (max -0.3)
- **非対称性**: 失敗は成功の 3 倍のインパクト
- リスク回避型学習、粘菌 (Physarum polycephalum) の管路動態に着想

### 評価基準 (sdnd-proof と同じ 3 基準)

- p < 0.05
- Cohen's d ≥ 0.8
- 95% CI が 0 を含まない

### 実行方針: 完全マトリクス実験

**4 対象 × 4 アルゴリズム = 16 実験**

#### 対象 (実行順)

1. **A: トポロジ間の重み** (最もシンプル、最初に実装)
   - Topology A, B, C の信頼度重み
   - Fixed: w_A=w_B=w_C=0.5 固定
   - Adaptive: flow_weight 更新

2. **B: モダリティ間の重み** (Visual vs Audio)
   - Topology C 内での統合重み
   - マルチモーダル研究の本丸

3. **C: ノード内の重み** (LLM 判断の詳細)
   - プロンプト内の判断材料の重み

4. **D: 複合的** (多階層)
   - 上記の組み合わせ

#### アルゴリズム (実行順)

1. **sdnd-proof AAS v1 学習ルール** (継承)
   - success: w + 0.1 × (1-w)
   - failure: w × 0.7

2. **Reinforcement Learning**
3. **EMA (Exponential Moving Average)** (sdnd-proof との比較対照)
4. **Gradient-based**

#### 実装段階

- **Phase 1.4d-prototype**: 対象 A + sdnd-proof で最小動作確認
- **Phase 1.4d-full**: 全 16 実験 + Stage 3 で Mirror Effect 本格観察

### Mirror Effect 観察

- **Stage 1, 2**: 純粋な重み更新のみ (Mirror Effect 観察しない)
- **Stage 3**: 最良組み合わせで Mirror Effect を集約的に観察
- Phase 1.3 拡張で観察された現象 (A vs C > B vs C) の動的追跡

### 推定工数

- 16 実験 × 1-3 時間 = 16-48 時間
- 複数週間の大規模実験
- Phase 1.4d 完成は数週間後

### 次回セッションの作業項目

1. Stage 1 第一実験 (対象 A + sdnd-proof) の詳細設計
2. Fixed vs Adaptive 対照実験の具体的手順
3. Claude Code 依頼文作成
4. 実装開始

---

## Phase 1.4b, 1.4c, 1.4e: 今後のタスク

### Phase 1.4b: YOLOv8n 並列化 [優先度: 中]
- 異なる閾値での multi-head YOLOv8n
- B_v3 で視覚側は既に改善済み、相対的優先度低下

### Phase 1.4c: LLM 並列化 [優先度: 中]
- qwen2.5:7b + llama3 + mistral の 3 LLM 多数決
- Grok 指摘の盲点: 複数モデル検証

### Phase 1.4e: 合議モード [優先度: 低]

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
- sparrow (8), bulbul (4), mixed (8)
- **mixed 全滅**

### データ品質ゲートの教訓

- YouTube 検索ではタイトルのみで判断すると **65% が不適切**
- 日本野鳥の会等の権威あるソースほど科学的編集が施されており、raw データには向かない
- **Robosheep の「疲労時レビュー回避」判断は研究の誠実性の勝利** (Grok round 2 Q5)

### 新ルール

- **Review Gate**: データレビューは疲労時を避け、集中力のある状態で実施
- **Scope Limitation**: Phase 1 の mixed 評価は self-recorded 2 例に限定
- **Data Quality Audit**: 新データソース追加時は全件事前レビュー

### Phase 2 への持ち越し

- Macaulay Library 申請 (Phase 1 完了後、Grok 推奨)
- 外部マイク調達 (Web カメラ音質問題の根本解決)
- 自前動画の長期蓄積

---

## データセット仕様

### Clean 22 fold (Phase 1 評価基準)

| カテゴリ | 自前 | YouTube (Tier A+B+B') | 合計 |
|---|---|---|---|
| sparrow | 5 | 3 | 8 |
| bulbul | 4 | 8 | 12 |
| mixed | 2 | 0 | **2** (統計的制限あり) |
| **合計** | **11** | **11** | **22** |

---

## 研究的発見のカタログ

1. **音質がマルチモーダル統合の価値を決定する**
   - Clean audio (YouTube): C - B = +0.332
   - Webcam audio (self): C ≈ B

2. **情報追加は non-monotonic**
   - C_v2 (objective B): 情報削減 → -0.014
   - C_v3 (objective D): 情報追加 → +0.050 (clean)

3. **sync_rate が正答の強力な予測因子** (新発見)
   - 正答 fold 平均 sync_rate = 0.283
   - 誤答 fold 平均 sync_rate = 0.030

4. **エラー方向のトポロジ依存性**

5. **bbox プロンプトの環境依存性**
   - 絶対閾値は自前動画に過適合
   - 相対分布 (B_v3) で YouTube に対応可能

6. **Phase 1.3 C の性能上限**
   - 0.823 (clean) が qwen2.5:7b × 現 prompt の近傍最適

7. **データ品質がゲートとして機能**
   - Full 42 fold: C_v3 No-Go
   - Clean 22 fold: C_v3 Go
   - **データ品質で判定が逆転する**

### 論文化候補

**Paper 1 (副次的、即時)**: "Negative results in multimodal LLM fusion: when adding information hurts"
- Phase 1.4a の No-Go 群
- データ品質 gate の定量化 (65% unusable)
- arXiv preprint 候補

**Paper 2 (メイン、Phase 1.4d 完了後)**: AAS v1 応用 — sdnd-proof flow_weight の多モーダル分類への適用
- sdnd-proof 対照実験の継承
- Mirror Effect の実証 (Phase 1.4d Stage 3)
- **scale を超えない安全設計**

---

## 外部判定者プロセス

### Grok 判定第 1 ラウンド (2026-04-19, 午前)
- 主要推奨: Q2 bbox v3 最優先、Q5 YouTube GT review 盲点
- 結果: Q2 実施で B_v3 Statistical Go、Q5 は Robosheep 判断で延期 (結果的に正解)

### Grok 判定第 2 ラウンド (2026-04-19, 午後)
- 主要推奨: Q2 paired bootstrap 今日中、Q3 mixed drop、Q4 1.4d 直行
- 結果: paired bootstrap 完了、B_v3 Statistical Go 確定

### ChatGPT 判定 (未実施)
- Phase 1 完了時にまとめて依頼予定

---

## コミット履歴 (主要)

| Commit | 内容 |
|---|---|
| 3a5ffc3 | Phase 1.1 単独 LLM |
| 031d2a8 | Phase 1.2 両モダリティ |
| 16c77b1 | Phase 1.3 Topology A, B |
| 998287f | BirdNET 北米 baseline |
| 5c36e3d | BirdNET 日本種感度 |
| 8ad78a9 | Phase 1.3 Topology C |
| 2a19fe5 | Phase 1.3 extended (42 fold) |
| 4e402d1 | Phase 1.4a C_v2 |
| 3dcbac4 | Phase 1.4a C_v3 |
| 4113107 | Phase 1.4a B_v3/C_v4 |
| 46770df | Clean dataset reevaluation |
| e63162f | Session summary v2 for Grok |
| b6a2580 | Paired bootstrap CI |
| 54e8de3 | TASKS.md Phase 1.4a 完了版 |

---

## 次のマイルストーン

### 次回セッション
- [ ] Phase 1.4d Stage 1 第一実験 (対象 A + sdnd-proof) の詳細設計
- [ ] Fixed vs Adaptive 対照実験の具体的手順
- [ ] Phase 1.4d-prototype の Claude Code 依頼文作成
- [ ] constitution.md safety principles の適用確認

### 今週中
- [ ] Phase 1.4d Stage 1 完了 (対象 A × sdnd-proof)
- [ ] 評価基準 (p<0.05, d≥0.8, 95%CI excludes 0) の検証

### 今月中
- [ ] Phase 1.4d Stage 1, 2 完了 (対象 A, B, C, D × sdnd-proof)
- [ ] Phase 1.4d Stage 3 開始 (Mirror Effect 観察)

### 長期 (2-3 ヶ月)
- [ ] Phase 1.4d 全 16 実験完了
- [ ] Paper 1 (negative results) arXiv preprint
- [ ] Paper 2 (AAS 応用) 準備
- [ ] Phase 2 hardware (外部マイク) 調達計画
- [ ] Macaulay Library データ取得 (Phase 2)
- [ ] ChatGPT 判定取得 (Phase 1 完了時)
- [ ] Zenodo DOI リリース

---

## Future Research

### 未解決課題
- qwen2.5:7b 単一依存 (llama3.2:3b での再現確認 — Grok 指摘)
- Mixed カテゴリの評価 (Macaulay Library 申請 or Phase 2 自前データ)
- bootstrap paired CI の統計的厳密化 (Clean データ拡張後)
- Phase 2 hardware (外部マイク) 具体的スケジュール

### 研究的深化の候補
- C_v5 (bbox_distribution 情報としてのみ追加) — Phase 1.4d の中で吸収
- 時系列情報の更なる活用
- 異種 LLM での Mirror Effect 観察 (1.4c + 1.4d)
- Tier A-only データでの極限性能測定 (n=4 で C_v3 が perfect 1.000)

### 研究哲学の発展
- Deterrence-oriented AI development の具体化
- AI 能力追求 vs AI 制御の設計原理
- sdnd-proof の非スケール原則の維持
- constitution.md の継承と適用

---

**Last Updated**: 2026-04-19 (Phase 1.4a 完了、Phase 1.4d 計画確定、sdnd-proof 対照実験方式継承)
