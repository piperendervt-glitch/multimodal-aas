# Phase 1.3 Raw Results Analysis

Phase 1.3 の Topology A (Audio-Only) と Topology B (Visual-Only) を
22 本の per-fold JSON から再構成して分析したレポート。
数字はすべて `results/phase1_3/topology_{a,b}/fold_*/*.json` を Python で
ロードして計算したもの。推測 (inference) と観察 (observation) は節ごとに
明記する。

- 入力 fold 数: A = 11, B = 11
- LLM: `qwen2.5:7b` @ temperature 0.1 (両トポロジ共通)
- 実行日: 2026-04-19 (`git log` 参照)

---

## 1. Topology A (Audio-Only) の実態分析

### 1.1 各 fold の BirdNET 検出状況

| fold | video_id | GT (S/B) | all_det (conf≥0.1) | target@0.3 | top_other_bird (count) | fallback |
|---:|---|:-:|---:|---|---|:-:|
| 01 | balcony_001 | 0/1 | 1  | -            | Northern Fulmar (×1)       | Y |
| 02 | balcony_002 | 0/1 | 0  | -            | -                          | Y |
| 03 | balcony_003 | 0/1 | 0  | -            | -                          | Y |
| 04 | balcony_004 | 0/1 | 9  | -            | Rock Pigeon (×7)           | Y |
| 05 | balcony_005 | 1/1 | 15 | bulbul×5     | Rock Pigeon (×7)           | - |
| 06 | balcony_006 | 1/0 | 0  | -            | -                          | Y |
| 07 | balcony_007 | 1/0 | 0  | -            | -                          | Y |
| 08 | balcony_008 | 1/0 | 2  | -            | -                          | Y |
| 09 | balcony_009 | 1/0 | 0  | -            | -                          | Y |
| 10 | balcony_010 | 1/1 | 6  | -            | Mallard (×2)               | Y |
| 11 | balcony_011 | 1/0 | 2  | -            | Large-billed Crow (×2)     | Y |

**観察**:

- 11 fold 中 5 fold (02, 03, 06, 07, 09) で BirdNET は min_conf=0.1 においても
  **全く何も検出しなかった** (`all_det=0`)。
- 対象種 (sparrow/bulbul) が `≥0.3` で検出されたのは fold_05 のみ
  (bulbul×5、max conf 0.96)。他の 10 fold はすべて fallback となった。
- fold_08 (balcony_008) は GT が sparrow なのに対し、BirdNET は
  Eurasian Tree Sparrow を `0.16` と `0.22` の 2 ウィンドウで検出して
  いた — 0.3 閾値で切り捨てられている。
- fold_04 (bulbul GT) では Rock Pigeon が 7 件検出されているが、
  対象種は一切検出されていない。

### 1.2 fold_05 の詳細 — Audio-Only が LLM に到達した唯一の fold

**ground_truth**: `{sparrow: 1, bulbul: 1}` (両方)

**LLM 入力**:

```json
{
  "detections": [
    {"species_code": "bulbul",
     "scientific_name": "Hypsipetes amaurotis",
     "confidence": 0.9627,
     "num_detections": 5}
  ],
  "other_birds_detected": ["Rock Pigeon"],
  "total_audio_duration_sec": 197.35
}
```

**LLM 応答 (raw)**:

```json
{
  "predictions": {"sparrow": 0, "bulbul": 1},
  "confidence": {"sparrow": 0.9627, "bulbul": 0.9627},
  "reasoning": "BirdNETがbulbulを高確信で検出",
  "fallback_used": false
}
```

**結果**: bulbul は正答、sparrow は誤答 (GT=1 → pred=0)。LLM には
sparrow の情報が一切渡っていないため、見逃すのは設計上必然。

**観察**: BirdNET がターゲット種のうち片方しか拾えなかった (この fold では
bulbul のみ) 場合、LLM に対する入力は非対称となり、他方のクラスは事実上
`0` 固定になる。これは `filtered_target_species` を LLM への単一証拠として
使う Topology A 設計の構造的盲点。

