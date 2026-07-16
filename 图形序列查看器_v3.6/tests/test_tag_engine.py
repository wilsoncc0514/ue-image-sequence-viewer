"""Pure tag-engine tests."""
from __future__ import annotations

import unittest

from core.tag_engine import ActiveTagItem, infer_status_from_tags, normalize_sub_value, normalize_tag_name, tags_require_rerender


class TagEngineTests(unittest.TestCase):
    def test_legacy_name_and_sub_normalization(self) -> None:
        self.assertEqual(normalize_tag_name("模型衔接地面处异常反光"), "漏光")
        self.assertEqual(normalize_sub_value("拖影", "轻微"), "小范围")
        self.assertEqual(normalize_sub_value("光变问题", "明显"), "＞30%")

    def test_pending_only_rules(self) -> None:
        items = [ActiveTagItem("拖影", True, "", "小范围"), ActiveTagItem("光变问题", True, "", "＜30%")]
        self.assertEqual(infer_status_from_tags(items), "待定")
        self.assertFalse(tags_require_rerender(items))

    def test_rerender_trigger_rules(self) -> None:
        items = [ActiveTagItem("光变问题", True, "", "＞30%")]
        self.assertEqual(infer_status_from_tags(items), "不合格")
        self.assertTrue(tags_require_rerender(items))

    def test_text_on_pending_issue_becomes_failed(self) -> None:
        items = [ActiveTagItem("拖影", True, "需要复查", "小范围")]
        self.assertEqual(infer_status_from_tags(items), "不合格")


if __name__ == "__main__":
    unittest.main()
