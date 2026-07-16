"""Build a clean release zip for 图形序列查看器.

Usage:
    python3 tools/package_release.py
"""
from __future__ import annotations

from pathlib import Path
import zipfile

EXCLUDED_DIRS = {"__pycache__", "__MACOSX", ".git", ".venv", "venv"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}
EXCLUDED_NAMES = {".DS_Store"}
EXCLUDED_PATTERNS = ("old_bak.py",)


def should_include(path: Path) -> bool:
    """Return whether ``path`` should be included in the release archive."""
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return not any(path.name.endswith(pattern) for pattern in EXCLUDED_PATTERNS)


def build_zip(project_root: Path, output_path: Path) -> None:
    """Write a clean release zip."""
    project_root = project_root.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(project_root.rglob("*")):
            if path.is_dir() or not should_include(path.relative_to(project_root)):
                continue
            zf.write(path, project_root.name / path.relative_to(project_root))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    build_zip(root, root.parent / f"{root.name}.zip")
