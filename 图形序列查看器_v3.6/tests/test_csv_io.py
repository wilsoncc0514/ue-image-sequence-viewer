"""CSV tag parsing tests."""
from __future__ import annotations

import unittest

from core.csv_io import CsvIOMixin
from core.tag_engine import normalize_sub_value


class DummyCsv(CsvIOMixin):
    def _normalize_sub_value(self, tag_name: str, sub_value: str) -> str:
        return normalize_sub_value(tag_name, sub_value)


class CsvParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = DummyCsv()
        self.defs = [
            {"name": "反光", "has_sub": False},
            {"name": "反光白噪点", "has_sub": False},
            {"name": "光变问题", "has_sub": True, "subs": ["＜30%", "＞30%"]},
        ]
        self.state = {
            "反光": {"check": False, "text": "", "sub": None},
            "反光白噪点": {"check": False, "text": "", "sub": None},
            "光变问题": {"check": False, "text": "", "sub": ""},
        }

    def test_empty_string_does_nothing(self) -> None:
        self.parser._parse_and_apply_tags("", self.state, self.defs)
        self.assertFalse(any(v["check"] for v in self.state.values()))

    def test_longer_tag_name_wins(self) -> None:
        self.parser._parse_and_apply_tags("反光白噪点", self.state, self.defs)
        self.assertTrue(self.state["反光白噪点"]["check"])
        self.assertFalse(self.state["反光"]["check"])

    def test_sub_and_text_parse(self) -> None:
        self.parser._parse_and_apply_tags("光变问题(>30%): 明显跳变", self.state, self.defs)
        self.assertTrue(self.state["光变问题"]["check"])
        self.assertEqual(self.state["光变问题"]["sub"], "＞30%")
        self.assertEqual(self.state["光变问题"]["text"], "明显跳变")

    def test_missing_csv_cell_is_empty_text(self) -> None:
        self.assertEqual(self.parser._csv_text(None), "")
        self.assertEqual(self.parser._csv_text("  待定  "), "待定")


if __name__ == "__main__":
    unittest.main()
