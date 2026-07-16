"""Dialog classes with macOS design language."""
from typing import Any
import os
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ui.styles import STYLE
from utils.logger import logger


class CustomQCDialog(tk.Toplevel):
    """QC by input dialog with macOS aesthetics."""

    def __init__(self, parent: Any, title: Any, prompt: Any) -> None:
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.import_csv_path = None
        colors = STYLE.colors
        fonts = STYLE.fonts

        self.configure(bg=colors.window_bg)
        self.resizable(False, False)

        # Title label
        lbl = tk.Label(
            self,
            text="请输入 QC by，或导入 CSV 自动识别。",
            bg=colors.window_bg,
            fg=colors.text_primary,
            justify=tk.LEFT,
            font=fonts.body_emphasized,
        )
        lbl.pack(padx=20, pady=(18, 10), anchor="w")

        # Input field
        self.entry = tk.Entry(
            self,
            bg=colors.field_bg,
            fg=colors.text_primary,
            insertbackground=colors.text_primary,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=colors.field_border,
            highlightcolor=colors.field_border,
            width=28,
        )
        self.entry.pack(padx=20, pady=(0, 16), fill=tk.X, ipady=4)
        self.entry.focus_set()

        # Button row
        btn_frame = tk.Frame(self, bg=colors.window_bg)
        btn_frame.pack(pady=(0, 18))

        ttk.Button(
            btn_frame,
            text="取消",
            width=8,
            command=self.cancel,
        ).pack(side=tk.LEFT, padx=6)

        ttk.Button(
            btn_frame,
            text="导入 CSV",
            width=10,
            command=self.import_csv,
        ).pack(side=tk.LEFT, padx=6)

        ttk.Button(
            btn_frame,
            text="确定",
            width=8,
            command=self.ok,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=6)

        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.cancel())

        # Position and show
        self.geometry(
            "380x160+{}+{}".format(
                parent.winfo_rootx() + 120, parent.winfo_rooty() + 120
            )
        )
        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

    @staticmethod
    def _read_qc_by_from_csv(csv_path: Any) -> Any:
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames:
                    return ""
                qc_field = None
                for field in reader.fieldnames:
                    if field and field.strip().lower() == "qc by":
                        qc_field = field
                        break
                if not qc_field:
                    return ""
                for row in reader:
                    qc_val = row.get(qc_field, "")
                    if qc_val and qc_val.strip():
                        return qc_val.strip()
        except Exception:
            logger.error("读取 CSV 中的 QC by 失败", exc_info=True)
        return ""

    def import_csv(self) -> Any:
        import_path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("CSV files", "*.csv")],
            title="导入 CSV 文件",
        )
        if not import_path:
            return
        self.import_csv_path = import_path
        qc_by = self._read_qc_by_from_csv(import_path)
        self.result = qc_by.strip() if qc_by else ""
        self.destroy()

    def ok(self) -> Any:
        self.result = self.entry.get()
        self.destroy()

    def cancel(self) -> Any:
        self.destroy()


class CsvOverwriteDialog(tk.Toplevel):
    """CSV overwrite confirmation dialog with macOS design."""

    def __init__(self, parent: Any, export_path: Any) -> None:
        super().__init__(parent)
        self.title("CSV 文件已存在")
        self.result = "cancel"
        colors = STYLE.colors
        fonts = STYLE.fonts

        self.configure(bg=colors.window_bg)
        self.resizable(False, False)

        filename = os.path.basename(export_path)
        msg = f"已存在同名 CSV 文件：\n{filename}\n\n请选择覆盖原文件，或自动保存为副本。"

        lbl = tk.Label(
            self,
            text=msg,
            bg=colors.window_bg,
            fg=colors.text_primary,
            justify=tk.LEFT,
            wraplength=380,
            font=fonts.body,
        )
        lbl.pack(padx=24, pady=(22, 18), anchor="w")

        btn_frame = tk.Frame(self, bg=colors.window_bg)
        btn_frame.pack(pady=(0, 20))

        ttk.Button(
            btn_frame,
            text="取消",
            width=10,
            command=self.cancel,
        ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            btn_frame,
            text="保存副本",
            width=12,
            command=self.save_copy,
        ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            btn_frame,
            text="覆盖",
            width=10,
            command=self.overwrite,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=8)

        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<Return>", lambda e: self.overwrite())

        self.geometry(
            "440x180+{}+{}".format(
                parent.winfo_rootx() + 140, parent.winfo_rooty() + 140
            )
        )
        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

    def overwrite(self) -> Any:
        self.result = "overwrite"
        self.destroy()

    def save_copy(self) -> Any:
        self.result = "copy"
        self.destroy()

    def cancel(self) -> Any:
        self.result = "cancel"
        self.destroy()


