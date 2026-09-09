"""对外接口。"""

from __future__ import annotations

from .fallback import basic_fallback_poem


def generate_poem(topic: str) -> dict:
    """根据 topic 生成一首四句五言古诗。

    M0 阶段：整条流程走确定性兜底，保证接口可运行；
    M3 开始接入“一次 LLM 生成 + 本地修补 + 兜底收口”。
    """
    if not isinstance(topic, str):
        raise TypeError("topic 必须是字符串")

    poem = basic_fallback_poem(topic)
    return {
        "topic": topic,
        "title": poem["title"],  # type: ignore[assignment]
        "lines": poem["lines"],  # type: ignore[assignment]
    }
