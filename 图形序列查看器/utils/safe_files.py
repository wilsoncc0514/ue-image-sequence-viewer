"""Failure-safe helpers for user-owned files."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Callable, TypeVar

from utils.logger import logger

T = TypeVar("T")


def require_file_size(path: str | os.PathLike[str], max_bytes: int) -> int:
    """Return the file size or reject files larger than ``max_bytes``."""
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    size = os.path.getsize(path)
    if size > max_bytes:
        raise ValueError(f"文件过大：{size} 字节，允许上限为 {max_bytes} 字节")
    return size


def atomic_write_text(
    target: str | os.PathLike[str],
    writer: Callable[[Any], T],
    *,
    encoding: str = "utf-8-sig",
    newline: str = "",
) -> T:
    """Write text beside ``target`` and replace it only after a full flush.

    The temporary file lives in the target directory so ``os.replace`` stays
    on one filesystem. If writing fails, an existing target remains untouched.
    """
    target_path = Path(target).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            newline=newline,
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            dir=target_path.parent,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            result = writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target_path)
        return result
    except BaseException:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                # The original target is still intact. Cleanup failure should
                # not hide the primary write error.
                logger.error("临时文件清理失败: %s", temp_path, exc_info=True)
        raise
