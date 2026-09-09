"""确定性兜底测试。"""

from poem_system.api import generate_poem
from poem_system.fallback import fallback_poem
from poem_system.normalize import normalize_topic
from poem_system.validate import validate_poem

TOPICS = [
    "月色",
    "AI时代的孤独",
    "2026年的第一场雪",
    "Mars Return",
    "海",
    "春",
    "送别",
    "远山",
    "",
    "!!!",
    "abc",
]


def test_fallback_always_valid() -> None:
    for topic in TOPICS:
        poem = fallback_poem(normalize_topic(topic))
        report = validate_poem(poem)
        assert report.ok, (topic, report.errors)


def test_api_always_valid_with_original_topic() -> None:
    for topic in TOPICS:
        result = generate_poem(topic)
        assert result["topic"] == topic
        assert validate_poem(result).ok is True


def test_fallback_stable_per_topic() -> None:
    for topic in TOPICS:
        a = generate_poem(topic)
        b = generate_poem(topic)
        assert a["title"] == b["title"]
        assert a["lines"] == b["lines"]


def test_fallback_varies_across_categories() -> None:
    poems = {
        tuple(generate_poem(topic)["lines"])
        for topic in ["月色", "Mars Return", "2026年的第一场雪", "海", "春", "送别"]
    }
    assert len(poems) >= 3
