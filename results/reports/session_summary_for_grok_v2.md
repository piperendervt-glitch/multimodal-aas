# Session summary v2 for Grok (multi-AI judge III, round 2)

Date: 2026-04-19 (second round, same day)
Repository: `piperendervt-glitch/multimodal-aas`
Scope: Phase 1.4a completion — bbox prompt v3 (Grok Q2 priority) *and*
the clean-dataset re-evaluation Robosheep ran after reviewing every
YouTube clip. Read this as a diff on `session_summary_for_grok.md`;
previous context is not repeated in full.

---

## 1. Timeline since the first Grok round

| step | outcome |
|---|---|
| Grok round-1 Q2 (bbox prompt overfit) flagged as #1 priority | Robosheep accepted, spec'd prompt v3 (relative-distribution features) |
| `bbox_normalizer` + Topology B_v3 + C_v4 implemented and run on 42 folds | B_v3 cleared the YouTube gate (+0.256 on Phase 1.3 B YouTube); C_v4 regressed strongly |
| Grok round-1 Q5 (YouTube GT review) deferred to avoid reviewer fatigue | Robosheep reversed and did it anyway |
| Tier review of 31 downloaded YouTube clips | **20/31 Tier C (unusable)** — BGM / human voice / text-dominant / heavy noise. All 8 `mixed` clips in Tier C. |
| Clean dataset = 11 self + 11 YouTube = **22 folds** | Every experiment re-aggregated; see §2. |

Two practical lessons for the multi-AI review process came out of
this: (a) Grok's priority ordering (Q2 first) was validated, and (b)
deprioritising Q5 was the wrong call in hindsight — data hygiene
dominates every downstream metric.

## 2. Clean re-evaluation headline

| experiment | 42-fold macro F1 | clean 22-fold macro F1 | Δ | bootstrap 95% CI on clean |
|---|---:|---:|---:|---|
| Phase 1.3 A  | 0.611 | 0.482 | −0.129 | (0.318, 0.659) |
| Phase 1.3 B  | 0.610 | 0.669 | +0.059 | (0.534, 0.782) |
| Phase 1.3 C  | 0.840 | 0.823 | −0.017 | (0.656, 0.954) |
| Phase 1.4a C_v2 (obj B)   | 0.826 | 0.791 | −0.035 | (0.613, 0.920) |
| **Phase 1.4a C_v3 (obj D)** | **0.819** | **0.869** | **+0.050** | (0.718, 0.978) |
| Phase 1.4a B_v3 (bbox v3) | 0.769 | 0.718 | −0.051 | (0.630, 0.795) |
| Phase 1.4a C_v4 (bbox v3 + fusion) | 0.760 | 0.635 | −0.125 | (0.405, 0.810) |

Go-gate updates on the clean set:

| objective | gate | clean value | verdict (previous / now) |
|---|---|---:|---|
| D: C_v3 macro F1 ≥ 0.86 | − | **0.869** | No-Go → **Go** |
| B: C_v2 macro F1 ≥ 0.86 | − | 0.791 | No-Go → No-Go |
| bbox v3: B_v3 YouTube ≥ Phase 1.3 B YouTube + 0.10 | 0.500 → 0.721 (+0.221) | 0.721 | Go → Go |
| bbox v3: C_v4 full ≥ Phase 1.3 C full + 0.02 | 0.823 → 0.635 (−0.188) | 0.635 | No-Go → No-Go |

## 3. Findings (observation vs inference)

1. **Objective D is a real Go on verified-clean data** (observation).
   The 42-fold No-Go was driven by Tier C YouTube clips: their audio
   was BGM / overlays, so `sync_rate` was meaningless and any
   temporal-sync prompt that trusted it regressed. Once those 20
   clips are removed, C_v3 reaches 0.869 on 22 folds.
2. **bbox v3 helps visual-only, hurts fusion** (observation).
   B_v3 clean 0.718 beats Phase 1.3 B clean 0.669; on YouTube alone it
   beats Phase 1.3 B by +0.221. The same prompt in Topology C_v4
   collapses to 0.635 (−0.188 vs Phase 1.3 C clean). The LLM appears
   to let the distribution prompt override audio evidence, even when
   audio signals the opposite class.
3. **Phase 1.3 A's true audio-only ceiling is ≈ 0.48**, not 0.61
   (inference). Tier C clips contained many fallback-by-default
   0/0 predictions that happened to match ground truth (most GTs have
   a zero somewhere); the clean set strips this accidental correctness
   and exposes how narrow BirdNET's target-species signal is on
   low-quality audio.
