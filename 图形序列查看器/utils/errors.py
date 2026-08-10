"""Unified exception handling helpers."""
from __future__ import annotations

import tkinter as tk
import traceback
from dataclasses import dataclass
from functools import wraps
from tkinter import messagebox
from typing import Any, Callable, ParamSpec, TypeVar

from utils.logger import logger

P = ParamSpec('P')
R = TypeVar('R')

@dataclass(slots=True)
class AppError(Exception):
    """Application-level error with a user-facing message."""
    title: str
    message: str

    def __str__(self) -> str:
        """Return the user-facing error text."""
        return self.message

def report_exception(exc: BaseException, *, title: str='程序错误', show_dialog: bool=False, parent: tk.Misc | None=None) -> None:
    """Log an exception and optionally show a concise user-facing dialog."""
    logger.error('Unhandled application error', exc_info=(type(exc), exc, exc.__traceback__))
    if show_dialog:
        try:
            if parent is None:
                messagebox.showerror(title, f'发生错误：\n{exc}')
            else:
                messagebox.showerror(title, f'发生错误：\n{exc}', parent=parent)
        except Exception:
            logger.error('Failed to show error dialog', exc_info=True)

def guarded_ui_callback(func: Callable[P, R]) -> Callable[P, R | None]:
    """Decorator for Tkinter callbacks that should never escape exceptions."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            parent = args[0].root if args and hasattr(args[0], 'root') else None
            report_exception(exc, parent=parent)
            return None
    return wrapper

def install_tk_exception_handler(root: tk.Tk) -> None:
    """Route Tkinter callback exceptions through the app logger and one dialog."""

    def _handler(exc_type: type[BaseException], exc_value: BaseException, exc_tb: Any) -> None:
        logger.error('Tkinter callback exception', exc_info=(exc_type, exc_value, exc_tb))
        try:
            detail = ''.join(traceback.format_exception_only(exc_type, exc_value)).strip()
            messagebox.showerror('程序错误', f'界面操作发生错误：\n{detail}', parent=root)
        except Exception:
            logger.error('Failed to display Tk exception dialog', exc_info=True)
    root.report_callback_exception = _handler
