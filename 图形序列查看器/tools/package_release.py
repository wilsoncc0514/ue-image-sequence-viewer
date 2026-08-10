"""Build a clean release zip for 图形序列查看器.

Usage:
    python3 tools/package_release.py
"""
from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path

EXCLUDED_DIRS = {
    "__pycache__",
    "__MACOSX",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "tests",
    "tools",
}
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


def build_zip(
    project_root: Path,
    output_path: Path,
    *,
    archive_root_name: str | None = None,
    extra_files: tuple[Path, ...] = (),
) -> None:
    """Write a clean release zip."""
    project_root = project_root.resolve()
    archive_root = archive_root_name or project_root.name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(project_root.rglob("*")):
                if path.is_dir() or not should_include(path.relative_to(project_root)):
                    continue
                zf.write(path, Path(archive_root) / path.relative_to(project_root))
            for path in extra_files:
                resolved = path.resolve()
                if resolved.is_file() and should_include(Path(resolved.name)):
                    zf.write(resolved, Path(archive_root) / resolved.name)
        os.replace(temp_path, output_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def read_project_version(project_root: Path) -> str:
    """Read the configured public version without importing the GUI package."""
    settings_text = (project_root / "config" / "settings.py").read_text(encoding="utf-8")
    match = re.search(r'version:\s*str\s*=\s*"(v\d+\.\d+(?:\.\d+)?)"', settings_text)
    if not match:
        raise ValueError("无法从 config/settings.py 读取版本号")
    return match.group(1)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    version = read_project_version(root)
    release_name = f"图形序列查看器_{version}"
    build_zip(
        root,
        root.parent / f"{release_name}.zip",
        archive_root_name=release_name,
        extra_files=(root.parent / "LICENSE", root.parent / "requirements.txt"),
    )
