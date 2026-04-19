"""Phase 1.1 single-node validation: qwen2.5:7b on five bird-ID prompts.

Sends each prompt in tests/phase1_1_prompts.json to Ollama's
/api/generate endpoint with format=json, then scores:

    match expected_primary             -> 1.0
    match expected_fallback (optional) -> 0.5
    otherwise / parse failure          -> 0.0

Writes the full raw JSON to results/phase1_1/raw_responses.json and a
human-readable table to results/phase1_1/summary.md. Exit code 0 on a
clean run (even with a No-Go score), 2 on Ollama connectivity errors,
3 on missing model.

Usage:
    python src/phase1_1_single_node.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = REPO_ROOT / "tests" / "phase1_1_prompts.json"
RESULTS_DIR = REPO_ROOT / "results" / "phase1_1"
RAW_RESPONSES_PATH = RESULTS_DIR / "raw_responses.json"
SUMMARY_PATH = RESULTS_DIR / "summary.md"

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE}/api/tags"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE}/api/generate"
MODEL = "qwen2.5:7b"
TEMPERATURE = 0.1
GENERATE_TIMEOUT_SEC = 180
CONNECT_TIMEOUT_SEC = 5

SYSTEM_PROMPT = """あなたは日本の野鳥観察を支援するアシスタントです。
ベランダに設置したバードケーキに来る鳥を観察しています。
撮影環境にはスズメとヒヨドリのみが飛来します。

以下の記述を読んで、どの鳥について記述されているかを判定してください。

候補:
- sparrow: スズメ (Passer montanus)
- bulbul: ヒヨドリ (Hypsipetes amaurotis)
- both: スズメとヒヨドリの両方
- none: 鳥がいない、または鳥の記述ではない
- unknown: 記述が曖昧で判定不能

以下の JSON 形式で厳密に応答してください。余計な前置きや説明は不要です。

{
  "predicted_species": "sparrow" | "bulbul" | "both" | "none" | "unknown",
  "confidence": 0.0 から 1.0 の数値,
  "reasoning": "判定の理由を日本語で簡潔に（50字以内）"
}"""

VALID_SPECIES = {"sparrow", "bulbul", "both", "none", "unknown"}


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


def call_ollama(description: str) -> tuple[str, float]:
    payload = {
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": description,
        "format": "json",
        "stream": False,
        "options": {"temperature": TEMPERATURE},
    }
    start = time.perf_counter()
    resp = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=GENERATE_TIMEOUT_SEC)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    body = resp.json()
    return body.get("response", ""), elapsed


def parse_response(text: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def score(species: str | None, primary: str, fallback: str | None) -> float:
    if species is None:
        return 0.0
    if species == primary:
        return 1.0
    if fallback is not None and species == fallback:
        return 0.5
    return 0.0


def go_decision(total: float, max_total: float) -> str:
    if total >= 3.0:
        return f"Go  (>= 3.0 / {max_total:.1f})"
    if total >= 1.5:
        return f"Review  (1.5 <= total < 3.0 / {max_total:.1f})"
    return f"No-Go  (< 1.5 / {max_total:.1f})"


def format_summary(
    results: list[dict[str, Any]],
    total: float,
    json_ok: int,
    avg_elapsed: float,
) -> str:
    n = len(results)
    lines = [
        "# Phase 1.1 Single-Node Validation",
        "",
        f"- Model: `{MODEL}`",
        f"- Temperature: {TEMPERATURE}",
        f"- Prompts: {n} (see `tests/phase1_1_prompts.json`)",
        "",
        "## Headline",
        "",
        f"- **Total score:** {total:.1f} / {float(n):.1f}",
        f"- **Go / No-Go:** {go_decision(total, float(n))}",
        f"- **JSON parse success:** {json_ok} / {n}",
        f"- **Mean response time:** {avg_elapsed:.2f} s",
        "",
        "## Per-prompt results",
        "",
        "| id | category | expected (primary / fallback) | predicted | confidence | score | JSON | time (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        fb = r["expected_fallback"] if r["expected_fallback"] is not None else "-"
        pred = r["predicted_species"] or "(parse failed)"
        conf = f"{r['confidence']}" if r["confidence"] is not None else "-"
        json_flag = "OK" if r["is_json_valid"] else "FAIL"
        lines.append(
            f"| {r['prompt_id']} | {r['category']} | {r['expected_primary']} / {fb} "
            f"| {pred} | {conf} | {r['score']:.1f} | {json_flag} | {r['elapsed_sec']:.2f} |"
        )
    lines.append("")
    lines.append("## Model reasoning")
    lines.append("")
    for r in results:
        reasoning = r["reasoning"] or "(none)"
        lines.append(f"- **{r['prompt_id']}** ({r['category']}): {reasoning}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_utf8_streams()

    if not PROMPTS_PATH.is_file():
        print(f"prompts file not found: {PROMPTS_PATH}", file=sys.stderr)
        return 1

    check_ollama_ready()

    spec = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    prompts = spec.get("prompts", [])
    if not prompts:
        print("no prompts to run", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    for p in prompts:
        print(f"[{p['id']}] {p['category']} ...", end=" ", flush=True)
        try:
            raw_text, elapsed = call_ollama(p["description"])
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            body = e.response.text[:200] if e.response is not None else ""
            print(f"\nHTTP {status} from Ollama: {body}", file=sys.stderr)
            return 1

        parsed = parse_response(raw_text)
        if parsed is not None:
            species_raw = parsed.get("predicted_species")
            species = species_raw if species_raw in VALID_SPECIES else None
            confidence = parsed.get("confidence")
            reasoning = parsed.get("reasoning") or ""
        else:
            species = None
            confidence = None
            reasoning = "JSON parse failed"

        entry_score = score(species, p["expected_primary"], p.get("expected_fallback"))
        results.append({
            "prompt_id": p["id"],
            "category": p["category"],
            "description": p["description"],
            "expected_primary": p["expected_primary"],
            "expected_fallback": p.get("expected_fallback"),
            "raw_response": raw_text,
            "parsed": parsed,
            "predicted_species": species,
            "confidence": confidence,
            "reasoning": reasoning,
            "score": entry_score,
            "is_json_valid": parsed is not None,
            "elapsed_sec": round(elapsed, 3),
        })
        print(f"-> {species or 'PARSE_FAIL'}  score={entry_score:.1f}  {elapsed:.1f}s")

    total_score = sum(r["score"] for r in results)
    json_ok = sum(1 for r in results if r["is_json_valid"])
    avg_elapsed = sum(r["elapsed_sec"] for r in results) / len(results)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_RESPONSES_PATH.write_text(
        json.dumps(
            {
                "model": MODEL,
                "temperature": TEMPERATURE,
                "system_prompt": SYSTEM_PROMPT,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(
        format_summary(results, total_score, json_ok, avg_elapsed),
        encoding="utf-8",
    )

    print()
    print(f"Total score   : {total_score:.1f} / {float(len(results)):.1f}")
    print(f"JSON parse OK : {json_ok} / {len(results)}")
    print(f"Mean response : {avg_elapsed:.2f} s")
    print(f"Decision      : {go_decision(total_score, float(len(results)))}")
    print(f"Raw           : {RAW_RESPONSES_PATH}")
    print(f"Summary       : {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
