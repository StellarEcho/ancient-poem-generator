"""单线 Harness：生成 → 解析 → 本地修 → 终态断言 → 兜底收口。"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from .client import RawModelResult, create_client
from .debug_log import DebugRecorder
from .fallback import fallback_poem, topic_seed
from .local_fix import fix_poem
from .normalize import PoemBrief, normalize_topic
from .parse import parse_candidate
from .validate import ValidationReport, validate_poem

_SYSTEM_PROMPT = """你是古诗生成器，只输出一个 JSON 对象，不要解释。
格式：{"title":"二至八个汉字","lines":["五字","五字","五字","五字"]}
硬性要求：
- title 2-8 个汉字；lines 恰好四句，每句恰好五个汉字
- 全是汉字，无标点、空格、数字、英文
- 第1句和第3句最后一个字的韵母相同
不要使用 JSON Schema；不要输出 markdown 代码块。"""

_FEW_SHOT_EXAMPLES: list[tuple[frozenset[str], dict]] = [
    (
        frozenset({"孤", "夜", "灯", "客"}),
        {
            "title": "寒夜客",
            "lines": ["孤灯照夜衣", "竹影入窗扉", "故园归梦稀", "山月共清辉"],
        },
    ),
    (
        frozenset({"春", "花", "风", "燕"}),
        {
            "title": "春池",
            "lines": ["春水绿池塘", "燕子绕雕梁", "花影入回廊", "日暖醉花香"],
        },
    ),
    (
        frozenset({"送", "别", "舟", "柳"}),
        {
            "title": "送别",
            "lines": ["折柳赠行舟", "烟波送客愁", "离歌动远洲", "孤影望重楼"],
        },
    ),
]


def _pick_example(brief: PoemBrief) -> dict:
    imagery = set(brief.imagery)

    def overlap(example: tuple[frozenset[str], dict]) -> tuple[int, int]:
        tags, _ = example
        return (len(tags & imagery), topic_seed(brief.raw))

    return min(_FEW_SHOT_EXAMPLES, key=overlap)[1]


def build_messages(brief: PoemBrief) -> list[dict]:
    example = _pick_example(brief)
    example_json = (
        '{"title":"%s","lines":["%s","%s","%s","%s"]}'
        % (example["title"], *example["lines"])
    )
    lines = [
        f"主题意象：{' '.join(brief.imagery)}",
        f"情绪：{brief.mood}",
        f"示例（仅演示格式，禁止照抄内容）：{example_json}",
    ]
    if brief.banned:
        lines.append(f"禁止在诗中出现：{'、'.join(brief.banned)}")
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


@dataclass
class HarnessResult:
    poem: dict
    source: str
    model_calls: int
    latency_ms: float
    model_used: str | None = None
    provider: str | None = None
    raw_model_content: str | None = None
    model_error: str | None = None
    model_usage: dict | None = None
    model_latency_ms: float | None = None
    model_ok: bool = False
    parse_ok: bool = False
    local_fix_ok: bool = False
    local_fix_changed: bool = False
    validation: ValidationReport = field(default_factory=lambda: ValidationReport(True, []))


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def run_harness(
    topic: str,
    *,
    offline: bool = False,
    model_client: object | None = None,
    timeout_s: float = 15.0,
    debug: bool = False,
) -> HarnessResult:
    """核心单线流程。对外 generate_poem 不暴露这些内部开关。"""
    started = time.perf_counter()
    brief = normalize_topic(topic)
    poem: dict | None = None
    source = "fallback"
    model_calls = 0
    raw_result: RawModelResult | None = None
    provider: str | None = None
    parse_ok = False
    local_fix_ok = False
    local_fix_changed = False

    if not offline:
        client: object | None = model_client
        if client is None:
            client = create_client(timeout_s=timeout_s)
        if client is not None:
            provider = getattr(client, "provider_name", None)
            model_calls = 1
            try:
                raw_result = client.generate(build_messages(brief))  # type: ignore[attr-defined]
            except Exception as exc:
                raw_result = RawModelResult(ok=False, error=f"{type(exc).__name__}: {exc}")
            if raw_result.ok:
                parsed = parse_candidate(raw_result.content)
                parse_ok = parsed is not None
                poem = fix_poem(parsed, brief)
                local_fix_ok = poem is not None
                if isinstance(parsed, dict) and poem is not None:
                    local_fix_changed = (
                        parsed.get("title") != poem.get("title")
                        or parsed.get("lines") != poem.get("lines")
                    )
                if local_fix_ok and validate_poem(poem).ok:
                    source = "model"

    if poem is None:
        poem = fallback_poem(brief)
        source = "fallback"

    final_poem = {
        "topic": topic,
        "title": poem["title"],
        "lines": poem["lines"],
    }
    assert final_poem["topic"] == topic
    report = validate_poem(final_poem)
    if not report.ok:
        # 兜底构造有 bug 才会到这里：宁可显式失败也不外抛非法结果。
        raise RuntimeError(f"internal fallback returned invalid poem: {report.errors}")

    latency_ms = (time.perf_counter() - started) * 1000
    result = HarnessResult(
        poem=final_poem,
        source=source,
        model_calls=model_calls,
        latency_ms=latency_ms,
        model_used=raw_result.model if raw_result else None,
        provider=provider,
        raw_model_content=raw_result.content if raw_result else None,
        model_error=raw_result.error if raw_result else None,
        model_usage=raw_result.usage if raw_result else None,
        model_latency_ms=raw_result.latency_ms if raw_result else None,
        model_ok=raw_result.ok if raw_result else False,
        parse_ok=parse_ok,
        local_fix_ok=local_fix_ok,
        local_fix_changed=local_fix_changed,
        validation=report,
    )

    if debug:
        DebugRecorder(enabled=True).save_run(
            topic=topic,
            source=source,
            poem=final_poem,
            model_calls=model_calls,
            latency_ms=latency_ms,
            model_used=result.model_used,
            provider=result.provider,
            raw_model_content=result.raw_model_content,
            model_error=result.model_error,
            model_usage=result.model_usage,
            parse_ok=result.parse_ok,
            local_fix_ok=result.local_fix_ok,
            local_fix_changed=result.local_fix_changed,
            validation_errors=report.errors,
            validation_warnings=report.warnings,
        )
    return result
