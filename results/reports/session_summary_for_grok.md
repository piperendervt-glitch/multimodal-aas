# Session summary for Grok (multi-AI judge III)

Date: 2026-04-19
Repository: `piperendervt-glitch/multimodal-aas`
Audience: external AI judge. This is one of several parallel reviews
(sdnd-proof style "judge III") to raise research transparency.
Please read Sections 1–5 as evidence, then answer Section 6 questions.

---

## 1. Project overview

- **Name**: `multimodal-aas-bird` — heterogeneous-node extension of the
  single-node AAS (Adaptive Artificial Synapse) from `sdnd-proof`.
- **Philosophy**: deterrence-oriented AI development; topology-level
  experiments precede weight-update mechanisms.
- **Target species**: *Passer montanus* (sparrow, スズメ),
  *Hypsipetes amaurotis* (bulbul, ヒヨドリ). Multi-label: `{S, B} ∈ {0, 1}`.
- **Corpus**: 11 self-recorded balcony clips (webcam + built-in mic)
  plus 32 YouTube clips (31 downloaded OK; 1 blocked by YouTube JS
  challenge). Effective 42-fold set per topology.
- **Node stack**: YOLOv8n (COCO bird class), BirdNET via `birdnetlib`
  (TFLite), Ollama `qwen2.5:7b` (temperature 0.1, format=json).
- **Hardware**: Windows 11, Ryzen 7 8745HX, RTX 5060 Ti 16 GB, Python
  3.12, ffmpeg 8.1 (nvenc). LLM on CPU through Ollama.

## 2. Phase-by-phase results and Go/No-Go

### Phase 0 — environment [complete]
- 11 self-recorded videos, total 27.7 min, indexed in
  `data/metadata.json`.

### Phase 1.1 — `qwen2.5:7b` single-node [Go, β-minimum]
- 5 prompts (sparrow / bulbul / both / unknown / none), score **3.0/5.0**.
- Gate β (>= 3.0) reached at the boundary; JSON parse 5/5.

### Phase 1.2 — end-to-end per modality [Go]
- Visual (YOLOv8n → LLM): 11/11 JSON parse, macro F1 **0.389**.
- Audio (BirdNET → LLM): 11/11 parse, macro F1 **0.268**.
- Known failure mode: visual node collapsed to "always sparrow".

### Phase 1.3 — topologies A / B / C on 11 self-recorded clips
| topology | macro F1 | fallback | notes |
|---|---:|---:|---|
| A (Audio-Only)            | **0.143** | 10/11 | BirdNET filtered out at target_conf ≥ 0.3 |
| B (Visual-Only)           | **0.819** | 0/11  | sharpened bbox thresholds fixed the Phase 1.2 collapse |
| C (Parallel Fusion)       | **0.733** | 0/11  | LLM mainly leans visual; audio silent on most self clips |

### BirdNET sanity chain — root cause for Topology A
- (a) BirdNET install: 20-min North-American reference → **423
  detections / 91 species**. BirdNET works.
- (b) Japanese target species: clean Passer-montanus clip → 8 hits,
  max_conf **0.839**; bulbul clip → 102 hits, max_conf **0.981**.
  Coverage is fine.
- (c) **Self-recorded audio**: confirmed as the limiting factor. Webcam
  mic bandwidth / SNR silences BirdNET's target-species layer.

### Phase 1.3 extended — 42 folds (11 self + 31 YouTube) [Go]
| topology | full  | self  | YouTube | YT-grok | YT-claude |
|---|---:|---:|---:|---:|---:|
| A | 0.611 | 0.143 | 0.720   | 0.812   | 0.619     |
| B | 0.610 | 0.795 | 0.542   | 0.535   | 0.540     |
| C | **0.840** | 0.733 | **0.874** | **0.912** | 0.833 |

Audio-quality hypothesis confirmed quantitatively: A's YouTube F1 is
**5× its self F1**. Parallel fusion (C) is strictly best when both
modalities are clean.

### Phase 1.4a objective B — frame_extractor prefilter [No-Go]
- Design: run YOLOv8n first; drop no-bird frames from LLM input.
- Result: Topology C_v2 macro F1 **0.826**, Δ vs C = **−0.014**. Gate
  was +0.02 (≥ 0.86). bulbul F1 regressed 0.800 → 0.773; sparrow F1
  unchanged.
- Interpretation: removing density info (`frames_with_bird /
  num_frames_analyzed`) slightly misled the LLM.

### Phase 1.4a objective D — modality synchronisation [No-Go]
- Design: split clip into 2 s windows; tell LLM how many windows have
  visual+audio (`both_present`), one side only, or neither.
