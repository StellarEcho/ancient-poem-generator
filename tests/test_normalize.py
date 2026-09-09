"""输入规范化测试。"""

from poem_system.normalize import normalize_topic
from poem_system.validate import is_han


def _all_han(values: list[str]) -> bool:
    return all(len(item) >= 1 and all(is_han(ch) for ch in item) for item in values)


def test_moon() -> None:
    brief = normalize_topic("月色")
    assert "月" in brief.imagery
    assert "夜" in brief.imagery
    assert brief.title_hints
    assert _all_han(brief.imagery)
    assert _all_han(brief.title_hints)


def test_mars_return() -> None:
    brief = normalize_topic("Mars Return")
    assert "星" in brief.imagery or "归" in brief.imagery
    assert any("mars" == b or "return" == b for b in brief.banned)
    assert brief.raw == "Mars Return"


def test_snow_year() -> None:
    brief = normalize_topic("2026年的第一场雪")
    assert "雪" in brief.imagery
    assert "寒" in brief.imagery
    assert "2026" in brief.banned


def test_ai_loneliness() -> None:
    brief = normalize_topic("AI时代的孤独")
    assert "孤" in brief.imagery
    assert "ai" in brief.banned


def test_empty_and_punctuation_fall_back_to_default() -> None:
    for topic in ["", "   ", "！！！", "12345"]:
        brief = normalize_topic(topic)
        assert brief.imagery
        assert brief.title_hints


def test_normalize_is_deterministic() -> None:
    a = normalize_topic("2026年的第一场雪")
    b = normalize_topic("2026年的第一场雪")
    assert a == b
    assert a.imagery == b.imagery
