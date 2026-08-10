"""Controller-level UI interaction tests without creating Tk windows."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock, patch

from ui.app import FrameScrubber


class _Tree:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id

    def identify_row(self, _y: int) -> str:
        return self.node_id


class UiInteractionTests(unittest.TestCase):
    def test_double_click_reveals_current_frame_from_selected_group(self) -> None:
        app = FrameScrubber.__new__(FrameScrubber)
        app.tree = cast(Any, _Tree("group"))
        app.groups = {"group": ["frame1.png", "frame2.png"]}
        app.current_tree_node = "group"
        app.current_idx = 1
        app._reveal_process = None

        with patch("ui.app.reveal_file") as reveal:
            reveal.return_value.poll.return_value = 0
            result = app.on_tree_double_click(SimpleNamespace(y=10))

        reveal.assert_called_once_with("frame2.png")
        self.assertEqual(result, "break")

    def test_double_click_ignores_folder_nodes(self) -> None:
        app = FrameScrubber.__new__(FrameScrubber)
        app.tree = cast(Any, _Tree("folder"))
        app.groups = {}

        with patch("ui.app.reveal_file") as reveal:
            result = app.on_tree_double_click(SimpleNamespace(y=10))

        reveal.assert_not_called()
        self.assertIsNone(result)

    def test_double_click_reports_a_fast_file_manager_failure(self) -> None:
        app = FrameScrubber.__new__(FrameScrubber)
        app.tree = cast(Any, _Tree("group"))
        app.groups = {"group": ["frame1.png"]}
        app.current_tree_node = "group"
        app.current_idx = 0
        app._reveal_process = None
        app.root = cast(Any, object())
        process = Mock()
        process.poll.return_value = 7

        with (
            patch("ui.app.reveal_file", return_value=process),
            patch("ui.app.messagebox.showerror") as showerror,
        ):
            app.on_tree_double_click(SimpleNamespace(y=10))

        showerror.assert_called_once()
        self.assertIsNone(app._reveal_process)


if __name__ == "__main__":
    unittest.main()
