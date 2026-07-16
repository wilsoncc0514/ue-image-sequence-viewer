"""tests/test_config.py module."""
from __future__ import annotations
from typing import Any
import unittest
from config.settings import AppConfig, PerformanceConfig

class PerformanceConfigTests(unittest.TestCase):
    """Validate bounded worker-count behavior."""

    def test_worker_count_is_bounded(self) -> None:
        cfg = PerformanceConfig(preload_worker_min=4, preload_worker_max=32)
        self.assertEqual(cfg.preload_worker_count(1), 4)
        self.assertEqual(cfg.preload_worker_count(8), 8)
        self.assertEqual(cfg.preload_worker_count(64), 32)

    def test_version_is_exposed(self) -> None:
        self.assertEqual(AppConfig().version, 'v3.6')
if __name__ == '__main__':
    unittest.main()
