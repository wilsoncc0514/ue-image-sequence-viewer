"""Reusable dark-mode Tk components for the main layout.

These helper factories reduce duplicated widget styling in ``ui.layout`` and
make future UI adjustments much cheaper.
"""
from __future__ import annotations

from typing import Any, Iterable
import tkinter as tk
from ui.styles import STYLE


def make_card(parent: tk.Misc, title: str, *, padx: int = 12, pady: tuple[int, int] = (0, 8)) -> tuple[tk.Frame, tk.Frame]:
    """Create a card-style section and return ``(card, body)``."""
    c = STYLE.colors
    f = STYLE.fonts
    card = tk.Frame(
        parent,
        bg=c.card_bg,
        highlightthickness=1,
        highlightbackground=c.card_border,
        highlightcolor=c.card_border,
        bd=0,
    )
    card.pack(fill=tk.X, padx=padx, pady=pady)
    header = tk.Label(card, text=title, bg=c.card_bg, fg=c.text_secondary, font=f.section, anchor="w")
    header.pack(fill=tk.X, padx=10, pady=(8, 3))
    body = tk.Frame(card, bg=c.card_bg)
    body.pack(fill=tk.X, padx=6, pady=(0, 8))
    return card, body


def make_checkbutton(parent: tk.Misc, *, text: str, variable: tk.Variable, command: Any | None = None) -> tk.Checkbutton:
    """Create a dark-mode checkbutton."""
    c = STYLE.colors
    return tk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        command=command,
        bg=c.card_bg,
        fg=c.text_secondary,
        selectcolor=c.control_active_bg,
        activebackground=c.card_bg,
        activeforeground=c.text_primary,
        anchor="w",
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=0,
    )


def make_radiobutton(parent: tk.Misc, *, text: str, variable: tk.Variable, value: str) -> tk.Radiobutton:
    """Create a dark-mode radiobutton."""
    c = STYLE.colors
    return tk.Radiobutton(
        parent,
        text=text,
        variable=variable,
        value=value,
        bg=c.card_bg,
        fg=c.text_secondary,
        selectcolor=c.control_active_bg,
        activebackground=c.card_bg,
        activeforeground=c.text_primary,
        anchor="w",
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=0,
    )


def make_entry(parent: tk.Misc, *, textvariable: tk.StringVar) -> tk.Entry:
    """Create a compact dark input field."""
    c = STYLE.colors
    return tk.Entry(
        parent,
        textvariable=textvariable,
        bg=c.field_bg,
        fg=c.text_primary,
        insertbackground=c.text_primary,
        disabledbackground=c.field_disabled_bg,
        disabledforeground=c.text_quaternary,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=c.field_border,
        highlightcolor=c.field_focus_border,
    )


def grid_status_options(parent: tk.Misc, options: Iterable[tuple[str, str]], variable: tk.StringVar) -> list[tk.Radiobutton]:
    """Create status radiobuttons in two columns."""
    buttons: list[tk.Radiobutton] = []
    for idx, (value, label) in enumerate(options):
        rb = make_radiobutton(parent, text=label, variable=variable, value=value)
        rb.grid(row=idx // 2, column=idx % 2, sticky="w", padx=6, pady=3)
        buttons.append(rb)
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_columnconfigure(1, weight=1)
    return buttons
