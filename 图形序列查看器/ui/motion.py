"""Centralized, accessibility-aware motion helpers for Tk widgets."""

from __future__ import annotations

import math
import os
import tkinter as tk
from dataclasses import dataclass
from typing import Any, Callable, Hashable

from utils.logger import logger

REDUCE_MOTION_ENV = "UE_VIEWER_REDUCE_MOTION"
_TRUTHY = {"1", "true", "yes", "on"}


def _out_cubic(progress: float) -> float:
    """Return an OutCubic eased progress in the inclusive 0..1 range."""
    bounded = min(max(progress, 0.0), 1.0)
    return 1.0 - (1.0 - bounded) ** 3


def _parse_hex_color(value: str) -> tuple[int, int, int]:
    normalized = value.strip().lstrip("#")
    if len(normalized) != 6:
        raise ValueError(f"expected #RRGGBB color, got {value!r}")
    try:
        return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"expected #RRGGBB color, got {value!r}") from exc


def _interpolate_hex(start: str, end: str, progress: float) -> str:
    start_rgb = _parse_hex_color(start)
    end_rgb = _parse_hex_color(end)
    eased = _out_cubic(progress)
    channels = tuple(
        round(start_value + (end_value - start_value) * eased)
        for start_value, end_value in zip(start_rgb, end_rgb)
    )
    return "#{:02x}{:02x}{:02x}".format(*channels)


@dataclass
class _PendingJob:
    job_id: Any
    apply_final: Callable[[], None]


