"""Image resource-limit regression tests."""
from __future__ import annotations

import tempfile
import threading
import unittest
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace

from core.render_controller import RenderControllerMixin
from PIL import Image


class ImageLimitTests(unittest.TestCase):
    def test_oversized_image_is_rejected_before_copy(self) -> None:
        controller = object.__new__(RenderControllerMixin)
        controller._closed = False
        controller.cache_lock = threading.RLock()
        controller.original_cache = OrderedDict()
        controller.max_original_cache_size = 2
        controller.dataset_id = 1
        controller._cache_original_hits = 0
        controller._cache_original_misses = 0
        controller._cache_stats_dirty = False
        controller.config = SimpleNamespace(safety=SimpleNamespace(max_image_pixels=100))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "large.png"
            Image.new("RGB", (11, 10)).save(path)
            self.assertIsNone(controller._get_original_image(1, 0, path))
        self.assertEqual(len(controller.original_cache), 0)


if __name__ == "__main__":
    unittest.main()
