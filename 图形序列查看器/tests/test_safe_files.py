"""Failure-safe file replacement tests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from utils.safe_files import atomic_write_text, require_file_size


class AtomicWriteTests(unittest.TestCase):
    def test_failed_write_preserves_existing_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="中文 路径 ") as tmp:
            target = Path(tmp) / "结果.csv"
            target.write_text("old", encoding="utf-8")

            def fail_after_partial_write(handle):
                handle.write("partial")
                raise OSError("disk full")

            with self.assertRaisesRegex(OSError, "disk full"):
                atomic_write_text(target, fail_after_partial_write, encoding="utf-8")

            self.assertEqual(target.read_text(encoding="utf-8"), "old")
            self.assertEqual(list(target.parent.glob(".*.tmp")), [])

    def test_success_replaces_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "result.csv"
            target.write_text("old", encoding="utf-8")
            result = atomic_write_text(target, lambda handle: (handle.write("new"), 1)[1], encoding="utf-8")
            self.assertEqual(result, 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "new")

    def test_file_size_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "input.csv"
            target.write_bytes(b"1234")
            self.assertEqual(require_file_size(target, 4), 4)
            with self.assertRaisesRegex(ValueError, "文件过大"):
                require_file_size(target, 3)


if __name__ == "__main__":
    unittest.main()
