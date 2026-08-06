"""Image rendering boundary tests."""
from __future__ import annotations

import unittest
from unittest.mock import Mock

from core.image_rendering import render_image_to_fit


class ImageRenderingTests(unittest.TestCase):
    def test_rejects_zero_sized_source(self) -> None:
        image = Mock(size=(0, 100))
        with self.assertRaisesRegex(ValueError, "Invalid image dimensions"):
            render_image_to_fit(image, 800, 600)

    def test_rejects_zero_sized_canvas(self) -> None:
        image = Mock(size=(100, 100))
        with self.assertRaisesRegex(ValueError, "Invalid canvas dimensions"):
            render_image_to_fit(image, 0, 600)


if __name__ == "__main__":
    unittest.main()
