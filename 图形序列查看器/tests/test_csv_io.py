"""CSV tag parsing tests."""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from config.settings import AppConfig, SafetyConfig
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

    def test_spreadsheet_formula_is_escaped_and_decoded(self) -> None:
        escaped = self.parser._excel_safe_cell("=HYPERLINK(\"https://example.invalid\")")
        self.assertTrue(escaped.startswith("'="))
        self.assertEqual(self.parser._csv_text(escaped), "=HYPERLINK(\"https://example.invalid\")")


class CsvTransactionTests(unittest.TestCase):
    class Dummy(CsvIOMixin):
        def __init__(self) -> None:
            self.config = AppConfig(safety=SafetyConfig(max_csv_bytes=4096, max_csv_rows=10))
            self.is_loading_state = False
            self.tag_data = {"seq01": {"original": True}, "seq02": {"original": True}}
            self.root_folder_name = "root"
            self.qc_by_name = "old"
            self.current_tree_node = None
            self.light_tags_def = [{"name": "反光", "has_sub": False}]
            self.comp_tags_def = []

        @staticmethod
        def _normalize_seq(value):
            return str(value or "").strip()

        def _create_empty_tag_state(self, status="", rerender=False):
            return {
                "status": status,
                "rerender": rerender,
                "light": {"反光": {"check": False, "text": "", "sub": None}},
                "comp": {},
            }

        @staticmethod
        def _normalize_tag_state(state):
            return state

        @staticmethod
        def _is_tag_state_empty(state):
            return not state.get("status") and not state.get("rerender") and not any(
                value.get("check") for value in state.get("light", {}).values()
            )

        def _mark_export_dirty(self):
            pass

        def _refresh_seq_stats(self):
            pass

        def _apply_tree_state_after_csv_import(self):
            pass

    def test_failed_import_preserves_existing_state(self) -> None:
        dummy = self.Dummy()
        original = dict(dummy.tag_data)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.csv"
            path.write_text(
                "seq,状态（合格/不合格/待定）,光影问题\nseq01,不合格,反光\nseq02,合格,\n",
                encoding="utf-8-sig",
            )
            original_parser = dummy._parse_and_apply_tags
            calls = 0

            def fail_second(tag_str, state_dict, tag_defs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise ValueError("bad row")
                return original_parser(tag_str, state_dict, tag_defs)

            with patch.object(dummy, "_parse_and_apply_tags", side_effect=fail_second):
                self.assertIsNone(dummy.import_csv(path, show_message=False))
        self.assertEqual(dummy.tag_data, original)
        self.assertEqual(dummy.qc_by_name, "old")
        self.assertFalse(dummy.is_loading_state)

    def test_successful_import_commits_all_rows(self) -> None:
        dummy = self.Dummy()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.csv"
            path.write_text(
                "seq,状态（合格/不合格/待定）,光影问题,QC by\nseq01,不合格,反光,Wilson\nseq02,合格,,\n",
                encoding="utf-8-sig",
            )
            result = dummy.import_csv(path, show_message=False)
        self.assertEqual(result["matched"], 2)
        self.assertEqual(dummy.tag_data["seq01"]["status"], "不合格")
        self.assertEqual(dummy.tag_data["seq02"]["status"], "合格")
        self.assertEqual(dummy.qc_by_name, "Wilson")

    def test_row_limit_failure_preserves_existing_state(self) -> None:
        dummy = self.Dummy()
        dummy.config = replace(dummy.config, safety=replace(dummy.config.safety, max_csv_rows=1))
        original = dict(dummy.tag_data)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "too-many.csv"
            path.write_text(
                "seq,状态（合格/不合格/待定）\nseq01,不合格\nseq02,合格\n",
                encoding="utf-8-sig",
            )
            self.assertIsNone(dummy.import_csv(path, show_message=False))
        self.assertEqual(dummy.tag_data, original)


if __name__ == "__main__":
    unittest.main()
