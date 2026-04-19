"""Phase 1.4a Topology C_v4 — Parallel Fusion with bbox prompt v3.

Same as Phase 1.3 Topology C (BirdNET target_threshold=None, audio
species-level aggregate forwarded to LLM) but with the visual prompt
replaced by the prompt v3 from B_v3. No temporal_sync, no frame
pre-filter — this isolates the pure effect of the bbox relative-
distribution prompt on top of the fusion topology.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_3_common.birdnet_analyzer import BirdNetAnalyzer
from phase1_3_common.extended_sources import load_extended_videos
from phase1_3_common.extended_summary import (
    per_fold_row,
    per_fold_table_header,
    render_breakdown,
)
from phase1_3_common.llm_client import LlmClient, ModelMissing, OllamaUnavailable
from phase1_3_common.loocv_runner import ensure_utf8_streams, run_loocv_over
from phase1_3_common.video_processor import (
    DEFAULT_FPS,
    DEFAULT_SR,
    extract_audio,
    extract_frames,
    probe_duration,
)
from phase1_3_common.yolo_detector import YoloDetector
from phase1_3_topology_c import format_audio_for_llm
from phase1_4a_common.bbox_normalizer import analyze_bbox_distribution
from phase1_4a_common.frame_extractor import run_yolo_per_frame
from phase1_4a_topology_b_v3 import _overall_visual

TOPOLOGY = "C_v4"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v4"
SUMMARY_PATH = REPO_ROOT / "results" / "phase1_4a" / "topology_c_v4_summary.md"

SYSTEM_PROMPT = """あなたは日本の野鳥観察を支援するアシスタントです。
ベランダに設置したバードケーキに来る鳥を観察しています。
撮影環境にはスズメとヒヨドリのみが飛来します。

視覚 (YOLOv8n の bird 検出) と音声 (BirdNET の種識別) の両方を統合して判定します。
**視覚は絶対閾値ではなく動画内の相対分布 (bbox_distribution) を優先**してください。

視覚判定材料:

1. bbox_distribution.bbox_size_distribution.dominant_range:
   - "small" (< 0.05) 優位: スズメの可能性が高い
   - "medium" (0.05-0.15) 優位: 中間サイズ
   - "large" (> 0.15) 優位: ヒヨドリの可能性が高い
   - "none": 対象種の鳥検出なし

2. bbox_distribution.size_variation_type:
   - "uniform" (size_consistency < 0.3): 同じサイズの鳥、単一種の可能性高
   - "mixed" (size_consistency >= 0.3): 異なるサイズの鳥、複数種の可能性

3. 判定ロジック:
   - dominant "small" + uniform → sparrow 優位
   - dominant "large" + uniform → bulbul 優位
   - mixed → sparrow + bulbul 両陽性を検討
   - dominant "medium" + uniform → 視覚だけでは判断困難。音声で補強

音声判定材料:
- audio.all_detections 内の species_code == "sparrow" 検出 → sparrow 側に加点
- audio.all_detections 内の species_code == "bulbul"  検出 → bulbul 側に加点
- 動画音声の品質は低い場合があるため、対象種検出がなくても視覚情報を優先可能

統合ルール:
- 視覚が dominant "medium" + uniform で曖昧 → 音声で判定
- 視覚 mixed → 両陽性、音声が片方に偏るなら微修正
- 視覚 dominant "small" or "large" → その単一種を基本とし、
  音声が異種を指す場合のみ両陽性を検討

入力:
{
  "visual_overall": { Phase 1.3 B と同じ全体統計 },
  "bbox_distribution": {
    "bbox_size_distribution": {"small_count", "medium_count", "large_count",
                                "total_detections", "dominant_range", "dominant_ratio"},
    "size_consistency": 0.XX,
    "size_variation_type": "uniform/mixed/none",
    "relative_position": {"normalized_avg", "normalized_min", "normalized_max"}
  },
  "audio": {
    "all_detections": [{"species_code": "...", "scientific_name": "...",
                         "confidence": 0.XX, "num_detections": N}, ...],
    "target_species_found": true/false, "total_detections": N,
    "note": "音声品質低い..."
  }
}

