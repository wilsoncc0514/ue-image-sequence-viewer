"""Mouse wheel binding helpers for scrollable UI regions."""
from __future__ import annotations

import tkinter as tk


def _wheel_units(event: tk.Event) -> int:
    if getattr(event, 'num', None) == 4:
        return -3
    if getattr(event, 'num', None) == 5:
        return 3
    delta = getattr(event, 'delta', 0)
    return -3 if delta > 0 else 3

def bind_mousewheel_scroll(canvas: tk.Canvas, root_widget: tk.Misc) -> None:
    """Bind mouse wheel scrolling to a canvas and its current descendants.

    Tkinter does not bubble wheel events consistently on macOS/Windows/Linux.
    This recursively binds the handler to existing right-panel controls so the
    tag panel scrolls whenever the pointer is inside it, not only on the narrow
    scrollbar.
    """

    def on_wheel(event: tk.Event) -> str:
        canvas.yview_scroll(_wheel_units(event), 'units')
        return 'break'

    def bind_recursive(widget: tk.Misc) -> None:
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            widget.bind(sequence, on_wheel, add='+')
        for child in widget.winfo_children():
            bind_recursive(child)
    bind_recursive(root_widget)
    for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
        canvas.bind(sequence, on_wheel, add='+')
