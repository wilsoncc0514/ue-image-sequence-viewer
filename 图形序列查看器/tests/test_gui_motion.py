"""Opt-in real-Tk verification for motion completion and cleanup."""

from __future__ import annotations

import os
import tkinter as tk
import unittest
from unittest.mock import patch

from ui.menu import build_app_menu, refresh_reduce_motion_menu
from ui.motion import REDUCE_MOTION_ENV, MotionManager


@unittest.skipUnless(os.environ.get("RUN_GUI_TESTS") == "1", "set RUN_GUI_TESTS=1 on a desktop session")
class GuiMotionTests(unittest.TestCase):
    def test_reduce_motion_menu_reflects_state_and_invokes_callback(self) -> None:
        root = tk.Tk()
        root.withdraw()

        class _App:
            def __init__(self) -> None:
                self.root = root
                self.motion = MotionManager(root)
                self.var_reduce_motion = tk.BooleanVar(root, value=False)
                self.calls = 0

            def on_reduce_motion_change(self) -> None:
                self.calls += 1
                self.motion.set_reduce_motion(self.var_reduce_motion.get())

        app = _App()
        build_app_menu(app)

        self.assertEqual(app.settings_menu.entrycget(0, "label"), "减少动态效果")
        self.assertEqual(app.settings_menu.entrycget(0, "state"), "normal")
        app.settings_menu.invoke(0)
        self.assertEqual(app.calls, 1)
        self.assertTrue(app.var_reduce_motion.get())
        self.assertTrue(app.motion.reduce_motion_active)

        with patch.dict(os.environ, {REDUCE_MOTION_ENV: "1"}):
            refresh_reduce_motion_menu(app)
            self.assertEqual(
                app.settings_menu.entrycget(0, "label"),
                "减少动态效果（环境变量已启用）",
            )
            self.assertEqual(app.settings_menu.entrycget(0, "state"), "disabled")

        app.motion.close()
        root.destroy()

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
