"""Content-driven height management for multiline Tk text fields."""

from __future__ import annotations

import tkinter as tk
from typing import Any


def resize_text_to_content(widget: Any, *, min_lines: int = 1) -> int:
    """Resize ``widget`` to all wrapped display lines and return its height."""
    # Tk's implicit trailing newline closes the final wrapped display row.
    # Stopping at ``end-1c`` therefore undercounts every non-empty paragraph.
    counted = widget.count("1.0", "end", "displaylines")
    display_lines = int(counted[0]) if counted else 0
    target = max(min_lines, display_lines)
    if int(widget.cget("height")) != target:
        widget.configure(height=target)
    return target


def bind_auto_height(widget: tk.Text, *, min_lines: int = 1) -> None:
    """Keep one Text widget tall enough after edits and width changes."""
    pending_job: Any = None

    def apply() -> None:
        nonlocal pending_job
        pending_job = None
        try:
            resize_text_to_content(widget, min_lines=min_lines)
        except tk.TclError:
            return

    def schedule(_event: Any = None) -> None:
        nonlocal pending_job
        if pending_job is not None:
            try:
                widget.after_cancel(pending_job)
            except tk.TclError:
                return
        pending_job = widget.after_idle(apply)

    def on_modified(_event: Any = None) -> None:
        try:
            widget.edit_modified(False)
        except tk.TclError:
            return
        schedule()

    widget.bind("<<Modified>>", on_modified, add="+")
    widget.bind("<Configure>", schedule, add="+")
    widget.edit_modified(False)
    schedule()
