"""Phase 1.2 two-node validation: visual pipeline (YOLOv8n + LLM).

For each of the 11 balcony videos in data/metadata.json, this script:

  1. Extracts frames at 1 fps with ffmpeg into
     data/processed/frames/{video_id}/ .
  2. Runs YOLOv8n on every frame and keeps only the COCO ``bird`` class
     (class id 14).
  3. Aggregates detection statistics (count, max relative bbox size, mean
     confidence, per-frame count vector).
  4. Sends the aggregate to Ollama ``qwen2.5:7b`` with ``format=json`` and
     asks for a sparrow/bulbul multi-label decision.
  5. Writes one JSON per video to ``results/phase1_2/visual/{video_id}.json``
     and a human-readable overview to ``results/phase1_2/visual_summary.md``.

Ground truth comes from ``data/labels/phase1_labels.json`` (primary_label
-> multi-label map). Even when ``review_needed`` is true the label is
used as-is; Phase 1.2 is an end-to-end smoke test, not an accuracy run.

Exit codes:
    0  run completed (the Go/No-Go decision is printed but does not gate
       the exit code — the summary and per-video JSONs are always written)
    1  generic error before the run could start
    2  Ollama reachable check failed
    3  qwen2.5:7b not installed in Ollama
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_PATH = REPO_ROOT / "data" / "metadata.json"
LABELS_PATH = REPO_ROOT / "data" / "labels" / "phase1_labels.json"
VIDEO_DIR = REPO_ROOT / "data" / "raw" / "balcony_videos"
FRAMES_ROOT = REPO_ROOT / "data" / "processed" / "frames"
RESULTS_DIR = REPO_ROOT / "results" / "phase1_2" / "visual"
SUMMARY_PATH = REPO_ROOT / "results" / "phase1_2" / "visual_summary.md"

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE}/api/tags"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE}/api/generate"
MODEL = "qwen2.5:7b"
TEMPERATURE = 0.1
GENERATE_TIMEOUT_SEC = 180
CONNECT_TIMEOUT_SEC = 5

FRAME_FPS = 1
YOLO_WEIGHTS = "yolov8n.pt"
BIRD_CLASS_ID = 14  # COCO "bird"

SYSTEM_PROMPT = """あなたは日本の野鳥観察を支援するアシスタントです。
ベランダに設置したバードケーキに来る鳥を撮影した動画から、
YOLOv8n による鳥検出結果を与えます。
撮影環境にはスズメとヒヨドリのみが飛来します。

検出結果を分析して、動画に映っている鳥の種を判定してください。

入力:
{
  "num_frames_analyzed": 分析したフレーム数,
  "frames_with_bird": 鳥が検出されたフレーム数,
  "max_bbox_size_relative": 最大の鳥の画面に対する相対サイズ (0.0-1.0),
  "avg_confidence": 平均検出確信度,
  "detection_counts": フレームごとの検出数リスト
}

以下のJSON形式で厳密に応答してください:
{
  "predictions": {
    "sparrow": 0 または 1,
    "bulbul": 0 または 1
  },
  "confidence": {
    "sparrow": 0.0 から 1.0,
    "bulbul": 0.0 から 1.0
  },
  "reasoning": "判定理由を日本語で簡潔に (50字以内)"
}