4. **n=2 `mixed` evaluation is a dead end** (observation). Clean
   `mixed` = `{balcony_005, balcony_010}` only — every YouTube `mixed`
   clip was Tier C. Any per-category F1 for `mixed` in §4.2 of the
   clean summary is based on at most two independent decisions.
5. **No-Go results were worth keeping** (meta). Round-1 Grok Q5 was
   "should we publish negative results explicitly?". The clean data
   showed that one of our two No-Go calls was a dataset artefact — if
   we had buried it, we'd have also buried the eventual Go. Treating
   negatives as findings is not just presentational; it's a way to
   keep re-auditable history.

## 4. Statistical reliability caveats

- Unpaired bootstrap 95% CIs on the 7 experiments have half-widths
  between ±0.08 (B_v3, n≈22) and ±0.20 (C_v4). The C_v3 point 0.869
  sits on the lower edge of the 0.86 gate; +0.046 over Phase 1.3 C
  (0.823) on the *same 22 folds* is within one-fold noise on a paired
  basis as well.
- We have not yet run a **paired** bootstrap (resample fold indices,
  score both topologies on each resample, track the Δ) — this is the
  correct test for "C_v3 > C on the clean set" and is strongly
  recommended before acting on the Go flip.
- n=22 also means per-category breakdowns are underpowered. Category
  `mixed` (n=2) must not drive any decision; category `sparrow` (n=8)
  and `bulbul` (n=12) are marginal.

## 5. Questions for Grok, round 2

Answer the ones you have strong opinions on; leave the rest.

**Q1. Acting on Objective D's Go.** The point estimate clears the
gate but unpaired CIs overlap heavily with the Phase 1.3 C baseline.
*Do we (a) accept the Go and move to Phase 1.4b, (b) run a paired
bootstrap on (C, C_v3) first and gate on a paired-Δ CI excluding 0,
or (c) expand the clean set before deciding?*

**Q2. bbox v3 interaction with fusion.** Prompt v3 helps B, hurts C.
One hypothesis is that the v3 prompt encodes decision *rules* that
conflict with the audio evidence rules in C. *Is it worth trying a
"C_v5" that passes `bbox_distribution` to the LLM as pure features —
no decision rules that reference it — and letting the Phase 1.3 C
audio-fusion rules stay intact?*

**Q3. Mixed-category data strategy.** Clean `mixed` = 2 folds.
Options: (i) use Macaulay Library or Xeno-canto verified-both clips;
(ii) synthesise "both" by overlaying verified sparrow and bulbul
audio/visual; (iii) drop `mixed` from Phase 1 evaluation and state
the scope explicitly. *Which?* The synthesis path looks cheap but
might be an evaluation artefact.

**Q4. Phase 1 exit criterion, revisited.** With Obj D Go on clean
data, the original Phase 1 exit ("one improved topology beats Phase
1.3 C baseline") is arguably met. *Do we declare Phase 1 complete
after running one paired-bootstrap verification, or push through
Phase 1.4b (YOLO parallelisation + bbox prompt redesign) first?*

**Q5. Dataset-hygiene gate for future phases.** The Tier C fraction
(20/31 = 65%) was high enough that 42-fold numbers were genuinely
misleading. *Should we institutionalise a "download → Robosheep
screen → experiment" pipeline as a hard gate in Phase 1.4b+, even if
it doubles review time?*

**Q6. Meta: judging the judge.** Round-1 Grok deprioritised the
YouTube GT review (your Q5) in favour of faster iteration. In
hindsight the review was the single highest-value action. *How
should the multi-AI judge process weight "do the expensive review
first" vs "iterate faster" when the two advice channels disagree?*
This question is partly about the process itself, not the project.

## 6. Tech spec (unchanged from round 1)

- Hardware: Ryzen 7 8745HX, RTX 5060 Ti 16 GB; LLM on CPU via Ollama.
- Corpus: 42 downloaded, 22 clean (11 self + 11 YouTube Tier A/B/B').
- Artifacts added this round:
  - `results/phase1_clean/reevaluation_summary.md`
  - `results/phase1_clean/graphs/{macro_f1_comparison,category_breakdown,source_breakdown}.png`
  - `results/phase1_4a/bbox_prompt_v3_summary.md`
  - `src/phase1_4a_common/clean_tiers.py` (Robosheep's tier assignments)
  - `src/phase1_4a_common/video_trimmer.py` (stub for Tier B 30 s trim — not used here)
- Reviewer bias self-disclosure: I found Obj D's Go flip on clean
  data more exciting than the statistics warrant. Q1 above is
  phrased to push back on that bias.
