"""Opt-in real-Tk verification for motion completion and cleanup."""

from __future__ import annotations

import os
import tkinter as tk
import unittest

from ui.motion import MotionManager


@unittest.skipUnless(os.environ.get("RUN_GUI_TESTS") == "1", "set RUN_GUI_TESTS=1 on a desktop session")
class GuiMotionTests(unittest.TestCase):
    def test_canvas_motion_finishes_without_fixed_sleep(self) -> None:
        root = tk.Tk()
        root.withdraw()
        canvas = tk.Canvas(root)
        item = canvas.create_text(0, 0, text="")
        manager = MotionManager(root, standard_ms=32, frame_interval_ms=8)
        outcome = tk.StringVar(root, value="")

        manager.set_canvas_text(
            canvas,
            item,
            text="已完成",
            color="#30d158",
            start_color="#070708",
            animate=True,
            on_finished=lambda: outcome.set("finished"),
        )

        def timeout() -> None:
            if not outcome.get():
                outcome.set("timeout")

        root.after(500, timeout)
        root.wait_variable(outcome)

        self.assertEqual(outcome.get(), "finished")
        self.assertEqual(canvas.itemcget(item, "text"), "已完成")
        self.assertEqual(canvas.itemcget(item, "fill"), "#30d158")
        self.assertEqual(manager.pending_count, 0)
        manager.close()
        root.destroy()


if __name__ == "__main__":
    unittest.main()
