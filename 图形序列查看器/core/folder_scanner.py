"""Bounded, cancellable folder scanning independent from Tkinter."""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from utils.helpers import natural_key


class ScanCancelled(Exception):
    """Raised when a caller requests cancellation."""


class ScanLimitExceeded(ValueError):
    """Raised when an untrusted directory exceeds configured boundaries."""


@dataclass(frozen=True)
class ScannedDirectory:
    """One directory and its filename-prefix image groups."""

    path: str
    parent_path: str | None
    name: str
    rel_path: str
    groups: tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True)
class FolderScanResult:
    """Immutable result safe to transfer from a worker to the Tk thread."""

    root_path: str
    directories: tuple[ScannedDirectory, ...]
    image_count: int
    entry_count: int


def extract_prefix(filename: str) -> str:
    """Return the sequence prefix used to group numbered frames."""
    import re

    base = os.path.splitext(filename)[0]
    match = re.search(r"^(.*?)[_\-\s]?\d+$", base)
    return match.group(1) if match and match.group(1) else "Ungrouped"


def scan_image_folder(
    folder_path: str,
    *,
    image_extensions: Iterable[str],
    max_entries: int,
    max_depth: int,
    cancel_event: threading.Event | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> FolderScanResult:
    """Scan an image tree with explicit count/depth bounds and cancellation."""
    if max_entries <= 0 or max_depth < 0:
        raise ValueError("扫描上限配置无效")
    root_path = os.path.abspath(os.path.normpath(folder_path))
    if not os.path.isdir(root_path):
        raise NotADirectoryError(root_path)

    allowed = {str(ext).lower() for ext in image_extensions}
    directories: list[ScannedDirectory] = []
    image_count = 0
    entry_count = 0

    for root_dir, dirs, files in os.walk(root_path, followlinks=False):
        if cancel_event is not None and cancel_event.is_set():
            raise ScanCancelled("文件夹扫描已取消")

        relative = os.path.relpath(root_dir, root_path)
        depth = 0 if relative == "." else len(Path(relative).parts)
        if depth >= max_depth:
            dirs.clear()
        dirs[:] = sorted(
            (name for name in dirs if not os.path.islink(os.path.join(root_dir, name))),
            key=natural_key,
        )

        entry_count += len(dirs) + len(files)
        if entry_count > max_entries:
            raise ScanLimitExceeded(f"目录项目数超过上限 {max_entries}")

        image_names = sorted(
            (
                name
                for name in files
                if not name.startswith("._")
                and name not in {".DS_Store", "Thumbs.db"}
                and os.path.splitext(name)[1].lower() in allowed
            ),
            key=natural_key,
        )
        grouped: dict[str, list[str]] = {}
        for index, name in enumerate(image_names):
            if index % 256 == 0 and cancel_event is not None and cancel_event.is_set():
                raise ScanCancelled("文件夹扫描已取消")
            grouped.setdefault(extract_prefix(name), []).append(os.path.join(root_dir, name))
        groups = tuple(
            (prefix, tuple(paths))
            for prefix, paths in sorted(grouped.items(), key=lambda item: natural_key(item[0]))
        )
        image_count += len(image_names)
        directories.append(
            ScannedDirectory(
                path=root_dir,
                parent_path=None if root_dir == root_path else os.path.dirname(root_dir),
                name=os.path.basename(root_dir),
                rel_path=relative,
                groups=groups,
            )
        )
        if progress is not None:
            progress(entry_count, image_count)

    return FolderScanResult(root_path, tuple(directories), image_count, entry_count)
