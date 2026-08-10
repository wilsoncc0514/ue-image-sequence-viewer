"""Regression tests for render worker thread-safety."""
from __future__ import annotations

import inspect
import queue
import unittest
from typing import Any, cast

from core.render_controller import RenderControllerMixin


class RenderThreadingTests(unittest.TestCase):
    def test_schedule_render_finish_uses_queue_not_tk_after(self) -> None:
        source = inspect.getsource(RenderControllerMixin._schedule_render_finish)
        self.assertIn("render_result_queue", source)
        self.assertNotIn("self.root.after", source)

    def test_get_original_image_does_not_touch_tk_overlay(self) -> None:
        source = inspect.getsource(RenderControllerMixin._get_original_image)
        self.assertNotIn("_update_cache_stats_overlay()", source)

    def test_full_result_queue_keeps_newest_result(self) -> None:
        controller = object.__new__(RenderControllerMixin)
        controller._closed = False
        controller.render_result_queue = queue.Queue(maxsize=1)
        controller.render_result_queue.put_nowait((1, 1, 1, 1, 1, cast(Any, "old"), None))
        controller._schedule_render_finish(2, 2, 2, 2, 2, cast(Any, "new"), None)
        self.assertEqual(controller.render_result_queue.get_nowait()[5], "new")


if __name__ == "__main__":
    unittest.main()
