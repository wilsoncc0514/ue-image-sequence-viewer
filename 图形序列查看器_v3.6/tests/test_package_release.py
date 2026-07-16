"""Tests for release package filtering."""
from __future__ import annotations

import unittest
from pathlib import Path
from tools.package_release import should_include


class PackageReleaseTests(unittest.TestCase):
    """Validate release exclusion rules."""

    def test_excludes_runtime_artifacts(self) -> None:
        self.assertFalse(should_include(Path("__pycache__/x.pyc")))
        self.assertFalse(should_include(Path(".DS_Store")))
        self.assertFalse(should_include(Path("20260522.log")))
        self.assertFalse(should_include(Path("ui/layout_v3_old_bak.py")))

    def test_includes_source_files(self) -> None:
        self.assertTrue(should_include(Path("ui/app.py")))
        self.assertTrue(should_include(Path("README.md")))


if __name__ == "__main__":
    unittest.main()
