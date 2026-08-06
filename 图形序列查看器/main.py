"""Application entry point."""
from __future__ import annotations

import argparse
import ctypes
import sys
import tkinter as tk

from config.settings import AppConfig
from ui.app import FrameScrubber
from utils.errors import install_tk_exception_handler
from utils.logger import install_exception_hook, logger


def main(argv: list[str] | None = None) -> None:
    """Start the Tkinter application."""
    parser = argparse.ArgumentParser(description="图形序列查看器")
    parser.add_argument("--smoke-test", action="store_true", help="创建并关闭主窗口，用于发布前 GUI 检查")
    args = parser.parse_args(argv)
    install_exception_hook()
    config = AppConfig()
    root = tk.Tk()
    install_tk_exception_handler(root)
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            logger.error("无法启用 Windows DPI 感知", exc_info=True)
    app = FrameScrubber(root, config=config)
    root.geometry(config.window.default_geometry)
    root.minsize(config.window.min_width, config.window.min_height)
    root.focus_set()
    if args.smoke_test:
        root.after(250, app._shutdown_app)
    root.mainloop()
if __name__ == '__main__':
    main()