### 1.3 BirdNET 閾値を変えた場合の反実仮想

11 fold の `all_detections` を閾値別に再集計して直接マルチラベル予測
(ターゲット検出あり → `1`) を行った場合の成績:

| threshold | sparrow (TP/FP/FN/TN) | bulbul (TP/FP/FN/TN) | sparrow F1 | bulbul F1 | macro F1 |
|---:|---|---|---:|---:|---:|
| 0.05 | 1/0/6/4 | 1/0/5/5 | 0.250 | 0.286 | **0.268** |
| 0.10 | 1/0/6/4 | 1/0/5/5 | 0.250 | 0.286 | **0.268** |
| 0.15 | 1/0/6/4 | 1/0/5/5 | 0.250 | 0.286 | **0.268** |
| 0.20 | 1/0/6/4 | 1/0/5/5 | 0.250 | 0.286 | **0.268** |
| 0.25 | 0/0/7/4 | 1/0/5/5 | 0.000 | 0.286 | 0.143 |
| 0.30 | 0/0/7/4 | 1/0/5/5 | 0.000 | 0.286 | 0.143 |

**観察**:

- 閾値を 0.3 → 0.05 まで下げても macro F1 は **0.268** (約 +0.125) までしか
  上昇しない。
- その上昇は専ら fold_08 の sparrow (conf 0.16–0.22) を救うかどうかで決まる。
- 閾値以外の場所 — 9/11 の fold は対象種の検出がそもそも 0 件 — は
  どの閾値でも救えない。BirdNET 側の感度/特異性問題であって、
  閾値チューニングで到達可能な上限は非常に低い。

**推奨閾値**: `0.2` (現行 0.3 より +1 TP、FP は増えない)。ただし
A 単独の改善幅は限定的で、根本解決にはならない。

### 1.4 他種誤検出の実態

11 fold 全体、confidence≥0.1 の全検出 (37 件) のヒストグラム:

| 種 | 件数 | conf (min / mean / max) |
|---|---:|---|
| Rock Pigeon | 15 | 0.10 / 0.18 / 0.92 |
| Brown-eared Bulbul (bulbul) | 8 | 0.17 / 0.56 / 0.96 |
| Eurasian Tree Sparrow (sparrow) | 2 | 0.16 / 0.19 / 0.22 |
| Mallard | 2 | 0.12 / 0.12 / 0.13 |
| Common Merganser | 2 | 0.12 / 0.17 / 0.22 |
| Large-billed Crow | 2 | 0.13 / 0.14 / 0.14 |
| Northern Fulmar | 1 | 0.16 |
| Whooper Swan | 1 | 0.10 |
| Great Bittern | 1 | 0.26 |
| Gray Heron | 1 | 0.11 |

**観察**:

- 最も多く誤検出されるのは **Rock Pigeon** (15 件、件数で bulbul の約 2 倍)。
  mean conf は 0.18 と低いが、max は 0.92 (つまり一部に高確信の誤検出がある)。
- sparrow の検出は 2 件のみで、いずれも conf ≤ 0.22。BirdNET はこの録音
  条件ではスズメをほぼ拾えていない (**推測**: 周囲ノイズ、マイク感度、
  バードケーキ越しの距離、Webcam 内蔵マイクの帯域制限が候補)。
- bulbul は良好に検出される (8 件中 4 件が conf ≥ 0.5)。
- 海鳥 (Northern Fulmar, Whooper Swan, Gray Heron, Common Merganser,
  Mallard) が出現する点から、環境音や衣擦れ等の非鳥音を鳥として誤認
  している可能性が高い。

---

## 2. Topology B (Visual-Only) の実態分析

### 2.1 全 fold の bbox サイズ分布