class MotionManager:
    """Own every optional UI transition and its pending Tk ``after`` job.

    New work with the same semantic key cancels older work. Enabling reduced
    motion finishes in-flight transitions immediately, while ``close`` only
    cancels callbacks because the widget tree is about to be destroyed.
    """

    def __init__(
        self,
        root: Any,
        *,
        fast_ms: int = 120,
        standard_ms: int = 180,
        emphasis_ms: int = 240,
        frame_interval_ms: int = 16,
        reduce_motion: bool = False,
    ) -> None:
        if min(fast_ms, standard_ms, emphasis_ms) < 0:
            raise ValueError("motion durations cannot be negative")
        if frame_interval_ms <= 0:
            raise ValueError("motion frame interval must be positive")
        self.root = root
        self.fast_ms = fast_ms
        self.standard_ms = standard_ms
        self.emphasis_ms = emphasis_ms
        self.frame_interval_ms = frame_interval_ms
        self._reduce_motion = bool(reduce_motion)
        self._closed = False
        self._pending: dict[Hashable, _PendingJob] = {}

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def environment_reduces_motion(self) -> bool:
        """Return whether the process environment forces reduced motion."""
        env_value = os.getenv(REDUCE_MOTION_ENV, "").strip().lower()
        return env_value in _TRUTHY

    @property
    def reduce_motion_active(self) -> bool:
        """Return the effective accessibility preference from every source."""
        return self._reduce_motion or self.environment_reduces_motion

    def motion_enabled(self) -> bool:
        return not self._closed and not self.reduce_motion_active

    def set_reduce_motion(self, enabled: bool) -> None:
        self._reduce_motion = bool(enabled)
        if self.reduce_motion_active:
            self.cancel_all(apply_final=True)

    def _cancel(self, key: Hashable, *, apply_final: bool) -> None:
        pending = self._pending.pop(key, None)
        if pending is None:
            return
        try:
            self.root.after_cancel(pending.job_id)
        except tk.TclError:
            logger.warning("Tk motion callback was already unavailable during cancellation", exc_info=True)
        if apply_final:
            pending.apply_final()

    def cancel_all(self, *, apply_final: bool) -> None:
        for key in list(self._pending):
            self._cancel(key, apply_final=apply_final)

    def close(self) -> None:
        if self._closed:
            return
        self.cancel_all(apply_final=False)
        self._closed = True

    def animate_value(
        self,
        key: Hashable,
        *,
        start: float,
        end: float,
        update: Callable[[float], None],
        duration_ms: int | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        """Animate one numeric value with the shared OutCubic lifecycle."""
        semantic_key = ("value", key)
        self._cancel(semantic_key, apply_final=False)
        duration = self.standard_ms if duration_ms is None else max(0, duration_ms)

        def apply(value: float) -> bool:
            try:
                update(value)
            except tk.TclError:
                logger.warning("Widget disappeared during numeric motion", exc_info=True)
                return False
            return True

        def apply_final() -> None:
            if not apply(end):
                return
            if on_finished is not None:
                on_finished()

        if not self.motion_enabled() or duration == 0 or start == end:
            apply_final()
            return

        steps = max(1, math.ceil(duration / self.frame_interval_ms))
        frame_delay_ms = max(1, round(duration / steps))
        current_step = 0
        pending = _PendingJob(job_id=None, apply_final=apply_final)

        def advance() -> None:
            nonlocal current_step
            if self._pending.get(semantic_key) is not pending:
                return
            current_step += 1
            if current_step >= steps:
                self._pending.pop(semantic_key, None)
                apply_final()
                return
            progress = _out_cubic(current_step / steps)
            if not apply(start + (end - start) * progress):
                self._pending.pop(semantic_key, None)
                return
            pending.job_id = self.root.after(frame_delay_ms, advance)

        pending.job_id = self.root.after(frame_delay_ms, advance)
        self._pending[semantic_key] = pending

    def set_canvas_text(
        self,
        canvas: Any,
        item: int,
        *,
        text: str,
        color: str,
        start_color: str,
        animate: bool,
        duration_ms: int | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        """Set Canvas text immediately and optionally fade its color to target."""
        key = ("canvas-text", id(canvas), item)
        self._cancel(key, apply_final=False)
        duration = self.standard_ms if duration_ms is None else max(0, duration_ms)

        def apply_final() -> None:
            try:
                canvas.itemconfigure(item, text=text, fill=color)
            except tk.TclError:
                logger.warning("Canvas disappeared before motion reached its final state", exc_info=True)
                return
            if on_finished is not None:
                on_finished()

        if not animate or not self.motion_enabled() or duration == 0:
            apply_final()
            return

        # Validate before changing visible state so invalid tokens fail clearly.
        _parse_hex_color(start_color)
        _parse_hex_color(color)
        canvas.itemconfigure(item, text=text, fill=start_color)
        steps = max(1, math.ceil(duration / self.frame_interval_ms))
        frame_delay_ms = max(1, round(duration / steps))
        current_step = 0
        pending = _PendingJob(job_id=None, apply_final=apply_final)

        def advance() -> None:
            nonlocal current_step
            if self._pending.get(key) is not pending:
                return
            current_step += 1
            if current_step >= steps:
                self._pending.pop(key, None)
                apply_final()
                return
            try:
                canvas.itemconfigure(
                    item,
                    fill=_interpolate_hex(start_color, color, current_step / steps),
                )
            except tk.TclError:
                self._pending.pop(key, None)
                logger.warning("Canvas disappeared during motion", exc_info=True)
                return
            pending.job_id = self.root.after(frame_delay_ms, advance)

        pending.job_id = self.root.after(frame_delay_ms, advance)
        self._pending[key] = pending

    def show_temporary_feedback(
        self,
        key: Hashable,
        widget: Any,
        *,
        active: dict[str, Any],
        restore: dict[str, Any],
        duration_ms: int,
        reduced_active: dict[str, Any] | None = None,
    ) -> None:
        """Show local confirmation and ensure rapid repeats have one restore job."""
        semantic_key = ("feedback", key)
        self._cancel(semantic_key, apply_final=False)
        chosen_active = active if self.motion_enabled() or reduced_active is None else reduced_active
        widget.configure(**chosen_active)

        def apply_final() -> None:
            try:
                widget.configure(**restore)
            except tk.TclError:
                logger.warning("Widget disappeared before feedback cleanup", exc_info=True)

        if duration_ms <= 0 or self._closed:
            apply_final()
            return

        pending = _PendingJob(job_id=None, apply_final=apply_final)

        def finish() -> None:
            if self._pending.get(semantic_key) is not pending:
                return
            self._pending.pop(semantic_key, None)
            apply_final()

        pending.job_id = self.root.after(duration_ms, finish)
        self._pending[semantic_key] = pending
