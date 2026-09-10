"""批量采样模型（当前阶段为 DeepSeek flash），积累返回特性与失败模式。

用法：
    DEEPSEEK_API_KEY=xxx POEM_PROVIDER=deepseek \
    python scripts/run_free_route_experiment.py \
        --repeats 2 --concurrency 3 --timeout 15

输出（默认 artifacts/experiments/free_route_<timestamp>/）：
    runs.jsonl    每次运行的完整记录
    summary.json  聚合指标
    summary.md    人读报告
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import statistics
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from poem_system.harness import HarnessResult, run_harness  # noqa: E402

TOPIC_MATRIX: list[tuple[str, str]] = [
    ("common", "月色"),
    ("common", "梅花"),
    ("common", "竹影"),
    ("common", "荷花"),
    ("common", "湖上"),
    ("common", "江边"),
    ("common", "草原"),
    ("common", "沙漠"),
    ("common", "黄昏"),
    ("common", "清晨"),
    ("common", "相思"),
    ("common", "友情"),
    ("common", "琴声"),
    ("common", "时间"),
    ("common", "宇宙"),
    ("common", "新年"),
    ("common", "端午"),
    ("common", "七夕"),
    ("common", "中秋"),
    ("common", "读书"),
    ("common", "少年"),
    ("common", "冬雪"),
    ("modern", "AI时代的孤独"),
    ("modern", "2026年的第一场雪"),
    ("english", "Mars Return"),
    ("english", "moonlight"),
    ("english", "love letter"),
    ("english", "winter night"),
    ("edge", ""),
    ("edge", "   "),
    ("edge", "！？。，、"),
    ("edge", "1234567890"),
    ("edge", "😀🚀🎉"),
    ("edge", "x" * 500),
    ("edge", "月" * 500),
    ("edge", "\ud800"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=2, help="每个 topic 重复次数")
    parser.add_argument("--concurrency", type=int, default=3, help="并发请求数")
    parser.add_argument("--timeout", type=float, default=15.0, help="单次客户端超时秒数")
    parser.add_argument("--out", type=Path, default=None, help="输出目录")
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="总运行数上限（0 表示不限制，用于快速抽样）",
    )
    return parser.parse_args()


def _failure_bucket(result: HarnessResult) -> str:
    if result.source == "model":
        return "accepted"
    if not result.model_ok:
        error = result.model_error or "UNKNOWN"
        if error == "TIMEOUT":
            return "timeout"
        if error.startswith("HTTP_429"):
            return "http_429"
        if error.startswith("HTTP_"):
            return "http_error"
        if error.startswith("NO_CHOICES"):
            return "no_choices"
        if error.startswith("BAD_JSON"):
            return "bad_json"
        if error == "MISSING_API_KEY":
            return "missing_key"
        return "client_error"
    if not result.parse_ok:
        raw = (result.raw_model_content or "").strip()
        if "User Safety" in raw or len(raw) < 20:
            return "non_poem_output"
        return "parse_fail"
    if not result.local_fix_ok:
        return "local_fix_fail"
    return "final_validation_fail"


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[index]


def _run_one(
    index: int,
    category: str,
    topic: str,
    repeat: int,
    timeout_s: float,
) -> dict:
    result = run_harness(topic, timeout_s=timeout_s)
    usage = result.model_usage or {}
    return {
        "run_id": index,
        "category": category,
        "repeat": repeat,
        "topic": topic,
        "topic_repr": repr(topic),
        "provider": result.provider,
        "source": result.source,
        "failure_bucket": _failure_bucket(result),
        "model_ok": result.model_ok,
        "model_used": result.model_used,
        "model_error": result.model_error,
        "parse_ok": result.parse_ok,
        "local_fix_ok": result.local_fix_ok,
        "local_fix_changed": result.local_fix_changed,
        "harness_latency_ms": round(result.latency_ms, 1),
        "model_latency_ms": (
            round(result.model_latency_ms, 1)
            if result.model_latency_ms is not None
            else None
        ),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "title": result.poem["title"],
        "lines": result.poem["lines"],
        "validation_errors": result.validation.errors,
        "validation_warnings": result.validation.warnings,
        "raw_model_content": (result.raw_model_content or "")[:4000],
    }


def _summarize(records: list[dict], config: dict, started_at: str) -> dict:
    latencies = [r["harness_latency_ms"] for r in records]
    model_latencies = [
        r["model_latency_ms"] for r in records if r["model_latency_ms"] is not None
    ]
    tokens = [r["total_tokens"] for r in records if r["total_tokens"] is not None]
    return {
        "config": config,
        "started_at": started_at,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "total_runs": len(records),
        "sources": dict(Counter(r["source"] for r in records)),
        "providers": dict(Counter(r["provider"] for r in records if r["provider"])),
        "failure_buckets": dict(Counter(r["failure_bucket"] for r in records)),
        "model_used": dict(
            Counter(r["model_used"] for r in records if r["model_used"])
        ),
        "latency_ms": {
            "p50": _percentile(latencies, 0.5),
            "p90": _percentile(latencies, 0.9),
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
            "mean": round(statistics.mean(latencies), 1) if latencies else None,
        },
        "model_latency_ms": {
            "p50": _percentile(model_latencies, 0.5),
            "p90": _percentile(model_latencies, 0.9),
            "mean": (
                round(statistics.mean(model_latencies), 1)
                if model_latencies
                else None
            ),
        },
        "tokens": {
            "runs_with_usage": len(tokens),
            "mean_total": round(statistics.mean(tokens), 1) if tokens else None,
            "max_total": max(tokens) if tokens else None,
        },
        "parse_ok_rate": (
            round(sum(1 for r in records if r["parse_ok"]) / len(records), 4)
            if records
            else None
        ),
        "local_fix_changed_rate": (
            round(
                sum(1 for r in records if r["local_fix_changed"]) / len(records),
                4,
            )
            if records
            else None
        ),
    }


def _write_summary_md(path: Path, summary: dict) -> None:
    lines = [
        "# 模型批量采样报告",
        "",
        f"- provider：{summary['config'].get('provider')}",
        f"- 开始：{summary['started_at']}",
        f"- 结束：{summary['finished_at']}",
        f"- 总运行：{summary['total_runs']}",
        f"- 并发：{summary['config']['concurrency']}，超时：{summary['config']['timeout_s']}s",
        "",
        "## 来源与失败分布",
        "",
        f"- source：{summary['sources']}",
        f"- failure：{summary['failure_buckets']}",
        f"- parse_ok_rate：{summary['parse_ok_rate']}",
        f"- local_fix_changed_rate：{summary['local_fix_changed_rate']}",
        "",
        "## 延迟与 Token",
        "",
        f"- 端到端延迟：{summary['latency_ms']}",
        f"- 模型请求延迟：{summary['model_latency_ms']}",
        f"- Token：{summary['tokens']}",
        "",
        "## 命中的模型",
        "",
    ]
    for model, count in sorted(
        summary["model_used"].items(), key=lambda item: -item[1]
    ):
        lines.append(f"- {model}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if not (
        os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    ):
        print("DEEPSEEK_API_KEY / OPENROUTER_API_KEY 均未设置", file=sys.stderr)
        return 2

    tasks: list[tuple[int, str, str, int]] = []
    index = 0
    for repeat in range(args.repeats):
        for category, topic in TOPIC_MATRIX:
            tasks.append((index, category, topic, repeat))
            index += 1
    if args.max_runs:
        tasks = tasks[: args.max_runs]

    out_dir = args.out or (
        Path("artifacts")
        / "experiments"
        / f"free_route_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now().isoformat(timespec="seconds")
    records: list[dict] = []
    runs_path = out_dir / "runs.jsonl"
    print(f"共 {len(tasks)} 次运行，输出到 {out_dir}", flush=True)

    with runs_path.open("w", encoding="utf-8") as fp:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.concurrency
        ) as executor:
            futures = {
                executor.submit(
                    _run_one,
                    index,
                    category,
                    topic,
                    repeat,
                    args.timeout,
                ): (category, topic, repeat)
                for index, category, topic, repeat in tasks
            }
            completed = 0
            try:
                for future in concurrent.futures.as_completed(futures):
                    record = future.result()
                    records.append(record)
                    fp.write(json.dumps(record, ensure_ascii=True) + "\n")
                    fp.flush()
                    completed += 1
                    print(
                        f"[{completed}/{len(tasks)}] {record['topic_repr']} "
                        f"provider={record['provider']} "
                        f"source={record['source']} "
                        f"bucket={record['failure_bucket']} "
                        f"model={record['model_used']} "
                        f"latency={record['harness_latency_ms']}ms",
                        flush=True,
                    )
            except KeyboardInterrupt:
                for pending in futures:
                    pending.cancel()
                print("已中断，写出部分结果", file=sys.stderr)

    config = {
        "provider": os.environ.get("POEM_PROVIDER") or "auto",
        "repeats": args.repeats,
        "concurrency": args.concurrency,
        "timeout_s": args.timeout,
        "topics": len(TOPIC_MATRIX),
        "finished_runs": len(records),
    }
    summary = _summarize(records, config, started_at)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_summary_md(out_dir / "summary.md", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
