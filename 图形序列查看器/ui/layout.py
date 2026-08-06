"""Main window layout construction helpers.

The controller delegates widget construction to this module.  Sections in the
right tag panel are built with reusable card components rather than legacy
``LabelFrame`` widgets, which gives a more coherent macOS dark-mode visual
language and keeps the controller smaller.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ui.components import grid_status_options, make_card, make_checkbutton, make_radiobutton
from ui.mousewheel import bind_mousewheel_scroll
from ui.styles import STYLE


def build_main_ui(app: Any) -> None:
    """Build the main window layout."""
    self = app
    colors = STYLE.colors
    fonts = STYLE.fonts

    right_bg = colors.panel_bg

    self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
    self.paned_window.pack(expand=True, fill=tk.BOTH)

    # Sidebar -----------------------------------------------------------------
    self.sidebar_frame = tk.Frame(
        self.paned_window,
        width=self.config.sidebar.initial_width,
        bg=colors.sidebar_bg,
    )
    self.sidebar_frame.pack_propagate(False)
    self.sidebar_frame.bind("<Button-1>", self.on_empty_panel_click, add="+")
    self.paned_window.add(self.sidebar_frame, weight=0)

    sidebar_header = tk.Frame(self.sidebar_frame, bg=colors.sidebar_bg)
    sidebar_header.pack(fill=tk.X, padx=10, pady=(8, 4))
    tk.Label(
        sidebar_header,
        text="文件夹与序列",
        font=fonts.section,
        bg=colors.sidebar_bg,
        fg=colors.text_primary,
    ).pack(side=tk.LEFT)

    folder_bar = tk.Frame(self.sidebar_frame, bg=colors.sidebar_bg)
    folder_bar.pack(fill=tk.X, padx=10, pady=(0, 8))
    self.lbl_root_folder_name = tk.Label(
        folder_bar,
        text="未加载文件夹",
        anchor="w",
        font=fonts.footnote,
        fg=colors.text_tertiary,
        bg=colors.sidebar_bg,
    )
    self.lbl_root_folder_name.pack(side=tk.LEFT)
    self.btn_copy_root_folder = tk.Button(
        folder_bar,
        text="⧉",
        width=2,
        height=1,
        padx=3,
        pady=0,
        relief=tk.FLAT,
        borderwidth=0,
        cursor="hand2",
        bg=colors.sidebar_bg,
        fg=colors.text_tertiary,
        activebackground=colors.control_hover_bg,
        activeforeground=colors.text_primary,
        command=self.copy_root_folder_name,
    )
    self.btn_copy_root_folder.pack(side=tk.LEFT, padx=(4, 0))

    tree_frame = tk.Frame(self.sidebar_frame, bg=colors.sidebar_bg)
    tree_frame.pack(expand=True, fill=tk.BOTH, padx=6)
    self.tree_scroll_y = ttk.Scrollbar(tree_frame)
    self.tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    self.tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
    self.tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    self.tree = ttk.Treeview(
        tree_frame,
        yscrollcommand=self.tree_scroll_y.set,
        xscrollcommand=self.tree_scroll_x.set,
        selectmode="browse",
        show="tree",
    )
    self.tree.column(
        "#0",
        width=max(260, self.config.sidebar.initial_width - 40),
        minwidth=self.config.sidebar.tree_min_width,
        stretch=True,
    )
    self.tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
    self.tree_scroll_y.config(command=self.tree.yview)
    self.tree_scroll_x.config(command=self.tree.xview)
    self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
    self.tree.bind("<Button-1>", self.on_tree_click)
    self.tree.bind("<Button-1>", self.on_empty_panel_click, add="+")
    self.tree.bind("<<TreeviewOpen>>", self.on_tree_open)
    self.tree.bind("<Up>", lambda e: self.on_tree_vertical_key(e, -1))
    self.tree.bind("<Down>", lambda e: self.on_tree_vertical_key(e, 1))

    self.btn_load = ttk.Button(
        self.sidebar_frame,
        text="Load Folder",
        command=self.load_folder,
        style="Accent.TButton",
    )
    self.btn_load.pack(fill=tk.X, padx=8, pady=(10, 10))

    # Main canvas --------------------------------------------------------------
    self.main_view_frame = tk.Frame(self.paned_window, bg=colors.canvas_bg)
    self.main_view_frame.bind("<Button-1>", self.on_empty_panel_click, add="+")
    self.paned_window.add(self.main_view_frame, weight=1)

    self.canvas = tk.Canvas(self.main_view_frame, bg=colors.canvas_bg, highlightthickness=0)
    self.canvas.pack(expand=True, fill=tk.BOTH)
    self.canvas.bind("<Button-1>", self.on_empty_panel_click, add="+")
    self.canvas.bind("<Configure>", self.on_canvas_resize)

    self.image_on_canvas = self.canvas.create_image(0, 0, anchor=tk.CENTER)
    self.txt_status = self.canvas.create_text(
        0,
        0,
        text="点击此处加载文件夹",
        fill=colors.text_placeholder,
        font=fonts.canvas_status,
        anchor=tk.CENTER,
    )
    self.txt_seq_stats = self.canvas.create_text(
        0,
        0,
        text="",
        fill=colors.text_tertiary,
        font=fonts.body_emphasized,
        anchor=tk.NE,
        justify=tk.RIGHT,
    )
    self.txt_cache_stats = self.canvas.create_text(
        0,
        0,
        text="",
        fill=colors.text_quaternary,
        font=fonts.monospace,
        anchor=tk.SE,
        justify=tk.RIGHT,
    )

    control_frame = tk.Frame(self.main_view_frame, bg=colors.canvas_bg, pady=10, padx=15)
    control_frame.pack(side=tk.BOTTOM, fill=tk.X)

    name_panel = tk.Frame(control_frame, bg=colors.canvas_bg)
    name_panel.pack(side=tk.TOP, pady=(0, 10))
    self.lbl_filename = tk.Label(
        name_panel,
        text="无文件",
        font=fonts.title,
        fg=colors.text_primary,
        bg=colors.canvas_bg,
    )
    self.lbl_filename.pack(side=tk.LEFT, padx=(0, 10))
    self.btn_copy = ttk.Button(name_panel, text="复制", width=6, command=self.copy_filename)
    self.btn_copy.pack(side=tk.LEFT)

    slider_panel = tk.Frame(control_frame, bg=colors.canvas_bg)
    slider_panel.pack(fill=tk.X, expand=True)
    self.slider = ttk.Scale(slider_panel, from_=0, to=0, orient=tk.HORIZONTAL, command=self.on_slider_move)
    self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))
    self.slider.bind("<ButtonPress-1>", self.on_slider_press)
    self.slider.bind("<ButtonRelease-1>", self.on_slider_release)
    self.lbl_counter = tk.Label(
        slider_panel,
        text="0 / 0",
        width=15,
        anchor="e",
        fg=colors.text_secondary,
        bg=colors.canvas_bg,
        font=fonts.body,
    )
    self.lbl_counter.pack(side=tk.RIGHT)

    # Tag panel ----------------------------------------------------------------
    self.right_panel = tk.Frame(self.paned_window, width=self.config.tag_panel.width, bg=right_bg)
    self.right_panel.pack_propagate(False)
    self.right_panel.bind("<Button-1>", self.on_empty_panel_click, add="+")
    self.paned_window.add(self.right_panel, weight=0)

    top_header_frame = tk.Frame(self.right_panel, bg=right_bg)
    top_header_frame.pack(fill=tk.X, pady=(12, 8), padx=12)
    tk.Label(
        top_header_frame,
        text="数据质检 Tag",
        font=fonts.title,
        bg=right_bg,
        fg=colors.text_primary,
    ).pack(side=tk.LEFT)
    self.lbl_qc_by = tk.Label(
        top_header_frame,
        text="QC by: 未录入",
        font=fonts.footnote,
        bg=right_bg,
        fg=colors.text_tertiary,
    )
    self.lbl_qc_by.pack(side=tk.RIGHT)
    self.lbl_qc_by.bind("<Button-1>", lambda e: self.change_qc_by())
    self.lbl_qc_by.config(cursor="hand2")

    tag_canvas = tk.Canvas(self.right_panel, bg=right_bg, highlightthickness=0)
    tag_scrollbar = ttk.Scrollbar(self.right_panel, orient="vertical", command=tag_canvas.yview)
    self.tag_frame = tk.Frame(tag_canvas, bg=right_bg)
    tag_canvas.configure(yscrollcommand=tag_scrollbar.set)
    tag_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tag_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    self.tag_canvas = tag_canvas
    tag_canvas.bind("<Button-1>", self.on_empty_panel_click, add="+")
    self.tag_frame.bind("<Button-1>", self.on_empty_panel_click, add="+")
    self.tag_canvas_window = tag_canvas.create_window(
        (0, 0),
        window=self.tag_frame,
        anchor="nw",
        width=self.config.tag_panel.width - 24,
    )
    self.tag_frame.bind("<Configure>", lambda e: tag_canvas.configure(scrollregion=tag_canvas.bbox("all")))
    tag_canvas.bind(
        "<Configure>",
        lambda e: tag_canvas.itemconfig(
            self.tag_canvas_window,
            width=max(self.config.tag_panel.canvas_window_min_width, e.width - 4),
        ),
    )
    self.var_status.trace_add("write", self.on_status_change)

    # Status card
    _, status_body = make_card(self.tag_frame, "检验结果", pady=(4, 8))
    self.status_radiobuttons = grid_status_options(
        status_body,
        [
            ("", "未标记"),
            ("合格", "合格"),
            ("待定", "待定"),
            ("不合格", "不合格"),
        ],
        self.var_status,
    )
    self.chk_rerender = make_checkbutton(status_body, text="重新渲染", variable=self.var_rerender)
    self.chk_rerender.grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(5, 3))
    self._sync_rerender_widget_state()

    def build_tags(container: tk.Frame, tag_defs: list[dict[str, Any]], vars_dict: dict[str, Any]) -> None:
        for tag_def in tag_defs:
            tag_name = tag_def["name"]
            tag_vars = vars_dict[tag_name]
            cb = make_checkbutton(container, text=tag_name, variable=tag_vars["check"])
            cb.pack(anchor="w", padx=6, pady=(6, 0))
            if tag_def.get("has_sub"):
                sub_frame = tk.Frame(container, bg=colors.card_bg)
                sub_frame.pack(anchor="w", padx=28)
                for sub_value in tag_def["subs"]:
                    make_radiobutton(sub_frame, text=sub_value, variable=tag_vars["sub"], value=sub_value).pack(side=tk.LEFT)
            entry = tk.Text(container,height=2,wrap="word")
            entry.pack(anchor="w", fill=tk.X, padx=(28, 12), pady=(0, 6))
            def _sync_text(event=None, tv=tag_vars["text"], w=entry):
                val = w.get("1.0", "end-1c")
                if tv.get() != val:
                    tv.set(val)

            entry.bind("<KeyRelease>", _sync_text)

            def _sync_from_var(*args, tv=tag_vars["text"], w=entry):
                val = tv.get()
                if w.get("1.0","end-1c") != val:
                    w.delete("1.0", "end")
                    w.insert("1.0", val)

            tag_vars["text"].trace_add("write", _sync_from_var)
            tag_vars["text_widget"] = entry

    _, self.lf_light = make_card(self.tag_frame, "光影问题", pady=(0, 8))
    build_tags(self.lf_light, self.light_tags_def, self.tag_vars_light)

    _, self.lf_comp = make_card(self.tag_frame, "构图问题", pady=(0, 8))
    build_tags(self.lf_comp, self.comp_tags_def, self.tag_vars_comp)

    bind_mousewheel_scroll(self.tag_canvas, self.tag_frame)

    btn_frame_export = tk.Frame(self.right_panel, bg=right_bg)
    btn_frame_export.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=12)
    ttk.Button(btn_frame_export, text="导入 CSV", command=self.import_csv).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
    ttk.Button(btn_frame_export, text="导出 CSV", command=self.export_csv).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
