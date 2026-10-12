"""Real Tk integration tests for document boundaries and failure recovery."""
from __future__ import annotations

import copy
import os
import tempfile
import time
import tkinter as tk
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from config.settings import AppConfig
from core.folder_scanner import scan_image_folder
from PIL import Image
from ui.app import FrameScrubber


@unittest.skipUnless(os.getenv("RUN_GUI_TESTS") == "1", "requires a desktop Tk session")
class GuiIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="质检 回归 ")
        self.root = tk.Tk()
        self.root.geometry("1450x900")
        cfg = AppConfig()
        self.app = FrameScrubber(self.root, replace(cfg, ui=replace(cfg.ui, reduce_motion=True)))
        self.root.update()

    def tearDown(self):
        if not self.app._closed:
            self.app._shutdown_app()
        self.temp.cleanup()

    def wait_for(self, predicate):
        outcome = tk.StringVar(self.root, value="")
        deadline = time.monotonic() + 5
        def poll():
            if predicate():
                outcome.set("done")
            elif time.monotonic() >= deadline:
                outcome.set("timeout")
            else:
                self.root.after(10, poll)
        self.root.after_idle(poll)
        self.root.wait_variable(outcome)
        self.assertEqual(outcome.get(), "done")

    def new_scan(self):
        folder = Path(self.temp.name) / "new"
        folder.mkdir(exist_ok=True)
        Image.new("RGB", (16, 16), "red").save(folder / "frame_001.png")
        result = scan_image_folder(str(folder), image_extensions=(".png",), max_entries=100, max_depth=3)
        return result, (str(folder), "new reviewer", None)

    def dirty_document(self):
        self.app.loaded_folder_path = "old folder"
        self.app.root_folder_name = "old"
        self.app.tag_data = {"old-seq": self.app._create_empty_tag_state(status="不合格")}
        self.app.seq_rel_paths = ["old-seq"]
        self.app.csv_exported = False
        self.app.tree.insert("", "end", iid="old-root", text="old")

    def test_folder_cancel_preserves_document(self):
        self.dirty_document()
        original = copy.deepcopy(self.app.tag_data)
        with patch("ui.app.messagebox.askyesnocancel", return_value=None) as ask:
            self.app._begin_apply_folder_scan(*self.new_scan())
            self.wait_for(lambda:self.app._scan_apply_state is None)
        ask.assert_called_once()
        self.assertEqual(self.app.tag_data, original)
        self.assertEqual(self.app.loaded_folder_path, "old folder")
        self.assertEqual(self.app.tree.get_children(), ("old-root",))

    def test_folder_failed_export_preserves_document(self):
        self.dirty_document()
        original = copy.deepcopy(self.app.tag_data)
        with patch("ui.app.messagebox.askyesnocancel", return_value=True), patch.object(self.app, "export_csv", return_value=False):
            self.app._begin_apply_folder_scan(*self.new_scan())
            self.wait_for(lambda:self.app._scan_apply_state is None)
        self.assertEqual(self.app.tag_data, original)
        self.assertEqual(self.app.tree.get_children(), ("old-root",))

    def test_folder_discard_commits_new_document(self):
        self.dirty_document()
        result, context = self.new_scan()
        with patch("ui.app.messagebox.askyesnocancel", return_value=False):
            self.app._begin_apply_folder_scan(result, context)
            self.wait_for(lambda:self.app._scan_apply_state is None)
        self.assertEqual(self.app.loaded_folder_path, context[0])
        self.assertNotIn("old-seq", self.app.tag_data)
        self.assertFalse(self.app.tree.exists("old-root"))
        self.assertEqual(sum(map(len, self.app.groups.values())), 1)

    def test_folder_successful_export_commits(self):
        self.dirty_document()
        result, context = self.new_scan()
        with patch("ui.app.messagebox.askyesnocancel", return_value=True), patch.object(self.app, "export_csv", return_value=True) as export:
            self.app._begin_apply_folder_scan(result, context)
            self.wait_for(lambda:self.app._scan_apply_state is None)
        export.assert_called_once()
        self.assertEqual(self.app.loaded_folder_path, context[0])

    def test_failed_tree_build_keeps_old_document(self):
        self.dirty_document()
        original = copy.deepcopy(self.app.tag_data)
        result, context = self.new_scan()
        with patch.object(self.app, "_create_empty_tag_state", side_effect=RuntimeError("tree build failed")), patch("ui.app.messagebox.showerror"):
            self.app._begin_apply_folder_scan(result, context)
            self.wait_for(lambda:self.app._scan_apply_state is None)
        self.assertEqual(self.app.tag_data, original)
        self.assertEqual(self.app.tree.get_children(), ("old-root",))

    def test_scan_error_does_not_replace_old_document(self):
        self.dirty_document()
        original = copy.deepcopy(self.app.tag_data)
        with patch("ui.app.scan_image_folder", side_effect=PermissionError("blocked")), patch("ui.app.messagebox.showerror"):
            self.app._start_folder_scan(self.temp.name, "reviewer", None)
            self.wait_for(lambda: self.app.btn_load.cget("text") == "加载文件夹")
        self.assertEqual(self.app.tag_data, original)
        self.assertEqual(self.app.loaded_folder_path, "old folder")

    def test_tree_initialization_failure_preserves_old_document(self):
        self.dirty_document()
        original = copy.deepcopy(self.app.tag_data)
        result, context = self.new_scan()
        with patch("ui.app.scan_image_folder", return_value=result), patch.object(self.app.tree, "insert", side_effect=tk.TclError("insert failed")), patch("ui.app.messagebox.showerror"):
            self.app._start_folder_scan(context[0], context[1], None)
            self.wait_for(lambda:self.app.btn_load.cget("text") == "加载文件夹")
        self.assertEqual(self.app.tag_data, original)
        self.assertEqual(self.app.loaded_folder_path, "old folder")

    def test_cross_sequence_undo_cannot_change_loaded_note(self):
        for seq, note in (("old", "旧备注"), ("new", "新备注")):
            self.app.node_metadata[seq] = seq
            state = self.app._create_empty_tag_state(status="不合格")
            state["comp"]["漏光"]["text"] = note
            self.app.tag_data[seq] = state
        self.app.current_tree_node = "old"
        self.app.load_tag_state("old")
        self.root.update()
        self.app.current_tree_node = "new"
        self.app.load_tag_state("new")
        self.root.update()
        widget = self.app.tag_vars_comp["漏光"]["text_widget"]
        with self.assertRaises(tk.TclError):
            widget.edit_undo()
        self.assertEqual(widget.get("1.0", "end-1c"), "新备注")
        widget.insert("end-1c", "编辑")
        self.root.update()
        widget.edit_undo()
        self.root.update()
        self.assertEqual(widget.get("1.0", "end-1c"), "新备注")
        self.assertEqual(self.app.tag_data["new"]["comp"]["漏光"]["text"], "新备注")

    def test_same_content_at_sequence_boundary_resets_undo(self):
        widget = self.app.tag_vars_comp["漏光"]["text_widget"]
        widget.insert("1.0", "相同备注")
        self.root.update()
        self.app.node_metadata["new"] = "new"
        state = self.app._create_empty_tag_state(status="不合格")
        state["comp"]["漏光"]["text"] = "相同备注"
        self.app.tag_data["new"] = state
        self.app.load_tag_state("new")
        self.root.update()
        with self.assertRaises(tk.TclError):
            widget.edit_undo()

    def test_text_down_key_does_not_navigate(self):
        widget = self.app.tag_vars_comp["漏光"]["text_widget"]
        widget.insert("1.0", "第一行\n第二行")
        self.root.update()
        widget.focus_force()
        widget.mark_set("insert", "1.0")
        self.root.update()
        with patch.object(self.app, "step_group") as navigate:
            widget.event_generate("<Down>")
            self.root.update()
        navigate.assert_not_called()
        self.assertEqual(widget.index("insert"), "2.0")

    def test_navigation_inside_same_sequence_keeps_user_undo(self):
        self.app.node_metadata.update(first="seq", second="seq")
        self.app.tag_data["seq"] = self.app._create_empty_tag_state(status="不合格")
        self.app.current_tree_node = "first"
        self.app.load_tag_state("first")
        self.root.update()
        widget = self.app.tag_vars_comp["漏光"]["text_widget"]
        widget.insert("1.0", "用户编辑")
        self.root.update()
        self.app.current_tree_node = "second"
        self.app.load_tag_state("second")
        self.root.update()
        widget.edit_undo()
        self.root.update()
        self.assertEqual(widget.get("1.0", "end-1c"), "")

    def test_failed_frame_and_loading_clear_old_image(self):
        folder = Path(self.temp.name)
        Image.new("RGB", (16, 16), "red").save(folder / "frame_001.png")
        (folder / "frame_002.png").write_bytes(b"bad image")
        self.app.current_filepaths = [str(folder / f"frame_00{i}.png") for i in (1, 2)]
        self.app.update_image_index(0, force=True)
        self.wait_for(lambda:bool(self.app.canvas.itemcget(self.app.image_on_canvas, "image")))
        self.app.update_image_index(1)
        self.assertEqual(self.app.canvas.itemcget(self.app.image_on_canvas, "image"), "")
        self.wait_for(lambda:self.app.canvas.itemcget(self.app.txt_status, "text") == "图片读取失败")
        self.assertEqual(self.app.canvas.itemcget(self.app.image_on_canvas, "image"), "")
        self.assertEqual(self.app.lbl_filename.cget("text"), "frame_002.png")

    def test_reviewer_change_marks_export_dirty_only_on_change(self):
        self.app.qc_by_name = "before"
        for value, dirty in ((None, False), ("before", False), ("after", True)):
            self.app.csv_exported = True
            with patch("ui.app.CustomQCDialog", return_value=SimpleNamespace(result=value)):
                self.app.change_qc_by()
            self.assertEqual(self.app.csv_exported, not dirty)