以下のJSON形式で応答してください:
{
  "predictions": {"sparrow": 0 または 1, "bulbul": 0 または 1},
  "confidence": {"sparrow": 0.0-1.0, "bulbul": 0.0-1.0},
  "reasoning": "判定理由 (50字以内)",
  "modality_used": "visual" または "audio" または "both" または "none",
  "fallback_used": false,
  "prompt_v3_factors": {
    "dominant_range": "small/medium/large/none",
    "size_variation_type": "uniform/mixed/none",
    "decision_basis": "判定に使った要因 (50字以内)"
  }
}

フォールバック: visual.frames_with_bird = 0 AND audio.target_species_found = false
の場合のみ {sparrow: 0, bulbul: 0}, fallback_used=true を返す。"""


def make_fold_fn(bn: BirdNetAnalyzer, det: YoloDetector, llm: LlmClient):
    def fold_fn(fold: int, video: dict[str, Any], gt: dict[str, int]) -> dict[str, Any]:
        t0 = time.perf_counter()
        audio_path = extract_audio(video["video_path"], video["video_id"], sr=DEFAULT_SR)
        t_audio_ext = time.perf_counter() - t0
        duration = probe_duration(audio_path)

        t0 = time.perf_counter()
        frame_paths = extract_frames(
            video["video_path"], video["video_id"], fps=DEFAULT_FPS
        )
        t_frame_ext = time.perf_counter() - t0

        t0 = time.perf_counter()
        bn_out = bn.analyze(audio_path, target_min_conf=None)
        t_bn = time.perf_counter() - t0

        t0 = time.perf_counter()
        per_frame = run_yolo_per_frame(det, frame_paths, fps_sampling=float(DEFAULT_FPS))
        t_yolo = time.perf_counter() - t0

        overall = _overall_visual(per_frame)
        bbox_dist = analyze_bbox_distribution(per_frame)
        audio_input = format_audio_for_llm(bn_out["all_detections"])

        llm_input = {
            "visual_overall": overall,
            "bbox_distribution": bbox_dist,
            "audio": audio_input,
        }

        t_llm = 0.0
        fallback = False
        llm_output: dict[str, Any] | None = None

        both_silent = (
            overall["frames_with_bird"] == 0 and not audio_input["target_species_found"]
        )

        if both_silent:
            fallback = True
            llm_output = {
                "raw": None,
                "parsed": {
                    "predictions": {"sparrow": 0, "bulbul": 0},
                    "confidence": {"sparrow": 0.0, "bulbul": 0.0},
                    "reasoning": "視覚で鳥なし、音声でも対象種なし (LLM スキップ)",
                    "modality_used": "none",
                    "fallback_used": True,
                },
                "elapsed_sec": 0.0,
            }
            final_pred = {
                "sparrow": 0,
                "bulbul": 0,
                "confidence": {"sparrow": 0.0, "bulbul": 0.0},
            }
        else:
            llm_output = llm.generate(SYSTEM_PROMPT, llm_input)
            t_llm = llm_output["elapsed_sec"]
            parsed = llm_output["parsed"]
            if parsed is None:
                fallback = True
                final_pred = {
                    "sparrow": 0,
                    "bulbul": 0,
                    "confidence": {"sparrow": 0.0, "bulbul": 0.0},
                }
            else:
                p = parsed["predictions"]
                c = parsed.get("confidence") or {}
                final_pred = {
                    "sparrow": int(p["sparrow"]),
                    "bulbul": int(p["bulbul"]),
                    "confidence": {
                        "sparrow": float(c.get("sparrow", 0.0)),
                        "bulbul": float(c.get("bulbul", 0.0)),
                    },
                }

        is_correct = {
            "sparrow": final_pred["sparrow"] == gt["sparrow"],
            "bulbul":  final_pred["bulbul"]  == gt["bulbul"],
        }

        return {
            "video_id": video["video_id"],
            "audio_extraction": {
                "audio_path": str(audio_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "duration_sec": round(duration, 3),
                "sample_rate": DEFAULT_SR,
            },
            "frame_extraction": {
                "num_frames": len(frame_paths),
                "fps_sampling": float(DEFAULT_FPS),
            },
            "yolo_output": overall,
            "bbox_distribution": bbox_dist,
            "birdnet_output": bn_out,
            "fallback_triggered": fallback,
            "llm_input": llm_input,
            "llm_output": llm_output,
            "final_prediction": final_pred,
            "ground_truth": gt,
            "is_correct": is_correct,
            "elapsed_sec": {
                "audio_extraction": round(t_audio_ext, 3),
                "frame_extraction": round(t_frame_ext, 3),
                "birdnet": round(t_bn, 3),
                "yolo": round(t_yolo, 3),
                "llm": round(t_llm, 3),
                "total": round(
                    t_audio_ext + t_frame_ext + t_bn + t_yolo + t_llm, 3
                ),
            },
        }

    return fold_fn


def render_summary(rows, skipped, total_time: float) -> str:
    from collections import Counter
    modality_counts: Counter[str] = Counter()
    dom_counts: Counter[str] = Counter()
    var_counts: Counter[str] = Counter()
    for r in rows:
        if "error" in r:
            modality_counts["error"] += 1
            continue
        modality_counts[((r.get("llm_output") or {}).get("parsed") or {}).get("modality_used", "-")] += 1
        bd = r.get("bbox_distribution") or {}
        dom_counts[bd.get("bbox_size_distribution", {}).get("dominant_range", "?")] += 1
        var_counts[bd.get("size_variation_type", "?")] += 1

    lines = [
        "# Phase 1.4a Topology C_v4 extended summary",
        "",
        "Pipeline: per-frame YOLOv8n + bbox_normalizer + BirdNET "
        "(target_threshold=None) -> `qwen2.5:7b` (prompt v3, no temporal_sync)",
        "",
        f"- Total folds executed: {len(rows)}",
        f"- Skipped YouTube entries: {len(skipped)}",
        f"- Total wall time: {total_time:.1f} s",
        "",
        "## Modality used (from LLM response)",
        "",
        "| modality | count |",
        "|---|---:|",
    ]
    for mod, cnt in sorted(modality_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {mod} | {cnt} |")
    lines.append("")

    lines.append("## dominant_range distribution")
    lines.append("")
    lines.append("| dominant_range | count |")
    lines.append("|---|---:|")
    for key in ("small", "medium", "large", "none"):
        lines.append(f"| {key} | {dom_counts.get(key, 0)} |")
    lines.append("")
    lines.append("## size_variation_type distribution")
    lines.append("")
    lines.append("| variation_type | count |")
    lines.append("|---|---:|")
    for key in ("uniform", "mixed", "none"):
        lines.append(f"| {key} | {var_counts.get(key, 0)} |")
    lines.append("")

    lines.append(render_breakdown(rows))
    lines.append("## Per-fold results")
    lines.append("")
    lines.extend(per_fold_table_header(["dominant_range", "variation_type"]))
    for r in rows:
        if "error" in r:
            lines.append(per_fold_row(r, ["-", "-"]))
            continue
        bd = r.get("bbox_distribution") or {}
        dom = bd.get("bbox_size_distribution", {}).get("dominant_range", "-")
        var = bd.get("size_variation_type", "-")
        lines.append(per_fold_row(r, [dom, var]))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()
    llm = LlmClient()
    try:
        llm.check_ready()
    except OllamaUnavailable as e:
        print(str(e), file=sys.stderr)
        return 2
    except ModelMissing as e:
        print(str(e), file=sys.stderr)
        return 3

    bn = BirdNetAnalyzer()
    det = YoloDetector()
    videos, skipped = load_extended_videos()
    print(f"Videos: {len(videos)} (skipped={len(skipped)})")

    run_start = time.perf_counter()
    rows = run_loocv_over(TOPOLOGY, make_fold_fn(bn, det, llm), RESULTS_BASE, videos)
    total_time = time.perf_counter() - run_start

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(render_summary(rows, skipped, total_time), encoding="utf-8")
    print(f"Summary: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
