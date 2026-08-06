"""CSV import/export behavior for QC tag data."""
from __future__ import annotations

import csv
import datetime
import os
import re
from dataclasses import dataclass
from tkinter import filedialog, messagebox
from typing import Any

from ui.dialogs import CsvOverwriteDialog, CsvSaveDialog
from utils.logger import logger
from utils.safe_files import atomic_write_text, require_file_size

from core.tag_engine import normalize_sub_value, normalize_tag_name


@dataclass(frozen=True)
class CsvImportResult:
    """Fully parsed changes that can be committed as one transaction."""

    updates: dict[str, Any]
    matched: int
    unmatched: int
    qc_by: str

class CsvIOMixin:

    @staticmethod
    def _csv_text(value: Any) -> str:
        """Return a stripped CSV cell value, treating missing cells as empty."""
        text = "" if value is None else str(value).strip()
        if text.startswith("'") and text[1:].lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
            return text[1:]
        return text

    @staticmethod
    def _excel_safe_cell(value: Any) -> Any:
        """Prevent spreadsheet formula execution while preserving round trips."""
        if not isinstance(value, str):
            return value
        if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + value
        return value

    def _parse_and_apply_tags(self, tag_str: Any, state_dict: Any, tag_defs: Any) -> None:
        """Parse exported tag text back into a tag-state dictionary.

        The parser matches tag names by descending length and uses explicit
        segment parsing instead of naive ``str.find``. This avoids accidental
        matches when a future tag name is a substring of another tag name.
        """
        if not tag_str:
            return

        raw_text = str(tag_str).replace("模型衔接地面处异常反光", "漏光")
        tag_names = [normalize_tag_name(t["name"]) for t in tag_defs]
        tag_names = sorted(set(tag_names), key=len, reverse=True)
        if not tag_names:
            return

        name_pattern = "|".join(re.escape(name) for name in tag_names)
        # Match: TagName, optional (sub), optional : text up to the ideographic comma separator.
        pattern = re.compile(rf"(?P<name>{name_pattern})(?P<sub>\([^)]*\))?(?P<text>\s*:\s*[^、]*)?")

        for match in pattern.finditer(raw_text):
            tag_name = normalize_tag_name(match.group("name"))
            if tag_name not in state_dict:
                continue
            state_dict[tag_name]["check"] = True

            sub_text = match.group("sub") or ""
            if sub_text:
                state_dict[tag_name]["sub"] = normalize_sub_value(tag_name, sub_text[1:-1].strip())

            text_part = match.group("text") or ""
            if text_part:
                value = re.sub(r"^\s*:\s*", "", text_part).strip()
                if value.endswith("、"):
                    value = value[:-1]
                state_dict[tag_name]["text"] = value.strip()

    def _read_csv_import(self, import_path: Any) -> CsvImportResult:
        """Parse and validate an import without mutating application state."""
        require_file_size(import_path, self.config.safety.max_csv_bytes)
        with open(import_path, "r", encoding="utf-8-sig", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames or "seq" not in reader.fieldnames:
                raise ValueError("导入的 CSV 缺少 'seq' 列，无法匹配序列。")

            seq_map = {self._normalize_seq(key): key for key in self.tag_data}
            if "." in self.tag_data:
                seq_map[self._normalize_seq(self.root_folder_name)] = "."
            updates: dict[str, Any] = {}
            qc_by_found = ""
            matched_count = 0
            unmatched_count = 0

            for row_number, row in enumerate(reader, start=2):
                if row_number - 1 > self.config.safety.max_csv_rows:
                    raise ValueError(f"CSV 数据行超过上限 {self.config.safety.max_csv_rows}")
                seq_val = self._csv_text(row.get("seq"))
                if not seq_val or seq_val == "Unknown":
                    continue
                status_val = self._csv_text(
                    row.get("状态（合格/不合格/待定）") or row.get("状态（合格/不合格）")
                )
                light_str = self._csv_text(row.get("光影问题"))
                comp_str = self._csv_text(row.get("构图问题"))
                remark_str = self._csv_text(row.get("备注"))
                qc_val = self._csv_text(row.get("QC by"))
                if qc_val and not qc_by_found:
                    qc_by_found = qc_val
                if not status_val and not light_str and not comp_str and "重新渲染" not in remark_str:
                    continue
                target_rel_path = seq_map.get(self._normalize_seq(seq_val))
                if not target_rel_path:
                    unmatched_count += 1
                    continue
                state = self._create_empty_tag_state(
                    status=status_val,
                    rerender="重新渲染" in remark_str,
                )
                self._parse_and_apply_tags(light_str, state["light"], self.light_tags_def)
                self._parse_and_apply_tags(comp_str, state["comp"], self.comp_tags_def)
                state = self._normalize_tag_state(state)
                if not self._is_tag_state_empty(state):
                    updates[target_rel_path] = state
                matched_count += 1

        return CsvImportResult(updates, matched_count, unmatched_count, qc_by_found)

    def import_csv(self, import_path: Any=None, show_message: Any=True) -> Any:
        if import_path is None:
            import_path = filedialog.askopenfilename(filetypes=[('CSV files', '*.csv')], title='导入 CSV 文件')
        if not import_path:
            return None
        previous_loading_state = self.is_loading_state
        try:
            result = self._read_csv_import(import_path)
        except Exception as e:
            logger.error('导入 CSV 失败', exc_info=True)
            if show_message:
                messagebox.showerror('导入失败', f'读取文件时发生错误：\n{str(e)}')
            return None
        finally:
            self.is_loading_state = previous_loading_state

        committed = dict(self.tag_data)
        committed.update(result.updates)
        self.tag_data = committed
        if result.qc_by:
            self.qc_by_name = result.qc_by
            if hasattr(self, "lbl_qc_by"):
                self.lbl_qc_by.config(text=f"质检人：{self.qc_by_name}")
        if self.current_tree_node:
            self.load_tag_state(self.current_tree_node)
        self._mark_export_dirty()
        self._refresh_seq_stats()
        self._apply_tree_state_after_csv_import()
        if show_message:
            messagebox.showinfo(
                "导入成功",
                f"已成功读取并同步 CSV 标记数据。\n匹配：{result.matched} 条；未匹配：{result.unmatched} 条。",
            )
        return {"matched": result.matched, "unmatched": result.unmatched, "qc_by": result.qc_by}

    def format_tag_export(self, tag_name: Any, state_dict: Any) -> Any:
        parts = []
        if state_dict.get('check') or state_dict.get('text'):
            s = tag_name
            if state_dict.get('check') and state_dict.get('sub'):
                s += f"({state_dict['sub']})"
            if state_dict.get('text'):
                s += f": {state_dict['text']}"
            parts.append(s)
        return parts

    @staticmethod
    def _make_copy_csv_path(path: Any) -> Any:
        base, ext = os.path.splitext(path)
        ext = ext or '.csv'
        candidate = f'{base}_副本{ext}'
        index = 2
        while os.path.exists(candidate):
            candidate = f'{base}_副本{index}{ext}'
            index += 1
        return candidate

    def _resolve_export_path_if_exists(self, export_path: Any) -> Any:
        if not os.path.exists(export_path):
            return export_path
        dialog = CsvOverwriteDialog(self.root, export_path)
        if dialog.result == 'overwrite':
            return export_path
        if dialog.result == 'copy':
            return self._make_copy_csv_path(export_path)
        return ''

    def _write_export_csv(self, export_path: Any) -> Any:
        today_str = datetime.date.today().strftime('%Y/%m/%d')
        headers = ['关卡名称', 'seq', '状态（合格/不合格/待定）', '光影问题', '构图问题', 'QC by', '日期', '备注']
        written_count = 0
        rel_paths = self._effective_seq_rel_paths()
        def write_rows(csvfile: Any) -> int:
            nonlocal written_count
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            for rel_path in rel_paths:
                data = self._normalize_tag_state(self.tag_data.get(rel_path))
                if self._is_tag_state_empty(data):
                    continue
                seq_name = rel_path.replace('\\', '/') if rel_path != 'Unknown' else 'Unknown'
                light_issues = []
                remarks = []
                for k, v in data['light'].items():
                    parts = self.format_tag_export(k, v)
                    if parts:
                        light_issues.extend(parts)
                        if '非法物体移动' in k:
                            remarks.append('打回')
                if data.get('rerender'):
                    remarks.append('重新渲染')
                comp_issues = []
                for k, v in data['comp'].items():
                    parts = self.format_tag_export(k, v)
                    if parts:
                        comp_issues.extend(parts)
                remark = '、'.join(dict.fromkeys(remarks))
                row = [self.root_folder_name, seq_name, data['status'], '、'.join(light_issues), '、'.join(comp_issues), self.qc_by_name, today_str, remark]
                writer.writerow([self._excel_safe_cell(value) for value in row])
                written_count += 1
            return written_count

        return atomic_write_text(export_path, write_rows)

    def export_csv(self) -> Any:
        if not self.tag_data:
            messagebox.showwarning('导出提示', '暂无任何标记数据。')
            return False
        if self.current_tree_node:
            self.save_tag_state(self.current_tree_node)
        self._confirm_current_last_seq_before_export()
        default_filename = f"{self.root_folder_name}_{datetime.date.today().strftime('%Y%m%d')}_QC_Export.csv"
        if self.loaded_folder_path:
            initial_dir = os.path.dirname(os.path.normpath(self.loaded_folder_path)) or self.loaded_folder_path
        else:
            initial_dir = os.getcwd()
        save_dialog = CsvSaveDialog(self.root, initial_dir, default_filename)
        export_path = save_dialog.result
        if not export_path:
            return False
        export_path = self._resolve_export_path_if_exists(export_path)
        if not export_path:
            return False
        try:
            written_count = self._write_export_csv(export_path)
            self.csv_exported = True
            self._refresh_export_status()
            messagebox.showinfo('导出成功', f'数据已导出至：\n{export_path}\n导出记录：{written_count} 条。')
            return True
        except Exception as e:
            messagebox.showerror('导出失败', f'错误：\n{str(e)}')
            return False
