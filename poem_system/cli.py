"""命令行手测入口。

用法：
    python -m poem_system.cli 月色
    python -m poem_system.cli --topics 月色 "Mars Return"
    python -m poem_system.cli --offline 月色
    python -m poem_system.cli --verbose 月色
"""

from __future__ import annotations

import argparse
import json
import sys

from .api import generate_poem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="poem_system.cli")
    parser.add_argument("topic", nargs="?", help="单个主题")
    parser.add_argument("--topics", nargs="+", help="多个主题")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="强制走确定性兜底，不调用模型",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印校验与调试细节（M1 起生效）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.topics:
        topics = args.topics
    elif args.topic is not None:
        topics = [args.topic]
    else:
        print("请提供主题：python -m poem_system.cli 月色", file=sys.stderr)
        return 2

    for topic in topics:
        result = generate_poem(topic)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
