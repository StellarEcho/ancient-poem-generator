"""本地修补测试。"""

from poem_system.local_fix import fix_poem
from poem_system.normalize import normalize_topic
from poem_system.validate import validate_poem


def test_clean_markdown_title() -> None:
    poem = {
        "title": "《月下清辉》",
        "lines": ["清辉照晚窗", "疏影过回廊", "客梦落寒霜", "孤灯夜未央"],
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert fixed["title"] == "月下清辉"
    assert validate_poem(fixed).ok


def test_clean_punctuation_from_lines() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗。", "疏影过回廊，", "客梦落寒霜！", "孤灯夜未央"],
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert validate_poem(fixed).ok


def test_rhyme_fix_via_whitelist_suffix() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗", "疏影过回廊", "客梦落寒江", "孤灯夜未央"],
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert fixed["lines"][2] != "客梦落寒江"


def test_rhyme_fix_falls_back_to_same_theme_line3() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗", "疏影过回廊", "月落乌啼霜", "孤灯夜未央"],
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert validate_poem(fixed).ok


def test_structural_bad_returns_none() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗明月", "疏影过回廊", "客梦落寒霜"],
    }
    assert fix_poem(poem, normalize_topic("月色")) is None
    assert fix_poem(None, normalize_topic("月色")) is None
    assert fix_poem({"title": "月下清辉", "lines": "清辉照晚窗"}, normalize_topic("月色")) is None


def test_duplicate_line_not_blocked() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗"] * 4,
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert validate_poem(fixed).ok


def test_line_with_embedded_english_and_number_is_cleaned() -> None:
    poem = {
        "title": "AI时代的孤独",
        "lines": ["孤灯照夜衣1", "AI竹影入窗扉", "故园归梦稀", "山月共清辉"],
    }
    fixed = fix_poem(poem, normalize_topic("AI时代的孤独"))
    assert fixed is not None
    assert validate_poem(fixed).ok
