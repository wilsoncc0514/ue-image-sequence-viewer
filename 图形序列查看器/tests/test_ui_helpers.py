"""Pure UI geometry and platform-command regression tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ui.text_height import resize_text_to_content
from ui.tree_viewport import centered_yview_fraction
from utils.file_reveal import build_reveal_command


class _FakeText:
    def __init__(self, display_lines: int, height: int = 1) -> None:
        self.display_lines = display_lines
        self.height = height
        self.count_args: tuple[object, ...] = ()

    def count(self, *args: object) -> tuple[int]:
        self.count_args = args
        return (self.display_lines,)

    def cget(self, _name: str) -> int:
        return self.height

    def configure(self, *, height: int) -> None:
        self.height = height


class UiHelperTests(unittest.TestCase):
    def test_text_starts_at_one_line_and_grows_to_all_display_lines(self) -> None:
        empty = _FakeText(display_lines=0, height=2)
        wrapped = _FakeText(display_lines=5)

        self.assertEqual(resize_text_to_content(empty), 1)
        self.assertEqual(resize_text_to_content(wrapped), 5)
        self.assertEqual(empty.height, 1)
        self.assertEqual(wrapped.height, 5)
        self.assertEqual(wrapped.count_args, ("1.0", "end", "displaylines"))

    def test_tree_centering_clamps_near_bottom(self) -> None:
        centered = centered_yview_fraction(
            first=0.20,
            last=0.50,
            item_y=240,
            item_height=28,
            viewport_height=300,
        )
        bottom = centered_yview_fraction(
            first=0.70,
            last=1.00,
            item_y=270,
            item_height=28,
            viewport_height=300,
        )

        self.assertAlmostEqual(centered, 0.304, places=3)
        self.assertEqual(bottom, 0.70)

    def test_reveal_commands_are_fixed_and_keep_path_as_one_argument(self) -> None:
        with tempfile.TemporaryDirectory(prefix="中文 path ") as tmp:
            image = Path(tmp) / "frame 0001.png"
            image.touch()

            self.assertEqual(build_reveal_command(image, platform="darwin"), ["open", "-R", str(image.resolve())])
            self.assertEqual(
                build_reveal_command(image, platform="win32"),
                ["explorer", f"/select,{image.resolve()}"],
            )


if __name__ == "__main__":
    unittest.main()