判定ヒント:
- スズメは小さい (bbox_size_relative < 0.1 程度)
- ヒヨドリは大きい (bbox_size_relative > 0.1 程度)
- frames_with_bird = 0 なら両方 0"""


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def check_ollama_ready() -> None:
    try:
        resp = requests.get(OLLAMA_TAGS_URL, timeout=CONNECT_TIMEOUT_SEC)
        resp.raise_for_status()
    except requests.ConnectionError:
        print(
            f"Ollama に接続できません ({OLLAMA_BASE})。\n"
            "Ollama が起動しているか確認してください (ollama serve)。",
            file=sys.stderr,
        )
        sys.exit(2)
    except requests.RequestException as e:
        print(f"Ollama への接続で予期せぬエラー: {e}", file=sys.stderr)
        sys.exit(2)

    tag_names = {m.get("name") for m in resp.json().get("models", [])}
    if MODEL not in tag_names:
        print(
            f"モデル {MODEL} が見つかりません。\n"
            f"次を実行してください: ollama pull {MODEL}",
            file=sys.stderr,
        )
        sys.exit(3)


def load_yolo():
    try:
        from ultralytics import YOLO
    except ImportError:
        print(
            "ultralytics が見つかりません。\n"
            "次を実行してください: pip install ultralytics",
            file=sys.stderr,
        )
        sys.exit(1)
    return YOLO(YOLO_WEIGHTS)


def extract_frames(video_path: Path, out_dir: Path, fps: int = FRAME_FPS) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("frame_*.jpg"):
        old.unlink()
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", "2",
        str(out_dir / "frame_%03d.jpg"),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(out_dir.glob("frame_*.jpg"))


def aggregate_yolo(model, frame_paths: list[Path]) -> dict[str, Any]:
    frames_with_bird = 0
    max_bbox_size_relative = 0.0
    confidences: list[float] = []
    detection_counts: list[int] = []

    for fp in frame_paths:
        results = model.predict(
            source=str(fp),
            classes=[BIRD_CLASS_ID],
            verbose=False,
        )
        r = results[0]
        boxes = r.boxes
        count = 0 if boxes is None else len(boxes)
        detection_counts.append(count)
        if count == 0:
            continue

        frames_with_bird += 1
        h, w = r.orig_shape
        img_area = float(h) * float(w)
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        for (x1, y1, x2, y2), c in zip(xyxy, confs):
            bbox_area = float((x2 - x1) * (y2 - y1))
            rel = bbox_area / img_area if img_area > 0 else 0.0
            if rel > max_bbox_size_relative:
                max_bbox_size_relative = rel
            confidences.append(float(c))

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        "num_frames_analyzed": len(frame_paths),
        "frames_with_bird": frames_with_bird,
        "max_bbox_size_relative": round(max_bbox_size_relative, 4),
        "avg_confidence": round(avg_conf, 4),
        "detection_counts": detection_counts,
    }


def call_llm(aggregate: dict[str, Any]) -> tuple[str, float]:
    prompt_obj = {
        "num_frames_analyzed": aggregate["num_frames_analyzed"],
        "frames_with_bird": aggregate["frames_with_bird"],
        "max_bbox_size_relative": aggregate["max_bbox_size_relative"],
        "avg_confidence": aggregate["avg_confidence"],
        "detection_counts": aggregate["detection_counts"],
    }
    payload = {
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": json.dumps(prompt_obj, ensure_ascii=False),
        "format": "json",
        "stream": False,
        "options": {"temperature": TEMPERATURE},
    }
    start = time.perf_counter()
    resp = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=GENERATE_TIMEOUT_SEC)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    return resp.json().get("response", ""), elapsed


def parse_llm_response(text: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    preds = obj.get("predictions")
    confs = obj.get("confidence")
    if not isinstance(preds, dict) or not isinstance(confs, dict):
        return None
    for k in ("sparrow", "bulbul"):
        if preds.get(k) not in (0, 1):
            return None
    return obj


def ground_truth_for(primary_label: str) -> dict[str, int]:
    if primary_label == "sparrow":
        return {"sparrow": 1, "bulbul": 0}
    if primary_label == "bulbul":
        return {"sparrow": 0, "bulbul": 1}
    if primary_label == "both":
        return {"sparrow": 1, "bulbul": 1}
    return {"sparrow": 0, "bulbul": 0}


def load_labels() -> dict[str, str]:
    data = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    return {lab["video_id"]: lab["primary_label"] for lab in data.get("labels", [])}


def compute_multilabel_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = 0
    per_class = {"sparrow": {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "correct": 0},
                 "bulbul":  {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "correct": 0}}
    for r in rows:
        if r.get("llm_response") is None or r["llm_response"].get("predictions") is None:
            continue
        preds = r["llm_response"]["predictions"]
        gt = r["ground_truth"]
        n += 1
        for k in ("sparrow", "bulbul"):
            p, g = preds[k], gt[k]
            if p == 1 and g == 1:
                per_class[k]["tp"] += 1
            elif p == 1 and g == 0:
                per_class[k]["fp"] += 1
            elif p == 0 and g == 1:
                per_class[k]["fn"] += 1
            else:
                per_class[k]["tn"] += 1
            if p == g:
                per_class[k]["correct"] += 1

    def f1_of(tp: int, fp: int, fn: int) -> float:
        if tp == 0:
            return 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    acc = {k: (per_class[k]["correct"] / n if n > 0 else 0.0) for k in per_class}
    f1 = {k: f1_of(per_class[k]["tp"], per_class[k]["fp"], per_class[k]["fn"]) for k in per_class}
    macro_f1 = (f1["sparrow"] + f1["bulbul"]) / 2.0
    return {
        "n_scored": n,
        "per_class": per_class,
        "accuracy": acc,
        "f1": f1,
        "macro_f1": macro_f1,
    }


def go_decision(n_valid: int, n_total: int) -> str:
    if n_valid >= n_total:
        return f"Go (β)  ({n_valid}/{n_total} videos parsed)"
    if n_valid >= 8:
        return f"Review  ({n_valid}/{n_total} videos parsed, need >= {n_total})"
    return f"No-Go  ({n_valid}/{n_total} videos parsed)"


def format_summary(rows: list[dict[str, Any]], metrics: dict[str, Any], total_time: float) -> str:
    n = len(rows)
    n_valid = metrics["n_scored"]
    lines = [
        "# Phase 1.2 Visual Node Summary",
        "",
        f"- Pipeline: ffmpeg @ {FRAME_FPS} fps -> YOLOv8n (bird class) -> `{MODEL}`",
        f"- Videos:   {n}",
        f"- Parsed:   {n_valid} / {n}",
        f"- Go / No-Go: {go_decision(n_valid, n)}",
        f"- Macro F1: {metrics['macro_f1']:.3f}",
        f"- Accuracy: sparrow={metrics['accuracy']['sparrow']:.3f}, "
        f"bulbul={metrics['accuracy']['bulbul']:.3f}",
        f"- Total wall time: {total_time:.1f} s",
        "",
        "## Per-video results",
        "",
        "| video_id | frames | with_bird | max_rel | avg_conf | pred (S/B) | GT (S/B) | S OK | B OK | t_extract | t_yolo | t_llm |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        yolo = r["yolo_results"]
        pred = r["llm_response"]["predictions"] if r["llm_response"] else {"sparrow": "-", "bulbul": "-"}
        gt = r["ground_truth"]
        ok = r["is_correct"]
        ok_s = "OK" if ok.get("sparrow") else "X"
        ok_b = "OK" if ok.get("bulbul") else "X"
        if r["llm_response"] is None:
            ok_s = ok_b = "PARSE"
        lines.append(
            f"| {r['video_id']} "
            f"| {yolo['num_frames_analyzed']} "
            f"| {yolo['frames_with_bird']} "
            f"| {yolo['max_bbox_size_relative']:.3f} "
            f"| {yolo['avg_confidence']:.3f} "
            f"| {pred['sparrow']}/{pred['bulbul']} "
            f"| {gt['sparrow']}/{gt['bulbul']} "
            f"| {ok_s} | {ok_b} "
            f"| {r['timing']['extract_sec']:.2f} "
            f"| {r['timing']['yolo_sec']:.2f} "
            f"| {r['timing']['llm_sec']:.2f} |"
        )
    lines.append("")
    lines.append("## Model reasoning")
    lines.append("")
    for r in rows:
        reasoning = (r["llm_response"] or {}).get("reasoning") or "(parse failed)"
        lines.append(f"- **{r['video_id']}**: {reasoning}")
    lines.append("")

    lines.append("## Mean stage times")
    lines.append("")
    n_all = len(rows) or 1
    mean_extract = sum(r["timing"]["extract_sec"] for r in rows) / n_all
    mean_yolo = sum(r["timing"]["yolo_sec"] for r in rows) / n_all
    mean_llm = sum(r["timing"]["llm_sec"] for r in rows) / n_all
    lines.append(f"- Frame extraction: {mean_extract:.2f} s")
    lines.append(f"- YOLOv8n inference: {mean_yolo:.2f} s")
    lines.append(f"- LLM call:         {mean_llm:.2f} s")
    lines.append("")
    return "\n".join(lines)


def process_video(model, video: dict[str, Any], primary_label: str) -> dict[str, Any]:
    video_id = video["video_id"]
    video_path = VIDEO_DIR / video["filename"]
    frames_dir = FRAMES_ROOT / video_id

    gt = ground_truth_for(primary_label)

    t0 = time.perf_counter()
    frame_paths = extract_frames(video_path, frames_dir, fps=FRAME_FPS)
    t_extract = time.perf_counter() - t0

    t0 = time.perf_counter()
    yolo_results = aggregate_yolo(model, frame_paths)
    t_yolo = time.perf_counter() - t0

    raw, t_llm = call_llm(yolo_results)
    parsed = parse_llm_response(raw)

    llm_response: dict[str, Any] | None = None
    is_correct = {"sparrow": False, "bulbul": False}
    if parsed is not None:
        llm_response = {
            "raw": raw,
            "predictions": parsed["predictions"],
            "confidence": parsed.get("confidence", {}),
            "reasoning": parsed.get("reasoning", ""),
        }
        is_correct = {
            "sparrow": parsed["predictions"]["sparrow"] == gt["sparrow"],
            "bulbul":  parsed["predictions"]["bulbul"]  == gt["bulbul"],
        }
    else:
        llm_response = None

    return {
        "video_id": video_id,
        "modality": "visual",
        "extraction": {
            "num_frames": len(frame_paths),
            "fps_sampling": float(FRAME_FPS),
            "frame_paths": [
                str(p.relative_to(REPO_ROOT)).replace("\\", "/")
                for p in frame_paths
            ],
        },
        "yolo_results": yolo_results,
        "llm_response_raw": raw,
        "llm_response": llm_response,
        "ground_truth": gt,
        "is_correct": is_correct,
        "timing": {
            "extract_sec": round(t_extract, 3),
            "yolo_sec": round(t_yolo, 3),
            "llm_sec": round(t_llm, 3),
        },
        "elapsed_sec": round(t_extract + t_yolo + t_llm, 3),
    }


def main() -> int:
    ensure_utf8_streams()

    if not METADATA_PATH.is_file():
        print(f"metadata not found: {METADATA_PATH}", file=sys.stderr)
        return 1
    if not LABELS_PATH.is_file():
        print(f"labels not found: {LABELS_PATH}", file=sys.stderr)
        return 1

    check_ollama_ready()
    model = load_yolo()

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    videos = metadata.get("videos", [])
    labels = load_labels()
    if not videos:
        print("no videos in metadata", file=sys.stderr)
        return 1

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    run_start = time.perf_counter()
    for v in videos:
        vid = v["video_id"]
        label = labels.get(vid)
        if label is None:
            print(f"[{vid}] no label, skipping", file=sys.stderr)
            continue
        print(f"[{vid}] {v['filename']} ...", flush=True)
        try:
            row = process_video(model, v, label)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            print(f"[{vid}] ffmpeg failed: {stderr.strip()[:300]}", file=sys.stderr)
            continue
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            body = e.response.text[:200] if e.response is not None else ""
            print(f"[{vid}] Ollama HTTP {status}: {body}", file=sys.stderr)
            continue
        except Exception as e:  # noqa: BLE001 - preserve per-video isolation
            print(f"[{vid}] unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
            continue

        (RESULTS_DIR / f"{vid}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rows.append(row)
        pred = row["llm_response"]["predictions"] if row["llm_response"] else "PARSE_FAIL"
        print(
            f"  frames={row['yolo_results']['num_frames_analyzed']} "
            f"with_bird={row['yolo_results']['frames_with_bird']} "
            f"pred={pred} gt={row['ground_truth']} "
            f"({row['elapsed_sec']:.1f}s)"
        )

    total_time = time.perf_counter() - run_start
    metrics = compute_multilabel_metrics(rows)
    SUMMARY_PATH.write_text(format_summary(rows, metrics, total_time), encoding="utf-8")

    print()
    print(f"Videos processed : {len(rows)} / {len(videos)}")
    print(f"Parsed JSON      : {metrics['n_scored']} / {len(rows)}")
    print(f"Macro F1         : {metrics['macro_f1']:.3f}")
    print(f"Decision         : {go_decision(metrics['n_scored'], len(videos))}")
    print(f"Summary          : {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