| fold | video_id | GT (S/B) | frames | with_bird | max_rel | avg_rel | std | pred (S/B) | S ok | B ok |
|---:|---|:-:|---:|---:|---:|---:|---:|:-:|:-:|:-:|
| 01 | balcony_001 | 0/1 | 362 |   8 | 0.183 | 0.116 | 0.032 | 1/1 | X | OK |
| 02 | balcony_002 | 0/1 |  41 |  10 | 0.151 | 0.125 | 0.017 | 0/1 | OK | OK |
| 03 | balcony_003 | 0/1 | 167 |  19 | 0.139 | 0.072 | 0.021 | 1/1 | X | OK |
| 04 | balcony_004 | 0/1 | 145 | 113 | 0.238 | 0.150 | 0.047 | 0/1 | OK | OK |
| 05 | balcony_005 | 1/1 | 197 | 115 | 0.212 | 0.106 | 0.055 | 0/1 | X | OK |
| 06 | balcony_006 | 1/0 | 160 |  24 | 0.083 | 0.047 | 0.016 | 1/0 | OK | OK |
| 07 | balcony_007 | 1/0 | 242 |  16 | 0.083 | 0.050 | 0.023 | 1/0 | OK | OK |
| 08 | balcony_008 | 1/0 |  62 |  21 | 0.206 | 0.067 | 0.048 | 1/1 | OK | X |
| 09 | balcony_009 | 1/0 | 155 |  18 | 0.069 | 0.034 | 0.011 | 1/0 | OK | OK |
| 10 | balcony_010 | 1/1 |  89 |  64 | 0.402 | 0.169 | 0.047 | 0/1 | X | OK |
| 11 | balcony_011 | 1/0 |  43 |   3 | 0.006 | 0.004 | 0.002 | 1/0 | OK | OK |

### 2.2 両クラス正答した fold (6/11)

- balcony_002, 004, 006, 007, 009, 011

| fold | video_id | GT | max_rel | avg_rel | std | reasoning (LLM) |
|---|---|---|---:|---:|---:|---|
| 02 | balcony_002 | 0/1 | 0.151 | 0.125 | 0.017 | 最大 bbox サイズがヒヨドリの範囲内であり、検出数も主に中型鳥 |
| 04 | balcony_004 | 0/1 | 0.238 | 0.150 | 0.047 | 最大 bbox サイズがヒヨドリの範囲であり、検出数も主に中型鳥 |
| 06 | balcony_006 | 1/0 | 0.083 | 0.047 | 0.016 | 最大 bbox サイズが 0.0833 でスズメの範囲内。検出数も少ない。 |
| 07 | balcony_007 | 1/0 | 0.083 | 0.050 | 0.023 | 最大 bbox サイズが 0.0832でスズメ未満、平均 bbox サイズも小さい |
| 09 | balcony_009 | 1/0 | 0.069 | 0.034 | 0.011 | 最大 bbox サイズが 0.0685で 0.08未満。 |
| 11 | balcony_011 | 1/0 | 0.006 | 0.004 | 0.002 | 最大 bbox サイズが非常に小さいためスズメと判定 |

**観察**:

- 正答 fold は **max_rel と GT の対応が明快** な場合に限られる。
  - sparrow 正答 (06, 07, 09, 11): max_rel が 0.006–0.083 と、すべて
    プロンプトの "sparrow < 0.08" 境界の外側または上限ちょうど。
  - bulbul 正答 (02, 04): max_rel が 0.151–0.238 と、"bulbul ≥ 0.1"
    ゾーンの十分内側。
- 両クラス正答はすべて **単独クラス (sparrow-only か bulbul-only)** 。
  "both" ラベル (05, 10) は一つも両クラス正答していない (後述)。

### 2.3 誤答の詳細

**sparrow クラス誤答 (4 fold)**:

