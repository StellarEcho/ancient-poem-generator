"""常用 topic 覆盖与极端输入边界。"""

from __future__ import annotations

import pytest

from poem_system.harness import run_harness
from poem_system.normalize import normalize_topic
from poem_system.validate import is_han, validate_poem

# topic → brief 中必须出现的核心意象
COMMON_TOPICS: dict[str, str] = {
    "月色": "月",
    "梅花": "梅",
    "兰花": "兰",
    "竹影": "竹",
    "菊花": "菊",
    "荷花": "荷",
    "柳岸": "柳",
    "湖上": "湖",
    "江边": "江",
    "山泉": "泉",
    "草原": "草",
    "沙漠": "沙",
    "黄昏": "晚",
    "清晨": "晨",
    "日出": "日",
    "对酒": "酒",
    "相思": "思",
    "友情": "友",
    "琴声": "琴",
    "时间": "年",
    "宇宙": "星",
    "夏夜": "夏",
    "冬雪": "冬",
    "少年": "春",
    "读书": "书",
    "新年": "年",
    "端午": "舟",
    "七夕": "星",
    "中秋": "月",
    "重阳": "秋",
    "清明": "雨",
}

EDGE_TOPICS = [
    "",
    " ",
    "\n\t",
    "\x00",
    "\u200b",
    "ＡＢＣ１２３",
    "！？。，、；：",
    "😀🎉🚀",
    "月色\nMars Return\t2026",
    "x" * 20_000,
    "月" * 5_000,
    "\ud800",
    "\u3007\u3105𠀀",
]


@pytest.mark.parametrize(("topic", "expected"), list(COMMON_TOPICS.items()))
def test_common_topics_map_to_expected_imagery(topic: str, expected: str) -> None:
    brief = normalize_topic(topic)
    assert expected in brief.imagery
    assert brief.title_hints
    assert all(is_han(ch) for hint in brief.title_hints for ch in hint)


@pytest.mark.parametrize("topic", list(COMMON_TOPICS))
def test_common_topics_offline_always_valid(topic: str) -> None:
    result = run_harness(topic, offline=True)
    assert result.poem["topic"] == topic
    assert validate_poem(result.poem).ok is True


@pytest.mark.parametrize("topic", EDGE_TOPICS)
def test_edge_topics_offline_always_valid(topic: str) -> None:
    result = run_harness(topic, offline=True)
    assert result.poem["topic"] == topic
    assert validate_poem(result.poem).ok is True


def test_edge_topics_do_not_crash_normalizer() -> None:
    for topic in EDGE_TOPICS:
        brief = normalize_topic(topic)
        assert brief.imagery
        assert brief.title_hints


def test_common_topics_produce_varied_fallbacks() -> None:
    poems = {
        tuple(run_harness(topic, offline=True).poem["lines"])
        for topic in COMMON_TOPICS
    }
    assert len(poems) >= 12


def test_edge_topics_stable() -> None:
    for topic in EDGE_TOPICS:
        first = run_harness(topic, offline=True).poem
        second = run_harness(topic, offline=True).poem
        assert first == second
