"""Behavioral regressions for the October data-integrity audit."""
from __future__ import annotations

import io
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.settings import AppConfig
from core.csv_io import CsvIOMixin
from core.folder_scanner import scan_image_folder
from core.seq_state import SeqStateMixin
from core.tag_codec import encode_note, parse_tag_cell
from models.tag_definitions import get_default_comp_tags, get_default_light_tags
from utils.logger import DelayedFileHandler, default_log_directory


class CsvSubject(CsvIOMixin, SeqStateMixin):
    def __init__(self):
        self.config = AppConfig()
        self.light_tags_def = get_default_light_tags()
        self.comp_tags_def = get_default_comp_tags()
        self.tag_data = {"seq01": self._create_empty_tag_state()}
        self.seq_rel_paths = ["seq01"]
        self.root_folder_name = "test"
        self.qc_by_name = "auditor"

    def _normalize_seq(self, value):
        return str(value).strip()


class CsvIntegrityTests(unittest.TestCase):
    def test_export_import_preserves_multiline_punctuation_and_tag_names(self):
        subject = CsvSubject()
        notes = '前景、背景\n第2行，其他: "漏光"\\路径 (括号)'
        subject.tag_data["seq01"]["status"] = "不合格"
        subject.tag_data["seq01"]["comp"]["漏光"].update(check=True, text=notes)
        subject.tag_data["seq01"]["light"]["反光多帧异常、不一致"].update(check=True, text=notes)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "中文 往返.csv"
            subject._write_export_csv(path)
            result = subject._read_csv_import(path)
        self.assertEqual(result.updates["seq01"]["comp"]["漏光"]["text"], notes)
        self.assertEqual(result.updates["seq01"]["light"]["反光多帧异常、不一致"]["text"], notes)

    def test_light_note_mentioning_leak_does_not_migrate(self):
        subject = CsvSubject()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.csv"
            path.write_text('seq,光影问题,构图问题\nseq01,其他: 已确认没有漏光,\n', encoding="utf-8-sig")
            state = subject._read_csv_import(path).updates["seq01"]
        self.assertFalse(state["comp"]["漏光"]["check"])
        self.assertEqual(state["light"]["其他"]["text"], "已确认没有漏光")

    def test_real_old_leak_and_legacy_alias_migrate_with_notes(self):
        for name in ("漏光", "模型衔接地面处异常反光"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                subject = CsvSubject()
                path = Path(tmp) / "legacy.csv"
                path.write_text(f'seq,光影问题,构图问题\nseq01,拖影(小范围)、{name}: 前景、背景,\n', encoding="utf-8-sig")
                state = subject._read_csv_import(path).updates["seq01"]
                self.assertTrue(state["light"]["拖影"]["check"])
                self.assertTrue(state["comp"]["漏光"]["check"])
                self.assertEqual(state["comp"]["漏光"]["text"], "前景、背景")

    def test_quoted_note_cannot_create_another_tag(self):
        note = "正常、漏光: 无异常"
        parsed = parse_tag_cell("其他: " + encode_note(note), ["其他", "漏光"])
        self.assertEqual(set(parsed), {"其他"})
        self.assertEqual(parsed["其他"]["text"], note)

    def test_legacy_unquoted_multiline_note_is_kept(self):
        parsed = parse_tag_cell("其他: 第一行、第二行\n第三行", ["其他", "漏光"])
        self.assertEqual(parsed["其他"]["text"], "第一行、第二行\n第三行")


class ScanAndLogIntegrityTests(unittest.TestCase):
    def test_inaccessible_subdirectory_fails_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocked = Path(tmp) / "blocked"
            blocked.mkdir()
            original = os.scandir

            def fail(path):
                if os.fspath(path) == str(blocked):
                    raise PermissionError("inaccessible child")
                return original(path)

            with patch("os.scandir", side_effect=fail), self.assertRaises(PermissionError):
                scan_image_folder(tmp, image_extensions=(".png",), max_entries=100, max_depth=4)

    def test_log_creation_failure_preserves_original_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocked = Path(tmp) / "file-not-directory"
            blocked.write_text("x")
            handler = DelayedFileHandler(blocked)
            record = logging.LogRecord("test", logging.ERROR, __file__, 1, "原始错误", (), None)
            stderr = io.StringIO()
            with patch("sys.stderr", stderr):
                handler.emit(record)
            handler.close()
            self.assertIn("原始错误", stderr.getvalue())
            self.assertIn("日志写入失败", stderr.getvalue())

    def test_log_write_failure_uses_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = DelayedFileHandler(tmp)
            record = logging.LogRecord("test", logging.ERROR, __file__, 1, "原始错误", (), None)
            handler.emit(record)
            assert handler.file_handler is not None
            with patch.object(handler.file_handler.stream, "write", side_effect=OSError("disk full")):
                stderr = io.StringIO()
                with patch("sys.stderr", stderr):
                    handler.emit(record)
            handler.close()
            self.assertIn("原始错误", stderr.getvalue())

    def test_logging_does_not_raise_without_console(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocked = Path(tmp) / "blocked"
            blocked.write_text("x")
            handler = DelayedFileHandler(blocked)
            with patch("sys.stderr", None), patch("sys.__stderr__", None):
                handler.emit(logging.LogRecord("test", logging.ERROR, __file__, 1, "error", (), None))
            handler.close()

    def test_default_log_location_is_user_directory(self):
        self.assertTrue(default_log_directory().is_relative_to(Path.home()))
