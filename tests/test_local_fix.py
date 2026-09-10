"""本地修补测试。"""

from poem_system.local_fix import fix_poem
from poem_system.normalize import normalize_topic
from poem_system.rhyme import rhyme_key
from poem_system.validate import validate_poem


def test_clean_markdown_title() -> None:
    poem = {
        "title": "《月下清辉》",
        "lines": ["清辉照晚窗", "疏影过回廊", "客梦落寒霜", "孤灯夜未央"],
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert fixed["title"] == "月下清辉"
    assert validate_poem(fixed).ok


def test_clean_punctuation_from_lines() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗。", "疏影过回廊，", "客梦落寒霜！", "孤灯夜未央"],
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert validate_poem(fixed).ok


def test_rhyme_fix_via_whitelist_suffix() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗", "疏影过回廊", "客梦落寒江", "孤灯夜未央"],
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert fixed["lines"][2] != "客梦落寒江"


def test_rhyme_fix_falls_back_to_same_theme_line3() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗", "疏影过回廊", "月落乌啼霜", "孤灯夜未央"],
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert validate_poem(fixed).ok


def test_structural_bad_returns_none() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗明月", "疏影过回廊", "客梦落寒霜"],
    }
    assert fix_poem(poem, normalize_topic("月色")) is None
    assert fix_poem(None, normalize_topic("月色")) is None
    assert fix_poem({"title": "月下清辉", "lines": "清辉照晚窗"}, normalize_topic("月色")) is None


def test_duplicate_line_not_blocked() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗"] * 4,
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert validate_poem(fixed).ok


def test_line_with_embedded_english_and_number_is_cleaned() -> None:
    poem = {
        "title": "AI时代的孤独",
        "lines": ["孤灯照夜衣1", "AI竹影入窗扉", "故园归梦稀", "山月共清辉"],
    }
    fixed = fix_poem(poem, normalize_topic("AI时代的孤独"))
    assert fixed is not None
    assert validate_poem(fixed).ok


def test_arbitrary_same_rhyme_char_not_used() -> None:
    poem = {
        "title": "月下清辉",
        "lines": ["清辉照晚窗", "疏影过回廊", "客梦落寒翁", "孤灯夜未央"],
    }
    fixed = fix_poem(poem, normalize_topic("月色"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert "翁" not in fixed["lines"][2]


def test_ong_rhyme_fixed_by_whitelist_suffix() -> None:
    poem = {
        "title": "夜行",
        "lines": ["星光照夜空", "雁影随风去", "远山映日光", "乡音悠悠声"],
    }
    fixed = fix_poem(poem, normalize_topic("冬夜"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert rhyme_key(fixed["lines"][2][-1]) == "ong"


def test_iou_rhyme_fixed_by_curated_line3() -> None:
    poem = {
        "title": "夜山孤灯",
        "lines": ["夜静远山幽", "孤灯照客舟", "云归山影收", "风送一江秋"],
    }
    fixed = fix_poem(poem, normalize_topic("夜色"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert rhyme_key(fixed["lines"][2][-1]) == "iou"


def test_van_rhyme_fixed_by_generic_line3_bank() -> None:
    poem = {
        "title": "晚霞苍茫",
        "lines": ["晚霞映山远", "孤云逐日飞", "暮色染林晚", "苍茫何处归"],
    }
    fixed = fix_poem(poem, normalize_topic("黄昏"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert rhyme_key(fixed["lines"][2][-1]) == "van"


def test_ie_rhyme_fixed_by_generic_line3_bank() -> None:
    poem = {
        "title": "冬夜寄春",
        "lines": ["寒雪落长夜", "孤灯照旧年", "北风动远天", "梅影待春烟"],
    }
    fixed = fix_poem(poem, normalize_topic("2026年的第一场雪"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert rhyme_key(fixed["lines"][2][-1]) == "ie"


def test_vn_rhyme_fixed_by_generic_line3_bank() -> None:
    poem = {
        "title": "草原辽阔情",
        "lines": ["草原风卷云", "天边远影分", "云动心自远", "地阔意难群"],
    }
    fixed = fix_poem(poem, normalize_topic("草原"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert rhyme_key(fixed["lines"][2][-1]) == "vn"


def test_e_rhyme_fixed_by_generic_line3_bank() -> None:
    poem = {
        "title": "孤灯客思",
        "lines": ["孤灯照夜客", "寒影伴人愁", "客心随月远", "独坐数更筹"],
    }
    fixed = fix_poem(poem, normalize_topic("AI时代的孤独"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert rhyme_key(fixed["lines"][2][-1]) == "e"


def test_ao_rhyme_fixed_by_generic_line3_bank() -> None:
    poem = {
        "title": "草原风远",
        "lines": ["风吹草浪高", "云影掠平皋", "远天连碧霄", "心随雁阵遥"],
    }
    fixed = fix_poem(poem, normalize_topic("草原"))
    assert fixed is not None
    assert validate_poem(fixed).ok
    assert rhyme_key(fixed["lines"][2][-1]) == "ao"
