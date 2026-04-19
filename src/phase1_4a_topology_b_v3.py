"""Phase 1.4a Topology B_v3 — Visual-Only with bbox prompt v3.

Replaces Phase 1.3 Topology B's hardcoded thresholds (sparrow < 0.08,
bulbul >= 0.13) with relative-distribution features (dominant_range,
size_variation_type). YOLO is still the same; we just add the
distribution analysis and rewrite the prompt to reason about
"what this clip's bird population looks like" instead of "compare
one max bbox to a global threshold".
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_3_common.extended_sources import load_extended_videos
from phase1_3_common.extended_summary import (
    per_fold_row,
    per_fold_table_header,
    render_breakdown,
)
from phase1_3_common.llm_client import LlmClient, ModelMissing, OllamaUnavailable
from phase1_3_common.loocv_runner import ensure_utf8_streams, run_loocv_over
from phase1_3_common.video_processor import DEFAULT_FPS, extract_frames
from phase1_3_common.yolo_detector import YoloDetector
from phase1_4a_common.bbox_normalizer import analyze_bbox_distribution
from phase1_4a_common.frame_extractor import run_yolo_per_frame

TOPOLOGY = "B_v3"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_4a" / "topology_b_v3"
SUMMARY_PATH = REPO_ROOT / "results" / "phase1_4a" / "topology_b_v3_summary.md"

SYSTEM_PROMPT = """あなたは日本の野鳥観察を支援するアシスタントです。
ベランダに設置したバードケーキに来る鳥を観察しています。
撮影環境にはスズメとヒヨドリのみが飛来します。

今回は YOLOv8n の bird 検出結果から、動画内の bbox サイズ分布を使って判定します。
**重要**: 動画によって撮影距離・ズーム・画角が異なるため、bbox の絶対値ではなく
「動画内での相対的な分布」に注目してください。

判定材料:

1. bbox_distribution.bbox_size_distribution.dominant_range:
   - "small" (< 0.05) 優位: スズメの可能性が高い (小型の鳥)
     ただし遠景で撮影された bulbul の可能性もあり
   - "medium" (0.05-0.15) 優位: 中間サイズ、通常距離
   - "large" (> 0.15) 優位: ヒヨドリの可能性が高い (中型の鳥)
     ただしクローズアップ撮影された sparrow の可能性もあり
   - "none": 対象種の鳥検出なし

2. bbox_distribution.size_variation_type:
   - "uniform" (size_consistency < 0.3): 同じサイズの鳥が一貫して映っている
     → 単一種の可能性高
   - "mixed" (size_consistency >= 0.3): 異なるサイズの鳥が混在
     → 複数種の可能性高 (特にスズメ + ヒヨドリ混在)

3. 判定ロジック:
   - dominant "small" + uniform → sparrow 優位
   - dominant "large" + uniform → bulbul 優位
   - mixed → sparrow + bulbul 両陽性を検討
   - dominant "medium" → size_variation_type で判断
     - uniform: 単一種 (視覚だけでは判断困難。max_bbox_size_relative と
       avg_bbox_size_relative の関係も参考に)
     - mixed: 両種の可能性

4. 補足情報:
   - max_bbox_size_relative, avg_bbox_size_relative は絶対値の参考情報
   - relative_position (normalized_avg / min / max) はこの動画内での比率
   - 絶対閾値 (0.08 / 0.13) は使わない

入力:
{
  "visual_overall": {
    "num_frames_analyzed": N,
    "frames_with_bird": K,
    "max_bbox_size_relative": 0.XX,
    "avg_bbox_size_relative": 0.XX,
    "std_bbox_size": 0.XX,
    "avg_detection_confidence": 0.XX,
    "detection_counts_per_frame": [...]
  },
  "bbox_distribution": {
    "bbox_size_distribution": {"small_count": N, "medium_count": N, "large_count": N,
                                "total_detections": N,
                                "dominant_range": "small/medium/large/none",
                                "dominant_ratio": 0.XX},
    "size_consistency": 0.XX,
    "size_variation_type": "uniform/mixed/none",
    "relative_position": {"normalized_avg": 0.XX, "normalized_min": 0.XX, "normalized_max": 1.0}
  }
}

出力は以下のJSON形式で厳密に:
{
  "predictions": {"sparrow": 0 または 1, "bulbul": 0 または 1},
  "confidence": {"sparrow": 0.0-1.0, "bulbul": 0.0-1.0},
  "reasoning": "判定理由 (50字以内)",
  "modality_used": "visual",
  "fallback_used": false,
  "prompt_v3_factors": {
    "dominant_range": "small/medium/large/none",
    "size_variation_type": "uniform/mixed/none",
    "decision_basis": "判定に使った要因 (50字以内)"
  }
}

