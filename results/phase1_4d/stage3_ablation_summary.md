# Phase 1.4d Stage 3 — Ablation summary (Target C factorisation)

Target C (commit `bfd840d`) hit a positive Statistical Go with
bootstrap Cohen's d = **+4.014** (CI [+0.024, +0.067], p = 0.0001) on
the ensemble-voting substrate over Topology A + B_v3 + C_v3. That run
stacks four design elements on top of the Stage 1 weight-only pipeline:

1. A second multiplicative knob — the **gate** `g` next to the weight `w`.
2. A distinct update signal for the gate — **consensus-agreement**
   (`pred_topo == ensemble_final_pred`) instead of ground truth.
3. **Multiplicative integration** of the two knobs: effective
   contribution = `w × g`.
4. Per-label routing (6 weights × 2 gates), inherited from Exp 5b.

This ablation peels those elements apart using the same 20-seed / 11-
fold / n=220 bootstrap machinery so every cell in the table below uses
the same statistic, same eval folds, and the same source predictions.

## 4-experiment comparison

| experiment | Weight learned | Gate learned | Gate signal | Integration | trial d | bootstrap d | bootstrap 95% CI | bootstrap p | Go |
|---|---|---|---|---|---:|---:|:---:|---:|:---:|
| Exp 5b extended | Yes (label-specific, GT) | No (= 1 implicitly) | — | additive `Σw · pred / Σw` | +0.485 | +2.041 | [+0.003, +0.026] | 0.0001 | Go (positive) |
| **Ablation 1** — gate only | **No (frozen at 0.5)** | Yes (label-specific) | consensus-agreement | multiplicative `Σ(0.5·g · pred) / Σ(0.5·g)` | +0.464 | **+2.217** | [+0.004, +0.044] | 0.0174 | **Go (positive)** |
| **Ablation 5** — GT-based gate | Yes (label-specific, GT) | Yes (label-specific) | **ground truth** | multiplicative `Σ(w·g · pred) / Σ(w·g)` | +0.380 | **+2.042** | [+0.001, +0.042] | 0.0350 | **Go (positive)** |
| Target C | Yes (label-specific, GT) | Yes (label-specific) | consensus-agreement | multiplicative `Σ(w·g · pred) / Σ(w·g)` | +0.899 | **+4.014** | [+0.024, +0.067] | 0.0001 | Go (positive) |

## Per-element isolation

The four d-values lock down the contribution of each design choice.

### 1. Gate alone vs weight alone

> Ablation 1 (d = +2.217) vs Exp 5b extended (d = +2.041).

Gate-only and weight-only hit essentially the same Cohen's d on this
substrate (difference 0.18, well inside either CI). The gate is not
a weaker knob than the label-specific weight — given only one of the
two mechanisms, either one buys roughly the same accuracy lift over
the fixed 0.5 × 0.5 baseline.

This rules out *Case A — gate dominates* and *Case C — synergy is
essential*. The working case is **Case B — independent similar-
magnitude effects**.

### 2. Do weight and gate add?

> Target C (d = +4.014) vs Ablation 1 + Exp 5b extended (sum ≈ +4.258).

Target C's d is very close to the arithmetic sum of the two single-
mechanism d-values. Combining a GT-driven weight with a consensus-
driven gate recovers (approximately) the sum of their individual
effects. Nothing suggests a super-additive interaction — the two
mechanisms seem to capture complementary signal dimensions without
the gate amplifying the weight or vice versa.

### 3. Is the consensus signal load-bearing?

> Ablation 5 (d = +2.042) vs Target C (d = +4.014) vs Exp 5b extended (d = +2.041).

When both variables are updated against ground truth, the gate
collapses onto the weight trajectory (identical rule + identical
signal + identical init). The effective contribution degenerates to
`w²·pred / Σw²`, which changes the mixing kernel but not the
information carried, and Cohen's d falls all the way back to the
Exp 5b extended level (+2.042 vs +2.041).

That collapse is exactly the outcome that falsifies *Case B — signal
source is not the novelty* for Ablation 5. The conclusion is
**Case A — consensus signal IS the novelty**. The gate only adds
information when its reward source differs from the weight's; the
multiplicative `w × g` form by itself is not what makes Target C win.

### 4. Integration arithmetic

Ablation 5 (multiplicative, same signal) ≈ Exp 5b extended (additive)
at n=220. So the multiplicative vs additive choice, taken in isolation,
is not where the extra d comes from either — it only pays off when the
two multiplied knobs encode *different* information.

## Sign distribution across 20 trials

| experiment | Δ > 0 | Δ = 0 | Δ < 0 |
|---|---:|---:|---:|
| Exp 5b extended | 4 | 16 | 0 |
| Ablation 1 (gate only) | 10 | 8 | 2 |
| Ablation 5 (GT gate) | 9 | 8 | 3 |
| Target C | 13 | 6 | 1 |

Target C spreads the Δ mass furthest into the positive side (13/20),
consistent with the largest bootstrap d. Ablation 1 and Ablation 5 are
near-twins at the trial level (10 / 9 positives), matching how close
their bootstrap d-values are to Exp 5b extended.

## What Paper 1 Chapter 5 should claim as *novel*

Based on the isolation above:

- **Novel contribution (load-bearing, falsifiable)** — the
  **consensus-agreement reward** on the gate. Ablation 5 shows that
  removing it collapses Target C's effect back to the weight-only
  baseline, and Ablation 1 shows that the signal alone is strong
  enough to clear the 3-criterion gate even without a GT-driven
  weight. The signal, not the arithmetic, is the idea.
- **Engineering choice (necessary but not novel)** — the
  **multiplicative `w × g` integration**. Ablation 5 demonstrates
  that the multiplicative form, taken alone with matched signals,
  does no better than the additive Exp 5b pipeline. It only becomes
  valuable as a carrier for two differently-informed quantities.
- **Engineering choice (inherited, not re-claimed)** — **per-label
  routing**. Already isolated in Stage 1 (Exp 5b extended d = +2.041
  vs single-weight controls). Target C uses it but does not add to
  what Exp 5b already published.

Recommended Chapter 5 framing:

> Target C introduces a *second online variable* (the gate) that
> shares the sdnd-proof asymmetric update rule with the weight but is
> fed a different correctness signal: agreement with the ensemble's
> own decision rather than with ground truth. Ablation 5 shows this
> signal split is the reason the gate adds information on top of the
> weight; Ablation 1 shows the signal is strong enough on its own to
> recover Exp 5b's accuracy lift; and the two effects combine roughly
> additively to double Cohen's d.

## Raw references

- Ablation 1: `results/phase1_4d/stage3_ablation_1_gate_only/`
- Ablation 5: `results/phase1_4d/stage3_ablation_5_gt_based_gate/`
- Target C:   `results/phase1_4d/stage3_target_c_gate_learning/`
- Exp 5b extended: `results/phase1_4d/stage1_exp5b_extended/`

All four experiments share seeds `[42, 137, 256, 512, 1024, 2048,
4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576,
2097152, 4194304, 8388608, 16777216, 33554432]`, a 22-fold clean set
(warm-up 11 / eval 11), and a paired fold bootstrap with n_pooled =
220, n_bootstrap = 10 000, bootstrap seed = 42. No new LLM inference
was performed — every trial reuses the committed Topology A / B_v3 /
C_v3 per-fold predictions and differs only in shuffle order and the
learned `w` / `g` trajectories.
