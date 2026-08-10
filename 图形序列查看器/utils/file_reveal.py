"""Open a platform file manager with one existing file selected."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def build_reveal_command(path: str | Path, *, platform: str | None = None) -> list[str]:
    """Validate ``path`` and return a fixed, shell-free reveal command."""
    resolved = Path(path).expanduser().resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"不是可定位的文件：{resolved}")
    target_platform = platform or sys.platform
    if target_platform == "darwin":
        return ["open", "-R", str(resolved)]
    if target_platform == "win32":
        return ["explorer", f"/select,{resolved}"]
    return ["xdg-open", str(resolved.parent)]


def reveal_file(path: str | Path) -> subprocess.Popen[bytes]:
    """Launch the native file manager without invoking a command shell."""
    return subprocess.Popen(
        build_reveal_command(path),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
