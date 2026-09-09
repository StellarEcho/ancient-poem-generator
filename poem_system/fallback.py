"""确定性兜底：构造即合法，输出与 topic 可见关联。

句料全部是完整五字句，组句时第 1、3 句末字同韵；产出仍经统一校验器
与终态断言，保证“构造合法”不是口头承诺。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .normalize import PoemBrief


@dataclass(frozen=True)
class _Stanza:
    tags: frozenset[str]
    title: str
    lines: tuple[str, str, str, str]


_STANZAS: list[_Stanza] = [
    _Stanza(
        frozenset({"月", "夜", "灯", "窗", "客", "孤"}),
        "月下清辉",
        ("清辉照晚窗", "疏影过回廊", "客梦落寒霜", "孤灯夜未央"),
    ),
    _Stanza(
        frozenset({"雪", "寒", "冬", "山", "夜"}),
        "寒雪",
        ("寒雪满空山", "朔风动客颜", "冻云垂野岸", "孤舟行路难"),
    ),
    _Stanza(
        frozenset({"雪", "夜", "归", "寒", "雁"}),
        "雪夜",
        ("归雁入长天", "寒灯照客眠", "孤舟泊远烟", "夜雪落窗前"),
    ),
    _Stanza(
        frozenset({"归", "星", "远", "途", "河"}),
        "星归",
        ("星河接远天", "归雁度云山", "远路入寒烟", "孤灯照客船"),
    ),
    _Stanza(
        frozenset({"春", "花", "风", "燕", "水"}),
        "春风",
        ("春水绿池塘", "燕子绕雕梁", "花影入回廊", "日暖醉花香"),
    ),
    _Stanza(
        frozenset({"秋", "霜", "雁", "客", "夜"}),
        "秋夜",
        ("秋风动晚窗", "木叶下回廊", "露重湿秋霜", "孤影对寒江"),
    ),
    _Stanza(
        frozenset({"山", "云", "远", "松", "月"}),
        "远山",
        ("青山入翠烟", "松影落溪前", "飞鸟入遥天", "明月照清泉"),
    ),
    _Stanza(
        frozenset({"海", "潮", "帆", "远", "天"}),
        "沧海",
        ("沧海接长天", "潮声动客船", "孤帆入远烟", "白浪送归年"),
    ),
    _Stanza(
        frozenset({"城", "灯", "夜", "楼", "秋"}),
        "城夜",
        ("秋灯照客窗", "夜雨过回廊", "孤梦落寒霜", "晓色动空江"),
    ),
    _Stanza(
        frozenset({"别", "柳", "舟", "烟", "离"}),
        "送别",
        ("折柳赠行舟", "烟波送客愁", "离歌动远洲", "孤影望重楼"),
    ),
    _Stanza(
        frozenset({"孤", "夜", "灯", "客", "归"}),
        "孤夜",
        ("孤灯照夜衣", "竹影入窗扉", "故园归梦稀", "山月共清辉"),
    ),
    _Stanza(
        frozenset({"雨", "夜", "窗", "寒", "客"}),
        "夜雨",
        ("夜雨落空山", "檐声入梦阑", "客枕怯新寒", "晓色上栏杆"),
    ),
]


def topic_seed(topic: str) -> int:
    """跨进程稳定的主题种子：禁止内置 hash()（随机盐）。"""
    return int.from_bytes(
        hashlib.blake2s(topic.encode("utf-8"), digest_size=8).digest(),
        "big",
    )


def _pick_title(brief: PoemBrief, stanza: _Stanza, seed: int) -> str:
    if brief.title_hints:
        return brief.title_hints[seed % len(brief.title_hints)]
    return stanza.title


def fallback_poem(brief: PoemBrief) -> dict:
    """基于 brief 返回构造即合法的诗。"""
    imagery = set(brief.imagery)
    scored = [
        (len(stanza.tags & imagery), stanza)
        for stanza in _STANZAS
    ]
    best = max(score for score, _ in scored)
    pool = [stanza for score, stanza in scored if score == best]

    seed = topic_seed(brief.raw)
    stanza = pool[seed % len(pool)]
    return {
        "title": _pick_title(brief, stanza, seed),
        "lines": list(stanza.lines),
    }
