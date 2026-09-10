"""批量测试 generate_poem 的示例脚本。

用法：
    python scripts/batch_generate.py 月色 "Mars Return" "AI时代的孤独"
    python scripts/batch_generate.py --topics-file topics.txt --output results.jsonl
    POEM_PROVIDER=deepseek python scripts/batch_generate.py --repeat 2 月色 梅花
    python scripts/batch_generate.py --offline --topics-file topics.txt

每个 topic 调一次 `generate_poem(topic)`，本地重新校验，逐行输出 JSON；
`--output` 会写 JSONL（ensure_ascii=True，兼容孤立代理字符等极端输入）。
退出码 0 表示全部合规，1 表示有不合规结果。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from poem_system import generate_poem  # noqa: E402
from poem_system.validate import validate_poem  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量调用 generate_poem 并校验结果")
    parser.add_argument("topics", nargs="*", help="一个或多个 topic")
    parser.add_argument(
        "--topics-file",
        type=Path,
        help="从文本文件读取 topic（每行一个）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="可选：把每次运行的完整结果写成 JSONL",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="每个 topic 重复次数（默认 1）",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="强制本地兜底，不调用任何模型",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="只打印汇总，不逐条打印 JSON",
    )
    return parser.parse_args()


def _load_topics(args: argparse.Namespace) -> list[str]:
    topics = list(args.topics)
    if args.topics_file is not None:
        lines = args.topics_file.read_text(encoding="utf-8").splitlines()
        topics.extend(line for line in lines if line.strip())
    return topics


def main() -> int:
    args = parse_args()
    topics = _load_topics(args)
    if not topics:
        print("请提供 topic 或 --topics-file", file=sys.stderr)
        return 2
    if args.repeat < 1:
        print("--repeat 必须 >= 1", file=sys.stderr)
        return 2
    if args.offline:
        os.environ["POEM_OFFLINE"] = "1"

    started = time.perf_counter()
    records: list[dict] = []
    valid_count = 0

    output_fp = args.output.open("w", encoding="utf-8") if args.output else None
    try:
        for topic in topics:
            for repeat_index in range(args.repeat):
                poem = generate_poem(topic)
                report = validate_poem(poem)
                record = {
                    "topic": topic,
                    "repeat": repeat_index,
                    "poem": poem,
                    "valid": report.ok,
                    "errors": report.errors,
                    "warnings": report.warnings,
                }
                records.append(record)
                if report.ok:
                    valid_count += 1
                if output_fp is not None:
                    output_fp.write(json.dumps(record, ensure_ascii=True) + "\n")
                if not args.quiet:
                    try:
                        print(json.dumps(poem, ensure_ascii=False))
                    except UnicodeEncodeError:
                        print(json.dumps(poem, ensure_ascii=True))
    finally:
        if output_fp is not None:
            output_fp.close()

    elapsed = time.perf_counter() - started
    total = len(records)
    print(
        f"# total={total} valid={valid_count} invalid={total - valid_count} "
        f"topics={len(topics)} provider={os.environ.get('POEM_PROVIDER', 'auto')} "
        f"offline={bool(args.offline)} elapsed={elapsed:.2f}s",
        file=sys.stderr,
    )
    if args.output is not None:
        print(f"# results written to {args.output}", file=sys.stderr)
    return 0 if valid_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
