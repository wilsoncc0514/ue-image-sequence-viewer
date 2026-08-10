"""Pure QC tag rule engine.

This module contains no Tkinter code. It normalizes legacy tag/sub-option names
and infers QC status / rerender requirements from active tag items.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ActiveTagItem:
    """Effective tag item extracted from the UI or imported state."""

    tag_name: str
    checked: bool
    text: str = ""
    sub_value: str = ""


def normalize_tag_name(tag_name: object) -> str:
    """Normalize legacy tag names to the current display names."""
    raw = str(tag_name or "").strip()
    return {"模型衔接地面处异常反光": "漏光"}.get(raw, raw)


def normalize_sub_value(tag_name: object, sub_value: object) -> str:
    """Normalize legacy sub-option values for a tag."""
    tag = normalize_tag_name(tag_name)
    raw = str(sub_value or "").strip()
    if tag == "拖影":
        return {"轻微": "小范围", "明显": "大范围"}.get(raw, raw)
    if tag == "光变问题":
        return {
            "轻微": "＜30%",
            "中等": "＞30%",
            "明显": "＞30%",
            "<30%": "＜30%",
            "＜30": "＜30%",
            "<30": "＜30%",
            ">30%": "＞30%",
            "＞30": "＞30%",
            ">30": "＞30%",
        }.get(raw, raw)
    return raw


def status_pending_sub_values() -> set[tuple[str, str]]:
    """Return tag/sub pairs that are pending-only when no other issue exists."""
    return {("拖影", "小范围"), ("光变问题", "＜30%")}


def status_rerender_triggers() -> set[tuple[str, str | None]]:
    """Return tag/sub pairs that force rerender and failed status."""
    return {
        ("漏光", None),
        ("反光白噪点", None),
        ("构图规避光变", None),
        ("光变问题", "＞30%"),
        ("拖影", "大范围"),
    }


def normalize_active_items(items: Iterable[ActiveTagItem]) -> list[ActiveTagItem]:
    """Normalize active tag items and drop empty entries."""
    normalized: list[ActiveTagItem] = []
    for item in items:
        tag = normalize_tag_name(item.tag_name)
        text = str(item.text or "").strip()
        checked = bool(item.checked)
        sub = normalize_sub_value(tag, item.sub_value) if checked else ""
        if not checked and not text:
            continue
        normalized.append(ActiveTagItem(tag, checked, text, sub))
    return normalized


def tags_require_rerender(items: Iterable[ActiveTagItem]) -> bool:
    """Return whether the active tag items force rerender."""
    triggers = status_rerender_triggers()
    for item in normalize_active_items(items):
        if (item.tag_name, None) in triggers:
            return True
        if item.checked and (item.tag_name, item.sub_value) in triggers:
            return True
    return False


def infer_status_from_tags(items: Iterable[ActiveTagItem]) -> str | None:
    """Infer QC status from active tag items.

    Rules:
        - Only ``拖影(小范围)`` and/or ``光变问题(＜30%)`` without text => ``待定``.
        - Rerender triggers or any other effective issue => ``不合格``.
        - No active issues => ``None`` so manual status is not overwritten.
    """
    normalized = normalize_active_items(items)
    if not normalized:
        return None

    pending_pairs = status_pending_sub_values()
    for item in normalized:
        if item.checked and (item.tag_name, item.sub_value) in pending_pairs and not item.text:
            continue
        return "不合格"
    return "待定"
