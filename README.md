# Multimodal AAS for Bird Observation

Adaptive Artificial Synapse (AAS) architecture with heterogeneous nodes
(vision + audio + LLM) for bird identification tasks.

This project extends the LLM-node AAS (sdnd-proof) to heterogeneous
neural-network nodes, validated on bird observation data collected from
a balcony camera, public bioacoustic archives, and live video streams.

## Project Status

Phase 0: Environment setup and data source preparation (in progress).

| Phase | Scope | Status |
|------:|-------|--------|
| 0     | Environment, repo, data sources, pre-registration | in progress |
| 1     | Raspberry Pi 4B + HQ Camera (SC0870 wide-angle) data collection | planned |
| 2     | Seven-node PC-side implementation | planned |
| 3     | Minimal end-to-end run | planned |
| 4a    | Component selection (2 detectors x 2 classifiers) | planned |
| 4b    | Topology comparison (6 fixed topologies, statistical test) | planned |

## Environment

- OS: Windows 11 (Lenovo Legion, Ryzen 7 8745HX, 32 GB RAM)
- GPU: NVIDIA RTX 5060 Ti 16 GB
- Python: 3.12.10 (inside `.venv`)
- ffmpeg: 8.1 (nvenc / nvdec enabled)
- Ollama: 0.21.0 (Windows-native, used for `qwen2.5:7b` integrator node)
- PyTorch: to be installed with CUDA 12.x (Phase 2)

## Directory Layout

```
multimodal-aas-bird/
├── .venv/               # Python 3.12 virtualenv (not committed)
├── data/                # Raw / processed datasets (not committed)
│   ├── balcony/         # Balcony camera data (Pi HQ camera)
│   ├── xeno_canto/      # Xeno-canto audio cache
│   └── youtube_streams/ # Live-stream processing artefacts only
├── docs/                # Design notes, license registry, pre-registration
├── logs/                # Run logs (not committed)
├── notebooks/           # Jupyter notebooks
└── src/                 # Node implementations and utilities
```

## Nodes (Phase 2 target)

1. `frame_extractor`        - ffmpeg-based frame / audio extraction
2. `bird_detector_yolo`     - YOLOv8n bird detection
3. `bird_detector_dino`     - Grounding DINO open-vocabulary detection
4. `bird_classifier_clip`   - CLIP zero-shot classifier
5. `bird_classifier_inat`   - iNaturalist fine-grained classifier
6. `bird_classifier_audio`  - BirdNET (existing asset)
7. `integrator_llm`         - Ollama `qwen2.5:7b` multimodal integrator

## Topologies (Phase 4b)

- A: Audio-Only
- B: Visual-Only
- C: Parallel Fusion
- D: Audio-First Gating
- E: Visual-Guided Audio
- F: Cross-Validation

Hypothesis, sample size, and statistical test are defined in
`docs/pre_registration.md` before any experiment is run.

## Data Strategy

Given sparse bird visits immediately after installing the bird-cake
feeder, a four-tier hierarchy is used. Full policy and attribution rules
are documented in `docs/data_sources.md`.

| Tier | Source | Notes |
|----:|--------|-------|
| 1 | Xeno-canto, Macaulay Library | CC / research-licensed audio |
| 2 | YouTube live streams | real-time processing only, no persistent download |
| 3 | CC-licensed video | attribution and license tracked per clip |
| 4 | Balcony (self-recorded) | primary evaluation set |

## References

- sdnd-proof (AAS v1, LLM-node version):
  https://github.com/piperendervt-glitch/sdnd-proof
  (prior result: 5/5 trials, p = 0.0007, Cohen's d = 4.29)
- Xeno-canto: https://xeno-canto.org/
- Macaulay Library (Cornell Lab): https://www.macaulaylibrary.org/
- BirdNET-Analyzer: https://github.com/kahst/BirdNET-Analyzer
- YOLOv8: https://github.com/ultralytics/ultralytics
- Grounding DINO: https://github.com/IDEA-Research/GroundingDINO
- CLIP: https://github.com/openai/CLIP
- Ollama: https://ollama.com/

## License

TBD. Code will be released under an OSI-approved license once the
experimental protocol is frozen. All data files follow the license of
their original source (see `docs/data_sources.md`).
