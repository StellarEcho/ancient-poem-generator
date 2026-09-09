"""假客户端故障矩阵：任何路径最终都合规。"""

from poem_system.client import RawModelResult
from poem_system.harness import run_harness
from poem_system.validate import DUP_LINE, validate_poem

PERFECT = {
    "title": "月下清辉",
    "lines": ["清辉照晚窗", "疏影过回廊", "客梦落寒霜", "孤灯夜未央"],
}
PERFECT_JSON = (
    '{"title":"月下清辉","lines":["清辉照晚窗","疏影过回廊",'
    '"客梦落寒霜","孤灯夜未央"]}'
)


class FakeClient:
    def __init__(self, results: list[RawModelResult]) -> None:
        self.results = list(results)
        self.calls = 0

    def generate(self, messages: list[dict]) -> RawModelResult:
        del messages
        self.calls += 1
        if not self.results:
            return RawModelResult(ok=False, error="NO_RESULT")
        return self.results.pop(0)


def _ok(content: str) -> RawModelResult:
    return RawModelResult(ok=True, content=content)


def _check_case(client: FakeClient, topic: str = "月色") -> None:
    result = run_harness(topic, model_client=client)
    assert client.calls == 1
    assert result.poem["topic"] == topic
    assert validate_poem(result.poem).ok is True


def test_perfect_json_uses_model() -> None:
    client = FakeClient([_ok(PERFECT_JSON)])
    result = run_harness("月色", model_client=client)
    assert result.source == "model"
    assert result.poem["lines"] == PERFECT["lines"]


def test_markdown_wrapped_json() -> None:
    raw = "```json\n" + PERFECT_JSON + "\n```"
    _check_case(FakeClient([_ok(raw)]))


def test_model_topic_rewrite_is_overwritten() -> None:
    raw = (
        '{"topic":"雅题","title":"月下清辉","lines":["清辉照晚窗",'
        '"疏影过回廊","客梦落寒霜","孤灯夜未央"]}'
    )
    client = FakeClient([_ok(raw)])
    result = run_harness("Mars Return", model_client=client)
    assert result.poem["topic"] == "Mars Return"


def test_rhyme_error_fixed_locally() -> None:
    raw = (
        '{"title":"月下清辉","lines":["清辉照晚窗","疏影过回廊",'
        '"客梦落寒江","孤灯夜未央"]}'
    )
    client = FakeClient([_ok(raw)])
    result = run_harness("月色", model_client=client)
    assert result.source == "model"
    assert validate_poem(result.poem).ok is True


def test_duplicate_line_still_accepted_as_model_source() -> None:
    raw = '{"title":"月下清辉","lines":["清辉照晚窗"] * 4}'
    # 上面不是合法 JSON，改用显式字符串。
    raw = (
        '{"title":"月下清辉","lines":["清辉照晚窗","清辉照晚窗",'
        '"清辉照晚窗","清辉照晚窗"]}'
    )
    client = FakeClient([_ok(raw)])
    result = run_harness("月色", model_client=client)
    assert result.source == "model"
    assert result.validation.ok is True
    assert DUP_LINE in result.validation.warnings


def test_invalid_seven_char_lines_fall_back() -> None:
    raw = (
        '{"title":"月下清辉","lines":["清辉照晚窗明月","疏影过回廊",'
        '"客梦落寒霜","孤灯夜未央"]}'
    )
    client = FakeClient([_ok(raw)])
    result = run_harness("月色", model_client=client)
    assert result.source == "fallback"
    assert validate_poem(result.poem).ok is True


def test_empty_content_falls_back() -> None:
    _check_case(FakeClient([RawModelResult(ok=True, content="")]))
    _check_case(FakeClient([RawModelResult(ok=False, error="HTTP_429")]))
    _check_case(FakeClient([RawModelResult(ok=False, error="TIMEOUT")]))


def test_client_exception_falls_back() -> None:
    class ExplodingClient:
        def generate(self, messages: list[dict]) -> RawModelResult:
            del messages
            raise ConnectionError("boom")

    result = run_harness("月色", model_client=ExplodingClient())
    assert result.source == "fallback"
    assert validate_poem(result.poem).ok is True


def test_offline_never_calls_model() -> None:
    client = FakeClient([])
    result = run_harness("月色", offline=True, model_client=client)
    assert client.calls == 0
    assert result.source == "fallback"
    assert validate_poem(result.poem).ok is True