| fold | video_id | GT_S | pred_S | max_rel | avg_rel | std | コメント |
|---:|---|:-:|:-:|---:|---:|---:|---|
| 01 | balcony_001 | 0 | 1 | 0.183 | 0.116 | 0.032 | bbox 大・平均も中型、にも関わらず LLM は「検出数複数」を根拠に sparrow=1 とした偽陽性 |
| 03 | balcony_003 | 0 | 1 | 0.139 | 0.072 | 0.021 | max_rel が 0.08–0.15 の曖昧ゾーン、LLM が両方=1 を選択 |
| 05 | balcony_005 | 1 | 0 | 0.212 | 0.106 | 0.055 | "both" GT だが、LLM は bulbul のみ (max_rel > 0.15) |
| 10 | balcony_010 | 1 | 0 | 0.402 | 0.169 | 0.047 | "both" GT、max_rel が極端に大 (0.40) のため bulbul のみ |

**bulbul クラス誤答 (1 fold)**:

| fold | video_id | GT_B | pred_B | max_rel | avg_rel | std | コメント |
|---:|---|:-:|:-:|---:|---:|---:|---|
| 08 | balcony_008 | 0 | 1 | 0.206 | 0.067 | 0.048 | sparrow-only なのに **瞬間的に近距離で撮れたフレーム** で max_rel=0.21。LLM はプロンプト基準に従って bulbul=1 を追加。std=0.048 が "混在" ヒントを発火させた可能性。|

**失敗パターンの共通点**:

- `max_rel` が 0.08–0.15 の中間帯にあると LLM は `1/1` を選びやすい
  (fold_01, fold_03)。"複数サイズが混在" ルールが過剰発火。
- `std` が大きい (≥ 0.04) 単独クラスでも "混在" と誤解釈される
  (fold_08: sparrow-only なのに std=0.048 で bulbul=1 が追加)。
- "both" ラベル (fold_05, fold_10) は sparrow を見逃す。これは小個体の
  bbox がフレーム内に同居していても、同じフレーム内での相対サイズ比較が
  プロンプトから欠けているため。

### 2.4 bbox サイズ閾値 (0.08 / 0.15) の妥当性

GT バケット別 max_rel 分布:

| GT bucket | 件数 | max_rel 範囲 |
|---|---:|---|
| S=1, B=0 (sparrow-only) | 5 | 0.006 – 0.206 (※fold_08 を除けば ≤ 0.083) |
| S=0, B=1 (bulbul-only)  | 4 | 0.139 – 0.238 |
| S=1, B=1 (both)         | 2 | 0.212 – 0.402 |

**観察**:

- sparrow-only の 4/5 fold で max_rel ≤ 0.083 → **0.08 は妥当な上限**。
  ただし fold_08 (sparrow-only で max_rel=0.206) は近距離でのサイズ爆発
  による例外。avg_rel=0.067、std=0.048 なので「avg でスクリーニング」が
  補正手段候補。
- bulbul-only の 4 fold は max_rel ≥ 0.139、**0.15 は高すぎる**
  (fold_03 の 0.139 を切り捨ててしまう)。
- "both" の max_rel は 0.212 と 0.402。avg_rel はそれぞれ 0.106 と 0.169
  (単純閾値では判別不能)。

**推奨閾値 (データ駆動)**:

- `sparrow=1` ← `max_rel < 0.10` AND `avg_rel < 0.07`
- `bulbul=1`  ← `max_rel ≥ 0.13` (0.15 より緩める)
- `both` の推論は bbox サイズだけでは不可能、フレーム内複数個体の
  サイズ diversity (std, 検出数/フレーム分布) を明示的に参照させる
  プロンプトが必要。

---

## 3. A vs B の詳細比較

### 3.1 11 動画別予測対比

