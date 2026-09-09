"""OpenRouter free 模型客户端（唯一模型，无 JSON Schema）。"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openrouter/free"
KEY_ENV = "OPENROUTER_API_KEY"


@dataclass
class RawModelResult:
    ok: bool
    content: str | None = None
    model: str | None = None
    usage: dict | None = None
    latency_ms: float | None = None
    error: str | None = None


class ModelClient:
    """一次调用一次机会；任何异常由 Harness 统一兜底，不在客户端重试。"""

    def __init__(
        self,
        api_key: str | None = None,
        timeout_s: float = 15.0,
        max_response_bytes: int = 2_000_000,
    ) -> None:
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.max_response_bytes = max_response_bytes

    def generate(self, messages: list[dict]) -> RawModelResult:
        api_key = self.api_key
        if api_key is None:
            api_key = os.environ.get(KEY_ENV, "")
        if not api_key:
            return RawModelResult(ok=False, error="MISSING_API_KEY")

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
        }
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                raw = response.read(self.max_response_bytes + 1)
            latency_ms = (time.perf_counter() - started) * 1000
            if len(raw) > self.max_response_bytes:
                return RawModelResult(
                    ok=False,
                    latency_ms=latency_ms,
                    error="LARGE_RESPONSE",
                )
            data = json.loads(raw.decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                return RawModelResult(
                    ok=False,
                    model=data.get("model"),
                    usage=data.get("usage"),
                    latency_ms=latency_ms,
                    error="EMPTY_CONTENT",
                )
            return RawModelResult(
                ok=True,
                content=content,
                model=data.get("model"),
                usage=data.get("usage"),
                latency_ms=latency_ms,
            )
        except urllib.error.HTTPError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            detail = exc.read(self.max_response_bytes).decode(
                "utf-8", errors="replace"
            )[:500]
            return RawModelResult(
                ok=False,
                latency_ms=latency_ms,
                error=f"HTTP_{exc.code}: {detail}",
            )
        except Exception as exc:  # 超时/SSL/JSON/网络异常统一收口
            latency_ms = (time.perf_counter() - started) * 1000
            return RawModelResult(
                ok=False,
                latency_ms=latency_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
