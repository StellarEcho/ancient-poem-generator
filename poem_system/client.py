"""模型客户端：DeepSeek flash（当前测试）与 OpenRouter free（保留）。

两个客户端共享同一约束：普通 chat completions、无 JSON Schema、
不重试、硬超时看门狗、任何异常由 Harness 统一兜底。
"""

from __future__ import annotations

import json
import os
import queue
import ssl
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

try:
    import certifi
except ImportError:  # 无 certifi 时退回 Python 默认证书链
    certifi = None

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openrouter/free"
OPENROUTER_KEY_ENV = "OPENROUTER_API_KEY"

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"  # 当前阶段的唯一模型
DEEPSEEK_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_THINKING_ENV = "DEEPSEEK_THINKING"
DEEPSEEK_MAX_TOKENS_ENV = "DEEPSEEK_MAX_TOKENS"
DEFAULT_DEEPSEEK_MAX_TOKENS = 1024

PROVIDER_ENV = "POEM_PROVIDER"


def _ssl_context() -> ssl.SSLContext:
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


@dataclass
class RawModelResult:
    ok: bool
    content: str | None = None
    model: str | None = None
    usage: dict | None = None
    latency_ms: float | None = None
    error: str | None = None


def _parse_chat_response(data: dict, latency_ms: float) -> RawModelResult:
    if "choices" not in data or not data.get("choices"):
        snippet = json.dumps(data, ensure_ascii=True)[:300]
        return RawModelResult(
            ok=False,
            model=data.get("model"),
            usage=data.get("usage"),
            latency_ms=latency_ms,
            error=f"NO_CHOICES: {snippet}",
        )
    message = data["choices"][0].get("message") or {}
    content = message.get("content")
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


class HTTPModelClient:
    """提供统一的硬超时看门狗；子类只需实现 `_request`。"""

    provider_name = "generic"
    key_env = ""

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
            api_key = os.environ.get(self.key_env, "")
        if not api_key:
            return RawModelResult(ok=False, error="MISSING_API_KEY")

        # urlopen 的 timeout 偶发兜不住挂死的 SSL read，这里再加一层
        # 硬看门狗：超时立刻返回，由 Harness 走确定性兜底。
        results: queue.Queue[RawModelResult] = queue.Queue(maxsize=1)

        def worker() -> None:
            try:
                results.put(self._request(api_key, messages))
            except Exception as exc:
                results.put(
                    RawModelResult(ok=False, error=f"{type(exc).__name__}: {exc}")
                )

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            return results.get(timeout=self.timeout_s + 0.5)
        except queue.Empty:
            return RawModelResult(ok=False, error="TIMEOUT")

    def _request(self, api_key: str, messages: list[dict]) -> RawModelResult:
        raise NotImplementedError

    def _post(self, url: str, payload: dict, api_key: str) -> RawModelResult:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_s,
                context=_ssl_context(),
            ) as response:
                raw = response.read(self.max_response_bytes + 1)
            latency_ms = (time.perf_counter() - started) * 1000
            if len(raw) > self.max_response_bytes:
                return RawModelResult(
                    ok=False,
                    latency_ms=latency_ms,
                    error="LARGE_RESPONSE",
                )
            try:
                data = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                return RawModelResult(
                    ok=False,
                    latency_ms=latency_ms,
                    error=f"BAD_JSON: {type(exc).__name__}: {exc}",
                )
            return _parse_chat_response(data, latency_ms)
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
        except Exception as exc:  # 超时/SSL/网络异常统一收口
            latency_ms = (time.perf_counter() - started) * 1000
            return RawModelResult(
                ok=False,
                latency_ms=latency_ms,
                error=f"{type(exc).__name__}: {exc}",
            )


class ModelClient(HTTPModelClient):
    """OpenRouter `openrouter/free` 客户端（保留给原验收路径）。"""

    provider_name = "openrouter"
    key_env = OPENROUTER_KEY_ENV

    def _request(self, api_key: str, messages: list[dict]) -> RawModelResult:
        payload = {"model": OPENROUTER_MODEL, "messages": messages}
        return self._post(OPENROUTER_URL, payload, api_key)


class DeepSeekClient(HTTPModelClient):
    """DeepSeek flash 客户端：当前测试阶段的唯一模型。

    `DEEPSEEK_THINKING=disabled`（默认）时请求关闭思考模式；
    若服务端不接受该参数会返回 HTTP 400，由 Harness 走兜底。
    """

    provider_name = "deepseek"
    key_env = DEEPSEEK_KEY_ENV

    def __init__(
        self,
        api_key: str | None = None,
        timeout_s: float = 15.0,
        max_response_bytes: int = 2_000_000,
        base_url: str | None = None,
        thinking: str | None = None,
    ) -> None:
        super().__init__(api_key, timeout_s, max_response_bytes)
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL).rstrip("/")
        self.thinking = thinking

    def _build_payload(self, messages: list[dict]) -> dict:
        try:
            max_tokens = int(
                os.environ.get(DEEPSEEK_MAX_TOKENS_ENV, DEFAULT_DEEPSEEK_MAX_TOKENS)
            )
        except ValueError:
            max_tokens = DEFAULT_DEEPSEEK_MAX_TOKENS
        payload: dict = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        mode = (self.thinking or os.environ.get(DEEPSEEK_THINKING_ENV, "disabled")).lower()
        if mode in {"disabled", "off", "none", "false", "0"}:
            payload["thinking"] = {"type": "disabled"}
        return payload

    def _request(self, api_key: str, messages: list[dict]) -> RawModelResult:
        return self._post(
            f"{self.base_url}/chat/completions",
            self._build_payload(messages),
            api_key,
        )


def create_client(timeout_s: float = 15.0) -> HTTPModelClient | None:
    """按环境选择 provider。

    显式 `POEM_PROVIDER` 优先；否则默认 OpenRouter（提交验收路径），
    没有 OpenRouter Key 时才回落到 DeepSeek。
    """
    provider = (os.environ.get(PROVIDER_ENV) or "").strip().lower()
    if not provider:
        if os.environ.get(OPENROUTER_KEY_ENV):
            provider = "openrouter"
        elif os.environ.get(DEEPSEEK_KEY_ENV):
            provider = "deepseek"
        else:
            return None
    if provider == "deepseek":
        return DeepSeekClient(timeout_s=timeout_s)
    if provider == "openrouter":
        return ModelClient(timeout_s=timeout_s)
    return None
