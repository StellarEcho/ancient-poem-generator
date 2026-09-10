"""ModelClient：缺 Key、硬超时、错误不泄露 Key。"""

from __future__ import annotations

import json
import time

from poem_system import client as client_module
from poem_system.client import (
    DEEPSEEK_MODEL,
    DeepSeekClient,
    ModelClient,
    RawModelResult,
    create_client,
)


def test_missing_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = ModelClient(api_key="").generate([])
    assert result.ok is False
    assert result.error == "MISSING_API_KEY"


def test_hard_watchdog_timeout() -> None:
    class SlowClient(ModelClient):
        def _request(self, api_key: str, messages: list[dict]) -> RawModelResult:
            del api_key, messages
            time.sleep(0.8)
            return RawModelResult(ok=True, content="迟到的结果")

    result = SlowClient(api_key="test-key", timeout_s=0.01).generate([])
    assert result.ok is False
    assert result.error == "TIMEOUT"


def test_request_result_passthrough() -> None:
    class FastClient(ModelClient):
        def _request(self, api_key: str, messages: list[dict]) -> RawModelResult:
            del api_key, messages
            return RawModelResult(ok=True, content="ok", model="fake:free")

    result = FastClient(api_key="test-key").generate([])
    assert result.ok is True
    assert result.content == "ok"
    assert result.model == "fake:free"


def test_error_never_contains_key() -> None:
    class BoomClient(ModelClient):
        def _request(self, api_key: str, messages: list[dict]) -> RawModelResult:
            del api_key, messages
            raise RuntimeError("ssl read failed")

    result = BoomClient(api_key="sk-secret-value").generate([])
    assert result.ok is False
    assert "sk-secret-value" not in (result.error or "")


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def read(self, limit: int = -1) -> bytes:
        del limit
        return self.payload


def test_no_choices_is_classified(monkeypatch) -> None:
    payload = json.dumps({"id": "x", "model": "foo:free"}).encode("utf-8")
    monkeypatch.setattr(
        client_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(payload),
    )
    result = ModelClient(api_key="test-key")._request("test-key", [])
    assert result.ok is False
    assert (result.error or "").startswith("NO_CHOICES")
    assert "test-key" not in (result.error or "")


def test_bad_json_is_classified(monkeypatch) -> None:
    monkeypatch.setattr(
        client_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"not-json"),
    )
    result = ModelClient(api_key="test-key")._request("test-key", [])
    assert result.ok is False
    assert (result.error or "").startswith("BAD_JSON")


def test_deepseek_uses_flash_and_disables_thinking(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_THINKING", raising=False)
    payload = DeepSeekClient(api_key="test-key")._build_payload(
        [{"role": "user", "content": "hi"}]
    )
    assert payload["model"] == DEEPSEEK_MODEL == "deepseek-flash"
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["max_tokens"] > 0


def test_deepseek_thinking_can_be_left_auto(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_THINKING", "auto")
    payload = DeepSeekClient(api_key="test-key")._build_payload([])
    assert "thinking" not in payload


def test_create_client_prefers_deepseek(monkeypatch) -> None:
    monkeypatch.setenv("POEM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = create_client()
    assert isinstance(client, DeepSeekClient)
    assert client.provider_name == "deepseek"


def test_create_client_returns_none_without_keys(monkeypatch) -> None:
    monkeypatch.delenv("POEM_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert create_client() is None


def test_create_client_defaults_to_openrouter_when_both_keys_exist(monkeypatch) -> None:
    monkeypatch.delenv("POEM_PROVIDER", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = create_client()
    assert isinstance(client, ModelClient)
    assert client.provider_name == "openrouter"
