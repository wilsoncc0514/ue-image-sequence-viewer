"""Deterministic tests for Tk motion lifecycle management."""

from __future__ import annotations

import os
import unittest
from collections.abc import Callable
from unittest.mock import patch

from ui.motion import REDUCE_MOTION_ENV, MotionManager


class _FakeRoot:
    def __init__(self) -> None:
        self._counter = 0
        self.jobs: dict[str, Callable[[], None]] = {}
        self.cancelled: list[str] = []

    def after(self, _delay_ms: int, callback: Callable[[], None]) -> str:
        self._counter += 1
        job_id = f"job-{self._counter}"
        self.jobs[job_id] = callback
        return job_id

    def after_cancel(self, job_id: str) -> None:
        self.cancelled.append(job_id)
        self.jobs.pop(job_id, None)

    def run_next(self) -> None:
        job_id = next(iter(self.jobs))
        callback = self.jobs.pop(job_id)
        callback()

    def run_all(self, limit: int = 100) -> None:
        count = 0
        while self.jobs:
            self.run_next()
            count += 1
            if count > limit:
                raise AssertionError("motion jobs did not finish")


class _FakeCanvas:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}

    def itemconfigure(self, _item: int, **options: object) -> None:
        self.options.update(options)


class _FakeWidget:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}

    def configure(self, **options: object) -> None:
        self.options.update(options)


class MotionManagerTests(unittest.TestCase):
    def test_canvas_fade_reaches_exact_target_and_cleans_job(self) -> None:
        root = _FakeRoot()
        canvas = _FakeCanvas()
        manager = MotionManager(root, standard_ms=32, frame_interval_ms=16)
        finished: list[bool] = []

        manager.set_canvas_text(
            canvas,
            1,
            text="已加载",
            color="#30d158",
            start_color="#070708",
            animate=True,
            on_finished=lambda: finished.append(True),
        )

        self.assertEqual(canvas.options["text"], "已加载")
        self.assertEqual(canvas.options["fill"], "#070708")
        self.assertEqual(manager.pending_count, 1)
        root.run_all()
        self.assertEqual(canvas.options["fill"], "#30d158")
        self.assertEqual(manager.pending_count, 0)
        self.assertEqual(finished, [True])

    def test_reduced_motion_applies_canvas_target_immediately(self) -> None:
        root = _FakeRoot()
        canvas = _FakeCanvas()
        manager = MotionManager(root, reduce_motion=True)

        manager.set_canvas_text(
            canvas,
            1,
            text="失败",
            color="#ff453a",
            start_color="#070708",
            animate=True,
        )

        self.assertEqual(canvas.options, {"text": "失败", "fill": "#ff453a"})
        self.assertEqual(root.jobs, {})

    def test_environment_can_reduce_motion(self) -> None:
        root = _FakeRoot()
        canvas = _FakeCanvas()
        with patch.dict(os.environ, {REDUCE_MOTION_ENV: "1"}):
            manager = MotionManager(root)
            manager.set_canvas_text(
                canvas,
                1,
                text="完成",
                color="#30d158",
                start_color="#070708",
                animate=True,
            )

        self.assertEqual(canvas.options["fill"], "#30d158")
        self.assertEqual(root.jobs, {})

    def test_new_canvas_transition_stops_old_transition(self) -> None:
        root = _FakeRoot()
        canvas = _FakeCanvas()
        manager = MotionManager(root, standard_ms=48, frame_interval_ms=16)

        manager.set_canvas_text(
            canvas,
            1,
            text="第一个",
            color="#30d158",
            start_color="#070708",
            animate=True,
        )
        old_job = next(iter(root.jobs))
        manager.set_canvas_text(
            canvas,
            1,
            text="第二个",
            color="#ff453a",
            start_color="#070708",
            animate=True,
        )

        self.assertIn(old_job, root.cancelled)
        root.run_all()
        self.assertEqual(canvas.options["text"], "第二个")
        self.assertEqual(canvas.options["fill"], "#ff453a")

    def test_enabling_reduced_motion_finishes_inflight_transition(self) -> None:
        root = _FakeRoot()
        canvas = _FakeCanvas()
        manager = MotionManager(root, standard_ms=48, frame_interval_ms=16)
        manager.set_canvas_text(
            canvas,
            1,
            text="完成",
            color="#30d158",
            start_color="#070708",
            animate=True,
        )

        manager.set_reduce_motion(True)

        self.assertEqual(canvas.options["fill"], "#30d158")
        self.assertEqual(manager.pending_count, 0)
        self.assertEqual(root.jobs, {})

    def test_repeated_temporary_feedback_cancels_old_restore(self) -> None:
        root = _FakeRoot()
        widget = _FakeWidget()
        manager = MotionManager(root)
        restore = {"text": "复制", "style": "TButton"}

        manager.show_temporary_feedback(
            "copy",
            widget,
            active={"text": "已复制", "style": "Success.TButton"},
            reduced_active={"text": "已复制", "style": "TButton"},
            restore=restore,
            duration_ms=1200,
        )
        old_job = next(iter(root.jobs))
        manager.show_temporary_feedback(
            "copy",
            widget,
            active={"text": "已复制", "style": "Success.TButton"},
            reduced_active={"text": "已复制", "style": "TButton"},
            restore=restore,
            duration_ms=1200,
        )

        self.assertIn(old_job, root.cancelled)
        self.assertEqual(widget.options["text"], "已复制")
        root.run_all()
        self.assertEqual(widget.options, restore)
        self.assertEqual(manager.pending_count, 0)

    def test_reduced_motion_keeps_text_feedback_without_color_emphasis(self) -> None:
        root = _FakeRoot()
        widget = _FakeWidget()
        manager = MotionManager(root, reduce_motion=True)

        manager.show_temporary_feedback(
            "copy",
            widget,
            active={"text": "已复制", "style": "Success.TButton"},
            reduced_active={"text": "已复制", "style": "TButton"},
            restore={"text": "复制", "style": "TButton"},
            duration_ms=1200,
        )

        self.assertEqual(widget.options, {"text": "已复制", "style": "TButton"})
        root.run_all()
        self.assertEqual(widget.options, {"text": "复制", "style": "TButton"})

    def test_close_cancels_jobs_without_running_callbacks(self) -> None:
        root = _FakeRoot()
        widget = _FakeWidget()
        manager = MotionManager(root)
        manager.show_temporary_feedback(
            "copy",
            widget,
            active={"text": "已复制"},
            restore={"text": "复制"},
            duration_ms=1200,
        )

        manager.close()

        self.assertEqual(root.jobs, {})
        self.assertEqual(manager.pending_count, 0)


if __name__ == "__main__":
    unittest.main()
