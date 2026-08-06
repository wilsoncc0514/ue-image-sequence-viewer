"""tests/test_config.py module."""
from __future__ import annotations

import unittest

from config.settings import AppConfig, PerformanceConfig, SafetyConfig


class PerformanceConfigTests(unittest.TestCase):
    """Validate bounded worker-count behavior."""

    def test_worker_count_is_bounded(self) -> None:
        cfg = PerformanceConfig(preload_worker_min=4, preload_worker_max=32)
        self.assertEqual(cfg.preload_worker_count(1), 4)
        self.assertEqual(cfg.preload_worker_count(8), 8)
        self.assertEqual(cfg.preload_worker_count(64), 32)

    def test_version_is_exposed(self) -> None:
        self.assertEqual(AppConfig().version, 'v3.6.1')

    def test_invalid_queue_capacity_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PerformanceConfig(max_render_result_queue_size=0)

    def test_invalid_safety_limit_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SafetyConfig(max_csv_bytes=0)
if __name__ == '__main__':
    unittest.main()
