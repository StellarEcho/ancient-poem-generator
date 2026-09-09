"""随机输入属性测试：任何 topic 都合规。"""

import random

from poem_system.harness import run_harness
from poem_system.validate import validate_poem


def test_offline_fuzz_topics_always_valid() -> None:
    rng = random.Random(20260909)
    alphabet = (
        "月色雪夜孤山云风春江水海城柳星归梦窗ABCdef0123456789"
        " ,.?!、《》\n\t emoji😀" + "〇ㄅ" + "𠀀"
    )
    topics = [
        "",
        " ",
        "   ",
        "!!!",
        "12345",
        "Mars Return",
        "2026年的第一场雪",
    ]
    for _ in range(100):
        length = rng.randint(0, 40)
        topics.append("".join(rng.choice(alphabet) for _ in range(length)))

    for topic in topics:
        result = run_harness(topic, offline=True)
        assert result.source == "fallback"
        assert result.poem["topic"] == topic
        report = validate_poem(result.poem)
        assert report.ok, (repr(topic), report.errors)