| fold | video_id | GT S/B | A_pred S/B | B_pred S/B | A 正答 S/B | B 正答 S/B | agree S | agree B |
|---:|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 01 | balcony_001 | 0/1 | 0/0 | 1/1 | OK/X  | X/OK  | X | X |
| 02 | balcony_002 | 0/1 | 0/0 | 0/1 | OK/X  | OK/OK | OK | X |
| 03 | balcony_003 | 0/1 | 0/0 | 1/1 | OK/X  | X/OK  | X | X |
| 04 | balcony_004 | 0/1 | 0/0 | 0/1 | OK/X  | OK/OK | OK | X |
| 05 | balcony_005 | 1/1 | 0/1 | 0/1 | X/OK  | X/OK  | OK | OK |
| 06 | balcony_006 | 1/0 | 0/0 | 1/0 | X/OK  | OK/OK | X | OK |
| 07 | balcony_007 | 1/0 | 0/0 | 1/0 | X/OK  | OK/OK | X | OK |
| 08 | balcony_008 | 1/0 | 0/0 | 1/1 | X/OK  | OK/X  | X | X |
| 09 | balcony_009 | 1/0 | 0/0 | 1/0 | X/OK  | OK/OK | X | OK |
| 10 | balcony_010 | 1/1 | 0/0 | 0/1 | X/X   | X/OK  | OK | X |
| 11 | balcony_011 | 1/0 | 0/0 | 1/0 | X/OK  | OK/OK | X | OK |

### 3.2 パターン分類

| 分類 | 件数 | 内訳 |
|---|---:|---|
| Both correct | 0 | — |
| Only A correct | 0 | — |
| Only B correct | 6 | balcony_002, 004, 006, 007, 009, 011 |
| Both wrong | 5 | balcony_001, 003, 005, 008, 010 |

**Only B correct (6 fold)** で A が返した値:

全 6 fold で A は `fallback_triggered=True` であり、予測は `0/0` 固定。
すなわち「A が独自に誤答している」のではなく、「A が対象種を検出できず
fallback した結果、たまたま GT の片方がゼロだったので部分点的に正解
扱いになった fold もある」のが実態。

**Both wrong (5 fold)** の共通点:

- 4 fold (001, 003, 008, 010) で A は fallback → 0/0。
- fold_005 のみ A は LLM 実行し 0/1 を返した (ただし sparrow を拾い切れず)。
- B は 3 fold (001, 003, 008) で "1/1" (過検出)、2 fold (005, 010) で
  "0/1" (sparrow 見逃し)。
- いずれも **"both" 含み または 過検出寄り** のエッジケース。

### 3.3 Mirror Effect 候補 A の初期計測

**予測一致率 (A=B)**:

| クラス | A=B | A 正答 | B 正答 | A の予測分布 |
|---|:-:|:-:|:-:|---|
| sparrow | 4/11 | 4/11 | 7/11 | 常に 0 (11/11) |
| bulbul  | 5/11 | 6/11 | 10/11 | ほぼ常に 0 (10/11、唯一の 1 は fold_05) |

**"A は B に追従している" か "A は独立に誤答している" か**:

- **観察**: A の予測分布は `sparrow: [0]*11` と `bulbul: [0]*10 + [1]*1`。
  つまり A は情報を運んでいるというより「ほぼ常に `0/0` を出す定数関数」
  に近い挙動。
- **推測**: Mirror Effect (A が B に追従する) の検証は、現状の A では
  **不可能**。A に LLM の裁量がほぼ無い (`fallback_triggered=10/11`) ため、
  A の出力は B と独立でも、B の逆でも、A は動かないから。
- **推測**: Mirror Effect を有意に計測するには A に「LLM が判断を行う機会」
  を増やす必要がある = 閾値を下げて LLM 到達率を上げるか、
  fallback ロジックを排して全 BirdNET 検出を LLM に渡す。

---

## 4. Phase 1.3 Topology C〜F 設計への示唆

### 4.1 Topology A の閾値問題への対処

**問題の再定義**: A が 10/11 fold で fallback に入る限り、C (Parallel
Fusion) で A の出力を使っても実質的には B 単独と同等、または B に
バイアス (fold_05 の bulbul 強調) を加えるだけ。

**3 案の比較**:

