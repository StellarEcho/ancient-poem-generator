"""确定性兜底：构造即合法，输出与 topic 可见关联。

句料全部是完整五字句，组句时第 1、3 句末字同韵；产出仍经统一校验器
与终态断言，保证“构造合法”不是口头承诺。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .normalize import PoemBrief
from .rhyme import rhyme_key


@dataclass(frozen=True)
class _Stanza:
    tags: frozenset[str]
    title: str
    lines: tuple[str, str, str, str]


_STANZAS: list[_Stanza] = [
    _Stanza(
        frozenset({"月", "夜", "灯", "窗", "客", "孤", "桂", "圆"}),
        "月下清辉",
        ("清辉照晚窗", "疏影过回廊", "客梦落寒霜", "孤灯夜未央"),
    ),
    _Stanza(
        frozenset({"雪", "寒", "冬", "山", "夜", "梅"}),
        "寒雪",
        ("寒雪满空山", "朔风动客颜", "冻云垂野岸", "孤舟行路难"),
    ),
    _Stanza(
        frozenset({"雪", "夜", "归", "寒", "雁"}),
        "雪夜",
        ("归雁入长天", "寒灯照客眠", "孤舟泊远烟", "夜雪落窗前"),
    ),
    _Stanza(
        frozenset({"归", "星", "远", "途", "河", "夜", "云", "梦"}),
        "星归",
        ("星河接远天", "归雁度云山", "远路入寒烟", "孤灯照客船"),
    ),
    _Stanza(
        frozenset({"春", "花", "风", "燕", "水", "柳", "日", "草", "田"}),
        "春风",
        ("春水绿池塘", "燕子绕雕梁", "花影入回廊", "日暖醉花香"),
    ),
    _Stanza(
        frozenset({"秋", "霜", "雁", "客", "夜", "菊", "山", "远"}),
        "秋夜",
        ("秋风动晚窗", "木叶下回廊", "露重湿秋霜", "孤影对寒江"),
    ),
    _Stanza(
        frozenset({"山", "云", "远", "松", "月", "泉", "溪"}),
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
        frozenset({"别", "柳", "舟", "烟", "离", "友", "酒"}),
        "送别",
        ("折柳赠行舟", "烟波送客愁", "离歌动远洲", "孤影望重楼"),
    ),
    _Stanza(
        frozenset({"孤", "夜", "灯", "客", "归", "酒", "书"}),
        "孤夜",
        ("孤灯照夜衣", "竹影入窗扉", "故园归梦稀", "山月共清辉"),
    ),
    _Stanza(
        frozenset({"雨", "夜", "窗", "寒", "客"}),
        "夜雨",
        ("夜雨落空山", "檐声入梦阑", "客枕怯新寒", "晓色上栏杆"),
    ),
    _Stanza(
        frozenset({"荷", "花", "水", "风", "夏", "蝉"}),
        "荷风",
        ("荷风送晚香", "碧水映斜阳", "一叶入清凉", "蝉声过短墙"),
    ),
    _Stanza(
        frozenset({"竹", "山", "风", "夜", "云", "兰"}),
        "竹影",
        ("竹影落空庭", "清风动翠屏", "幽鸟宿寒汀", "云深隐夜星"),
    ),
    _Stanza(
        frozenset({"湖", "水", "月", "云", "山", "舟"}),
        "湖上",
        ("湖光接远天", "云影落清涟", "一棹入寒烟", "鸥鸟过前川"),
    ),
    _Stanza(
        frozenset({"江", "河", "水", "舟", "帆", "远", "流"}),
        "江行",
        ("江水向东流", "孤帆带月秋", "客心何处留", "落日满汀洲"),
    ),
    _Stanza(
        frozenset({"沙", "风", "远", "关", "马", "月", "山", "草"}),
        "出塞",
        ("黄沙接远天", "孤雁度关山", "落日满长烟", "风劲马嘶寒"),
    ),
    _Stanza(
        frozenset({"晚", "霞", "山", "远", "日", "云", "鸟"}),
        "晚望",
        ("晚霞映远山", "归鸟入云间", "落日满空山", "渔火照人还"),
    ),
    _Stanza(
        frozenset({"晨", "鸟", "花", "风", "露", "竹", "草", "田"}),
        "晨兴",
        ("晨光照画廊", "露湿草花香", "鸟语过横塘", "风清竹影凉"),
    ),
    _Stanza(
        frozenset({"酒", "月", "夜", "友", "客", "杯"}),
        "对月",
        ("举杯邀月明", "故友话平生", "一盏照心清", "相逢醉晚风"),
    ),
    _Stanza(
        frozenset({"思", "月", "夜", "花", "梦", "星"}),
        "相思",
        ("月照小窗明", "花落梦难成", "相思寄远星", "风来动翠屏"),
    ),
    _Stanza(
        frozenset({"年", "春", "灯", "花", "夜", "节"}),
        "新岁",
        ("灯火照新年", "春风入画帘", "笑语满庭前", "梅香落玉笺"),
    ),
    _Stanza(
        frozenset({"舟", "水", "风", "艾", "江", "鼓"}),
        "江畔",
        ("龙舟破碧澜", "艾草满晴川", "鼓声动远山", "风送粽香还"),
    ),
    _Stanza(
        frozenset({"星", "河", "夜", "鹊", "云", "天"}),
        "星河",
        ("银河隔远天", "鹊影度云间", "星河渡万年", "灯火照人间"),
    ),
    _Stanza(
        frozenset({"草", "原", "田", "风", "云", "远", "天"}),
        "草原",
        ("草原连远天", "风过草生烟", "云低牛羊闲", "牧笛入长天"),
    ),
]

# 通用第 3 句白名单：覆盖主句料库里缺失的韵母，供本地修补使用。
_EXTRA_LINE3: list[tuple[str, frozenset[str]]] = [
    ("归云抱故园", frozenset({"园", "云", "归", "乡"})),
    ("青山月正圆", frozenset({"山", "月", "圆", "夜"})),
    ("孤舟泊古原", frozenset({"舟", "原", "远", "孤"})),
    ("远岫接平川", frozenset({"远", "川", "山", "水"})),
    ("钟声出远川", frozenset({"钟", "远", "山", "水"})),
    ("孤灯守长夜", frozenset({"孤", "灯", "夜", "客"})),
    ("长亭又送别", frozenset({"别", "柳", "舟", "远"})),
    ("清风伴永夜", frozenset({"风", "夜", "月", "清"})),
    ("清泉洗客心", frozenset({"泉", "心", "客", "山"})),
    ("空山闻鸟音", frozenset({"山", "鸟", "音", "云"})),
    ("月照故人心", frozenset({"月", "心", "友", "夜"})),
    ("钟声入暮深", frozenset({"钟", "深", "晚", "山"})),
    ("灯影照归人", frozenset({"灯", "人", "归", "夜"})),
    ("风雪掩柴门", frozenset({"风", "雪", "门", "寒"})),
    ("风翻满院花", frozenset({"风", "花", "春", "院"})),
    ("烟雨湿窗纱", frozenset({"雨", "花", "窗", "烟"})),
    ("春深落尽花", frozenset({"春", "花", "深", "雨"})),
    ("归心向天涯", frozenset({"归", "心", "远", "家"})),
    ("云开见晚霞", frozenset({"云", "霞", "晚", "山"})),
    ("明月送清辉", frozenset({"月", "辉", "夜", "清"})),
    ("长歌入翠微", frozenset({"歌", "微", "山", "远"})),
    ("鸿雁向南飞", frozenset({"雁", "飞", "远", "秋"})),
    ("寒江映晚灯", frozenset({"江", "灯", "晚", "夜"})),
    ("秋风送雁声", frozenset({"秋", "风", "雁", "声"})),
    ("孤舟对短灯", frozenset({"孤", "舟", "灯", "夜"})),
    ("远岫入青冥", frozenset({"远", "山", "青", "云"})),
    ("夜雨洗秋清", frozenset({"雨", "秋", "清", "夜"})),
    ("疏星映短亭", frozenset({"星", "亭", "夜", "远"})),
    ("云开见远鸿", frozenset({"云", "鸿", "远", "天"})),
    ("寒山闻晚钟", frozenset({"山", "钟", "晚", "寒"})),
    ("孤舟泊江东", frozenset({"舟", "江", "东", "远"})),
    ("一雁度清秋", frozenset({"雁", "秋", "清", "远"})),
    ("灯前忆旧游", frozenset({"灯", "游", "夜", "友"})),
    ("孤帆带客愁", frozenset({"舟", "帆", "客", "愁"})),
    ("残阳照小楼", frozenset({"阳", "楼", "晚", "城"})),
    ("归梦落汀洲", frozenset({"归", "梦", "洲", "水"})),
    ("山深藏白云", frozenset({"山", "云", "深", "远"})),
    ("天边一片云", frozenset({"天", "云", "远", "边"})),
    ("风来满院歌", frozenset({"风", "歌", "院", "春"})),
    ("青山映碧河", frozenset({"山", "河", "青", "水"})),
    ("长亭送远客", frozenset({"别", "客", "亭", "远"})),
    ("烟波接远涛", frozenset({"水", "远", "烟", "波"})),
    ("孤舟度晚潮", frozenset({"舟", "水", "晚", "潮"})),
    ("秋风卷海涛", frozenset({"风", "秋", "海", "涛"})),
]


def topic_seed(topic: str) -> int:
    """跨进程稳定的主题种子：禁止内置 hash()（随机盐）。"""
    try:
        data = topic.encode("utf-8")
    except UnicodeEncodeError:
        # 极端输入（孤立代理字符）用 surrogatepass 保证仍然确定且不崩。
        data = topic.encode("utf-8", errors="surrogatepass")
    return int.from_bytes(
        hashlib.blake2s(data, digest_size=8).digest(),
        "big",
    )


def _pick_title(brief: PoemBrief, stanza: _Stanza) -> str:
    if brief.title_hints:
        return brief.title_hints[0]
    return stanza.title


def fallback_line3_candidates(brief: PoemBrief, target_key: str) -> list[str]:
    """返回目标韵母匹配的兜底第 3 句候选（按意象重合度排序）。

    仅供本地修补使用：所有候选都来自人工校对的句料库白名单。
    """
    imagery = set(brief.imagery)
    scored: list[tuple[int, str, str]] = []
    for stanza in _STANZAS:
        line = stanza.lines[2]
        try:
            if rhyme_key(line[-1]) != target_key:
                continue
        except ValueError:
            continue
        scored.append((len(stanza.tags & imagery), line, stanza.title))
    for line, tags in _EXTRA_LINE3:
        try:
            if rhyme_key(line[-1]) != target_key:
                continue
        except ValueError:
            continue
        scored.append((len(tags & imagery), line, "extra"))
    scored.sort(key=lambda item: (-item[0], item[2], item[1]))
    return [line for _, line, _ in scored]


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
        "title": _pick_title(brief, stanza),
        "lines": list(stanza.lines),
    }
