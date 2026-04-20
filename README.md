# Multimodal AAS for Bird Observation

Adaptive Artificial Synapse (AAS) architecture with heterogeneous nodes
(vision + audio + LLM) for bird identification tasks.

This project extends the single-node LLM AAS
([sdnd-proof](https://github.com/piperendervt-glitch/sdnd-proof),
p=0.0007, Cohen's d=4.29) to a multi-node heterogeneous ensemble and
asks where sdnd-proof's `flow_weight` learning rule transfers, where
it fails, and where the resulting architecture boundary lies.

## Project Status — Phase 1.4d complete (Paper 1 drafting ready)

| Phase | Scope | Status |
|------:|-------|--------|
| 0     | Environment, data sources, pre-registration | complete |
| 1.1   | `qwen2.5:7b` single-node integrator sanity check | complete (Go, 3.0/5.0) |
| 1.2   | Visual-only and audio-only single-topology pipelines | complete |
| 1.3   | Topologies A / B / C on 11 self-recorded clips | complete |
| 1.3-ext | Extended evaluation on 11 self + 31 YouTube = 42 folds | complete |
| 1.4a  | Frame extractor, temporal sync, bbox prompt v3 | complete (1× Statistical Go) |
| 1.4a-clean | Robosheep tier review + paired bootstrap | complete |
| **1.4d** | **AAS `flow_weight` transfer — Stage 1 / 2 / 3** | **complete** |
| 1.4b  | YOLO parallelism (multi-threshold) | optional |
| 1.4c  | Heterogeneous LLM ensemble | optional |
| 1.4e  | Consensus / conflict resolution | optional |

## Phase 1.4d — the four pillars of Paper 1

Four decisive results came out of Phase 1.4d. All four use the clean
22-fold dataset (11 self-recorded balcony clips + 11 Robosheep-vetted
YouTube clips) and pass / fail the sdnd-proof 3-criterion gate
(`p < 0.05`, `|Cohen's d| ≥ 0.8`, 95% CI excludes 0).

1. **Negative Go — prompt injection harms** (Stage 2 Exp 1, bootstrap n=55).
   Showing the LLM numerical `reliability scores` for each
   modality-label pair *reduces* macro F1.
   → d = **−2.073**, p = 0.0001, CI **[−0.171, −0.015]**.
2. **No Transfer — silent info filtering collapses at scale** (Stage
   2 Exp 2 extended, bootstrap n=220). The apparent n=5 effect
   (d=+0.447) was a small-sample artifact; n=220 lands at d=−0.115.
   → teaches the "re-validate at larger n before acting" lesson.
3. **Positive Go weak — ensemble voting over label-specific weights**
   (Stage 1 Exp 5b extended, bootstrap n=220). Same 6-weight
   label-specific rule as sdnd-proof, applied to the three Phase 1.4a
   topologies A + B_v3 + C_v3 in a weighted vote.
   → d = **+2.041**, p = 0.0001, CI **[+0.003, +0.026]**.
4. **Positive Go strong — gate routing on top of the weights** (Stage
   3 Target C). Adds an explicit per-label gate that rewards topologies
   agreeing with the ensemble's own final prediction; effective
   contribution = `w × g` per topology-label pair.
   → trial t-test d = **+0.899**, p = 0.0007, CI **[+0.022, +0.069]** AND
   bootstrap d = **+4.014**, p = 0.0001, CI **[+0.024, +0.067]**.
   All three criteria pass on both trial and fold-level analyses —
   Phase 1.4d's gold-standard Go.
   Two ablations localise the extra effect: freezing the weight at
   0.5 leaves the gate alone at d = **+2.217** (matches Exp 5b's
   weight-alone d = +2.041); swapping the gate's update signal from
   consensus to ground truth collapses d back to **+2.042** (Exp 5b
   level). The novel mechanism is the **gate's consensus-agreement
   update signal** — rewarding topologies that match the emerging
   majority. The multiplicative `w × g` arithmetic only pays off when
   the two factors encode *different* signals.
   Commits: Ablation 1 `49d4273`, Ablation 5 `49615c4`, summary
   `38933b1` (`results/phase1_4d/stage3_ablation_summary.md`).

## Architecture boundary discovered

The single clearest finding of the phase is where the sdnd-proof rule
transfers and where it does not:

- **Single-LLM substrate** (Stage 2 Exp 1/2/3): injecting learned
  weights into the LLM prompt is either actively harmful (Exp 1) or
  underpowered and fragile (Exp 2/3). Small-n positives dissolve at
  n=220.
- **Ensemble-voting substrate** (Stage 1 Exp 5b, Stage 3 Target C):
  learned weights combined with the topologies' own binary
  predictions transfer cleanly, and adding an explicit gate on top
  nearly **doubles Cohen's d** (+2.041 → +4.014) while driving
  positive trials from 4/20 to 10/20.
- **Source of the extra +2.0 in Target C**: the ablation isolates it
  to the gate's **consensus-agreement update signal**, not the
  multiplicative integration. A second online variable helps only
  when its reward source is decorrelated from the weight's.

Put bluntly: sdnd-proof `flow_weight` learning should be **applied
outside the LLM** (as a mixing layer over heterogeneous topologies),
not **shown to the LLM** as numerical advice.

## Methodology

- **Data**: clean 22 folds (11 self-recorded + 11 Robosheep-reviewed
  YouTube; tiers A / B / B′ only). 20 of the 31 downloaded YouTube
  clips (65%) were dropped for BGM / text overlays / human voice —
  the tier review itself changed several Go verdicts and is written
  up in `results/phase1_clean/`.
- **Statistical protocol**: paired fold bootstrap over 20 trials × 11
  second-half folds = n=220, 10,000 resamples, seed 42. Same rule for
  every experiment. Applied to both small-n positive claims (to
  detect artefacts) and negative claims (to validate harm).
- **Go gate**: the sdnd-proof 3-criterion gate (p<0.05, |d|≥0.8, 95%
  CI excludes 0), with direction reported separately so a negative d
  that clears the thresholds is labelled "Negative Go" instead of
  being silently reported as a success.

## Documents

- `docs/PHASE_1_4D_SUMMARY.md` — every Stage 1 / 2 / 3 experiment and
  its verdict, in one place.
- `docs/PAPER1_OUTLINE.md` — draft chapter skeleton for Paper 1.
- `docs/TASKS.md` — task ledger (now mostly a log; active work has
  shifted to Paper 1 drafting).
- `docs/data_sources.md` — data attribution and license registry.
- `docs/pre_registration.md` — hypotheses and sample sizes, frozen
  before any experiment.

## Environment

- OS: Windows 11 (Lenovo Legion, Ryzen 7 8745HX, 32 GB RAM)
- GPU: NVIDIA RTX 5060 Ti 16 GB (LLM inference runs on CPU via Ollama)
- Python: 3.12.10 (inside `.venv`)
- ffmpeg: 8.1 (nvenc / nvdec enabled)
- Ollama: 0.21.0 (Windows-native, `qwen2.5:7b` integrator)
- Additional: `ultralytics`, `birdnetlib`, `librosa`, `resampy`,
  `tensorflow` (for the BirdNET TFLite model), `matplotlib`, `scipy`.

## Directory Layout

```
multimodal-aas-bird/
├── .venv/                          # Python 3.12 virtualenv (not committed)
├── data/                           # Raw media and metadata (most not committed)
│   ├── metadata.json               # self-recorded 11-clip metadata
│   ├── youtube_metadata.json       # YouTube 31-clip metadata + Robosheep tiers
│   ├── labels/phase1_labels.json   # ground-truth labels
│   ├── raw/                        # mp4 / wav downloads (gitignored)
│   └── processed/                  # cached frame / audio extractions (gitignored)
├── docs/                           # Design notes, pre-registration, summaries
├── logs/                           # Run logs (gitignored)
├── notebooks/                      # Jupyter notebooks (empty so far)
├── results/                        # Committed per-experiment artefacts
│   ├── phase1_1/ … phase1_3_extended/
│   ├── phase1_4a/ … phase1_4d/
│   ├── phase1_clean/               # Robosheep tier re-evaluation
│   └── reports/                    # Grok review packets
└── src/                            # All code
    ├── phase1_3_common/            # Shared loaders / metrics
    ├── phase1_4a_common/           # bbox v3, frame extractor, tiers
    └── phase1_4d/                  # Stage 1 / 2 / 3 experiments
```

## Nodes and topologies

| id | role | source |
|---|---|---|
| A (visual) | YOLOv8n bird class → LLM `qwen2.5:7b` | Phase 1.3 |
| B (visual) | Same, with Phase 1.4a `bbox prompt v3` | `topology_b_v3` |
| C (fusion) | YOLO + BirdNET parallel → LLM fusion | Phase 1.3 |
| C_v3       | As C with `temporal_sync` info | Phase 1.4a |

The Stage 3 Target C `Adaptive` ensemble mixes A, B_v3, and C_v3 with
six label-specific weights (`w`) and six label-specific gates (`g`);
the effective contribution of each (topology, label) pair in the vote
is `w × g` and both quantities are learned online via the sdnd-proof
update rule.

## Reproducing headline numbers

The committed per-fold JSONs are the source of truth; no LLM
re-inference is needed to reproduce any of the Stage 1 / 3 statistical
claims. Representative entry points:

```bash
# Stage 2 bootstrap (n=55 per experiment)
.venv/Scripts/python.exe src/phase1_4d/stage2_fold_bootstrap.py

# Stage 2 Exp 2 extended (n=220, detects the artifact)
.venv/Scripts/python.exe src/phase1_4d/stage2_target_b_no_score_extended.py

# Stage 1 Exp 5b extended (n=220, weak positive Go)
.venv/Scripts/python.exe src/phase1_4d/stage1_exp5b_extended_validation.py

# Stage 3 Target C (gold-standard positive Go)
.venv/Scripts/python.exe src/phase1_4d/stage3_target_c_gate_learning.py

# Stage 3 Ablation 1 (gate only, weight frozen at 0.5)
.venv/Scripts/python.exe src/phase1_4d/stage3_ablation_1_gate_only.py

# Stage 3 Ablation 5 (both weight and gate updated against ground truth)
.venv/Scripts/python.exe src/phase1_4d/stage3_ablation_5_gt_based_gate.py
```

Each script writes `summary.md`, a `*_analysis.json`, and figures
under `results/phase1_4d/…/graphs/`.

## References

- **sdnd-proof** (AAS v1, LLM-node): https://github.com/piperendervt-glitch/sdnd-proof
  — p=0.0007, Cohen's d=4.29, 5/5 trials.
- BirdNET-Analyzer: https://github.com/kahst/BirdNET-Analyzer
- YOLOv8: https://github.com/ultralytics/ultralytics
- Ollama: https://ollama.com/
- Xeno-canto: https://xeno-canto.org/

## License

TBD. Code will be released under an OSI-approved license once the
Paper 1 protocol is frozen. All media files follow the license of
their original source (see `docs/data_sources.md`).
