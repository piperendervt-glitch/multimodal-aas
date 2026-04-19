"""Thin Ollama ``/api/generate`` client for Phase 1.3 topology nodes.

Always uses ``format=json`` so the model's output is a JSON document.
The raw text is preserved alongside the parsed object; ``parsed`` is
``None`` if the response is not a well-formed JSON object containing
0/1 ``sparrow`` and ``bulbul`` keys under ``predictions``. Callers
interpret ``parsed is None`` as a JSON-parse failure and fall back
accordingly.
"""

from __future__ import annotations

import json
import time
from typing import Any

import requests

OLLAMA_BASE = "http://localhost:11434"
TAGS_URL = f"{OLLAMA_BASE}/api/tags"
GENERATE_URL = f"{OLLAMA_BASE}/api/generate"

DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_TIMEOUT = 180
DEFAULT_CONNECT_TIMEOUT = 5


class OllamaUnavailable(RuntimeError):
    pass


class ModelMissing(RuntimeError):
    pass


class LlmClient:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def check_ready(self) -> None:
        try:
            resp = requests.get(TAGS_URL, timeout=DEFAULT_CONNECT_TIMEOUT)
            resp.raise_for_status()
        except requests.ConnectionError as e:
            raise OllamaUnavailable(
                f"Ollama に接続できません ({OLLAMA_BASE})。"
                " Ollama が起動しているか確認してください (ollama serve)。"
            ) from e
        except requests.RequestException as e:
            raise OllamaUnavailable(f"Ollama への接続で予期せぬエラー: {e}") from e
        tag_names = {m.get("name") for m in resp.json().get("models", [])}
        if self.model not in tag_names:
            raise ModelMissing(
                f"モデル {self.model} が見つかりません。"
                f" 次を実行してください: ollama pull {self.model}"
            )

    def generate(self, system: str, prompt_obj: Any) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "system": system,
            "prompt": json.dumps(prompt_obj, ensure_ascii=False),
            "format": "json",
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        t0 = time.perf_counter()
        resp = requests.post(GENERATE_URL, json=payload, timeout=self.timeout)
        elapsed = time.perf_counter() - t0
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        parsed = _parse_prediction(raw)
        return {
            "raw": raw,
            "parsed": parsed,
            "elapsed_sec": round(elapsed, 3),
        }


def _parse_prediction(raw: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    preds = obj.get("predictions")
    if not isinstance(preds, dict):
        return None
    for k in ("sparrow", "bulbul"):
        if preds.get(k) not in (0, 1):
            return None
    return obj