class CsvSaveDialog(tk.Toplevel):
    """Custom CSV save location dialog with macOS design."""

    def __init__(self, parent: Any, initial_dir: Any, initial_filename: Any) -> None:
        super().__init__(parent)
        self.title("导出 CSV")
        self.result = ""
        colors = STYLE.colors
        fonts = STYLE.fonts

        self.configure(bg=colors.window_bg)
        self.resizable(False, False)

        safe_dir = initial_dir if initial_dir and os.path.isdir(initial_dir) else os.getcwd()
        self.dir_var = tk.StringVar(value=safe_dir)
        self.filename_var = tk.StringVar(value=initial_filename)

        # Header
        title_lbl = tk.Label(
            self,
            text="保存 CSV 文件",
            bg=colors.window_bg,
            fg=colors.text_primary,
            font=fonts.title,
        )
        title_lbl.pack(padx=20, pady=(20, 12), anchor="w")

        # Directory row
        row_dir = tk.Frame(self, bg=colors.window_bg)
        row_dir.pack(fill=tk.X, padx=20, pady=(0, 10))

        tk.Label(
            row_dir,
            text="位置",
            bg=colors.window_bg,
            fg=colors.text_secondary,
            width=6,
            anchor="w",
            font=fonts.body,
        ).pack(side=tk.LEFT)

        self.dir_label = tk.Label(
            row_dir,
            textvariable=self.dir_var,
            bg=colors.field_bg,
            fg=colors.text_primary,
            anchor="w",
            padx=10,
            pady=4,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=colors.field_border,
            highlightcolor=colors.field_border,
            font=fonts.body,
        )
        self.dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 10))

        ttk.Button(
            row_dir,
            text="选择位置…",
            width=12,
            command=self.choose_dir,
        ).pack(side=tk.LEFT)

        # Filename row
        row_file = tk.Frame(self, bg=colors.window_bg)
        row_file.pack(fill=tk.X, padx=20, pady=(0, 18))

        tk.Label(
            row_file,
            text="文件名",
            bg=colors.window_bg,
            fg=colors.text_secondary,
            width=6,
            anchor="w",
            font=fonts.body,
        ).pack(side=tk.LEFT)

        self.entry = tk.Entry(
            row_file,
            textvariable=self.filename_var,
            bg=colors.field_bg,
            fg=colors.text_primary,
            insertbackground=colors.text_primary,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=colors.field_border,
            highlightcolor=colors.field_border,
            font=fonts.body,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), ipady=4)
        self.entry.focus_set()
        self.entry.selection_range(0, tk.END)

        # Action buttons
        btn_frame = tk.Frame(self, bg=colors.window_bg)
        btn_frame.pack(pady=(0, 20))

        ttk.Button(
            btn_frame,
            text="取消",
            width=10,
            command=self.cancel,
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            btn_frame,
            text="保存",
            width=10,
            command=self.ok,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=10)

        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<Return>", lambda e: self.ok())

        self.geometry(
            "580x220+{}+{}".format(
                parent.winfo_rootx() + 120, parent.winfo_rooty() + 120
            )
        )
        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

    def choose_dir(self) -> Any:
        chosen = filedialog.askdirectory(
            parent=self,
            title="选择 CSV 保存位置",
            initialdir=self.dir_var.get(),
        )
        if chosen:
            self.dir_var.set(chosen)

    def ok(self) -> Any:
        filename = self.filename_var.get().strip()
        if not filename:
            messagebox.showwarning(
                "文件名为空",
                "请输入 CSV 文件名。",
                parent=self,
            )
            return
        if os.path.basename(filename) != filename:
            messagebox.showwarning(
                "文件名无效",
                "文件名中不能包含路径分隔符。",
                parent=self,
            )
            return
        if not filename.lower().endswith(".csv"):
            filename += ".csv"
        self.result = os.path.join(self.dir_var.get(), filename)
        self.destroy()

    def cancel(self) -> Any:
        self.result = ""
        self.destroy()


class SeqQualifiedDialog(tk.Toplevel):
    """Lightweight confirmation dialog for unmarked sequences."""

    def __init__(self, parent: Any, seq_name: Any) -> None:
        super().__init__(parent)
        self.title("seq 未标记")
        self.result = "ignore"
        colors = STYLE.colors
        fonts = STYLE.fonts

        self.configure(bg=colors.window_bg)
        self.resizable(False, False)

        prompt = f"当前 seq 尚未进行 Tag 操作：\n{seq_name}\n\n是否将本组 seq 判定为合格？"

        lbl = tk.Label(
            self,
            text=prompt,
            bg=colors.window_bg,
            fg=colors.text_primary,
            justify=tk.LEFT,
            wraplength=380,
            font=fonts.body,
        )
        lbl.pack(padx=24, pady=(24, 20), anchor="w")

        btn_frame = tk.Frame(self, bg=colors.window_bg)
        btn_frame.pack(pady=(0, 22))

        ttk.Button(
            btn_frame,
            text="忽略",
            width=12,
            command=self.ignore,
        ).pack(side=tk.LEFT, padx=12)

        ttk.Button(
            btn_frame,
            text="是",
            width=12,
            command=self.yes,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=12)

        self.bind("<Return>", lambda e: self.yes())
        self.bind("<Escape>", lambda e: self.ignore())

        self.geometry(
            "+{}+{}".format(parent.winfo_rootx() + 140, parent.winfo_rooty() + 140)
        )
        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

    def yes(self) -> Any:
        self.result = "yes"
        self.destroy()

    def ignore(self) -> Any:
        self.result = "ignore"
        self.destroy()