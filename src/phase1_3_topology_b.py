"""Phase 1.3 — Topology B: Visual-Only (YOLOv8n -> LLM).

Pipeline per fold:
    mp4 -> frames @ 1 fps (cached) -> YOLOv8n (bird class) -> aggregate
        -> qwen2.5:7b (format=json)

Fallback: when ``frames_with_bird`` is zero the LLM call is skipped and
the prediction is set to ``{sparrow: 0, bulbul: 0, fallback_used: true}``.
The full detection vector is still persisted.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from phase1_3_common.llm_client import LlmClient, ModelMissing, OllamaUnavailable
from phase1_3_common.loocv_runner import (
    compute_metrics,
    ensure_utf8_streams,
    run_loocv,
)
from phase1_3_common.video_processor import DEFAULT_FPS, extract_frames
from phase1_3_common.yolo_detector import YoloDetector

TOPOLOGY = "B"
RESULTS_BASE = REPO_ROOT / "results" / "phase1_3" / "topology_b"
SUMMARY_PATH = REPO_ROOT / "results" / "phase1_3" / "topology_b_summary.md"

SYSTEM_PROMPT = """あなたは日本の野鳥観察を支援するアシスタントです。
ベランダに設置したバードケーキに来る鳥を観察しています。
撮影環境にはスズメとヒヨドリのみが飛来します。

YOLOv8n による鳥検出結果のみから、動画に映っている鳥の種を判定してください。
音声情報はありません。視覚のみで判断します。

重要な判定材料:
- スズメ (sparrow) は小型: 画面に対する bbox サイズは通常 0.08 未満
- ヒヨドリ (bulbul) は中型: 画面に対する bbox サイズは通常 0.1 以上

入力:
{
  "num_frames_analyzed": 15,
  "frames_with_bird": 12,
  "max_bbox_size_relative": 0.08,
  "avg_bbox_size_relative": 0.06,
  "std_bbox_size": 0.02,
  "max_detection_confidence": 0.87,
  "avg_detection_confidence": 0.76,
  "detection_counts_per_frame": [1, 2, 2, 1, 0, ...]
}

以下のJSON形式で応答してください:
{
  "predictions": {"sparrow": 0 または 1, "bulbul": 0 または 1},
  "confidence": {"sparrow": 0.0-1.0, "bulbul": 0.0-1.0},
  "reasoning": "判定理由 (50字以内)",
  "fallback_used": false
}

