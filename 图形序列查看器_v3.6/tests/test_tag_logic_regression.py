"""Regression tests for tag normalization helpers."""
from __future__ import annotations
import unittest
from core.tag_logic import TagLogicMixin
from core.seq_state import SeqStateMixin


class Dummy(TagLogicMixin, SeqStateMixin):
    light_tags_def = [{"name": "漏光", "has_sub": False}, {"name": "光变问题", "has_sub": True, "subs": ["＜30%", "＞30%"]}]
    comp_tags_def = []


class TagNormalizeRegressionTests(unittest.TestCase):
    def test_instance_normalize_tag_name_does_not_receive_self(self) -> None:
        self.assertEqual(Dummy()._normalize_tag_name("模型衔接地面处异常反光"), "漏光")

    def test_instance_normalize_sub_value_does_not_receive_self(self) -> None:
        self.assertEqual(Dummy()._normalize_sub_value("光变问题", "明显"), "＞30%")

    def test_seq_state_uses_static_effective_value_helper(self) -> None:
        d = Dummy()
        data = {"status": "", "rerender": False, "light": {"漏光": {"check": False, "text": "", "sub": None}}, "comp": {}}
        self.assertTrue(d._is_tag_state_empty(data))


if __name__ == "__main__":
    unittest.main()
