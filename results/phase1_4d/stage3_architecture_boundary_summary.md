# Phase 1.4d Stage 3 — architecture boundary summary

Paper 1 Chapter 1 stakes a claim: **the sdnd-proof `flow_weight` rule
transfers inside an ensemble-voting architecture and does not transfer
inside a single-LLM architecture.** The four ablations in this
document are the decisive evidence behind that claim. Each ablation is
a minimal edit to Target C's substrate (commit `bfd840d`), sharing
identical seeds, identical fold splits, and identical paired-fold
bootstrap (n_pooled=220, 10k resamples, seed=42).

## 8-experiment comparison

Experiments are grouped by architecture. "d" and "CI" are paired-fold
bootstrap values; "Go" is the sdnd-proof 3-criterion gate (p < 0.05,
|d| ≥ 0.8, 95% CI excludes 0, direction separately reported).

| # | Experiment | Architecture | # Topology | Weight | Gate | bootstrap d | 95% CI | p | direction | verdict |
|---|---|---|---:|---|---|---:|:---:|---:|---|---|
| 1 | Stage 2 Exp 1 | Single-LLM, scores injected | 1 | 4 (mod × label) | — | **−2.073** | [−0.171, −0.015] | 0.0001 | negative | **Go (negative)** |
| 2 | Stage 2 Exp 2 extended | Single-LLM, silent filter | 1 | 4 (mod × label) | — | −0.115 | [−0.023, +0.022] | 0.877 | zero-ish | No-Go |
| 3 | **Ablation E** | **Ensemble (degenerate)** | **1 (C_v3)** | **2 (label)** | **2 (label)** | **+0.000** | **[+0.000, +0.000]** | **n/a** | **zero** | **No-Go** |
| 4 | Ablation F-1 | Ensemble | 2 (A, B_v3) | 4 | 4 | **−3.052** | [−0.045, −0.011] | 0.0004 | negative | **Go (negative)** |
| 5 | Ablation F-2 | Ensemble | 2 (A, C_v3) | 4 | 4 | +0.000 | [+0.000, +0.000] | n/a | zero | No-Go |
| 6 | Ablation F-3 | Ensemble | 2 (B_v3, C_v3) | 4 | 4 | −0.575 | [−0.037, +0.019] | 0.572 | negative | No-Go |
| 7 | Exp 5b extended | Ensemble (no gate) | 3 | 6 | — | **+2.041** | [+0.003, +0.026] | 0.0001 | positive | **Go (positive)** |
| 8 | **Target C** | **Ensemble (weight + consensus gate)** | **3** | **6** | **6** | **+4.014** | **[+0.024, +0.067]** | **0.0001** | **positive** | **Go (positive)** |

Commits: Ablation E = `9c09ad3`, F-1 = `690b340`, F-2 = `0091ae1`,
F-3 = `ee8ec08`. Earlier rows unchanged.

## What each ablation isolates

### Ablation E — ensemble code alone is not enough

With only C_v3 in the vote the effective contribution reduces to
`(w × g) · pred / (w × g) = pred`, so Fixed and Adaptive arms produce
*identical* binary predictions on every fold by construction. The
observation matches: **Δ = 0.000 across all 20 trials and all 220 eval
folds.** No divergence anywhere in the diagnostic.

This is the cleanest possible null check on the architecture-boundary
claim. It rules out "the ensemble code framework itself is magic" —
nothing about the weighted-vote harness, the consensus-agreement
reward, or the multiplicative `w × g` integration translates into F1
without topology diversity.

Compare to Stage 2 Exp 1 and Exp 2 extended, which also use a single
node (one LLM over filtered detection data). Those two share
Ablation E's architecture class ("one node, one inference path"):
Exp 2 extended lands at d = −0.115 (no transfer); Exp 1 at d = −2.073
(actively harmful when weights leak into the prompt). Different
implementation substrates, but the shared fact is that neither
single-node family can rise above d ≈ 0 in the positive direction.

### Ablation F — 2-topology is not enough either

Dropping any one of the three topologies breaks Target C. The
resulting d-values land *below* not just Target C (+4.014) but also
below Exp 5b extended's weight-only +2.041:

- **F-1 (A + B_v3, drop C_v3 fusion)** → **d = −3.052, Go (negative)**.
  The temporal-sync fusion topology is essential. Its removal does
  not just flatten the effect — it reverses the sign strongly enough
  to clear the 3-criterion gate in the *negative* direction. Inspecting
  the trajectory (2 trials with Δ ≈ −0.3 and −0.4) confirms the
  consensus gate, without a fusion node to anchor the majority, can
  amplify a wrong topology and produce worse predictions than equal
  weights.
- **F-2 (A + C_v3, drop B_v3 pure-visual)** → **d = +0.000**. The
  learning never shifts any adaptive prediction across the 0.5
  threshold vs the fixed arm on the 220 eval folds. Pure-visual is not
  decisive on its own but is needed for the consensus gate to have
  enough "voices" to resolve disagreements positively.
