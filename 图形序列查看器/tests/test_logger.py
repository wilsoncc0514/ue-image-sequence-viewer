"""Logging lifecycle tests that keep expected test failures off disk."""

from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from utils.logger import DelayedFileHandler, logger


class LoggerTests(unittest.TestCase):
    def test_import_does_not_enable_runtime_file_logging(self) -> None:
        self.assertFalse(any(isinstance(handler, DelayedFileHandler) for handler in logger.handlers))

    def test_delayed_handler_creates_one_utf8_log_on_first_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            handler = DelayedFileHandler(log_dir=log_dir)
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="真实错误",
                args=(),
                exc_info=None,
            )

            self.assertEqual(list(log_dir.glob("*.log")), [])
            handler.emit(record)
            log_files = list(log_dir.glob("*.log"))
            handler.emit(record)
            handler.close()

            self.assertEqual(len(log_files), 1)
            self.assertEqual(list(log_dir.glob("*.log")), log_files)
            self.assertIn("真实错误", log_files[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