- Iteration log:
  1. Full timeline (≤150 windows) → **25/42 ReadTimeout** at 180 s.
  2. Compact timeline (40 windows) → LLM hallucinated input schema on
     **17/42** folds.
  3. **6-field `temporal_sync` counters** on top of Phase 1.3 C input →
     42/42 parsed, 0 fallback.
- Result: Topology C_v3 macro F1 **0.819**, Δ vs C = **−0.021**.
  sparrow F1 +0.026 but bulbul F1 −0.068. Net No-Go.

## 3. Findings (observation vs inference)

1. **Audio quality dictates the value of fusion** (observation). On
   clean audio, C − B = +0.332; on webcam audio, C − B ≈ 0. Hardware
   choice is inseparable from AAS architecture decisions.
2. **Adding info isn't monotonic in LLM accuracy** (observation).
   Both objective B (info removed) and D (info added) lost accuracy;
   the Phase 1.3 C prompt sits near a local optimum for this LLM.
3. **sync_rate correlates strongly with correctness** (observation,
   new). In C_v3, folds that were fully correct had mean sync_rate
   **0.283** vs **0.030** for folds with any class wrong — a ~9×
   separation on n=42.
4. **Error direction trades between classes** (observation). C_v3
   raised sparrow F1 and dropped bulbul F1; C_v2 left sparrow and
   dropped bulbul. The LLM distributes error by class under each
   intervention.
5. **Visual prompt overfits to self-recorded bbox scale** (inference).
   B's YouTube F1 (0.542) << self F1 (0.795). bbox thresholds 0.08 /
   0.13 match balcony framing but not diverse angles/zooms.
6. **Phase 1.3 C (macro F1 0.840) may be near the prompt × model
   ceiling** (inference, pending). Two independent interventions both
   regressed — weak evidence that further prompt-level tweaks will
   plateau without model or prompt-paradigm change.

## 4. Statistical reliability caveat

n = 42 per topology. A single fold flip moves macro F1 by ≈ 0.02. The
Phase 1.4a No-Go deltas (−0.014, −0.021) are within one-fold noise.
A bootstrap CI on the paired C − C_v{2,3} delta is recommended before
treating the No-Go as definitive.

## 5. Pending issues

1. **YouTube ground-truth review** — 31 expected labels still
   `review_needed=true`. `video_review_sheet.md` holds the template.
2. **bbox prompt generalisation** — largest single source of YouTube
   regression in B.
3. **`mixed` ("both") category** — C 0.701, C_v3 regressed to 0.667.
   LLM struggles to emit both classes from noisy evidence.
4. **Phase 1.4 remainder per `TASKS.md`**:
   - 1.4b YOLO parallelisation (multi-threshold, adaptive routing)
   - 1.4c heterogeneous LLM ensemble
   - 1.4d AAS weight-update rule + Mirror Effect
   - 1.4e consensus mode

## 6. Questions for Grok

Please answer directly — each decision is actionable this week.

**Q1. Phase 1.4a objective C (temporal detail, per-window prediction)**
— worth doing next, or jump to 1.4b?
*Context: B and D both No-Go, but `sync_rate` shows a real signal.
Does objective C likely clear the 0.86 gate, or plateau again?*

**Q2. Phase 1.4b priority** — between (a) YOLO multi-threshold
parallelism and (b) a from-scratch bbox-prompt redesign, which first?
*Context: (b) is the diagnosed cause of YouTube B regression, but (a)
is what the spec names.*

**Q3. Phase-1 exit criterion** — should we declare Phase 1 complete
after 1.4a (current state) and draft a paper, or push through 1.4b/d
first? *AAS value probably lives in 1.4d (Mirror Effect + weight
update). But n=42 is thin for statistics.*

**Q4. Publishability of present findings** — are items 1 (audio
quality gates fusion value), 3 (sync_rate/correctness correlation),
and 4 (class-wise error trading) strong enough to publish alone, or
should we wait for 1.4d?

**Q5. Handling the two No-Go results** — standard practice is to bury
No-Gos. Should we instead treat Phase 1.4a B/D explicitly as findings
(prompt-paradigm ceiling, sync_rate as a better feature), and keep the
full negative-result record in the paper?

## 7. Tech spec (for context)

- Runtime: 1 fold ≈ 10–25 s end-to-end; 42-fold run ≈ 7 min (C) / 7 min
  (C_v3). Data plane cached between runs (`data/processed/{audio,
  frames}/`).
- Artifacts (repo paths):
  - `results/phase1_3_extended/abc_extended_comparison.md`
  - `results/phase1_4a/{topology_c_v2,topology_c_v3}_summary.md`
  - `results/phase1_4a/{go_judgment_b,go_judgment_d}.md`
  - `results/phase1_3/video_review_sheet.md`
- All per-fold JSON preserved for any independent re-analysis.
