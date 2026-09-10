"""确定性兜底测试。"""

from poem_system.api import generate_poem
from poem_system.fallback import fallback_line3_candidates, fallback_poem, topic_seed
from poem_system.rhyme import rhyme_key
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


def test_topic_seed_is_stable_and_distinct() -> None:
    assert topic_seed("月色") == topic_seed("月色")
    assert topic_seed("Mars Return") == topic_seed("Mars Return")
    assert topic_seed("月色") != topic_seed("Mars Return")


def test_fallback_line3_candidates_match_target_rhyme() -> None:
    brief = normalize_topic("月色")
    candidates = fallback_line3_candidates(brief, "uang")
    assert candidates
    assert all(rhyme_key(line[-1]) == "uang" for line in candidates)
    assert candidates[0] == "客梦落寒霜"
