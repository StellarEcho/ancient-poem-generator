"""五言古诗生成系统。

对外唯一承诺：`generate_poem(topic) -> dict` 永远返回合规结果。
"""

__version__ = "0.1.0"

from .api import generate_poem  # noqa: E402

__all__ = ["generate_poem"]
