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
    # 传统节日（具体用法优先）
    _Feature(("中秋", "团圆"), ("月", "夜", "桂", "圆", "灯"), "团圆", ("月圆", "中秋")),
    _Feature(("春节", "新年", "除夕", "年味"), ("年", "春", "灯", "花", "夜"), "喜庆", ("新岁", "春灯")),
    _Feature(("端午", "龙舟", "粽"), ("舟", "水", "风", "艾", "江", "鼓"), "热闹", ("江畔", "龙舟")),
    _Feature(("七夕", "鹊桥"), ("星", "河", "夜", "鹊", "云"), "深情", ("星河", "鹊桥")),
    _Feature(("重阳", "登高"), ("秋", "山", "菊", "远"), "高远", ("登高", "重阳")),
    _Feature(("清明",), ("雨", "春", "柳", "烟"), "清冷", ("清明", "烟雨")),
    # 四君子与常见花卉
    _Feature(("梅",), ("梅", "雪", "花", "寒"), "清雅", ("梅花", "寒梅")),
    _Feature(("兰",), ("兰", "山", "云", "风"), "幽雅", ("幽兰", "兰香")),
    _Feature(("竹",), ("竹", "山", "风", "夜", "云"), "清逸", ("竹影", "清风")),
    _Feature(("菊",), ("菊", "秋", "霜", "山"), "高洁", ("秋菊", "霜菊")),
    _Feature(("荷", "莲"), ("荷", "花", "水", "风", "夏", "蝉"), "清丽", ("荷风", "莲影")),
    _Feature(("柳",), ("柳", "春", "水", "风"), "依依", ("柳岸", "春柳")),
    # 山水行旅
    _Feature(("湖",), ("湖", "水", "月", "云", "山"), "澄澈", ("湖上", "湖月")),
    _Feature(
        ("江", "江河", "河流", "黄河", "长河", "大河", "川", "流水"),
        ("江", "河", "水", "舟", "帆", "远"),
        "悠远",
        ("江行", "远江"),
    ),
    _Feature(("瀑布", "泉", "溪"), ("泉", "水", "山", "云"), "清越", ("山泉", "飞瀑")),
    _Feature(("草原", "田野", "原野", "旷野"), ("草", "原", "风", "云", "远"), "辽阔", ("草原", "旷野")),
    _Feature(
        ("沙", "沙漠", "戈壁", "边塞", "关", "战场", "战争"),
        ("沙", "风", "远", "关", "马", "月"),
        "苍凉",
        ("出塞", "关山"),
    ),
    _Feature(("黄昏", "晚霞", "夕阳", "落日"), ("晚", "霞", "山", "远", "日", "云"), "苍茫", ("晚望", "落霞")),
    _Feature(("清晨", "晨", "晓"), ("晨", "鸟", "花", "风", "露", "竹"), "清新", ("晨兴", "晓景")),
    _Feature(("日出", "朝阳", "太阳"), ("日", "云", "山", "远"), "明朗", ("朝阳", "日出")),
    _Feature(("少年", "青春", "梦想"), ("春", "花", "风", "日"), "昂扬", ("少年", "春华")),
    _Feature(("读书", "书卷", "书香"), ("书", "灯", "夜", "窗"), "沉静", ("夜读", "书窗")),
    # 情感与日常
    _Feature(("酒", "醉", "杯"), ("酒", "月", "夜", "友", "客", "杯"), "酣畅", ("对月", "醉月")),
    _Feature(("相思", "爱情", "恋人", "思念"), ("思", "月", "夜", "花", "梦", "星"), "深婉", ("相思", "月思")),
    _Feature(("友情", "朋友", "故友", "友谊"), ("友", "酒", "柳", "月", "别"), "温厚", ("故友", "对月")),
    _Feature(("琴", "歌", "音乐"), ("琴", "声", "夜", "月", "风"), "雅致", ("琴声", "夜歌")),
    _Feature(("时间", "岁月", "光阴", "流年"), ("年", "流", "水", "远", "夜", "梦"), "悠长", ("流年", "岁晚")),
    _Feature(("宇宙", "未来", "太空", "科幻"), ("星", "河", "远", "夜", "云", "梦"), "旷远", ("星河", "远夜")),
    _Feature(("夏",), ("夏", "荷", "风", "蝉", "水"), "明快", ("夏日", "荷风")),
    _Feature(("冬",), ("冬", "雪", "寒", "夜", "灯"), "凛冽", ("冬夜", "寒灯")),
    # 基础意象
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
    _Feature(("星", "银河", "星辰"), ("星", "河", "夜", "远"), "旷远", ("星河", "星夜")),
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
    _Feature(("love",), ("思", "月", "夜", "花", "梦"), "深婉", ("相思", "月思"), ("love",)),
    _Feature(("friend", "friendship"), ("友", "酒", "柳", "月"), "温厚", ("故友", "对月"), ("friend",)),
    _Feature(("home",), ("归", "乡", "雁", "月"), "思归", ("归乡", "雁归"), ("home",)),
    _Feature(("river",), ("江", "河", "水", "舟"), "悠远", ("江行", "远江"), ("river",)),
    _Feature(("lake",), ("湖", "水", "月", "云"), "澄澈", ("湖上", "湖月"), ("lake",)),
    _Feature(("bamboo",), ("竹", "山", "风", "夜"), "清逸", ("竹影", "清风"), ("bamboo",)),
    _Feature(("plum",), ("梅", "雪", "花", "寒"), "清雅", ("梅花", "寒梅"), ("plum",)),
    _Feature(("lotus",), ("荷", "花", "水", "风"), "清丽", ("荷风", "莲影"), ("lotus",)),
    _Feature(("wine",), ("酒", "月", "夜", "友"), "酣畅", ("对月", "醉月"), ("wine",)),
    _Feature(("dusk", "sunset"), ("晚", "霞", "山", "远", "日"), "苍茫", ("晚望", "落霞"), ("dusk", "sunset")),
    _Feature(("dawn", "morning"), ("晨", "鸟", "花", "风", "露"), "清新", ("晨兴", "晓景"), ("dawn", "morning")),
    _Feature(("war",), ("沙", "风", "远", "关", "马"), "苍凉", ("关山", "出塞"), ("war",)),
    _Feature(("time",), ("年", "流", "水", "远"), "悠长", ("流年", "岁晚"), ("time",)),
    _Feature(("future", "space", "universe"), ("星", "河", "远", "夜", "云"), "旷远", ("星河", "远夜"), ("future", "space", "universe")),
    _Feature(("music", "song"), ("琴", "声", "夜", "月", "风"), "雅致", ("琴声", "夜歌"), ("music", "song")),
    _Feature(("summer",), ("夏", "荷", "风", "蝉", "水"), "明快", ("夏日", "荷风"), ("summer",)),
    _Feature(("winter",), ("冬", "雪", "寒", "夜", "灯"), "凛冽", ("冬夜", "寒灯"), ("winter",)),
    _Feature(("festival",), ("年", "春", "灯", "花", "夜"), "喜庆", ("新岁", "春灯"), ("festival",)),
    _Feature(("willow",), ("柳", "春", "水", "风"), "依依", ("柳岸", "春柳"), ("willow",)),
    _Feature(("waterfall", "stream"), ("泉", "水", "山", "云"), "清越", ("山泉", "飞瀑"), ("waterfall", "stream")),
    _Feature(("grassland", "field"), ("草", "风", "云", "远"), "辽阔", ("草原", "旷野"), ("grassland", "field")),
    _Feature(("sunrise", "sun"), ("日", "云", "山", "远"), "明朗", ("朝阳", "日出"), ("sunrise", "sun")),
    _Feature(("youth", "dream"), ("春", "花", "风", "日"), "昂扬", ("少年", "春华"), ("youth", "dream")),
    _Feature(("book", "reading"), ("书", "灯", "夜", "窗"), "沉静", ("夜读", "书窗"), ("book", "reading")),
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
