"""零模型本地修补：只救小毛病，结构烂直接放弃交兜底。"""

from __future__ import annotations

from .fallback import fallback_poem
from .normalize import PoemBrief
from .rhyme import rhyme_key
from .validate import RHYME, is_han, only_han, validate_poem

# 白名单尾字库：只收诗里常见词，按末字韵母分组；禁止任意同韵字乱替。
_SUFFIXES: dict[str, tuple[str, ...]] = {
    "uang": ("寒霜", "秋霜", "晚霜", "寒窗", "幽窗"),
    "ang": ("回廊", "空廊", "池塘", "斜阳"),
    "ian": ("长天", "寒烟", "远烟", "旧年", "云边", "窗前"),
    "i": ("夜衣", "人衣", "归稀", "梦稀"),
    "ou": ("行舟", "客愁", "远洲", "重楼"),
    "ve": ("夜月", "残月", "冷月"),
    "an": ("空山", "新寒", "夜阑", "江南"),
    "iang": ("寒江", "秋江", "夜江"),
    "eng": ("寒灯", "夜灯", "青灯"),
    "ing": ("夜星", "寒星", "长亭"),
    "u": ("江渚", "远树", "古树"),
    "v": ("夜雨", "秋雨", "故雨"),
}


def _clean_title(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = "".join(ch for ch in value if is_han(ch))
    if 2 <= len(cleaned) <= 8 and only_han(cleaned):
        return cleaned
    return None


def _clean_line(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = "".join(ch for ch in value if is_han(ch))
    return cleaned if len(cleaned) == 5 else None


def _with_valid_rhyme(lines: list[str], target_key: str, brief: PoemBrief) -> list[str] | None:
    prefix = lines[2][:3]
    for suffix in _SUFFIXES.get(target_key, ()):
        candidate_lines = [lines[0], lines[1], prefix + suffix, lines[3]]
        if len(set(candidate_lines)) != 4:
            continue
        try:
            if rhyme_key(candidate_lines[2][-1]) != target_key:
                continue
        except ValueError:
            continue
        if validate_poem({"title": "暂定", "lines": candidate_lines}).ok:
            return candidate_lines

    # 白名单之外：用同一主题兜底句料里的第 3 句收口。
    fallback_line3 = fallback_poem(brief)["lines"][2]
    candidate_lines = [lines[0], lines[1], fallback_line3, lines[3]]
    if len(set(candidate_lines)) == 4 and validate_poem(
        {"title": "暂定", "lines": candidate_lines}
    ).ok:
        return candidate_lines
    return None


def fix_poem(poem: object, brief: PoemBrief) -> dict | None:
    """本地修补候选诗；修不好返回 None（由调用方走兜底）。"""
    if not isinstance(poem, dict):
        return None

    lines_raw = poem.get("lines")
    if not isinstance(lines_raw, list):
        return None

    lines: list[str] = []
    for item in lines_raw:
        cleaned = _clean_line(item)
        if cleaned is None:
            return None
        lines.append(cleaned)
    if len(lines) != 4:
        return None

    title = _clean_title(poem.get("title"))
    if title is None and brief.title_hints:
        title = brief.title_hints[0]
    if title is None:
        return None

    candidate: dict = {"title": title, "lines": lines}
    report = validate_poem(candidate)
    if report.ok:
        return candidate
    if report.errors != [RHYME]:
        return None

    try:
        target_key = rhyme_key(lines[0][-1])
    except ValueError:
        return None
    fixed_lines = _with_valid_rhyme(lines, target_key, brief)
    if fixed_lines is None:
        return None
    return {"title": title, "lines": fixed_lines}
