"""Opt-in macOS GUI smoke tests for release validation."""
from __future__ import annotations

import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from PIL import Image
from ui.app import FrameScrubber


@unittest.skipUnless(os.environ.get("RUN_GUI_TESTS") == "1", "set RUN_GUI_TESTS=1 on a desktop session")
class GuiSmokeTests(unittest.TestCase):
    def test_background_scan_builds_tree_for_unicode_path_and_closes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="图像 序列 ") as tmp:
            sequence = Path(tmp) / "镜头 01"
            sequence.mkdir()
            for frame in (1, 2):
                Image.new("RGB", (8, 8), color=(frame, 2, 3)).save(sequence / f"shot_{frame:04d}.png")

            root = tk.Tk()
            root.withdraw()
            app = FrameScrubber(root)
            self.assertFalse(hasattr(app, "tree_scroll_x"))
            self.assertEqual(int(app.sidebar_frame.cget("width")), int(app.right_panel.cget("width")))
            outcome: dict[str, object] = {}

            def poll() -> None:
                if app.loaded_folder_path == tmp and app._scan_apply_state is None:
                    outcome["image_count"] = sum(len(paths) for paths in app.groups.values())
                    app._shutdown_app()
                    return
                root.after(20, poll)

            def timeout() -> None:
                if not app._closed:
                    outcome["timeout"] = True
                    app._shutdown_app()

            app._start_folder_scan(tmp, "GUI smoke", None)
            root.after(20, poll)
            root.after(5000, timeout)
            root.mainloop()

        self.assertNotIn("timeout", outcome)
        self.assertEqual(outcome.get("image_count"), 2)


if __name__ == "__main__":
    unittest.main()
