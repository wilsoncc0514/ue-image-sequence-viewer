"""Static cross-platform launcher checks."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_macos_launcher_is_portable_and_executable(self) -> None:
        path = ROOT / "启动图形序列查看器-Mac.command"
        launcher = path.read_text(encoding="utf-8")

        self.assertIn("${0:A:h}", launcher)
        self.assertIn(".venv/bin/python3", launcher)
        self.assertIn("main.py", launcher)
        self.assertIn('"$@"', launcher)
        self.assertTrue(os.access(path, os.X_OK))

    def test_windows_launcher_uses_gui_python_and_forwards_arguments(self) -> None:
        launcher = (ROOT / "启动图形序列查看器-Windows.bat").read_text(encoding="utf-8")

        self.assertIn("%~dp0", launcher)
        self.assertIn(r".venv\Scripts\pythonw.exe", launcher)
        self.assertIn('start ""', launcher)
        self.assertIn("sys.version_info.__ge__((3, 10))", launcher)
        self.assertIn("%*", launcher)
        self.assertIn('if /I "%~1"=="--smoke-test"', launcher)
        self.assertIn('"%PY_CHECK%" %PY_ARGS% "%APP_DIR%main.py" %*', launcher)
        self.assertNotIn("tasklist", launcher.lower())

    def test_windows_ci_runs_the_synchronous_launcher_smoke_test(self) -> None:
        workflow = (ROOT.parent / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        linux_job, windows_job = workflow.split("  windows-smoke:", maxsplit=1)

        self.assertIn("mypy", linux_job)
        self.assertNotIn("mypy", windows_job)
        self.assertIn("runs-on: windows-latest", windows_job)
        self.assertIn('call "启动图形序列查看器-Windows.bat" --smoke-test', windows_job)

    def test_ambiguous_legacy_launcher_names_are_removed(self) -> None:
        self.assertFalse((ROOT / "启动图形序列查看器.command").exists())
        self.assertFalse((ROOT / "启动图形序列查看器.bat").exists())

    @unittest.skipUnless(sys.platform == "win32", "requires Windows cmd")
    def test_windows_smoke_propagates_program_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            launcher = Path(tmp) / "launch.bat"
            shutil.copyfile(ROOT / "启动图形序列查看器-Windows.bat", launcher)
            (Path(tmp) / "main.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
            result = subprocess.run(["cmd", "/c", str(launcher), "--smoke-test"], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 7)


if __name__ == "__main__":
    unittest.main()
