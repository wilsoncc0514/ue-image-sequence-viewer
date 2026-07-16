"""Application entry point."""
from __future__ import annotations
from typing import Any
import tkinter as tk
from config.settings import AppConfig
from ui.app import FrameScrubber
from utils.errors import install_tk_exception_handler
from utils.logger import install_exception_hook

def main() -> None:
    """Start the Tkinter application."""
    install_exception_hook()
    config = AppConfig()
    root = tk.Tk()
    install_tk_exception_handler(root)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    FrameScrubber(root, config=config)
    root.geometry(config.window.default_geometry)
    root.minsize(config.window.min_width, config.window.min_height)
    root.focus_set()
    root.mainloop()
if __name__ == '__main__':
    main()
