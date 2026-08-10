"""tests/test_config.py module."""
from __future__ import annotations

import unittest

from config.settings import AppConfig, PerformanceConfig, SafetyConfig, UIConfig


class PerformanceConfigTests(unittest.TestCase):
    """Validate bounded worker-count behavior."""

    def test_worker_count_is_bounded(self) -> None:
        cfg = PerformanceConfig(preload_worker_min=4, preload_worker_max=32)
        self.assertEqual(cfg.preload_worker_count(1), 4)
        self.assertEqual(cfg.preload_worker_count(8), 8)
        self.assertEqual(cfg.preload_worker_count(64), 32)

    def test_version_is_exposed(self) -> None:
        self.assertEqual(AppConfig().version, "v3.7.0")

    def test_invalid_queue_capacity_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PerformanceConfig(max_render_result_queue_size=0)

    def test_invalid_file_reveal_polling_interval_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PerformanceConfig(file_reveal_poll_ms=0)

    def test_invalid_safety_limit_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SafetyConfig(max_csv_bytes=0)

    def test_invalid_motion_frame_interval_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            UIConfig(motion_frame_interval_ms=0)

    def test_negative_motion_duration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            UIConfig(motion_standard_ms=-1)
if __name__ == '__main__':
    unittest.main()