判定ルール:
- frames_with_bird = 0: {sparrow: 0, bulbul: 0}, fallback_used=true
- max_bbox_size_relative < 0.08: sparrow=1, bulbul=0
- max_bbox_size_relative >= 0.15: sparrow=0, bulbul=1
- 0.08 <= max_bbox_size_relative < 0.15: サイズ中間、検出数や分布から判断
- 複数サイズが混在（std が大きい）: sparrow=1, bulbul=1 も考慮"""


def make_fold_fn(det: YoloDetector, llm: LlmClient):
    def fold_fn(fold: int, video: dict[str, Any], gt: dict[str, int]) -> dict[str, Any]:
        t0 = time.perf_counter()
        frame_paths = extract_frames(video["video_path"], video["video_id"], fps=DEFAULT_FPS)
        t_extract = time.perf_counter() - t0

        t0 = time.perf_counter()
        yolo_out = det.aggregate(frame_paths)
        t_yolo = time.perf_counter() - t0

        llm_input = {
            "num_frames_analyzed": yolo_out["num_frames_analyzed"],
            "frames_with_bird": yolo_out["frames_with_bird"],
            "max_bbox_size_relative": yolo_out["max_bbox_size_relative"],
            "avg_bbox_size_relative": yolo_out["avg_bbox_size_relative"],
            "std_bbox_size": yolo_out["std_bbox_size"],
            "max_detection_confidence": yolo_out["max_detection_confidence"],
            "avg_detection_confidence": yolo_out["avg_detection_confidence"],
            "detection_counts_per_frame": yolo_out["detection_counts_per_frame"],
        }

        t_llm = 0.0
        fallback = False
        llm_output: dict[str, Any] | None = None

        if yolo_out["frames_with_bird"] == 0:
            fallback = True
            llm_output = {
                "raw": None,
                "parsed": {
                    "predictions": {"sparrow": 0, "bulbul": 0},
                    "confidence": {"sparrow": 0.0, "bulbul": 0.0},
                    "reasoning": "鳥が検出されたフレームなし (LLM スキップ)",
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
            "yolo_output": yolo_out,
            "fallback_triggered": fallback,
            "llm_input": llm_input,
            "llm_output": llm_output,
            "final_prediction": final_pred,
            "ground_truth": gt,
            "is_correct": is_correct,
            "elapsed_sec": {
                "frame_extract": round(t_extract, 3),
                "yolo": round(t_yolo, 3),
                "llm": round(t_llm, 3),
                "total": round(t_extract + t_yolo + t_llm, 3),
            },
        }
    return fold_fn


def format_summary(rows: list[dict[str, Any]], metrics: dict[str, Any], total_time: float) -> str:
    n = len(rows)
    lines = [
        "# Phase 1.3 Topology B (Visual-Only) Summary",
        "",
        "- Pipeline: ffmpeg @ 1 fps (CFR) -> YOLOv8n (bird class) -> `qwen2.5:7b`",
        f"- Folds:   {n}",
        f"- Scored:  {metrics['n_scored']}",
        f"- Fallback triggered: {metrics['fallback_triggered']} / {n}",
        f"- LLM parse failures (non-fallback): {metrics['parse_fail']} / {n}",
        f"- Errors:  {metrics['errors']} / {n}",
        f"- Macro F1: {metrics['macro_f1']:.3f}",
        f"- Sparrow F1: {metrics['f1']['sparrow']:.3f} | Bulbul F1: {metrics['f1']['bulbul']:.3f}",
        f"- Sparrow accuracy: {metrics['accuracy']['sparrow']:.3f} | "
        f"Bulbul accuracy: {metrics['accuracy']['bulbul']:.3f}",
        f"- Total wall time: {total_time:.1f} s",
        "",
        "## Per-fold results",
        "",
        "| fold | video_id | frames | with_bird | max_rel | avg_rel | std | max_conf | pred (S/B) | GT (S/B) | S OK | B OK | fallback | t_extract | t_yolo | t_llm |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['fold']:02d} | {r['video_id']} | - | - | - | - | - | - | ERR | {r['ground_truth']['sparrow']}/{r['ground_truth']['bulbul']} | - | - | - | - | - | - |")
            continue
        y = r["yolo_output"]
        pred = r["final_prediction"]
        gt = r["ground_truth"]
        ok = r["is_correct"]
        ok_s = "OK" if ok["sparrow"] else "X"
        ok_b = "OK" if ok["bulbul"] else "X"
        fb = "Y" if r["fallback_triggered"] else "-"
        t = r["elapsed_sec"]
        lines.append(
            f"| {r['fold']:02d} | {r['video_id']} "
            f"| {y['num_frames_analyzed']} | {y['frames_with_bird']} "
            f"| {y['max_bbox_size_relative']:.3f} | {y['avg_bbox_size_relative']:.3f} | {y['std_bbox_size']:.3f} "
            f"| {y['max_detection_confidence']:.3f} "
            f"| {pred['sparrow']}/{pred['bulbul']} "
            f"| {gt['sparrow']}/{gt['bulbul']} "
            f"| {ok_s} | {ok_b} | {fb} "
            f"| {t['frame_extract']:.2f} "
            f"| {t['yolo']:.2f} "
            f"| {t['llm']:.2f} |"
        )
    lines.append("")

    lines.append("## Confusion matrices")
    lines.append("")
    for species in ("sparrow", "bulbul"):
        m = metrics["confusion_matrix"][species]
        lines.append(f"### {species}")
        lines.append("")
        lines.append("| | pred=1 | pred=0 |")
        lines.append("|---|---|---|")
        lines.append(f"| gt=1 | TP={m['tp']} | FN={m['fn']} |")
        lines.append(f"| gt=0 | FP={m['fp']} | TN={m['tn']} |")
        lines.append("")

    lines.append("## Model reasoning")
    lines.append("")
    for r in rows:
        if "error" in r:
            lines.append(f"- **fold_{r['fold']:02d} {r['video_id']}**: [error] {r['error']}")
            continue
        parsed = (r.get("llm_output") or {}).get("parsed") or {}
        reasoning = parsed.get("reasoning") or "(none)"
        lines.append(f"- **fold_{r['fold']:02d} {r['video_id']}**: {reasoning}")
    lines.append("")

    lines.append("## Mean stage times (across all folds)")
    lines.append("")
    n_all = sum(1 for r in rows if "error" not in r) or 1
    mean_extract = sum(r["elapsed_sec"]["frame_extract"] for r in rows if "error" not in r) / n_all
    mean_yolo = sum(r["elapsed_sec"]["yolo"] for r in rows if "error" not in r) / n_all
    mean_llm = sum(r["elapsed_sec"]["llm"] for r in rows if "error" not in r) / n_all
    lines.append(f"- Frame extraction:    {mean_extract:.2f} s")
    lines.append(f"- YOLOv8n inference:   {mean_yolo:.2f} s")
    lines.append(f"- LLM call (non-fallback avg): {mean_llm:.2f} s")
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

    run_start = time.perf_counter()
    rows = run_loocv(TOPOLOGY, make_fold_fn(det, llm), RESULTS_BASE)
    total_time = time.perf_counter() - run_start

    metrics = compute_metrics(rows)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(format_summary(rows, metrics, total_time), encoding="utf-8")

    print()
    print(f"Folds scored     : {metrics['n_scored']} / {len(rows)}")
    print(f"Fallback          : {metrics['fallback_triggered']}")
    print(f"LLM parse failures: {metrics['parse_fail']}")
    print(f"Errors            : {metrics['errors']}")
    print(f"Macro F1          : {metrics['macro_f1']:.3f}")
    print(f"Summary           : {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
