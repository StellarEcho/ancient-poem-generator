"""原始输出解析测试。"""

from poem_system.parse import parse_candidate


def test_plain_json() -> None:
    raw = '{"title":"月下清辉","lines":["清辉照晚窗","疏影过回廊","客梦落寒霜","孤灯夜未央"]}'
    poem = parse_candidate(raw)
    assert poem is not None
    assert poem["title"] == "月下清辉"
    assert len(poem["lines"]) == 4


def test_json_inside_markdown_and_explanation() -> None:
    raw = (
        "好的，为你生成：\n```json\n"
        '{"title":"雪夜","lines":["归雁入长天","寒灯照客眠","孤舟泊远烟","夜雪落窗前"]}\n'
        "```\n希望你喜欢！"
    )
    poem = parse_candidate(raw)
    assert poem is not None
    assert poem["title"] == "雪夜"


def test_title_with_book_marks_inside_json() -> None:
    raw = '{"title":"《月下清辉》","lines":["清辉照晚窗","疏影过回廊","客梦落寒霜","孤灯夜未央"]}'
    poem = parse_candidate(raw)
    assert poem is not None
    assert poem["title"] == "《月下清辉》"  # local_fix 负责清理


def test_json_lines_as_string_still_returns_dict() -> None:
    raw = '{"title":"月","lines":"清辉照晚窗"}'
    poem = parse_candidate(raw)
    assert poem is not None
    assert isinstance(poem["lines"], str)


def test_prose_line_extraction_with_markdown_bold_title() -> None:
    raw = "**雪夜**\n归雁入长天\n寒灯照客眠\n孤舟泊远烟\n夜雪落窗前"
    poem = parse_candidate(raw)
    assert poem is not None
    assert poem["title"] == "雪夜"
    assert poem["lines"] == [
        "归雁入长天",
        "寒灯照客眠",
        "孤舟泊远烟",
        "夜雪落窗前",
    ]


def test_empty_and_nonsense() -> None:
    assert parse_candidate(None) is None
    assert parse_candidate("") is None
    assert parse_candidate("   ") is None
    assert parse_candidate("这是一段没有格式的散文") is None
    assert parse_candidate("[]") is None


def test_two_megabyte_prose_is_handled() -> None:
    huge = "x" * 2_000_000
    assert parse_candidate(huge) is None


def test_braces_inside_json_string() -> None:
    raw = (
        '{"title":"月{夜}","lines":["清辉照晚窗","疏影过回廊",'
        '"客梦落寒霜","孤灯夜未央"]}'
    )
    poem = parse_candidate(raw)
    assert poem is not None
    assert poem["title"] == "月{夜}"


def test_trailing_comma_json_recovers_lines() -> None:
    raw = (
        '{"title":"月夜","lines":["清辉照晚窗","疏影过回廊",'
        '"客梦落寒霜","孤灯夜未央",],}'
    )
    poem = parse_candidate(raw)
    assert poem is not None
    assert poem["lines"] == [
        "清辉照晚窗",
        "疏影过回廊",
        "客梦落寒霜",
        "孤灯夜未央",
    ]


def test_lines_object_is_parseable_but_invalid_candidate() -> None:
    raw = '{"title":"月夜","lines":{"1":"清辉照晚窗"}}'
    poem = parse_candidate(raw)
    assert poem is not None
    assert isinstance(poem["lines"], dict)
