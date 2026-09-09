"""从模型原始输出稳健提取候选诗。"""

from __future__ import annotations

import json
import re

_HAN5 = re.compile(r"[\u4e00-\u9fff]{5}")
_HAN_TITLE = re.compile(r"[\u4e00-\u9fff]{2,8}")


def _extract_json_object(text: str) -> str:
    """返回文本中第一个完整 {...} 子串；找不到返回空串。"""
    start = text.find("{")
    if start == -1:
        return ""

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        ch = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""


def _extract_five_han_lines(text: str) -> list[str] | None:
    """逐行抽取恰好 5 个汉字的片段，返回首个连续四句窗口。"""
    candidates: list[str] = []
    for line in text.splitlines():
        candidates.extend(_HAN5.findall(line))
    if len(candidates) < 4:
        return None
    for start in range(len(candidates) - 3):
        window = candidates[start : start + 4]
        if all(len(item) == 5 for item in window):
            return list(window)
    return None


def _extract_title(text: str, poem_lines: list[str]) -> str | None:
    """从 markdown 加粗行/散文里取第一个 2–8 字标题（跳过诗句本身）。"""
    poem_line_set = set(poem_lines)
    for match in _HAN_TITLE.findall(text):
        if match not in poem_line_set:
            return match
    return None


def parse_candidate(raw: object) -> dict | None:
    """解析顺序：整段 JSON → 最外层 {} → 连续四句五字 → None。"""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None

    for chunk in (text, _extract_json_object(text)):
        if not chunk:
            continue
        try:
            parsed = json.loads(chunk)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed

    lines = _extract_five_han_lines(text)
    if lines is not None:
        return {"title": _extract_title(text, lines), "lines": lines}
    return None
