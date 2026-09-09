"""M0：接口与 stub 冒烟测试。"""

from poem_system.api import generate_poem


def test_generate_poem_returns_stable_poem() -> None:
    poem = generate_poem("月色")

    assert set(poem) == {"topic", "title", "lines"}
    assert poem["topic"] == "月色"
    assert 2 <= len(poem["title"]) <= 8
    assert len(poem["lines"]) == 4
    assert all(len(line) == 5 for line in poem["lines"])
