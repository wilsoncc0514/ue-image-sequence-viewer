"""Central macOS dark-mode design tokens and ttk style registration.

All color and typography decisions used by the UI live here.  The style profile
uses conservative Tk-compatible font weights to avoid platform-specific Tcl
errors while keeping a macOS-like dark appearance.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass, field
from functools import lru_cache
from tkinter import ttk


@dataclass(frozen=True)
class ColorTokens:
    """Dark-mode color tokens inspired by macOS graphite surfaces."""

    window_bg: str = "#171719"
    sidebar_bg: str = "#1b1b1d"
    panel_bg: str = "#1b1b1d"
    canvas_bg: str = "#070708"
    canvas_border: str = "#242427"

    card_bg: str = "#232326"
    card_bg_alt: str = "#202023"
    card_border: str = "#313135"

    field_bg: str = "#2a2a2d"
    field_border: str = "#38383c"
    field_focus_border: str = "#0a84ff"
    field_disabled_bg: str = "#1c1c1f"

    control_bg: str = "#333337"
    control_hover_bg: str = "#414146"
    control_active_bg: str = "#4a4a50"
    control_disabled_bg: str = "#26262a"

    separator: str = "#303035"
    hairline: str = "#29292d"

    text_primary: str = "#f5f5f7"
    text_secondary: str = "#e5e5ea"
    text_tertiary: str = "#aeaeb2"
    text_quaternary: str = "#8e8e93"
    text_placeholder: str = "#636366"

    accent_primary: str = "#0a84ff"
    accent_primary_hover: str = "#2f9bff"
    accent_primary_active: str = "#5eacff"
    accent_soft: str = "#12324f"

    success: str = "#30d158"
    success_button: str = "#237a3b"
    success_button_hover: str = "#2b9147"
    success_button_active: str = "#1d6531"
    warning: str = "#ff9f0a"
    warning_button: str = "#8a5a00"
    warning_button_hover: str = "#a56d00"
    warning_button_active: str = "#704900"
    danger: str = "#ff453a"
    danger_button: str = "#c9342d"
    danger_button_hover: str = "#e24239"
    danger_button_active: str = "#a92a25"
    system_teal: str = "#64d2ff"


@lru_cache(maxsize=1)
def _available_font_families() -> frozenset[str]:
    """Return available Tk font families once per process."""
    try:
        return frozenset(tkfont.families())
    except tk.TclError:
        return frozenset()


@dataclass(frozen=True)
class FontTokens:
    """Tk-safe font tokens.

    Tk on macOS/Homebrew is inconsistent about SF Pro and non-standard weights.
    The app therefore limits weights to ``normal`` and ``bold`` and falls back to
    Helvetica if SF Pro is unavailable.
    """

    preferred_text: str = "SF Pro Text"
    preferred_display: str = "SF Pro Display"
    fallback: str = "Helvetica"

    def _family(self, preferred: str) -> str:
        return preferred if preferred in _available_font_families() else self.fallback

    @property
    def base(self) -> tuple[str, int, str]:
        return (self._family(self.preferred_text), 11, "normal")

    @property
    def small(self) -> tuple[str, int, str]:
        return (self._family(self.preferred_text), 10, "normal")

    @property
    def footnote(self) -> tuple[str, int, str]:
        return (self._family(self.preferred_text), 10, "normal")

    @property
    def body(self) -> tuple[str, int, str]:
        return (self._family(self.preferred_text), 11, "normal")

    @property
    def body_emphasized(self) -> tuple[str, int, str]:
        return (self._family(self.preferred_text), 11, "bold")

    @property
    def bold(self) -> tuple[str, int, str]:
        return self.body_emphasized

    @property
    def title(self) -> tuple[str, int, str]:
        return (self._family(self.preferred_display), 14, "bold")

    @property
    def section(self) -> tuple[str, int, str]:
        return (self._family(self.preferred_display), 12, "bold")

    @property
    def canvas_status(self) -> tuple[str, int, str]:
        return (self._family(self.preferred_display), 16, "normal")

    @property
    def monospace(self) -> tuple[str, int, str]:
        family = "SF Mono" if "SF Mono" in _available_font_families() else "Menlo"
        return (family, 10, "normal")


@dataclass(frozen=True)
class StyleTokens:
    """Aggregated visual design tokens."""

    colors: ColorTokens = field(default_factory=ColorTokens)
    fonts: FontTokens = field(default_factory=FontTokens)


STYLE = StyleTokens()


def apply_ttk_style(root: tk.Misc) -> None:
    """Apply the app-wide ttk dark-mode style profile."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    c = STYLE.colors
    f = STYLE.fonts

    button_bg_map = [("active", c.control_hover_bg), ("pressed", c.control_active_bg), ("!active", c.control_bg)]
    button_fg_map = [("disabled", c.text_quaternary), ("!disabled", c.text_primary)]
    button_border_map = [("active", c.control_hover_bg), ("pressed", c.control_active_bg)]
    tree_bg_map = [("selected", c.accent_soft)]
    tree_fg_map = [("selected", c.text_primary)]
    scrollbar_bg_map = [("active", c.control_hover_bg), ("!active", c.control_bg)]

    style.configure("TFrame", background=c.window_bg)
    style.configure("Card.TFrame", background=c.card_bg)
    style.configure("TagPanel.TFrame", background=c.panel_bg)

    style.configure(
        "TButton",
        padding=(14, 6),
        font=f.body,
        foreground=c.text_primary,
        background=c.control_bg,
        bordercolor=c.control_bg,
        lightcolor=c.control_bg,
        darkcolor=c.control_bg,
        focuscolor=c.field_focus_border,
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "TButton",
        background=button_bg_map,
        foreground=button_fg_map,
        bordercolor=button_border_map,
        lightcolor=button_border_map,
        darkcolor=button_border_map,
    )

    def configure_semantic_button(
        style_name: str,
        *,
        background: str,
        hover: str,
        active: str,
    ) -> None:
        style.configure(
            style_name,
            padding=(14, 6),
            font=f.body_emphasized,
            foreground=c.text_primary,
            background=background,
            bordercolor=background,
            lightcolor=background,
            darkcolor=background,
            focuscolor=c.field_focus_border,
            relief="flat",
            borderwidth=0,
        )
        style.map(
            style_name,
            background=[("active", hover), ("pressed", active), ("!active", background)],
            foreground=button_fg_map,
        )

    configure_semantic_button(
        "Primary.TButton",
        background=c.accent_primary,
        hover=c.accent_primary_hover,
        active=c.accent_primary_active,
    )
    # Compatibility alias for older callers while the UI migrates to roles.
    configure_semantic_button(
        "Accent.TButton",
        background=c.accent_primary,
        hover=c.accent_primary_hover,
        active=c.accent_primary_active,
    )
    configure_semantic_button(
        "Success.TButton",
        background=c.success_button,
        hover=c.success_button_hover,
        active=c.success_button_active,
    )
    configure_semantic_button(
        "Warning.TButton",
        background=c.warning_button,
        hover=c.warning_button_hover,
        active=c.warning_button_active,
    )
    configure_semantic_button(
        "Destructive.TButton",
        background=c.danger_button,
        hover=c.danger_button_hover,
        active=c.danger_button_active,
    )

    style.configure("Icon.TButton", padding=(4, 2), font=f.base)

    style.configure("TLabel", font=f.body, background=c.window_bg, foreground=c.text_secondary)
    style.configure("Muted.TLabel", font=f.footnote, background=c.window_bg, foreground=c.text_tertiary)
    style.configure("Section.TLabel", font=f.section, background=c.window_bg, foreground=c.text_primary)
    style.configure("PanelMuted.TLabel", font=f.footnote, background=c.panel_bg, foreground=c.text_tertiary)
    style.configure("PanelWarning.TLabel", font=f.footnote, background=c.panel_bg, foreground=c.warning)
    style.configure("PanelSuccess.TLabel", font=f.footnote, background=c.panel_bg, foreground=c.success)

    style.configure(
        "Treeview",
        rowheight=28,
        font=f.body,
        borderwidth=0,
        background=c.sidebar_bg,
        fieldbackground=c.sidebar_bg,
        foreground=c.text_secondary,
    )
    style.configure("Treeview.Heading", font=f.body_emphasized, background=c.panel_bg, foreground=c.text_primary, borderwidth=0)
    style.map("Treeview", background=tree_bg_map, foreground=tree_fg_map)

    style.configure("TScale", background=c.panel_bg, troughcolor=c.field_bg, sliderlength=16, sliderrelief="flat")
    style.map("TScale", background=[("active", c.accent_primary), ("!active", c.accent_primary)])

    for orient in ("Vertical", "Horizontal"):
        style.configure(
            f"{orient}.TScrollbar",
            gripcount=0,
            background=c.control_bg,
            troughcolor=c.panel_bg,
            bordercolor=c.panel_bg,
            arrowcolor=c.text_quaternary,
            relief="flat",
            borderwidth=0,
            width=8,
        )
        style.map(f"{orient}.TScrollbar", background=scrollbar_bg_map)

    # Keep LabelFrame dark if any legacy group boxes remain.
    style.configure(
        "TLabelframe",
        background=c.panel_bg,
        foreground=c.text_secondary,
        bordercolor=c.hairline,
        borderwidth=1,
        relief="solid",
    )
    style.configure("TLabelframe.Label", background=c.panel_bg, foreground=c.text_secondary, font=f.section)
