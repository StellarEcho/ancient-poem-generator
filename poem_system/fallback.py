"""确定性兜底生成器（M0 最小版本，M2 替换为完整实现）。"""

from __future__ import annotations

_GENERIC_POEM: dict[str, object] = {
    "title": "清秋夜",
    "lines": ["清辉照晚窗", "疏影过回廊", "客梦落寒霜", "孤灯夜未央"],
}


def basic_fallback_poem(topic: str) -> dict[str, object]:
    """返回一条结构合法的兜底诗；当前不区分 topic，仅保证可运行。"""
    del topic  # M2 会基于 topic 选择意象；M0 阶段不依赖输入。
    return {
        "title": _GENERIC_POEM["title"],
        "lines": list(_GENERIC_POEM["lines"]),  # type: ignore[arg-type]
    }
