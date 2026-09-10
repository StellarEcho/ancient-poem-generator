"""真实 openrouter/free 抽样（默认跳过，需显式 -m network）。"""

from __future__ import annotations

import os

import pytest

from poem_system.harness import run_harness
from poem_system.validate import validate_poem

pytestmark = pytest.mark.network

_KEY = os.environ.get("OPENROUTER_API_KEY", "")
_NEEDS_KEY = pytest.mark.skipif(
    not _KEY,
    reason="OPENROUTER_API_KEY 未配置",
)


@_NEEDS_KEY
@pytest.mark.parametrize(
    "topic",
    [
        "月色",
        "梅花",
        "湖上",
        "黄昏",
        "相思",
        "新年",
        "星河",
        "Mars Return",
        "2026年的第一场雪",
        "AI时代的孤独",
    ],
)
def test_free_route_smoke(topic: str) -> None:
    result = run_harness(topic)
    assert result.model_calls == 1
    assert result.poem["topic"] == topic
    report = validate_poem(result.poem)
    assert report.ok is True
    assert report.errors == []
    if result.source == "model":
        assert result.model_used is not None
        assert result.model_used.endswith(":free")
    print(
        f"\n[{topic}] source={result.source} model={result.model_used} "
        f"latency_ms={result.latency_ms:.1f}"
    )
