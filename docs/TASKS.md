# TASKS.md — multimodal-aas development plan

This file tracks the development plan for multimodal-aas (AAS v2, heterogeneous nodes). It captures completed work, active phase design, future roadmap, frozen design decisions, and open questions. It is a living document: update as work progresses.

## 概要

multimodal-aas is the v2 continuation of sdnd-proof (AAS v1). It extends the LLM-only Adaptive Artificial Synapse (AAS) proof-of-concept to heterogeneous nodes (vision + audio + LLM) for bird observation tasks. The research orientation is deterrence-oriented AI development — verifying whether topology-learning multimodal architectures remain controllable at minimal scale before investing in larger systems.

- **Project root**: `C:\Users\pipe_render\research\multimodal-aas-bird`
- **Repository**: https://github.com/piperendervt-glitch/multimodal-aas
- **Predecessor**: sdnd-proof (AAS v1, 3-node LLM proof-of-concept, Cohen's d = 4.29, p = 0.0007)
- **Current phase**: Phase 1 (architecture minimum validation)
- **Research philosophy**: stage-gated, Go/No-Go at each sub-phase, judged by multiple AI systems plus other stakeholders (sdnd-proof style)

## 全体ロードマップ

| Phase | 目的 | 状態 |
| --- | --- | --- |
| Phase 0 | 環境構築 | 完了 |
| Phase 1 | アーキテクチャ最小検証 | 進行中 |
| Phase 2 | 拡張実装（本格データ、全ノード） | 未着手 |
| Phase 3 | コンポーネント選択実験 | 未着手 |
| Phase 4 | トポロジ比較実験（本実験） | 未着手 |
| Phase 5 | 公開・論文化 | 未着手 |

---

## Phase 0: 環境構築 [完了 2026-04-19]

- [x] Python 3.12 venv の構築
- [x] ffmpeg / yt-dlp のインストール
- [x] プロジェクト初期構造（src, docs, .gitignore, README, requirements.txt）
- [x] Xeno-canto API v3 対応の疎通テストスクリプト（疎通は保留）
- [x] 事前登録ドラフト（docs/pre_registration.md）
- [x] データソース階層文書（docs/data_sources.md）
- [x] Git 初期化・GitHub 公開（https://github.com/piperendervt-glitch/multimodal-aas）
- [x] Phase 1 メタデータ生成スクリプト（src/generate_metadata.py）
- [x] ラベルテンプレート生成スクリプト（src/generate_label_template.py）
- [x] 11 本の自前撮影動画のインベントリ（data/metadata.json）
- [x] 初期ラベルテンプレート（data/labels/phase1_labels.json）

### Phase 0 残タスク（Phase 1 の前提として優先度中）

- [ ] GitHub リポジトリの About セクション編集（Description、Topics）
- [ ] sdnd-proof README への相互リンク追加
- [ ] `phase1_labels.json` の review_needed を手動で確認し、必要な修正を反映
- [ ] README.md と docs/data_sources.md の「data/ ディレクトリ構造」記述を現配置に同期
- [ ] Claude Code が検出した VFR 動画（balcony_011）のフラグを metadata.json に追記

---

## Phase 1: アーキテクチャ最小検証 [進行中]

### Phase 1 全体方針

**目的**: 多モーダル異種ノード AAS アーキテクチャが機能するかを、最小コストで検証する。各サブ段階に Go/No-Go ゲートを設け、成立しない場合は Phase 2 への投資前に方向転換する。

**判定者**: 複数の AI システム（Claude, ChatGPT, Grok）および他のステークホルダー（sdnd-proof と同じスタイル）。最終判断は Robosheep が行うが、全員の意見を記録する。

**No-Go 時の対応**: 事前には決めず、状況を見て判断する。ただし判定者の複数化により主観バイアスは抑制する。

### Phase 1 共通データセット

**出典**: 自前撮影動画 11 本（合計約 27.7 分、ベランダ 10 本 + 北海道 1 本）

**構成**: 
- sparrow 単独: 5 本
- bulbul 単独: 4 本
- sparrow + bulbul 混在: 2 本

**データ取扱い**:
- 分割方式: Leave-One-Out 交差検証（LOO-CV、11 fold）
- ラベル方式: マルチラベル分類（sparrow と bulbul を独立にバイナリ予測）
- Phase 4 との関係: 11 本は Phase 4 でも共通ベンチマークとして再利用、Phase 4 では追加データも併用

**既知の技術的注意点**:
- balcony_011 は fps=29.947 の VFR 動画 → 前処理で `ffmpeg -vsync cfr` による CFR 変換を検討
- 解像度が 480×360 〜 960×720 とばらつく → 検出・分類ノード前のリサイズ統一が必要
- 全 11 本に AAC 音声トラックあり

### Phase 1 評価指標（バランス型 + Mirror Effect 包括計測）

**主要指標**:
- macro F1（sparrow クラスと bulbul クラス独立に計算し平均）
- confusion matrix（クラスごとの誤り傾向）

**Mirror Effect 関連指標（全候補を並行計測）**:
- 候補 A: ノード間の予測一致率
- 候補 B: 予測分布の類似度（KL divergence）
- 候補 C: 重み変化の相関（Phase 1.4d 以降のみ）
- 候補 D: 出力の時系列変化（動画内で予測がどう推移するか）

**補助指標**:
- 処理時間（end-to-end、ノード別）
- 計算コスト（GPU メモリ、トークン使用量）
- 出力確信度分布

**統計的評価**:
- paired Welch t-test を計算（pre_registration.md 記載通り）
- ただし p 値は参考指標として観察するのみ、統計的判断の根拠にはしない
- 統計的判断の本格化は Phase 4

### Phase 1.1: Single node [未着手]

**構成**: LLM（Ollama qwen2.5:7b）のみ

**目的**: LLM ノードの基盤動作確認

**検証内容**:
- 鳥の記述テキスト（例: 「茶色い小鳥、チュンチュンと鳴く」）を与え、種名を答えさせる
- 10 個のテストプロンプトを準備
- JSON 形式での構造化出力に従えるか

**Go 基準 β**: 鳥の記述から種名（sparrow / bulbul / unknown）を答えられる

**No-Go 時**: 別モデル（llama3, mistral:7b）やプロンプトの見直し

### Phase 1.2: Two nodes (single modality) [未着手]

**構成**: LLM + YOLOv8n（視覚）または LLM + BirdNET（音声）

**目的**: 異種ノード間のデータ受け渡しとルーティング動作確認

**検証内容**:
- 5 本の動画に対して end-to-end でパイプラインを実行
- YOLOv8n / BirdNET の出力を LLM が解釈できるか
- エラーハンドリング（検出失敗時の挙動）

**Go 基準 β**: 5 本の動画で全て出力が得られる

**No-Go 時**: 出力形式のアダプタ層見直し、プロンプト設計変更

### Phase 1.3: Three nodes (multimodal, topology comparison) [未着手]

**構成**: YOLOv8n + BirdNET + LLM（qwen2.5:7b）

**目的**: マルチモーダル統合の確認、全 6 トポロジの比較

**実施内容**:
- 全 6 トポロジ × 11 動画 × LOO-CV = 66 実行
- 各トポロジの動作ログ、予測、Mirror Effect 指標を記録

**トポロジ一覧**:

| ID | 名称 | 特徴 | LLM 呼出回数 |
| --- | --- | --- | --- |
| A | Audio-Only | BirdNET + LLM のみ（ベースライン） | 1 |
| B | Visual-Only | YOLOv8n + LLM のみ（ベースライン） | 1 |
| C | Parallel Fusion | 両モダリティ並列、LLM が統合 | 1 |
| D | Audio-First Gating | 音声確信度 > 閾値の場合のみ視覚実行 | 2 |
| E | Visual-Guided Audio | 視覚で鳥検出された場合のみ音声識別 | 2 |
| F | Cross-Validation | 独立判断 + LLM 仲裁 | 3 |

**ゲーティング閾値（D, E）**: Phase 1.3 では仮値 0.7。Phase 4 で事前登録値を確定。

**Go 基準 β**: 複数トポロジで結果に差が観察される

**No-Go 時**: トポロジ設計の根本的見直し、もしくは研究方向全体の再検討を要する重要な判断点

### Phase 1.4: Extended architecture [段階的実装、工数大]

**目的**: frame_extractor 追加および同種ノード並列化による拡張効果の検証

**Go 基準 β'**: Phase 1.3 より性能（macro F1）か効率（処理時間）のいずれかが向上

**実装方針**: 段階的実装 + 途中での再評価。1.4b 完了時点で 1.4c 以降の詳細を再議論する。

#### Phase 1.4a: frame_extractor 追加 [設計確定]

- 構成: frame_extractor + YOLOv8n + BirdNET + LLM（4 ノード）
- 前処理の知能化（動画 → 代表フレーム選択）
- Phase 1.3 ベースラインとの比較

#### Phase 1.4b: YOLOv8n parallelism [設計確定]

- 構成: frame_extractor + YOLOv8n × 2 + BirdNET + LLM
- YOLOv8n × 2（異なる confidence 閾値、adaptive routing）
- Mirror Effect のスケーリング挙動を観測
- Phase 1.4a ベースラインとの比較

#### Phase 1.4c: LLM parallelism [1.4b 完了後に詳細再議論]

- 方向性: 異種 LLM × 3（qwen2.5:7b + llama3 + mistral:7b）による多数決
- 具体的実装は 1.4b の結果次第で決定
- 計算コスト課題: RTX 5060 Ti (16GB VRAM) で 3 モデル同時並列は困難 → シーケンシャル実行または量子化版を検討

#### Phase 1.4d: 重み更新機構 [1.4c 後に設計]

- 方向性: 正解フィードバックによる LLM 層重みの適応更新
- 実装前に更新ルール（増減量、正規化方法）の事前登録が必要
- AAS 原理を LLM 層に移植

#### Phase 1.4e: 合議モード [1.4d 後に設計]

- 重み更新が停滞した場合の escape hatch
- Multi-agent debate 方式での LLM 間対話
- 終了条件（最大ラウンド数、収束判定）の事前設計が必要

---

## Phase 2: 拡張実装 [未着手]

Phase 1 で全 Go/No-Go を通過した場合の、本格投資フェーズ。Phase 1.4c-e の詳細は 1.4b 完了時に再議論するため、Phase 2 の範囲もそれに応じて調整する。

**主な内容（仮）**:
- データ量の拡大（11 本 → 50-100 本）
- Xeno-canto API 利用の再開検討（保留中）
- 異種ノード拡充（Grounding DINO、CLIP、Wav2Vec2 などの追加）
- Phase 1 で未実装だったトポロジ構成の追加

---

## Phase 3: コンポーネント選択実験 [未着手]

複数の検出器・分類器を比較して最良の組み合わせを選ぶ。方向 2（異種ノード追加）の本格実施。

**候補**:
- 視覚検出: YOLOv8n vs Grounding DINO
- 視覚分類: CLIP vs iNaturalist model
- 音声分類: BirdNET（既に使用）vs Wav2Vec2 など

---

## Phase 4: トポロジ比較実験（本実験） [未着手]

事前登録の厳密運用で、統計的に意味のあるトポロジ比較を行う。

**主な内容**:
- 事前登録の最終化（SHA-256、freeze date、freeze commit、ゲーティング閾値、重み更新ルール）
- 11 本共通ベンチマーク + 追加データで実行
- paired Welch t-test による統計的判断を本格化
- macro F1 が主要評価指標

---

## Phase 5: 公開・論文化 [未着手]

- Zenodo リリース（DOI 取得）
- 結果レポート作成
- sdnd-proof との比較論文ドラフト
- 方向 1（同種ノード並列化）の AAS v3 への発展可能性を記述

---

## 凍結された設計判断

以下は議論の結果凍結された事項。変更する場合は明示的に合意を取り直す。

- **対象種**: sparrow (Passer montanus) と bulbul (Hypsipetes amaurotis) の 2 クラス
- **ラベル方式**: マルチラベル分類（各クラスを独立にバイナリ予測）
- **Phase 1 データ**: 自前撮影 11 本（合計約 27.7 分）
- **データ分割**: Leave-One-Out 交差検証（11 fold）
- **Phase 1.3 トポロジ数**: 6（A-F、全実施）
- **Phase 1.3 実行数**: 6 トポロジ × 11 動画 × LOO-CV = 66 実行
- **Phase 1.4 実施方針**: 段階的実装（1.4a → 1.4b → [再議論] → 1.4c → 1.4d → 1.4e）
- **Phase 1.4 実験デザイン**: 拡張オプション比較（frame のみ vs 並列のみ vs 両方）
- **LLM（Phase 1.3 まで）**: Ollama qwen2.5:7b
- **LLM（Phase 1.4c 以降）**: 異種モデル × 3（qwen2.5:7b + llama3 + mistral:7b、詳細は再議論）
- **主要評価指標**: macro F1
- **Mirror Effect 計測**: 候補 A, B, C, D を並行
- **統計検定方針**: paired Welch t-test を計算、Phase 1 では p 値は参考指標
- **Go/No-Go 判定者**: 複数 AI + 他者（sdnd-proof スタイル）
- **ゲーティング閾値（Phase 1.3）**: 仮値 0.7
- **研究方向順序**: 方向 1（同種ノード並列化）→ 方向 2（異種ノード追加）→ 方向 3（単調スケーリング）

---

## 未決定事項（TODO）

- [ ] Phase 1.4c の LLM 並列化の詳細設計（1.4b 完了時に議論）
- [ ] Phase 1.4d の重み更新ルール（1.4c 完了時に事前登録）
- [ ] Phase 1.4e の合議モード実装方式（1.4d 完了時に設計）
- [ ] Phase 4 での追加データ収集方針（Xeno-canto 再開 vs 自前追加録音 vs その他公開データセット）
- [ ] Phase 4 ゲーティング閾値の事前登録値
- [ ] Mirror Effect の定量化における閾値・重み付けの具体化
- [ ] Zenodo 連携準備（v0.1.0 初期リリースで DOI 取得するかの判断）
- [ ] Phase 1.4c で 3 LLM 並列する場合の VRAM 対応（量子化 vs シーケンシャル）
- [ ] Phase 4b の pre_registration 凍結手順（SHA-256、freeze date、freeze commit）

---

## ブロッカー・依存関係

- Phase 1.2 以降は Phase 1.1 Go 判定後
- Phase 1.3 は Phase 1.2 Go 判定後
- Phase 1.4 は Phase 1.3 Go 判定後
- Phase 1.4c の詳細設計は Phase 1.4b の結果次第
- Phase 2 は Phase 1.4 全体の Go 判定後
- Phase 4 は Phase 3 完了と pre_registration 凍結が前提
- Phase 5 Zenodo は Phase 4 完了が前提

---

## Future Research（Phase 5 以降、別プロジェクト化も視野）

これらは multimodal-aas v2 の直接スコープ外だが、研究系譜として明記する。

- **AAS v3 構想**: 異種 × 同種並列 AAS（multimodal × parallel units）
  - v1 sdnd-proof: 同種ノード AAS
  - v2 multimodal-aas: 異種ノード AAS
  - v3 (future): 異種 × 同種並列 AAS
- 方向 3（単調スケーリング）: ノード数増加に対する性能スケーリング法則
- 物理 AAS（アクアポニクス、HXP）との統合検討
- TRUSS との接続（ホスト AI 安全性フレームワークへの multimodal-aas の組み込み）

---

## 関連プロジェクト

- **sdnd-proof**: https://github.com/piperendervt-glitch/sdnd-proof （AAS v1、凍結済み）
- **TRUSS**: ホスト AI 安全性フレームワーク
- **Aquaponics Physical AAS**: 物理 AAS 実装テストベッド（構想段階）
- **HXP (Human eXtension Platform)**: ウェアラブル感覚拡張（別プロジェクト）

---

## 更新履歴

- 2026-04-19: Phase 0 完了、Phase 1 詳細設計を反映した TASKS.md 初版作成
