"""Shared typed state contract for the application controller mixins.

Tk widgets are created by :mod:`ui.layout`, while business behavior is split
across several mixins.  Keeping their shared state here makes that runtime
composition visible to static type checkers without weakening ``attr-defined``
checks project-wide.
"""

from __future__ import annotations

import queue
import subprocess
import threading
import tkinter as tk
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from tkinter import ttk
from typing import TYPE_CHECKING, Any

from config.settings import AppConfig
from PIL import Image, ImageTk

from core.folder_scanner import FolderScanResult

if TYPE_CHECKING:
    from ui.motion import MotionManager

TagDefinition = dict[str, Any]
TagState = dict[str, Any]
TagVariables = dict[str, Any]
RenderKey = tuple[int, int, int, int]
OriginalKey = tuple[int, int]
RenderRequest = tuple[int, int, int, str, int, int]
RenderResult = tuple[int, int, int, int, int, Image.Image | None, BaseException | None]


class AppState:
    """Runtime state and cross-mixin methods supplied by ``FrameScrubber``."""

    config: AppConfig
    root: tk.Tk
    motion: MotionManager

    _closed: bool
    root_folder_name: str
    loaded_folder_path: str
    qc_by_name: str
    csv_exported: bool
    is_loading_state: bool
    current_tk_image: ImageTk.PhotoImage | None
    _node_counter: int

    cpu_count: int
    preload_worker_count: int
    executor: ThreadPoolExecutor
    render_queue: queue.Queue[RenderRequest]
    render_result_queue: queue.Queue[RenderResult]
    render_stop_event: threading.Event
    render_seq: int
    render_worker: threading.Thread
    render_cache: OrderedDict[RenderKey, Image.Image]
    original_cache: OrderedDict[OriginalKey, Image.Image]
    max_render_cache_size: int
    max_original_cache_size: int
    preload_radius: int
    drag_preload_radius: int
    preload_pending: set[RenderKey]
    cache_lock: threading.RLock
    preload_seq: int
    _preload_submit_job: str | None
    _resize_job: str | None
    _render_result_poll_job: str | None
    _render_result_empty_streak: int
    _cache_render_hits: int
    _cache_render_misses: int
    _cache_original_hits: int
    _cache_original_misses: int
    _cache_stats_dirty: bool

    scan_executor: ThreadPoolExecutor
    scan_cancel_event: threading.Event | None
    scan_future: Future[FolderScanResult] | None
    scan_progress_queue: queue.Queue[tuple[int, int]]
    _scan_poll_job: str | None
    _scan_generation: int
    _scan_apply_state: dict[str, Any] | None

    groups: dict[str, list[str]]
    tag_data: dict[str, TagState]
    node_metadata: dict[str, str]
    seq_folder_nodes: set[str]
    seq_rel_paths: list[str]
    seq_rel_path_set: set[str]
    current_tree_node: str | None
    _suppress_unmarked_prompt: bool
    _suppress_unmarked_prompt_target: str | None

    current_filepaths: list[str]
    current_idx: int
    dataset_id: int
    _slider_job: str | None
    _slider_pending_idx: int | None
    _slider_is_dragging: bool
    _programmatic_slider_update: bool
    _keyboard_preview_active: bool
    _keyboard_preview_job: str | None
    _tree_center_job: str | None
    _reveal_process: subprocess.Popen[bytes] | None
    _reveal_poll_job: str | None
    _reveal_started_at: float
    navigation_direction: int
    _last_frame_idx_for_direction: int

    var_status: tk.StringVar
    var_rerender: tk.BooleanVar
    var_reduce_motion: tk.BooleanVar
    light_tags_def: list[TagDefinition]
    comp_tags_def: list[TagDefinition]
    tag_vars_light: dict[str, TagVariables]
    tag_vars_comp: dict[str, TagVariables]

    paned_window: tk.PanedWindow
    sidebar_frame: tk.Frame
    right_panel: tk.Frame
    tree: ttk.Treeview
    canvas: tk.Canvas
    slider: ttk.Scale
    image_on_canvas: int
    txt_status: int
    txt_seq_stats: int
    txt_cache_stats: int
    lbl_filename: ttk.Label
    lbl_counter: ttk.Label
    lbl_qc_by: tk.Label
    lbl_export_status: ttk.Label
    lbl_root_folder_name: tk.Label
    btn_load: ttk.Button
    btn_copy: tk.Button
    btn_copy_root_folder: tk.Button
    btn_export_csv: ttk.Button
    chk_rerender: tk.Checkbutton
    lf_light: tk.Misc
    lf_comp: tk.Misc

    def _show_canvas_status(self, text: str, *, color: str | None = None, animate: bool = False) -> None:
        raise NotImplementedError

    def _mark_export_dirty(self) -> None:
        raise NotImplementedError

    def _refresh_export_status(self) -> None:
        raise NotImplementedError

    def _refresh_seq_stats(self) -> None:
        raise NotImplementedError

    def _persist_current_tag_state_and_refresh_stats(self) -> None:
        raise NotImplementedError

    def _schedule_tree_center(self, node_id: str) -> None:
        raise NotImplementedError

    def _reset_tag_vars(self) -> None:
        raise NotImplementedError

    def _normalize_tag_state(self, state: Any) -> TagState:
        raise NotImplementedError

    def _is_tag_state_empty(self, state: Any) -> bool:
        raise NotImplementedError

    def _create_empty_tag_state(self, *, status: str = "", rerender: bool = False) -> TagState:
        raise NotImplementedError

    def _effective_seq_rel_paths(self) -> list[str]:
        raise NotImplementedError

    def _normalize_seq(self, value: Any) -> str:
        raise NotImplementedError

    def _apply_tree_state_after_csv_import(self) -> None:
        raise NotImplementedError

    def _confirm_current_last_seq_before_export(self) -> None:
        raise NotImplementedError

    def save_tag_state(self, node_id: str) -> None:
        raise NotImplementedError

    def load_tag_state(self, node_id: str) -> None:
        raise NotImplementedError

    def on_status_change(self, *args: Any, mark_dirty: bool = True) -> None:
        raise NotImplementedError

    def on_tree_select(self, event: Any) -> Any:
        raise NotImplementedError

    def on_tree_vertical_key(self, event: Any, step: int) -> str:
        raise NotImplementedError

    def update_image_index(self, idx: int, force: bool = False) -> None:
        raise NotImplementedError

    def step_frame(self, step: int) -> str | None:
        raise NotImplementedError

    def step_group(self, step: int) -> None:
        raise NotImplementedError
