"""Generate results/phase1_3/video_review_sheet.md for human review.

Pulls per-video metadata, ground-truth labels and per-fold A / B / C
results together so a reviewer can watch each clip alongside the
pipelines' predictions and LLM reasoning. Human-review fields are left
blank for the reviewer to fill in.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_PATH = REPO_ROOT / "data" / "metadata.json"
LABELS_PATH = REPO_ROOT / "data" / "labels" / "phase1_labels.json"
BASE = REPO_ROOT / "results" / "phase1_3"
OUT_PATH = BASE / "video_review_sheet.md"

# Target species matching constants (mirrors phase1_3_common.birdnet_analyzer).
SPARROW_SCI = "Passer montanus"
BULBUL_SCI = "Hypsipetes amaurotis"
SPARROW_COMMON = "Eurasian Tree Sparrow"
BULBUL_COMMON = "Brown-eared Bulbul"
BIRDNET_DISPLAY_MIN_CONF = 0.1

# Priority annotation pulled from Phase 1.3 A-vs-B-vs-C analysis.
PRIORITY_NOTES = {
    "balcony_001": "C が B より勝った fold (B sparrow 偽陽性, C が抑制)",
    "balcony_008": "C が B より勝った fold (B が bulbul 誤付加, C が抑制)",
    "balcony_004": "C が B より負けた fold (B 正答、C が bulbul を sparrow に誤分類)",
    "balcony_003": "A/B/C すべて失敗 (視覚が bulbul を sparrow に誤分類する傾向)",
    "balcony_005": "両方失敗 / 'both' ラベル / A が唯一 LLM に到達した fold",
    "balcony_010": "両方失敗 / 'both' ラベル",
}


def ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def load_metadata() -> list[dict[str, Any]]:
    return json.loads(METADATA_PATH.read_text(encoding="utf-8")).get("videos", [])


def load_labels() -> dict[str, dict[str, Any]]:
    data = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    return {x["video_id"]: x for x in data.get("labels", [])}


def load_topology(name: str) -> dict[str, dict[str, Any]]:
    base = BASE / f"topology_{name}"
    out: dict[str, dict[str, Any]] = {}
    if not base.is_dir():
        return out
    for fold_dir in sorted(base.glob("fold_*")):
        for p in sorted(fold_dir.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            out[data["video_id"]] = data
    return out


def ground_truth_tuple(primary_label: str) -> tuple[int, int]:
    if primary_label == "sparrow":
        return 1, 0
    if primary_label == "bulbul":
        return 0, 1
    if primary_label == "both":
        return 1, 1
    return 0, 0


def ok_mark(pred: int | None, gt: int) -> str:
    if pred is None:
        return "-"
    return "○" if pred == gt else "✗"


def format_file_size(bytes_: int | None) -> str:
    if not bytes_:
        return "-"
    mb = bytes_ / (1024 * 1024)
    return f"{mb:.2f} MB"


def _matches_target(sci: str, com: str, target_sci: str, target_common: str) -> bool:
    return target_sci in (sci or "") or target_common in (com or "")


def birdnet_target_stats(
    all_detections: list[dict[str, Any]],
    target_sci: str,
    target_common: str,
    min_conf: float = BIRDNET_DISPLAY_MIN_CONF,
) -> tuple[int, float]:
    hits = [
        d for d in all_detections
        if _matches_target(d.get("scientific_name", ""), d.get("species", ""), target_sci, target_common)
        and float(d.get("confidence", 0.0)) >= min_conf
    ]
    if not hits:
        return 0, 0.0
    return len(hits), max(float(h["confidence"]) for h in hits)


def birdnet_top_other(
    all_detections: list[dict[str, Any]],
    min_conf: float = BIRDNET_DISPLAY_MIN_CONF,
    top_n: int = 3,
) -> list[tuple[str, int, float]]:
    agg: dict[str, list[float]] = {}
    for d in all_detections:
        if float(d.get("confidence", 0.0)) < min_conf:
            continue
        sci = d.get("scientific_name", "")
        com = d.get("species", "") or "(unknown)"
        if _matches_target(sci, com, SPARROW_SCI, SPARROW_COMMON):
            continue
        if _matches_target(sci, com, BULBUL_SCI, BULBUL_COMMON):
            continue
        agg.setdefault(com, []).append(float(d["confidence"]))
    ranked = [
        (name, len(confs), max(confs))
        for name, confs in agg.items()
    ]
    ranked.sort(key=lambda r: (-r[2], -r[1], r[0]))
    return ranked[:top_n]


def render_video_section(
    fold: int,
    video_meta: dict[str, Any],
    label: dict[str, Any],
    a_row: dict[str, Any] | None,
    b_row: dict[str, Any] | None,
    c_row: dict[str, Any] | None,
) -> str:
    vid = video_meta["video_id"]
    gt_s, gt_b = ground_truth_tuple(label.get("primary_label", ""))

    lines: list[str] = []
    lines.append(f"## {vid}")
    lines.append("")

    lines.append("### 動画情報")
    lines.append("")
    lines.append(f"- ファイル名: `{video_meta.get('filename', '-')}`")
    dur = video_meta.get("duration_sec")
    lines.append(f"- 再生時間: {dur:.1f} s" if isinstance(dur, (int, float)) else "- 再生時間: -")
    lines.append(f"- 解像度: {video_meta.get('resolution', '-')}")
    lines.append(f"- FPS: {video_meta.get('fps', '-')}")
    lines.append(f"- ファイルサイズ: {format_file_size(video_meta.get('file_size_bytes'))}")
    if vid in PRIORITY_NOTES:
        lines.append(f"- **優先レビュー理由**: {PRIORITY_NOTES[vid]}")
    lines.append("")

    lines.append("### Ground Truth (phase1_labels.json より)")
    lines.append("")
    lines.append(f"- primary_label: `{label.get('primary_label', '-')}`")
    lines.append(f"- sparrow: {gt_s}")
    lines.append(f"- bulbul: {gt_b}")
    lines.append(f"- review_needed: {str(label.get('review_needed', '-')).lower()}")
    lines.append(f"- location_detail: {label.get('location_detail', '-')}")
    notes = label.get("notes") or ""
    lines.append(f"- notes: {notes if notes else '(なし)'}")
    lines.append("")

    lines.append("### Topology A (Audio-Only) の結果")
    lines.append("")
    if a_row is None or "error" in a_row:
        lines.append("_結果が読み込めませんでした_")
    else:
        pred = a_row.get("final_prediction") or {}
        conf = pred.get("confidence") or {}
        lines.append(f"- 予測: {{sparrow: {pred.get('sparrow', '-')}, bulbul: {pred.get('bulbul', '-')}}}")
        lines.append(
            f"- confidence: {{sparrow: {float(conf.get('sparrow', 0.0)):.2f}, "
            f"bulbul: {float(conf.get('bulbul', 0.0)):.2f}}}"
        )
        lines.append(f"- fallback_triggered: {str(a_row.get('fallback_triggered', False)).lower()}")
        all_det = (a_row.get("birdnet_output") or {}).get("all_detections") or []
        sp_n, sp_max = birdnet_target_stats(all_det, SPARROW_SCI, SPARROW_COMMON)
        bu_n, bu_max = birdnet_target_stats(all_det, BULBUL_SCI, BULBUL_COMMON)
        lines.append("- BirdNET 検出 (threshold=0.1 でフィルタ, 対象種):")
        if sp_n + bu_n == 0:
            lines.append("  - _No target species detected_")
        else:
            if sp_n > 0:
                lines.append(f"  - Passer montanus: max_conf={sp_max:.3f}, num_detections={sp_n}")
            else:
                lines.append("  - Passer montanus: _not detected_")
            if bu_n > 0:
                lines.append(f"  - Hypsipetes amaurotis: max_conf={bu_max:.3f}, num_detections={bu_n}")
            else:
                lines.append("  - Hypsipetes amaurotis: _not detected_")
        top_others = birdnet_top_other(all_det)
        if top_others:
            lines.append("- BirdNET 誤検出 top 3 (対象種以外, 参考):")
            for name, count, mx in top_others:
                lines.append(f"  - {name}: max_conf={mx:.3f}, num={count}")
        else:
            lines.append("- BirdNET 誤検出 top 3 (対象種以外): _なし_")
        reasoning = ((a_row.get("llm_output") or {}).get("parsed") or {}).get("reasoning") or "(なし)"
        lines.append(f"- LLM reasoning: \"{reasoning}\"")
        lines.append(
            f"- 正誤: sparrow {ok_mark(pred.get('sparrow'), gt_s)}, "
            f"bulbul {ok_mark(pred.get('bulbul'), gt_b)}"
        )
    lines.append("")

    lines.append("### Topology B (Visual-Only) の結果")
    lines.append("")
    if b_row is None or "error" in b_row:
        lines.append("_結果が読み込めませんでした_")
    else:
        pred = b_row.get("final_prediction") or {}
        conf = pred.get("confidence") or {}
        y = b_row.get("yolo_output") or {}
        lines.append(f"- 予測: {{sparrow: {pred.get('sparrow', '-')}, bulbul: {pred.get('bulbul', '-')}}}")
        lines.append(
            f"- confidence: {{sparrow: {float(conf.get('sparrow', 0.0)):.2f}, "
            f"bulbul: {float(conf.get('bulbul', 0.0)):.2f}}}"
        )
        lines.append(f"- fallback_triggered: {str(b_row.get('fallback_triggered', False)).lower()}")
        lines.append("- YOLOv8n 結果:")
        lines.append(f"  - num_frames_analyzed: {y.get('num_frames_analyzed', '-')}")
        lines.append(f"  - frames_with_bird: {y.get('frames_with_bird', '-')}")
        lines.append(f"  - max_bbox_size_relative: {y.get('max_bbox_size_relative', 0.0):.3f}")
        lines.append(f"  - avg_bbox_size_relative: {y.get('avg_bbox_size_relative', 0.0):.3f}")
        lines.append(f"  - std_bbox_size: {y.get('std_bbox_size', 0.0):.3f}")
        lines.append(f"  - avg_detection_confidence: {y.get('avg_detection_confidence', 0.0):.3f}")
        reasoning = ((b_row.get("llm_output") or {}).get("parsed") or {}).get("reasoning") or "(なし)"
        lines.append(f"- LLM reasoning: \"{reasoning}\"")
        lines.append(
            f"- 正誤: sparrow {ok_mark(pred.get('sparrow'), gt_s)}, "
            f"bulbul {ok_mark(pred.get('bulbul'), gt_b)}"
        )
    lines.append("")

    lines.append("### Topology C (Parallel Fusion) の結果")
    lines.append("")
    if c_row is None or "error" in c_row:
        lines.append("_結果が読み込めませんでした_")
    else:
        pred = c_row.get("final_prediction") or {}
        conf = pred.get("confidence") or {}
        parsed = (c_row.get("llm_output") or {}).get("parsed") or {}
        modality = parsed.get("modality_used", "-")
        lines.append(f"- 予測: {{sparrow: {pred.get('sparrow', '-')}, bulbul: {pred.get('bulbul', '-')}}}")
        lines.append(
            f"- confidence: {{sparrow: {float(conf.get('sparrow', 0.0)):.2f}, "
            f"bulbul: {float(conf.get('bulbul', 0.0)):.2f}}}"
        )
        lines.append(f"- fallback_triggered: {str(c_row.get('fallback_triggered', False)).lower()}")
        lines.append(f"- modality_used: {modality}")
        reasoning = parsed.get("reasoning") or "(なし)"
        lines.append(f"- LLM reasoning: \"{reasoning}\"")
        lines.append(
            f"- 正誤: sparrow {ok_mark(pred.get('sparrow'), gt_s)}, "
            f"bulbul {ok_mark(pred.get('bulbul'), gt_b)}"
        )
    lines.append("")

    lines.append("### 人間レビュー欄 (Robosheep が記入)")
    lines.append("")
    lines.append("- [ ] 動画を視聴した")
    lines.append("- ground_truth は正しいか: [yes / no / 修正案]")
    lines.append("- 実際の内容メモ: [sparrow 何羽、bulbul 何羽、バードケーキ周辺か、動画全体の印象など]")
    lines.append("- 各トポロジの評価:")
    lines.append("  - A: [妥当 / 誤り / 部分的]")
    lines.append("  - B: [妥当 / 誤り / 部分的]")
    lines.append("  - C: [妥当 / 誤り / 部分的]")
    lines.append("- 特記事項: [LLM reasoning の質、予測の理由の妥当性など]")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def build_priority_block() -> list[str]:
    lines = [
        "## レビュー優先度",
        "",
        "以下の動画は特に注意して視聴することを推奨:",
        "",
        "- **C が B より勝った fold**: `balcony_001`, `balcony_008` "
        "(B が sparrow 偽陽性、C が正しく抑えた)",
        "- **C が B より負けた fold**: `balcony_004` "
        "(B 正答、C が bulbul を sparrow と誤判定)",
        "- **両方失敗**: `balcony_003`, `balcony_005`, `balcony_010` "
        "(特に 005, 010 は 'both' ラベル)",
        "- **Topology A が唯一 LLM 到達**: `balcony_005`",
        "",
    ]
    return lines


def build_summary_block() -> list[str]:
    return [
        "# Phase 1.3 Video Review Sheet",
        "",
        "## 使い方",
        "",
        "各動画を実際に視聴し、「人間レビュー欄」に記入してください。",
        "動画ファイルは `data/raw/balcony_videos/` にあります (gitignored)。",
        "",
        "## 全体サマリ (参考)",
        "",
        "| Topology | macro F1 | sparrow F1 | bulbul F1 | fallback |",
        "|---|---:|---:|---:|---:|",
        "| A | 0.143 | 0.000 | 0.286 | 10 / 11 |",
        "| B | 0.819 | 0.714 | 0.923 |  0 / 11 |",
        "| C | 0.733 | 0.800 | 0.667 |  0 / 11 |",
        "",
    ]


def main() -> int:
    ensure_utf8_streams()
    videos = load_metadata()
    labels = load_labels()
    a_rows = load_topology("a")
    b_rows = load_topology("b")
    c_rows = load_topology("c")

    parts: list[str] = []
    parts.extend(build_summary_block())
    parts.extend(build_priority_block())
    parts.append("---")
    parts.append("")

    for i, v in enumerate(videos, start=1):
        vid = v["video_id"]
        label = labels.get(vid, {"primary_label": ""})
        parts.append(
            render_video_section(
                fold=i,
                video_meta=v,
                label=label,
                a_row=a_rows.get(vid),
                b_row=b_rows.get(vid),
                c_row=c_rows.get(vid),
            )
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(
        f"Videos: {len(videos)}, A rows: {len(a_rows)}, "
        f"B rows: {len(b_rows)}, C rows: {len(c_rows)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
