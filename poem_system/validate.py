"""合规校验：结构、纯汉字、字数、韵脚，返回结构化错误码。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .rhyme import rhyme_key

HAN_START = 0x4E00
HAN_END = 0x9FFF

WRONG_TYPE = "WRONG_TYPE"
TITLE_LEN = "TITLE_LEN"
LINE_COUNT = "LINE_COUNT"
LINE_LEN = "LINE_LEN"
NON_HAN = "NON_HAN"
RHYME = "RHYME"
DUP_LINE = "DUP_LINE"
EMPTY = "EMPTY"


def is_han(ch: str) -> bool:
    """是否单个基本区汉字（U+4E00–U+9FFF）。"""
    return len(ch) == 1 and HAN_START <= ord(ch) <= HAN_END


def only_han(text: str) -> bool:
    """整串是否只由基本区汉字组成。"""
    return all(is_han(ch) for ch in text)


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str]
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


def validate_poem(poem: object) -> ValidationReport:
    """校验候选诗；收集全部错误码，不只返回 bool。"""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(poem, dict):
        return ValidationReport(ok=False, errors=[WRONG_TYPE])

    title = poem.get("title")
    lines = poem.get("lines")

    if not isinstance(title, str):
        errors.append(WRONG_TYPE)
    elif title == "":
        errors.append(EMPTY)
    elif not 2 <= len(title) <= 8:
        errors.append(TITLE_LEN)
    if isinstance(title, str) and not only_han(title):
        errors.append(NON_HAN)

    if not isinstance(lines, list):
        errors.append(WRONG_TYPE)
    else:
        if len(lines) != 4:
            errors.append(LINE_COUNT)

        text_lines: list[str] = []
        for line in lines:
            if not isinstance(line, str):
                errors.append(WRONG_TYPE)
                continue
            if line == "":
                errors.append(EMPTY)
            elif len(line) != 5:
                errors.append(LINE_LEN)
            if not only_han(line):
                errors.append(NON_HAN)
            text_lines.append(line)

        if len(text_lines) == 4 and len(set(text_lines)) != 4:
            warnings.append(DUP_LINE)

        if (
            len(text_lines) == 4
            and isinstance(title, str)
            and all(len(line) == 5 and only_han(line) for line in text_lines)
        ):
            try:
                if rhyme_key(text_lines[0][-1]) != rhyme_key(text_lines[2][-1]):
                    errors.append(RHYME)
            except ValueError:
                errors.append(RHYME)

    # 去重保持稳定顺序；去重前保证关键错误不被吞掉。
    seen: set[str] = set()
    unique_errors: list[str] = []
    for code in errors:
        if code not in seen:
            seen.add(code)
            unique_errors.append(code)
    seen_warnings: set[str] = set()
    unique_warnings: list[str] = []
    for code in warnings:
        if code not in seen_warnings:
            seen_warnings.add(code)
            unique_warnings.append(code)
    return ValidationReport(
        ok=not unique_errors,
        errors=unique_errors,
        warnings=unique_warnings,
    )


def validate_structure_and_rhyme(title: str, lines: list[str]) -> ValidationReport:
    """CLI/测试用的便捷入口。"""
    return validate_poem({"title": title, "lines": lines})