- **F-3 (B_v3 + C_v3, drop A pure-audio)** → **d = −0.575, No-Go**.
  Removing A leaves the ensemble fragile: some trials help
  (seed = 2097152, Δ = +0.097), some hurt (seed = 2048, Δ = −0.090),
  and the net effect is a weak negative that fails the Go gate on all
  three criteria.

No 2-topology combination clears any positive Go. Each removed node
takes a distinct contribution out of the full-3 routing: C_v3 provides
the fusion anchor, B_v3 provides the tie-breaker voice, A provides the
audio-evidence specialisation for bulbul. Target C's effect is a
property of the full three-way diversity; partial ensembles do not
carry it.

## Paper 1 Chapter 1 — the architecture boundary claim

| row in the 8-experiment table | architecture class | d range observed |
|---|---|---|
| Rows 1, 2 (Stage 2 Exp 1, 2 ext) | single-LLM | **[−2.073, −0.115]** |
| Row 3 (Ablation E) | ensemble code + 1 topology | **0.000 exactly** |
| Rows 4, 5, 6 (F-1/2/3) | ensemble code + 2 topologies | **[−3.052, 0.000]** |
| Rows 7, 8 (Exp 5b ext, Target C) | ensemble + 3 topologies | **[+2.041, +4.014]** |

Two readings come out of that ordering:

1. **Architecture boundary is real.** The transfer of the sdnd-proof
   `flow_weight` rule does not happen inside a single-LLM pipeline (rows
   1–3) nor inside under-diverse ensembles (rows 4–6). It requires the
   full 3-topology ensemble (rows 7, 8). Ablation E is the analytically-
   clean single-topology null; F-1/2/3 close the loophole that "any
   ensemble code with ≥2 topologies would do."

2. **The lift is carried by topology diversity, not by the code
   framework.** Ablation E demonstrates that the consensus-gate
   machinery *on its own* produces Δ = 0 — zero lift — when there is
   no diversity to route across. The +4.014 is therefore a property
   of (A × B_v3 × C_v3) × (weight × consensus-gate) jointly, not of
   either factor in isolation.

Combined with the Stage 3 ablation summary (commit `38933b1`) — which
isolated the **consensus-agreement update signal** as the novelty
within the consensus-gate mechanism — the full Paper 1 Chapter 1
claim is now robust against four distinct reviewer critiques:

- "Maybe the single-LLM Stage 2 failure was an implementation
  detail." → Ablation E: even *with* the ensemble code, a single
  topology gives Δ = 0.
- "Maybe any extra node would have been enough." → F-1/F-2/F-3: all
  three 2-topology collapses fail, and F-1 actively hurts.
- "Maybe it's the multiplicative integration doing the work." →
  Ablation 5 (commit `49615c4`): matching the gate and weight signals
  with multiplicative integration still collapses to d = +2.042.
- "Maybe it's the second online variable, any signal." → Ablation 1
  (commit `49d4273`): gate only, with frozen weight, gives d = +2.217,
  but only under the consensus reward — and even that is *not* what
  makes Target C exceed Exp 5b: it's the signal decorrelation that
  multiplies the d.

## Summary for the chapter-1 headline figure

The n=220 Cohen's d axis, sorted low-to-high:

```
-3.052  Ablation F-1 (ensemble, 2 topo, drop C_v3)      Go (negative)
-2.073  Stage 2 Exp 1 (single-LLM, scores in prompt)    Go (negative)
-0.575  Ablation F-3 (ensemble, 2 topo, drop A)         No-Go
-0.115  Stage 2 Exp 2 extended (single-LLM, filter)     No-Go
+0.000  Ablation E (ensemble, 1 topo = C_v3)            No-Go
+0.000  Ablation F-2 (ensemble, 2 topo, drop B_v3)      No-Go
+2.041  Exp 5b extended (ensemble, 3 topo, weight only) Go (positive)
+4.014  Target C (ensemble, 3 topo, weight + gate)      Go (positive)
```

Only the two rows with **3 topologies + ensemble voting + a weight
update outside the LLM** clear the positive Go gate. Everything else
ranges from "no transfer" to "actively harmful." The architecture
boundary runs between `+0.000` and `+2.041` in this ordering — between
under-diverse ensembles and the 3-topology configuration.

## Output files

- `results/phase1_4d/stage3_ablation_E/` — single-node degenerate
  ensemble; trials, bootstrap, summary.
- `results/phase1_4d/stage3_ablation_F1/` — A + B_v3.
- `results/phase1_4d/stage3_ablation_F2/` — A + C_v3.
- `results/phase1_4d/stage3_ablation_F3/` — B_v3 + C_v3.
- `results/phase1_4d/stage3_ablation_summary.md` — Ablation 1 / 5 /
  Target C / Exp 5b extended comparison (consensus-signal ablation).
- `results/phase1_4d/stage3_target_c_gate_learning/` — Target C (n=220).
- `results/phase1_4d/stage1_exp5b_extended/` — weight-only 3-topology.
- `results/phase1_4d/stage2_target_b_no_score_extended/` — Stage 2
  Exp 2 extended.
- `results/phase1_4d/stage2_bootstrap_analysis/` — Stage 2 Exp 1 / 2 / 3
  bootstraps (n=55).
