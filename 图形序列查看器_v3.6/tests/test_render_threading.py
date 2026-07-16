"""Regression tests for render worker thread-safety."""
from __future__ import annotations
import inspect
import unittest
from core.render_controller import RenderControllerMixin


class RenderThreadingTests(unittest.TestCase):
    def test_schedule_render_finish_uses_queue_not_tk_after(self) -> None:
        source = inspect.getsource(RenderControllerMixin._schedule_render_finish)
        self.assertIn("render_result_queue", source)
        self.assertNotIn("self.root.after", source)

    def test_get_original_image_does_not_touch_tk_overlay(self) -> None:
        source = inspect.getsource(RenderControllerMixin._get_original_image)
        self.assertNotIn("_update_cache_stats_overlay()", source)


if __name__ == "__main__":
    unittest.main()
