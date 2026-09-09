"""topic → PoemBrief：纯本地、零模型调用、确定性。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .validate import is_han


@dataclass(frozen=True)
class PoemBrief:
    raw: str
    imagery: list[str] = field(default_factory=list)
    mood: str = ""
    title_hints: list[str] = field(default_factory=list)
    banned: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Feature:
    needles: tuple[str, ...]
    imagery: tuple[str, ...]
    mood: str
    title_hints: tuple[str, ...]
    banned: tuple[str, ...] = ()


_FEATURES: list[_Feature] = [
    _Feature(("月", "月光", "月色"), ("月", "夜", "灯"), "清幽", ("月夜", "清辉")),
    _Feature(("孤独", "寂寞", "孤", "独"), ("孤", "灯", "夜", "客"), "孤寂", ("孤夜", "客灯")),
    _Feature(("雪",), ("雪", "寒", "夜", "冬"), "清寒", ("寒雪", "雪夜")),
    _Feature(("夜",), ("夜", "月", "灯", "寒"), "清冷", ("长夜", "夜吟")),
    _Feature(("山",), ("山", "云", "远", "松"), "清远", ("远山", "山月")),
    _Feature(("海", "沧海", "潮"), ("海", "潮", "远", "帆"), "壮阔", ("沧海", "远潮")),
    _Feature(("春",), ("春", "花", "风", "燕"), "明丽", ("春风", "花时")),
    _Feature(("秋",), ("秋", "霜", "雁", "凉"), "清愁", ("清秋", "秋思")),
    _Feature(("城", "城市"), ("城", "灯", "夜", "楼"), "繁华", ("城夜", "灯楼")),
    _Feature(("归", "回家", "故乡"), ("归", "雁", "途", "乡"), "思归", ("归途", "雁归")),
    _Feature(("别", "离", "送"), ("别", "柳", "舟", "烟"), "依依", ("送别", "离歌")),
    _Feature(("星",), ("星", "河", "夜", "远"), "旷远", ("星河", "星夜")),
    _Feature(("风",), ("风", "云", "花", "夜"), "萧散", ("清风", "夜风")),
    _Feature(("雨",), ("雨", "夜", "窗", "寒"), "清冷", ("夜雨", "秋雨")),
    _Feature(("花",), ("花", "春", "影", "香"), "清婉", ("春花", "花影")),
    _Feature(("灯",), ("灯", "夜", "窗", "影"), "幽静", ("灯影", "夜灯")),
    _Feature(("乡", "家乡"), ("乡", "归", "雁", "月"), "思乡", ("故乡", "归梦")),
    _Feature(("梦",), ("梦", "夜", "花", "云"), "幽渺", ("幽梦", "夜梦")),
    _Feature(("云",), ("云", "山", "雁", "月"), "淡远", ("孤云", "远云")),
]

_ENGLISH_FEATURES: list[_Feature] = [
    _Feature(("mars",), ("星", "归", "远", "夜"), "旷远", ("星归", "远夜"), ("mars",)),
    _Feature(("return",), ("归", "雁", "途", "乡"), "思归", ("归途", "雁归"), ("return",)),
    _Feature(("ai", "artificial intelligence"), ("孤", "灯", "夜", "思"), "孤寂", ("夜思", "孤灯"), ("ai",)),
    _Feature(("moon",), ("月", "夜", "灯"), "清幽", ("月夜", "清辉"), ("moon",)),
    _Feature(("snow", "winter"), ("雪", "寒", "夜", "冬"), "清寒", ("寒雪", "雪夜"), ("snow", "winter")),
    _Feature(("sea", "ocean"), ("海", "潮", "远", "帆"), "壮阔", ("沧海", "远潮"), ("sea", "ocean")),
    _Feature(("spring",), ("春", "花", "风", "燕"), "明丽", ("春风", "花时"), ("spring",)),
    _Feature(("autumn", "fall"), ("秋", "霜", "雁", "凉"), "清愁", ("清秋", "秋思"), ("autumn", "fall")),
    _Feature(("city",), ("城", "灯", "夜", "楼"), "繁华", ("城夜", "灯楼"), ("city",)),
    _Feature(("star",), ("星", "河", "夜", "远"), "旷远", ("星河", "星夜"), ("star",)),
    _Feature(("mountain",), ("山", "云", "远", "松"), "清远", ("远山", "山月"), ("mountain",)),
    _Feature(("lonely", "loneliness", "alone"), ("孤", "灯", "夜", "客"), "孤寂", ("孤夜", "客灯"), ("lonely",)),
]

_DEFAULT_IMAGERY = ("夜", "灯", "山", "云")
_DEFAULT_MOOD = "清远"
_DEFAULT_TITLE_HINTS = ("夜吟", "远山")

_SNOW_YEAR = re.compile(r"20\d{2}年的第一场雪")
_YEAR = re.compile(r"20\d{2}")
_TOKEN = re.compile(r"[a-z]+|\d+")


def _merge_unique(values: list[str], new: tuple[str, ...]) -> None:
    for item in new:
        if item and item not in values:
            values.append(item)


def _clean_title_hints(hints: list[str]) -> list[str]:
    out: list[str] = []
    for hint in hints:
        if 2 <= len(hint) <= 8 and all(is_han(ch) for ch in hint) and hint not in out:
            out.append(hint)
        if len(out) >= 4:
            break
    return out


def normalize_topic(topic: str) -> PoemBrief:
    """把任意字符串映射为可入诗、可提示模型的主题简报。

    - 数字年份/英文做字典与正则映射；
    - 不认识的内容落到通用意象组；
    - 整个过程不调用模型、不抛异常（topic 非 str 由 api 层负责）。
    """
    raw = topic
    lowered = topic.casefold()

    imagery: list[str] = []
    title_hints: list[str] = []
    banned: list[str] = []
    moods: list[str] = []

    if _SNOW_YEAR.search(lowered):
        _merge_unique(imagery, ("雪", "寒", "年", "夜"))
        _merge_unique(title_hints, ("雪夜", "寒年"))
        moods.append("清寒")

    for feature in _ENGLISH_FEATURES:
        if any(needle in lowered for needle in feature.needles):
            _merge_unique(imagery, feature.imagery)
            _merge_unique(title_hints, feature.title_hints)
            _merge_unique(banned, feature.banned)
            moods.append(feature.mood)

    for feature in _FEATURES:
        if any(needle in raw for needle in feature.needles):
            _merge_unique(imagery, feature.imagery)
            _merge_unique(title_hints, feature.title_hints)
            _merge_unique(banned, feature.banned)
            moods.append(feature.mood)

    if _YEAR.search(lowered):
        _merge_unique(imagery, ("年", "夜", "春"))
        _merge_unique(title_hints, ("新年", "春夜"))
        _merge_unique(banned, tuple(re.findall(r"\d+", raw)))
        moods.append("思远")

    if not imagery:
        imagery.extend(_DEFAULT_IMAGERY)
    if not title_hints:
        title_hints.extend(_DEFAULT_TITLE_HINTS)

    # 收集英文/数字原文 token 作为禁用词。
    for token in _TOKEN.findall(lowered):
        _merge_unique(banned, (token,))

    mood = moods[0] if moods else _DEFAULT_MOOD
    return PoemBrief(
        raw=raw,
        imagery=_clean_imagery(imagery),
        mood=mood,
        title_hints=_clean_title_hints(title_hints),
        banned=banned,
    )


def _clean_imagery(values: list[str]) -> list[str]:
    out: list[str] = []
    for item in values:
        if item and is_han(item) and item not in out:
            out.append(item)
    return out
