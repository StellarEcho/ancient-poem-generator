"""韵脚固定测试向量。"""

import pytest

from poem_system.rhyme import rhyme_key, same_rhyme


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("窗", "霜"),  # uang / uang
        ("光", "窗"),  # uang / uang
    ],
)
def test_rhymes(a: str, b: str) -> None:
    assert same_rhyme(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("窗", "灯"),  # uang vs eng
        ("光", "廊"),  # uang vs ang
        ("天", "安"),  # ian vs an
        ("秋", "愁"),  # iou vs ou
        ("月", "色"),  # ve vs e
    ],
)
def test_not_rhymes(a: str, b: str) -> None:
    assert not same_rhyme(a, b)


@pytest.mark.parametrize(
    ("ch", "expected"),
    [
        ("衣", "i"),
        ("乌", "u"),
        ("迂", "v"),
        ("威", "uei"),
        ("忧", "iou"),
    ],
)
def test_strict_finals(ch: str, expected: str) -> None:
    assert rhyme_key(ch) == expected


@pytest.mark.parametrize("bad", ["", "ab", "窗窗"])
def test_rhyme_key_rejects_non_single_char(bad: str) -> None:
    with pytest.raises(ValueError):
        rhyme_key(bad)


def test_rhyme_key_rejects_non_han() -> None:
    with pytest.raises(ValueError):
        rhyme_key("a")
