"""韵脚判定：严格 Style.FINALS 相等，不做宽口径归并。"""

from __future__ import annotations

from pypinyin import Style, lazy_pinyin


def rhyme_key(ch: str) -> str:
    """返回单个汉字的普通话韵母 key（忽略声调，ü 统一为 v）。

    以 pypinyin `style=Style.FINALS, strict=True` 的输出为准，
    例如：衣→i、乌→u、迂→v、威→uei、忧→iou。
    取不到韵母（非汉字/生僻字）时抛 ValueError。
    """
    if not isinstance(ch, str) or len(ch) != 1:
        raise ValueError(f"rhyme_key 需要单个字符: {ch!r}")

    finals = lazy_pinyin(ch, style=Style.FINALS, strict=True, errors="ignore")
    if not finals or not finals[0]:
        raise ValueError(f"无法取得韵母: {ch!r}")
    return finals[0].replace("ü", "v")


def same_rhyme(a: str, b: str) -> bool:
    """第 1、3 句末字是否押韵（韵母相等、忽略声调）。"""
    return rhyme_key(a) == rhyme_key(b)