| 案 | 概要 | 期待効果 | リスク |
|---|---|---|---|
| (a) 閾値を下げる (0.3→0.1) | target_min_conf を 0.1 に | A の LLM 到達率が 2/11 まで上がる (fold_05, fold_08)。macro F1 上限 ≈ 0.27 | fold_08 の sparrow 検出は 0.16–0.22、LLM が "低確信だから無視" を選ぶ可能性 |
| (b) 閾値を撤廃、全 BirdNET 検出を LLM に渡す | Phase 1.2 音声版と同じ入力 | LLM が他種検出 (Rock Pigeon 等) の不在/存在から背景的な推論可 | 入力量増 (LLM context 20–30 項目)、ノイズで LLM が迷う可能性 |
| (c) 2 段階閾値 | 高確信 (≥0.5) は直接採用、低確信 (0.1–0.5) は LLM 参考情報 | LLM の裁量枠を広げつつ fold_05 型の高確信ケースは即決 | 実装複雑化、2 パスプロンプト設計 |

**推奨**: **(b) を基本とし、(c) を Topology E / F で検討**。理由:

- Phase 1.2 の audio 版 (macro F1 = 0.268) は実質 (b) の構成であり、
  現行の閾値付き (A macro F1 = 0.143) より優れていた。
- (a) 単独では fold_08 の sparrow 検出を活かすだけで上限が低い。
- (c) は単ノードとして複雑、トポロジ境界を曖昧にする。

### 4.2 Topology B プロンプト改良の横展開

**B の成功要因 (vs Phase 1.2)**:

- 明示的な bbox サイズ閾値 (0.08 / 0.15) を与えたこと。
- `std_bbox_size`、`avg_bbox_size_relative` など統計量の追加で LLM の推論に
  "混在" の概念を導入したこと。
- `frames_with_bird=0` の場合は LLM を呼ばず fallback する二段階処理。

**C〜F への再利用**:

- 上記プロンプトをサブプロンプトテンプレートとして共通化、
  各トポロジで "視覚根拠セクション" にそのまま差し込む。
- 閾値の具体値は後述の 2.4 節の推奨値に更新 (0.15→0.13 など)。

### 4.3 各トポロジの期待挙動 (現状データに基づく推測)

| Topology | 構成 | 期待挙動 | 根拠 |
|---|---|---|---|
| C (Parallel Fusion) | A, B の出力を LLM に並列入力 | 現行 A では B 単独+α。A を (b) 案で緩和すれば macro F1 ≈ 0.82 維持 or 微増 | A がほぼ定数関数なので寄与率が低い |
| D (Audio-First Gating) | A が検出あれば採用、無ければ B | 実質 B 単独 (fold_05 のみ A 側採用) | A の到達率 1/11 |
| E (Visual-First Gating) | B で bird 検出 → A で種確認 | B の結果に A を要求するが、A の sparrow 識別力は皆無 | sparrow 識別は BirdNET のボトルネック |
| F (Cross-Validation) | A と B が一致すれば採用、不一致なら仲裁 | 一致率が sparrow 4/11, bulbul 5/11 と低く、仲裁ロジックが支配的 | §3.3 agreement 表 |

**観察の強調**: **A の根本的問題 (BirdNET が sparrow を検出できない)
は、どのトポロジ構成でも解決しない**。A への入力改善 (例: マイクアレイ、
より近接したマイク、高 SNR 録音) が必要だが、これは Phase 4 のハードウェア
見直し課題。

### 4.4 推奨される C〜F 設計方針 (データ駆動)

**優先順位付きの推奨**:

1. **C (Parallel Fusion) を最優先で実装**し、A 側の前処理を (b) 案
   (全 BirdNET 検出を LLM へ) に変更。Phase 1.2 の audio 版結果と比較
   して C の追加価値を定量化する。

2. **D (Audio-First Gating) は現状データでは実装する価値が低い**。
   実装しても実質 B 単独が観測されるのみ。優先度 最低。

