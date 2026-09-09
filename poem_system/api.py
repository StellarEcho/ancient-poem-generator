"""对外接口。"""

from __future__ import annotations

import os

from .harness import run_harness


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def generate_poem(topic: str) -> dict:
    """根据 topic 生成一首四句五言古诗。

    保持题目给定的单参数签名。内部遵循：
    - 无 OPENROUTER_API_KEY、POEM_OFFLINE=1 或客户端异常 → 同一兜底；
    - 不重试、不暴露调试参数。
    """
    if not isinstance(topic, str):
        raise TypeError("topic 必须是字符串")
    return run_harness(
        topic,
        offline=_env_flag("POEM_OFFLINE"),
        debug=_env_flag("POEM_DEBUG"),
    ).poem
