"""Regression tests for tag normalization helpers."""
from __future__ import annotations

import unittest

from core.seq_state import SeqStateMixin
from core.tag_logic import TagLogicMixin


class Dummy(TagLogicMixin, SeqStateMixin):
    light_tags_def = [{"name": "光变问题", "has_sub": True, "subs": ["＜30%", "＞30%"]}]
    comp_tags_def = [{"name": "漏光", "has_sub": False}]


class TagNormalizeRegressionTests(unittest.TestCase):
    def test_instance_normalize_tag_name_does_not_receive_self(self) -> None:
        self.assertEqual(Dummy()._normalize_tag_name("模型衔接地面处异常反光"), "漏光")

    def test_instance_normalize_sub_value_does_not_receive_self(self) -> None:
        self.assertEqual(Dummy()._normalize_sub_value("光变问题", "明显"), "＞30%")

    def test_seq_state_uses_static_effective_value_helper(self) -> None:
        d = Dummy()
        data = {"status": "", "rerender": False, "light": {"漏光": {"check": False, "text": "", "sub": None}}, "comp": {}}
        self.assertTrue(d._is_tag_state_empty(data))

    def test_normalize_state_moves_legacy_light_leak_to_composition(self) -> None:
        d = Dummy()
        data = {
            "status": "不合格",
            "rerender": True,
            "light": {"漏光": {"check": True, "text": "地面边缘", "sub": None}},
            "comp": {},
        }

        normalized = d._normalize_tag_state(data)

        self.assertNotIn("漏光", normalized["light"])
        self.assertEqual(
            normalized["comp"]["漏光"],
            {"check": True, "text": "地面边缘", "sub": None},
        )


if __name__ == "__main__":
    unittest.main()
