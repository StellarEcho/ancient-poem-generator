"""校验器测试向量。"""

import pytest

from poem_system.validate import (
    DUP_LINE,
    EMPTY,
    LINE_COUNT,
    LINE_LEN,
    NON_HAN,
    RHYME,
    TITLE_LEN,
    WRONG_TYPE,
    only_han,
    validate_poem,
)

VALID = {
    "title": "月下清辉",
    "lines": ["清辉照晚窗", "疏影过回廊", "客梦落寒霜", "孤灯夜未央"],
}


def test_valid_poem() -> None:
    report = validate_poem(VALID)
    assert report.ok is True
    assert report.errors == []


def test_non_dict() -> None:
    assert validate_poem(None).errors == [WRONG_TYPE]
    assert validate_poem("月色").errors == [WRONG_TYPE]


def test_missing_or_wrong_types() -> None:
    assert WRONG_TYPE in validate_poem({"lines": []}).errors
    assert WRONG_TYPE in validate_poem({"title": 3, "lines": []}).errors
    assert WRONG_TYPE in validate_poem({"title": "月下清辉", "lines": "清辉"}).errors


@pytest.mark.parametrize(
    "title",
    [
        "月",
        "明月清风夜未央明灯",  # 9 字
        "明",
    ],
)
def test_title_length_errors(title: str) -> None:
    poem = dict(VALID, title=title)
    errors = validate_poem(poem).errors
    if len(title) == 2:
        assert TITLE_LEN not in errors
    else:
        assert TITLE_LEN in errors


@pytest.mark.parametrize("count", [3, 5, 0])
def test_line_count(count: int) -> None:
    lines = list(VALID["lines"])
    while len(lines) < count:
        lines.append(lines[-1])
    poem = dict(VALID, lines=lines[:count])
    assert LINE_COUNT in validate_poem(poem).errors


@pytest.mark.parametrize("line", ["清辉照晚", "清辉照晚窗明", "月", ""])
def test_line_length(line: str) -> None:
    poem = dict(VALID, lines=[line, "疏影过回廊", "客梦落寒霜", "孤灯夜未央"])
    errors = validate_poem(poem).errors
    if line == "":
        assert EMPTY in errors
        assert LINE_LEN not in errors
    else:
        assert LINE_LEN in errors


@pytest.mark.parametrize(
    "text",
    [
        "清辉照晚a",
        "清辉照晚1",
        "清辉照晚 ",
        "清辉照晚，",
        "清辉照晚。",
        "清辉　照晚",  # 全角空格
        "清辉照晚〇",
        "清辉照晚ㄅ",  # 注音符号
        "清辉照\uD841\uDF00",  # 扩展区生僻字（代理对）
    ],
)
def test_non_han_rejected(text: str) -> None:
    poem = dict(VALID, lines=[text, "疏影过回廊", "客梦落寒霜", "孤灯夜未央"])
    assert NON_HAN in validate_poem(poem).errors


def test_only_han() -> None:
    assert only_han("清辉照晚窗") is True
    assert only_han("清辉,照晚窗") is False
    assert only_han("abc") is False
    assert only_han("") is True


def test_rhyme_error() -> None:
    poem = dict(VALID, lines=["清辉照晚窗", "疏影过回廊", "客梦落寒江", "孤灯夜未央"])
    assert RHYME in validate_poem(poem).errors


def test_duplicate_line_error() -> None:
    poem = dict(VALID, lines=["清辉照晚窗"] * 4)
    assert DUP_LINE in validate_poem(poem).errors