3. **E (Visual-First Gating) は B の閾値ベース判定に A を「確証レイヤー」
   として乗せる** 構成で再定義。B で bulbul 判定が出たとき、A が bulbul
   を否定すれば sparrow に倒すなど、非対称ルールを明示。

4. **F (Cross-Validation) は仲裁ロジックの設計が本体**。現状データでは
   A と B が一致するのは bulbul=0 の 5 fold 程度で、信号量が不足。
   低閾値 A (上記 (b)) の導入後に再評価。

**リスク評価**:

| トポロジ | 追加実装コスト | 期待 macro F1 改善幅 | 備考 |
|---|---|---|---|
| C | 低 (既存モジュール再利用) | +0.00 〜 +0.05 (vs B単独) | 最も安全、実装価値高 |
| D | 低 | ≈ 0 | 実装する必要性が低い |
| E | 中 (非対称ルール設計) | 不明 | B の誤答 (001, 003, 008) を A が否定できるか要検証 |
| F | 高 (仲裁ロジック) | 不明 | 信号量不足、A の拡張後再評価 |

---

## 5. Phase 1.3 全体の Go/No-Go 判定への含意

### 5.1 β 基準 "複数トポロジで結果に差がある" の評価

現在実装済みの A と B の macro F1 差は:

- Topology A: **0.143** (LLM 到達率 1/11、実質的に定数関数)
- Topology B: **0.819** (LLM 到達率 11/11、bbox ベースの推論が機能)

**観察**: 差 0.676 は十分大きく、「トポロジの違いが結果に反映される」
という β 基準は形式的には満たされている。

**懸念**: この差の大部分は "BirdNET が sparrow を検出できない" という
ハードウェア/モデル由来の非対称性によるものであり、
トポロジ設計 (Parallel Fusion vs Gating vs Cross-Validation) の
優劣を示したものではない。

### 5.2 A/B 差を Go 根拠にできるか

**推奨判断**: **部分的な Go、ただし C 実装後に再判定すべき**。

- Go 要件を「パイプラインが最後まで動く」「トポロジ間で挙動差が出る」
  と解釈すれば **Go**。
- Go 要件を「Mirror Effect / Topology 効果が初期観察できる」と解釈すれば
  **データ不足**。A が事実上定数関数のため、A vs B の差は topology 効果
  ではなく信号量差を見ているだけ。

### 5.3 C〜F 実装後に見るべき指標

1. **A の LLM 到達率 (=1 − fallback_rate)**。これが 6/11 以上にならないと
   C〜F の比較は意味を持たない。
2. **A と B の予測一致率**: Mirror Effect の直接観察量。現状 sparrow
   4/11, bulbul 5/11 がベースライン。
3. **C で both ラベル (fold_05, fold_10) の sparrow が拾えるか**。
   これは A のマイク改善 (Phase 4) や、B の複数個体検出 (Phase 4
   の DINO/CLIP 採用) で解消すべき構造問題を切り分ける指標。
4. **トポロジ間 macro F1 の統計的有意性**。n=11 ではまだ弱いので、
   Phase 4 以降のデータ拡張 (Xeno-canto, 追加バルコニー録画) が必要。

---

## 付録: 分析に使用した数値の再現方法

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe - <<'PY'
import json
from pathlib import Path
ROOT = Path("results/phase1_3")
a = [json.loads(p.read_text(encoding="utf-8"))
     for p in sorted((ROOT / "topology_a").glob("fold_*/*.json"))]
b = [json.loads(p.read_text(encoding="utf-8"))
     for p in sorted((ROOT / "topology_b").glob("fold_*/*.json"))]
# ... 本レポート本文の表を再計算可能
PY
```

22 件の per-fold JSON と `topology_{a,b}_summary.md`、
`a_vs_b_comparison.md` がすべての一次情報源。レポート中の数値は
これらのファイルと完全に一致する。
