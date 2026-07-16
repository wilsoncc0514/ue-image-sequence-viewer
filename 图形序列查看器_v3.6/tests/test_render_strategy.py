"""Tests for frame-preload ordering and render polling settings."""
from __future__ import annotations

import unittest

from config.settings import PerformanceConfig
from core.render_controller import RenderControllerMixin


class RenderStrategyTests(unittest.TestCase):
    """Validate directional preload windows."""

    def test_forward_direction_prioritizes_future_frames(self) -> None:
        values = list(RenderControllerMixin._nearby_indices(10, 100, 4, 1, 1))
        self.assertEqual(values[:5], [10, 11, 12, 13, 14])
        self.assertEqual(values[-1], 9)

    def test_reverse_radius_can_be_limited(self) -> None:
        values = list(RenderControllerMixin._nearby_indices(10, 100, 8, -1, 2))
        self.assertEqual(values[:9], [10, 9, 8, 7, 6, 5, 4, 3, 2])
        self.assertEqual(values[-2:], [11, 12])

    def test_balanced_direction_interleaves(self) -> None:
        self.assertEqual(list(RenderControllerMixin._nearby_indices(2, 6, 2, 0)), [2, 3, 1, 4, 0])

    def test_invalid_bounds_yield_empty(self) -> None:
        self.assertEqual(list(RenderControllerMixin._nearby_indices(9, 3, 2, 1)), [])


class RenderAdaptivePollConfigTests(unittest.TestCase):
    """Validate adaptive render polling configuration fields."""

    def test_adaptive_poll_config_fields_exist(self) -> None:
        cfg = PerformanceConfig()
        self.assertLessEqual(cfg.render_result_poll_ms, cfg.render_result_poll_idle_ms)
        self.assertLessEqual(cfg.render_result_poll_idle_ms, cfg.render_result_poll_max_idle_ms)
        self.assertGreaterEqual(cfg.render_result_empty_slowdown_after, 1)


if __name__ == "__main__":
    unittest.main()
