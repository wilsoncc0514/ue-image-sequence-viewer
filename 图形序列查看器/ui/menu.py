"""Native application menu construction and accessibility state sync."""

from __future__ import annotations

import sys
import tkinter as tk
from typing import Any


def build_app_menu(app: Any) -> None:
    """Build a small native menu without introducing custom menu styling."""
    accelerator = "⌘," if sys.platform == "darwin" else "Ctrl+,"
    menu_bar = tk.Menu(app.root, tearoff=False)
    settings_menu = tk.Menu(menu_bar, tearoff=False)
    settings_menu.add_checkbutton(
        label="减少动态效果",
        variable=app.var_reduce_motion,
        command=app.on_reduce_motion_change,
        accelerator=accelerator,
    )
    menu_bar.add_cascade(label="设置", menu=settings_menu)
    app.root.configure(menu=menu_bar)
    # Tk menus need live Python references on some platforms.
    app.app_menu = menu_bar
    app.settings_menu = settings_menu
    refresh_reduce_motion_menu(app)


def refresh_reduce_motion_menu(app: Any) -> None:
    """Keep the menu honest when the environment forces reduced motion."""
    menu = getattr(app, "settings_menu", None)
    if menu is None:
        return
    forced = app.motion.environment_reduces_motion
    label = "减少动态效果（环境变量已启用）" if forced else "减少动态效果"
    menu.entryconfigure(0, label=label, state=tk.DISABLED if forced else tk.NORMAL)