フォールバック: visual_overall.frames_with_bird = 0 のときのみ
{sparrow: 0, bulbul: 0}, fallback_used=true を返す。"""


def _overall_visual(per_frame_yolo: list[dict[str, Any]]) -> dict[str, Any]:
    """Phase 1.3-B-style visual aggregate from per-frame YOLO output."""
    bbox_rels: list[float] = []
    confs: list[float] = []
    counts: list[int] = []
    frames_with_bird = 0
    for f in per_frame_yolo:
        counts.append(f["num_detections"])
        if f["num_detections"] > 0:
            frames_with_bird += 1
        for d in f["detections"]:
            bbox_rels.append(float(d["bbox_rel"]))
            confs.append(float(d["confidence"]))
    max_rel = max(bbox_rels) if bbox_rels else 0.0
    avg_rel = sum(bbox_rels) / len(bbox_rels) if bbox_rels else 0.0
    if len(bbox_rels) > 1:
        mean = sum(bbox_rels) / len(bbox_rels)
        var = sum((x - mean) ** 2 for x in bbox_rels) / (len(bbox_rels) - 1)
        std_rel = math.sqrt(var)
    else:
        std_rel = 0.0
    max_conf = max(confs) if confs else 0.0
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    return {
        "num_frames_analyzed": len(per_frame_yolo),
        "frames_with_bird": frames_with_bird,
        "max_bbox_size_relative": round(max_rel, 4),
        "avg_bbox_size_relative": round(avg_rel, 4),
        "std_bbox_size": round(std_rel, 4),
        "max_detection_confidence": round(max_conf, 4),
        "avg_detection_confidence": round(avg_conf, 4),
        "detection_counts_per_frame": counts,
    }


def make_fold_fn(det: YoloDetector, llm: LlmClient):
    def fold_fn(fold: int, video: dict[str, Any], gt: dict[str, int]) -> dict[str, Any]:
        t0 = time.perf_counter()
        frame_paths = extract_frames(
            video["video_path"], video["video_id"], fps=DEFAULT_FPS
        )
        t_frame_ext = time.perf_counter() - t0

        t0 = time.perf_counter()
        per_frame = run_yolo_per_frame(det, frame_paths, fps_sampling=float(DEFAULT_FPS))
        t_yolo = time.perf_counter() - t0

        overall = _overall_visual(per_frame)
        bbox_dist = analyze_bbox_distribution(per_frame)

        llm_input = {
            "visual_overall": overall,
            "bbox_distribution": bbox_dist,
        }

        t_llm = 0.0
        fallback = False
        llm_output: dict[str, Any] | None = None

        if overall["frames_with_bird"] == 0:
            fallback = True
            llm_output = {
                "raw": None,
                "parsed": {
                    "predictions": {"sparrow": 0, "bulbul": 0},
                    "confidence": {"sparrow": 0.0, "bulbul": 0.0},
                    "reasoning": "鳥が検出されたフレームなし (LLM スキップ)",
                    "modality_used": "visual",
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
            "frame_extraction": {
                "num_frames": len(frame_paths),
                "fps_sampling": float(DEFAULT_FPS),
            },
            "yolo_output": overall,
            "bbox_distribution": bbox_dist,
            "fallback_triggered": fallback,
            "llm_input": llm_input,
            "llm_output": llm_output,
            "final_prediction": final_pred,
            "ground_truth": gt,
            "is_correct": is_correct,
            "elapsed_sec": {
                "frame_extract": round(t_frame_ext, 3),
                "yolo": round(t_yolo, 3),
                "llm": round(t_llm, 3),
                "total": round(t_frame_ext + t_yolo + t_llm, 3),
            },
        }

    return fold_fn


def render_summary(rows, skipped, total_time: float) -> str:
    from collections import Counter
    dom_counts: Counter[str] = Counter()
    var_counts: Counter[str] = Counter()
    for r in rows:
        if "error" in r:
            continue
        bd = r.get("bbox_distribution") or {}
        dom_counts[bd.get("bbox_size_distribution", {}).get("dominant_range", "?")] += 1
        var_counts[bd.get("size_variation_type", "?")] += 1

    lines = [
        "# Phase 1.4a Topology B_v3 extended summary",
        "",
        "Pipeline: ffmpeg @ 1 fps (CFR) -> per-frame YOLOv8n -> bbox_normalizer "
        "-> `qwen2.5:7b` (prompt v3 with relative distribution)",
        "",
        f"- Total folds executed: {len(rows)}",
        f"- Skipped YouTube entries: {len(skipped)}",
        f"- Total wall time: {total_time:.1f} s",
        "",
        "## dominant_range distribution",
        "",
        "| dominant_range | count |",
        "|---|---:|",
    ]
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

    det = YoloDetector()
    videos, skipped = load_extended_videos()
    print(f"Videos: {len(videos)} (skipped={len(skipped)})")

    run_start = time.perf_counter()
    rows = run_loocv_over(TOPOLOGY, make_fold_fn(det, llm), RESULTS_BASE, videos)
    total_time = time.perf_counter() - run_start

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(render_summary(rows, skipped, total_time), encoding="utf-8")
    print(f"Summary: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
