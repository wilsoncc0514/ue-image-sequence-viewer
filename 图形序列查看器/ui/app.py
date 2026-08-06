"""Main application controller for 图形序列查看器."""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, messagebox
from typing import Any

from config.settings import AppConfig
from core.csv_io import CsvIOMixin
from core.folder_scanner import FolderScanResult, ScanCancelled, scan_image_folder
from core.render_controller import RenderControllerMixin
from core.seq_state import SeqStateMixin
from core.tag_logic import TagLogicMixin
from models.tag_definitions import get_default_comp_tags, get_default_light_tags
from utils.logger import logger

from ui.dialogs import CustomQCDialog
from ui.layout import build_main_ui
from ui.styles import STYLE, apply_ttk_style


class FrameScrubber(TagLogicMixin, SeqStateMixin, CsvIOMixin, RenderControllerMixin):
    """Main application controller coordinating UI, state, CSV I/O and rendering."""

    def __init__(self, root: tk.Tk, config: AppConfig | None = None) -> None:
        """Create the application controller and wire together all subsystems."""
        self.config = config or AppConfig()
        self.root = root
        self.root.title(f"{self.config.window.title} {self.config.version}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self._init_runtime_state()
        self._init_render_state()
        self._init_scan_state()
        self._init_tree_state()
        self._init_navigation_state()
        self._init_tag_state()
        self._init_style_and_ui()

        self._bind_shortcuts()
        self._start_render_result_polling()


    def change_qc_by(self):
        dlg = CustomQCDialog(self.root,"QC by","")
        if dlg.result:
            self.qc_by_name = dlg.result
            self.lbl_qc_by.config(text=f"QC by: {self.qc_by_name}")

    def _init_runtime_state(self) -> None:
        """Initialize process-level and document-level runtime state."""
        self._closed = False
        self.root_folder_name = ""
        self.loaded_folder_path = ""
        self.qc_by_name = ""
        self.csv_exported = False
        self.is_loading_state = False
        self.current_tk_image = None
        self._node_counter = 0

    def _init_render_state(self) -> None:
        """Initialize asynchronous render workers, queues, caches and counters."""
        self.cpu_count = os.cpu_count() or 4
        self.preload_worker_count = self.config.performance.preload_worker_count(self.cpu_count)
        self.executor = ThreadPoolExecutor(max_workers=self.preload_worker_count)
        self.render_queue = queue.Queue(maxsize=1)
        self.render_result_queue = queue.Queue(maxsize=self.config.performance.max_render_result_queue_size)
        self.render_stop_event = threading.Event()
        self.render_seq = 0
        self._render_result_poll_job = None
        self._render_result_empty_streak = 0
        self.render_worker = threading.Thread(target=self._render_worker_loop, daemon=True)
        self.render_worker.start()

        self.render_cache = OrderedDict()
        self.original_cache = OrderedDict()
        self.max_render_cache_size = self.config.performance.max_render_cache_size
        self.max_original_cache_size = self.config.performance.max_original_cache_size
        self.preload_radius = self.config.performance.preload_radius
        self.drag_preload_radius = self.config.performance.drag_preload_radius
        self.preload_pending = set()
        self.cache_lock = threading.RLock()
        self.preload_seq = 0
        self._preload_submit_job = None
        self._resize_job = None

        self._cache_render_hits = 0
        self._cache_render_misses = 0
        self._cache_original_hits = 0
        self._cache_original_misses = 0
        self._cache_stats_dirty = False

    def _init_scan_state(self) -> None:
        """Initialize the single cancellable directory-scan worker."""
        self.scan_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="folder-scan")
        self.scan_cancel_event: threading.Event | None = None
        self.scan_future = None
        self.scan_progress_queue: queue.Queue[tuple[int, int]] = queue.Queue(maxsize=1)
        self._scan_poll_job = None
        self._scan_generation = 0
        self._scan_apply_state = None

    def _init_tree_state(self) -> None:
        """Initialize loaded group, seq and tree-navigation state."""
        self.groups = {}
        self.tag_data = {}
        self.node_metadata = {}
        self.seq_folder_nodes = set()
        self.seq_rel_paths = []
        self.seq_rel_path_set = set()
        self.current_tree_node = None
        self._suppress_unmarked_prompt = False
        self._suppress_unmarked_prompt_target = None

    def _init_navigation_state(self) -> None:
        """Initialize current frame, slider and keyboard preview state."""
        self.current_filepaths = []
        self.current_idx = -1
        self.dataset_id = 0
        self._slider_job = None
        self._slider_pending_idx = None
        self._slider_is_dragging = False
        self._programmatic_slider_update = False
        self._keyboard_preview_active = False
        self._keyboard_preview_job = None
        self.navigation_direction = 0
        self._last_frame_idx_for_direction = -1

    def _init_tag_state(self) -> None:
        """Initialize tag definitions and Tk variables."""
        self.var_status = tk.StringVar(value="")
        self.var_rerender = tk.BooleanVar(value=False)
        self.var_rerender.trace_add("write", self.on_rerender_change)
        self.light_tags_def = get_default_light_tags()
        self.comp_tags_def = get_default_comp_tags()
        self.tag_vars_light = {}
        self.tag_vars_comp = {}
        self._init_tag_vars(self.light_tags_def, self.tag_vars_light)
        self._init_tag_vars(self.comp_tags_def, self.tag_vars_comp)

    def _init_style_and_ui(self) -> None:
        """Apply global styles and build Tk widgets."""
        apply_ttk_style(self.root)
        try:
            self.root.configure(bg=STYLE.colors.window_bg)
        except Exception:
            pass
        self._setup_ui()

    def on_closing(self) -> Any:
        if self.current_tree_node:
            self.save_tag_state(self.current_tree_node)
        if self._should_prompt_export_on_close():
            choice = messagebox.askyesnocancel('退出前导出 CSV', '当前已有质检数据尚未导出 CSV。\n\n是否现在导出？\n\n是：先导出 CSV 再退出\n否：不导出并退出\n取消：留在当前界面')
            if choice is None:
                return
            if choice:
                if not self.export_csv():
                    return
        self._shutdown_app()

    def _shutdown_app(self) -> Any:
        self._closed = True
        if self.scan_cancel_event is not None:
            self.scan_cancel_event.set()
        self.render_stop_event.set()
        self._invalidate_preload()
        self._invalidate_render()
        self._cancel_slider_job()
        if self._keyboard_preview_job:
            self.root.after_cancel(self._keyboard_preview_job)
            self._keyboard_preview_job = None
        if self._render_result_poll_job:
            self.root.after_cancel(self._render_result_poll_job)
            self._render_result_poll_job = None
        if self._scan_poll_job:
            self.root.after_cancel(self._scan_poll_job)
            self._scan_poll_job = None
        self._cancel_preload_submit_job()
        self._clear_render_queue()
        try:
            self.executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            self.executor.shutdown(wait=False)
        try:
            self.scan_executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            self.scan_executor.shutdown(wait=False)
        self.root.destroy()

    def _mark_export_dirty(self) -> Any:
        self.csv_exported = False

    def _has_exportable_tag_data(self) -> Any:
        return any((not self._is_tag_state_empty(self._normalize_tag_state(self.tag_data.get(rel))) for rel in self._effective_seq_rel_paths()))

    def _should_prompt_export_on_close(self) -> Any:
        return bool(self.tag_data) and (not self.csv_exported) and self._has_exportable_tag_data()

    @staticmethod
    def _estimate_visual_chars(text: Any) -> Any:
        """用于侧栏宽度的轻量字符估算。

        ASCII 约按 1 个视觉字符计算；中文等宽字符约按 1.7 个视觉字符计算。
        这里只用于避免侧栏固定过宽，不追求像素级精确。
        """
        total = 0.0
        for ch in str(text or ''):
            if ord(ch) < 128:
                total += 1.0
            else:
                total += 1.7
        return total

    def _adjust_sidebar_width(self) -> Any:
        """按当前文件夹/序列文本估算左侧栏宽度，并限制在合理区间。"""
        if not hasattr(self, 'sidebar_frame') or not hasattr(self, 'tree'):
            return
        samples = [self.root_folder_name or '未加载文件夹']

        def walk(node: Any='', depth: Any=0) -> Any:
            for child in self.tree.get_children(node):
                text = self.tree.item(child, 'text')
                samples.append('  ' * depth + str(text))
                walk(child, depth + 1)
        walk()
        max_chars = max((self._estimate_visual_chars(s) for s in samples), default=24)
        estimated = int(max_chars * 8 + 96)
        target_width = max(self.config.sidebar.min_width, min(self.config.sidebar.max_width, estimated))
        tree_width = max(self.config.sidebar.tree_min_width, target_width - 46)
        self.sidebar_frame.config(width=target_width)
        try:
            self.paned_window.paneconfigure(self.sidebar_frame, minsize=self.config.sidebar.min_width)
        except tk.TclError:
            pass
        try:
            self.tree.column('#0', width=tree_width, minwidth=self.config.sidebar.tree_min_width, stretch=True)
        except tk.TclError:
            pass

    def _setup_ui(self) -> None:
        build_main_ui(self)

    def _bind_shortcuts(self) -> Any:
        self.root.bind('<Left>', lambda e: self.on_global_horizontal_key(e, -1))
        self.root.bind('<Right>', lambda e: self.on_global_horizontal_key(e, 1))
        self.tree.bind('<Left>', lambda e: self.on_global_horizontal_key(e, -1))
        self.tree.bind('<Right>', lambda e: self.on_global_horizontal_key(e, 1))
        self.root.bind('<Up>', lambda e: self.on_global_vertical_key(e, -1))
        self.root.bind('<Down>', lambda e: self.on_global_vertical_key(e, 1))
        self.root.bind_all('<Button-1>', self.on_global_mouse_click, add='+')


    def on_empty_panel_click(self, event: Any) -> Any:
        """Open folder picker when the side/tag panels are clicked before loading data.

        This makes the blank left module and blank right tag module behave like
        the Load Folder button while preserving normal widget behavior after a
        folder has been loaded.
        """
        if self.loaded_folder_path or self.groups:
            return None
        widget = getattr(event, 'widget', None)
        try:
            widget_class = widget.winfo_class() if widget is not None else ''
        except tk.TclError:
            widget_class = ''
        if widget_class in {'Button', 'TButton'}:
            return None
        self.load_folder()
        return 'break'

    def on_tree_select(self, event: Any) -> Any:
        self.tree.focus_set()
        selection = self.tree.selection()
        if not selection:
            return
        new_node_id = selection[0]
        old_node_id = self.current_tree_node
        if old_node_id:
            self.save_tag_state(old_node_id)
            self._confirm_unmarked_seq_if_needed(old_node_id, new_node_id)
        self.current_tree_node = new_node_id
        self.load_tag_state(new_node_id)
        filepaths = self.groups.get(new_node_id, [])
        if not filepaths:
            self.clear_view(reset_tags=False)
            self.canvas.itemconfig(self.txt_status, text='该节点为目录，请选择子序列', fill=STYLE.colors.text_quaternary)
            self._refresh_seq_stats()
            return
        self.dataset_id += 1
        self._invalidate_preload()
        self._invalidate_render()
        self._cancel_preload_submit_job()
        self._cancel_slider_job()
        self._clear_render_queue()
        self._clear_caches(clear_original=True)
        self.current_filepaths = filepaths
        self.current_idx = -1
        self.canvas.itemconfig(self.image_on_canvas, image='')
        self.slider.state(['!disabled'])
        self.slider.config(to=len(filepaths) - 1)
        self.canvas.itemconfig(self.txt_status, text='')
        self.lbl_filename.config(text='Loading...')
        self.lbl_counter.config(text=f'0 / {len(filepaths)}')
        self.slider.set(0)
        self.update_image_index(0, force=True)
        self._refresh_seq_stats()

    def on_tree_click(self, event: Any) -> Any:
        """点击 seq 层时直接展开/收起，并在展开时跳到第一组子序列。"""
        row_id = self.tree.identify_row(event.y)
        if not row_id or row_id not in self.seq_folder_nodes:
            return None
        self._toggle_seq_node_from_click(row_id)
        return 'break'

    def on_tree_open(self, event: Any) -> Any:
        """通过键盘或系统默认方式展开 seq 组时，自动将光标放到第一组子序列。"""
        node_id = self.tree.focus()
        if not node_id or node_id not in self.seq_folder_nodes:
            return
        first_child = self._first_child_sequence_node(node_id)
        if first_child:
            self._select_tree_node_without_unmarked_prompt(first_child)

    def clear_view(self, reset_tags: Any=True) -> Any:
        self.dataset_id += 1
        self._invalidate_preload()
        self._invalidate_render()
        self._cancel_preload_submit_job()
        self._cancel_slider_job()
        self._clear_render_queue()
        self.current_filepaths = []
        self._clear_caches(clear_original=True)
        self.current_idx = -1
        self.slider.state(['disabled'])
        self.slider.config(to=0)
        self.canvas.itemconfig(self.image_on_canvas, image='')
        self.canvas.itemconfig(self.txt_status, text='未选择', fill=STYLE.colors.text_quaternary)
        self.lbl_filename.config(text='无文件')
        self.lbl_counter.config(text='0 / 0')
        if reset_tags:
            self.current_tree_node = None
            self.is_loading_state = True
            self.var_status.set('')
            self.var_rerender.set(False)
            self._reset_tag_vars()
            self.is_loading_state = False
            self.on_status_change(mark_dirty=False)
        self._refresh_seq_stats()

    def copy_filename(self) -> Any:
        if not self.current_filepaths or self.current_idx < 0:
            return
        filename = os.path.basename(self.current_filepaths[self.current_idx])
        self.root.clipboard_clear()
        self.root.clipboard_append(filename)
        self.btn_copy.config(text='已复制!')
        self.root.after(1500, lambda: self.btn_copy.config(text='复制'))

    def copy_root_folder_name(self) -> Any:
        folder_name = self.root_folder_name.strip() if self.root_folder_name else ''
        if not folder_name:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(folder_name)
        self.btn_copy_root_folder.config(text='✓')
        self.root.after(1200, lambda: self.btn_copy_root_folder.config(text='⧉'))

    def on_global_mouse_click(self, event: Any) -> Any:
        """点击输入框以外区域时释放输入框光标。"""
        try:
            focus_widget = self.root.focus_get()
        except tk.TclError:
            return None
        if not self._is_text_input_widget(focus_widget):
            return None
        if self._is_text_input_widget(event.widget):
            return None
        try:
            event.widget.focus_set()
        except tk.TclError:
            self.root.focus_set()
        return None

    @staticmethod
    def _normalize_seq(value: Any) -> Any:
        value = (value or '').strip().replace('\\', '/')
        while value.startswith('./'):
            value = value[2:]
        return '.' if value in ('', '.') else value.rstrip('/')

    def _new_tree_iid(self) -> Any:
        self._node_counter += 1
        return f'seq_node_{self._node_counter}'

    def load_folder(self) -> Any:
        """Choose a root and start a bounded background scan."""
        if self.scan_future is not None and not self.scan_future.done():
            self.cancel_folder_scan()
            return
        folder_path = filedialog.askdirectory(title='选择关卡根目录')
        if not folder_path:
            return
        dialog = CustomQCDialog(self.root, 'QC by', '请输入质检人名称：')
        if dialog.result is None:
            return
        self._start_folder_scan(folder_path, dialog.result.strip(), dialog.import_csv_path)

    def _start_folder_scan(self, folder_path: str, qc_by_name: str, import_csv_path: str | None) -> None:
        """Submit one scan; the worker only writes to a bounded plain queue."""
        self._scan_generation += 1
        generation = self._scan_generation
        cancel_event = threading.Event()
        self.scan_cancel_event = cancel_event
        while True:
            try:
                self.scan_progress_queue.get_nowait()
            except queue.Empty:
                break

        def report_progress(entries: int, images: int) -> None:
            value = (entries, images)
            try:
                self.scan_progress_queue.put_nowait(value)
            except queue.Full:
                try:
                    self.scan_progress_queue.get_nowait()
                except queue.Empty:
                    return
                self.scan_progress_queue.put_nowait(value)

        self.btn_load.config(text="取消扫描", command=self.cancel_folder_scan)
        self.canvas.itemconfig(self.txt_status, text="正在扫描文件夹…", fill=STYLE.colors.text_quaternary)
        context = (folder_path, qc_by_name, import_csv_path)
        self.scan_future = self.scan_executor.submit(
            scan_image_folder,
            folder_path,
            image_extensions=self.config.safety.image_extensions,
            max_entries=self.config.safety.max_scan_entries,
            max_depth=self.config.safety.max_scan_depth,
            cancel_event=cancel_event,
            progress=report_progress,
        )
        self._scan_poll_job = self.root.after(
            self.config.performance.folder_scan_poll_ms,
            lambda: self._poll_folder_scan(generation, context),
        )

    def cancel_folder_scan(self) -> None:
        """Request cancellation without clearing the currently loaded data."""
        if self.scan_cancel_event is not None:
            self.scan_cancel_event.set()
        self.btn_load.state(["disabled"])
        self.canvas.itemconfig(self.txt_status, text="正在取消扫描…", fill=STYLE.colors.text_quaternary)

    def _restore_load_button(self) -> None:
        self.btn_load.config(text="Load Folder", command=self.load_folder)
        self.btn_load.state(["!disabled"])

    def _poll_folder_scan(self, generation: int, context: tuple[str, str, str | None]) -> None:
        """Poll a worker future from Tk and reject stale generations."""
        self._scan_poll_job = None
        if self._closed or generation != self._scan_generation or self.scan_future is None:
            return
        latest_progress = None
        while True:
            try:
                latest_progress = self.scan_progress_queue.get_nowait()
            except queue.Empty:
                break
        if latest_progress is not None:
            entries, images = latest_progress
            self.canvas.itemconfig(self.txt_status, text=f"正在扫描：{entries} 项，{images} 张图片")
        if not self.scan_future.done():
            self._scan_poll_job = self.root.after(
                self.config.performance.folder_scan_poll_ms,
                lambda: self._poll_folder_scan(generation, context),
            )
            return
        if self.scan_cancel_event is not None and self.scan_cancel_event.is_set():
            self.canvas.itemconfig(self.txt_status, text="扫描已取消", fill=STYLE.colors.text_quaternary)
            self._restore_load_button()
            return
        try:
            result = self.scan_future.result()
        except ScanCancelled:
            self.canvas.itemconfig(self.txt_status, text="扫描已取消", fill=STYLE.colors.text_quaternary)
            self._restore_load_button()
            return
        except Exception as exc:
            logger.error("文件夹扫描失败", exc_info=True)
            self.canvas.itemconfig(self.txt_status, text="文件夹扫描失败", fill=STYLE.colors.danger)
            self._restore_load_button()
            messagebox.showerror("加载失败", str(exc), parent=self.root)
            return
        self._begin_apply_folder_scan(result, context)

    def _begin_apply_folder_scan(
        self,
        result: FolderScanResult,
        context: tuple[str, str, str | None],
    ) -> None:
        """Commit a successful scan and build Tk nodes in bounded batches."""
        folder_path, qc_by_name, _ = context
        self.qc_by_name = qc_by_name
        self.root_folder_name = os.path.basename(os.path.normpath(folder_path))
        self.loaded_folder_path = folder_path
        self.csv_exported = False
        self.tree.delete(*self.tree.get_children())
        self._node_counter = 0
        self.groups.clear()
        self.tag_data.clear()
        self.node_metadata.clear()
        self.seq_folder_nodes.clear()
        self.seq_rel_paths.clear()
        self.seq_rel_path_set.clear()
        self.clear_view()
        self.lbl_qc_by.config(text=f'QC by: {self.qc_by_name}')
        if hasattr(self, 'lbl_root_folder_name'):
            self.lbl_root_folder_name.config(text=self.root_folder_name)
        root_node = self.tree.insert('', 'end', text=self.root_folder_name, open=True)
        self._scan_apply_state = {
            "result": result,
            "context": context,
            "folder_nodes": {result.root_path: root_node},
            "directory_index": 0,
            "group_index": 0,
            "current_node": None,
        }
        self.btn_load.state(["disabled"])
        self.canvas.itemconfig(self.txt_status, text="正在构建序列列表…", fill=STYLE.colors.text_quaternary)
        self.root.after_idle(self._apply_folder_scan_batch_guarded)

    def _apply_folder_scan_batch_guarded(self) -> None:
        """Restore UI controls if applying a valid scan result still fails."""
        try:
            self._apply_folder_scan_batch()
        except Exception as exc:
            logger.error("构建序列列表失败", exc_info=True)
            self._scan_apply_state = None
            self.canvas.itemconfig(self.txt_status, text="构建序列列表失败", fill=STYLE.colors.danger)
            self._restore_load_button()
            messagebox.showerror("加载失败", str(exc), parent=self.root)

    def _apply_folder_scan_batch(self) -> None:
        """Apply at most one configured batch of Treeview operations."""
        state = self._scan_apply_state
        if self._closed or state is None:
            return
        result: FolderScanResult = state["result"]
        budget = self.config.performance.tree_build_batch_size
        while budget > 0 and state["directory_index"] < len(result.directories):
            scanned = result.directories[state["directory_index"]]
            if state["current_node"] is None:
                if scanned.path == result.root_path:
                    seq_node = state["folder_nodes"][result.root_path]
                else:
                    parent_node = state["folder_nodes"].get(scanned.parent_path)
                    if parent_node is None:
                        raise RuntimeError(f"扫描结果缺少父目录：{scanned.path}")
                    seq_node = self.tree.insert(parent_node, "end", text=scanned.name)
                    state["folder_nodes"][scanned.path] = seq_node
                state["current_node"] = seq_node
                budget -= 1
                if scanned.groups:
                    rel = scanned.rel_path
                    self.seq_folder_nodes.add(seq_node)
                    self.node_metadata[seq_node] = rel
                    if rel not in self.seq_rel_path_set:
                        self.seq_rel_path_set.add(rel)
                        self.seq_rel_paths.append(rel)
                    self.tag_data.setdefault(rel, self._create_empty_tag_state())

            while budget > 0 and state["group_index"] < len(scanned.groups):
                prefix, paths = scanned.groups[state["group_index"]]
                uid = self._new_tree_iid()
                self.tree.insert(state["current_node"], "end", text=prefix, iid=uid)
                self.groups[uid] = list(paths)
                self.node_metadata[uid] = scanned.rel_path
                state["group_index"] += 1
                budget -= 1

            if state["group_index"] >= len(scanned.groups):
                state["directory_index"] += 1
                state["group_index"] = 0
                state["current_node"] = None

        if state["directory_index"] < len(result.directories):
            self.root.after_idle(self._apply_folder_scan_batch_guarded)
            return
        _, _, pending_import_csv_path = state["context"]
        self._scan_apply_state = None
        self._adjust_sidebar_width()
        if result.image_count == 0:
            self.canvas.itemconfig(self.txt_status, text='未找到图片')
        else:
            self.canvas.itemconfig(self.txt_status, text=f"已加载 {result.image_count} 张图片")
        if pending_import_csv_path:
            self.import_csv(import_path=pending_import_csv_path, show_message=True)
        self._refresh_seq_stats()
        self._restore_load_button()
