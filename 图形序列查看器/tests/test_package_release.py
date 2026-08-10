"""Tests for release package filtering."""
from __future__ import annotations

import unittest
from pathlib import Path

from tools.package_release import read_project_version, should_include


class PackageReleaseTests(unittest.TestCase):
    """Validate release exclusion rules."""

    def test_excludes_runtime_artifacts(self) -> None:
        self.assertFalse(should_include(Path("__pycache__/x.pyc")))
        self.assertFalse(should_include(Path(".mypy_cache/3.10/cache.db")))
        self.assertFalse(should_include(Path(".pytest_cache/v/cache/nodeids")))
        self.assertFalse(should_include(Path(".ruff_cache/0.12/cache")))
        self.assertFalse(should_include(Path(".DS_Store")))
        self.assertFalse(should_include(Path("20260522.log")))
        self.assertFalse(should_include(Path("ui/layout_v3_old_bak.py")))
        self.assertFalse(should_include(Path("tests/test_config.py")))
        self.assertFalse(should_include(Path("tools/package_release.py")))

    def test_includes_source_files(self) -> None:
        self.assertTrue(should_include(Path("ui/app.py")))
        self.assertTrue(should_include(Path("README.md")))
        self.assertTrue(should_include(Path("启动图形序列查看器.command")))
        self.assertTrue(should_include(Path("启动图形序列查看器.bat")))

    def test_reads_release_version(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        self.assertEqual(read_project_version(project_root), "v3.7.0")


if __name__ == "__main__":
    unittest.main()
