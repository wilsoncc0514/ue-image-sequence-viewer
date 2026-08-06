"""Seq-level state, statistics and navigation behavior."""
from __future__ import annotations

import tkinter as tk
from typing import Any

from ui.dialogs import SeqQualifiedDialog

from core.tag_engine import normalize_sub_value, normalize_tag_name


class SeqStateMixin:
    """Mixin implementing seq-level QC state management."""

    def _create_empty_tag_state(self, status: Any='', rerender: Any=False) -> Any:
        return {'status': status, 'rerender': bool(rerender), 'light': {t['name']: {'check': False, 'text': '', 'sub': '' if t.get('has_sub') else None} for t in self.light_tags_def}, 'comp': {t['name']: {'check': False, 'text': '', 'sub': None} for t in self.comp_tags_def}}

    @staticmethod
    def _tag_item_has_effective_value(value: Any) -> Any:
        """判断单个 Tag 是否有有效内容。

        只将父级勾选或备注文本视为有效。sub 程度本身不单独计入，
        用于兼容旧版本遗留的“未勾父级但 sub 默认为轻微”的脏数据。
        """
        if not isinstance(value, dict):
            return False
        return bool(value.get('check')) or bool(str(value.get('text', '')).strip())

    @staticmethod
    def _is_tag_state_empty(data: Any) -> Any:
        if not data:
            return True
        if str(data.get('status', '')).strip():
            return False
        if bool(data.get('rerender', False)):
            return False
        for section in ('light', 'comp'):
            for v in data.get(section, {}).values():
                if SeqStateMixin._tag_item_has_effective_value(v):
                    return False
        return True

    def _normalize_tag_state(self, data: Any) -> Any:
        """规范化 tag_data，清理旧版本遗留的无效 sub 值。

        旧版本曾把未勾选父级的 sub 默认值也保存下来，造成：
        - 未标记 seq 被统计为已标记；
        - 导出 CSV 时出现空数据行；
        - 跳转其他 seq 时不弹“是否合格”确认。
        本函数将 sub 限定为“父级已勾选”时才保留。
        """
        src = data if isinstance(data, dict) else {}
        status = str(src.get('status', '')).strip()
        if status not in {'', '合格', '待定', '不合格'}:
            status = ''
        rerender = bool(src.get('rerender', False))
        normalized = self._create_empty_tag_state(status=status, rerender=rerender)
        for section_name, defs in (('light', self.light_tags_def), ('comp', self.comp_tags_def)):
            src_section = src.get(section_name, {}) if isinstance(src.get(section_name, {}), dict) else {}
            normalized_src_section = {}
            for raw_name, raw_value in src_section.items():
                normalized_src_section[normalize_tag_name(raw_name)] = raw_value
            for t in defs:
                name = t['name']
                raw = normalized_src_section.get(name, {}) if isinstance(normalized_src_section.get(name, {}), dict) else {}
                check = bool(raw.get('check', False))
                text = str(raw.get('text', '')).strip()
                if t.get('has_sub'):
                    sub = normalize_sub_value(name, raw.get('sub', '')) if check else ''
                    if sub not in t.get('subs', []):
                        sub = ''
                else:
                    sub = None
                normalized[section_name][name] = {'check': check, 'text': text, 'sub': sub}
        if normalized.get('status') not in {'待定', '不合格'} and (not any((self._tag_item_has_effective_value(v) for section in ('light', 'comp') for v in normalized.get(section, {}).values()))):
            normalized['rerender'] = False
        return normalized

    def _effective_seq_rel_paths(self) -> Any:
        rels = list(getattr(self, 'seq_rel_paths', []) or [])
        if not rels:
            rels = list(self.tag_data.keys())
        return rels

    def _is_seq_unmarked(self, rel_path: Any) -> Any:
        return self._is_tag_state_empty(self._normalize_tag_state(self.tag_data.get(rel_path)))

    def _refresh_seq_stats(self) -> Any:
        """刷新画布右上角 seq 统计。

        v2.33：统计前先规范化每个 seq 的状态，避免旧版本遗留 sub 默认值
        将未标记 seq 误判为已标记。
        """
        if not hasattr(self, 'txt_seq_stats'):
            return
        rel_paths = self._effective_seq_rel_paths()
        total = len(rel_paths)
        if total <= 0:
            self.canvas.itemconfig(self.txt_seq_stats, text='')
            return
        unmarked = sum((1 for rel in rel_paths if self._is_seq_unmarked(rel)))
        self.canvas.itemconfig(self.txt_seq_stats, text=f'本组场景 {total} 个 seq\n未标记 {unmarked} 个')
        try:
            cw = self.canvas.winfo_width()
            if cw > 1:
                self.canvas.coords(self.txt_seq_stats, cw - 18, 18)
        except tk.TclError:
            pass

    def _persist_current_tag_state_and_refresh_stats(self) -> Any:
        if self.current_tree_node:
            self.save_tag_state(self.current_tree_node)
        self._refresh_seq_stats()

    def _mark_seq_as_qualified(self, rel_path: Any) -> Any:
        self.tag_data[rel_path] = self._create_empty_tag_state(status='合格')
        if self.current_tree_node and self.node_metadata.get(self.current_tree_node) == rel_path:
            old_state = self.is_loading_state
            self.is_loading_state = True
            self._reset_tag_vars()
            self.var_status.set('合格')
            self.var_rerender.set(False)
            self.is_loading_state = old_state
            self.on_status_change(mark_dirty=False)
        self._mark_export_dirty()
        self._refresh_seq_stats()

    def _confirm_unmarked_seq_if_needed(self, old_node_id: Any, new_node_id: Any) -> Any:
        """离开未标记 seq 前询问是否判定为合格。

        v2.31 修复点：
        旧逻辑要求 new_node_id 也必须存在 node_metadata。用户点击根目录、
        普通目录或某些 Treeview 区域时 new_rel 为空，会直接跳过确认。
        现在只要 old_node_id 属于某个 seq，且目标不是同一个 seq，就会触发确认。
        """
        if self._suppress_unmarked_prompt and self._suppress_unmarked_prompt_target == new_node_id:
            return
        if not old_node_id or old_node_id == new_node_id:
            return
        old_rel = self.node_metadata.get(old_node_id)
        if not old_rel:
            return
        new_rel = self.node_metadata.get(new_node_id) if new_node_id else None
        if new_rel == old_rel:
            return
        if not self._is_seq_unmarked(old_rel):
            return
        display_name = old_rel.replace('\\', '/')
        dialog = SeqQualifiedDialog(self.root, display_name)
        if dialog.result == 'yes':
            self._mark_seq_as_qualified(old_rel)
            if self.current_tree_node and self.node_metadata.get(self.current_tree_node) == old_rel:
                self.load_tag_state(self.current_tree_node)

    def _iter_tree_nodes(self, parent: Any='') -> Any:
        for node in self.tree.get_children(parent):
            yield node
            yield from self._iter_tree_nodes(node)

    def _iter_seq_nodes_in_tree_order(self) -> Any:
        for node in self._iter_tree_nodes(''):
            if node in self.seq_folder_nodes:
                yield node

    def _first_child_sequence_node(self, seq_node: Any) -> Any:
        children = self.tree.get_children(seq_node)
        return children[0] if children else None

    def _select_tree_node_without_unmarked_prompt(self, node_id: Any) -> Any:
        """选中并激活树节点，但不触发离开未标记 seq 的二次询问。"""
        if not node_id:
            return
        self._suppress_unmarked_prompt = True
        self._suppress_unmarked_prompt_target = node_id
        same_selection = node_id in self.tree.selection()
        self.tree.selection_set(node_id)
        self.tree.focus(node_id)
        self.tree.see(node_id)
        if same_selection:
            self.on_tree_select(None)

        def _clear_suppress(expected: Any=node_id) -> Any:
            if self._suppress_unmarked_prompt_target == expected:
                self._suppress_unmarked_prompt = False
                self._suppress_unmarked_prompt_target = None
        self.root.after(120, _clear_suppress)

    def _prepare_tree_navigation_from_current_to(self, target_node_id: Any) -> Any:
        """从当前节点切换到目标节点前，保存旧状态并处理未标记 seq 询问。"""
        old_node_id = self.current_tree_node
        if old_node_id:
            self.save_tag_state(old_node_id)
            self._confirm_unmarked_seq_if_needed(old_node_id, target_node_id)

    def _toggle_seq_node_from_click(self, seq_node: Any) -> Any:
        """点击 seq 层时展开/收起；展开后自动跳到第一组子序列。"""
        if not seq_node or seq_node not in self.seq_folder_nodes:
            return
        self._prepare_tree_navigation_from_current_to(seq_node)
        is_open = bool(self.tree.item(seq_node, 'open'))
        if is_open:
            self.tree.item(seq_node, open=False)
            self._select_tree_node_without_unmarked_prompt(seq_node)
            return
        self.tree.item(seq_node, open=True)
        first_child = self._first_child_sequence_node(seq_node)
        if first_child:
            self._select_tree_node_without_unmarked_prompt(first_child)
        else:
            self._select_tree_node_without_unmarked_prompt(seq_node)

    def _apply_tree_state_after_csv_import(self) -> Any:
        """CSV 导入后：展开已打标 seq，并跳转到首个未打标 seq 的第一组子序列。"""
        first_unmarked_child = None
        for seq_node in self._iter_seq_nodes_in_tree_order():
            rel_path = self.node_metadata.get(seq_node)
            if not rel_path:
                continue
            is_marked = not self._is_seq_unmarked(rel_path)
            if is_marked:
                self.tree.item(seq_node, open=True)
            else:
                self.tree.item(seq_node, open=False)
                if first_unmarked_child is None:
                    child = self._first_child_sequence_node(seq_node)
                    if child:
                        first_unmarked_child = child
        if first_unmarked_child:
            parent = self.tree.parent(first_unmarked_child)
            if parent:
                self.tree.item(parent, open=True)
            self._select_tree_node_without_unmarked_prompt(first_unmarked_child)

    def _is_current_seq_last_in_tree_order(self) -> Any:
        if not self.current_tree_node:
            return False
        current_rel = self.node_metadata.get(self.current_tree_node)
        if not current_rel:
            return False
        seq_rels = [self.node_metadata.get(node) for node in self._iter_seq_nodes_in_tree_order()]
        seq_rels = [rel for rel in seq_rels if rel]
        return bool(seq_rels) and current_rel == seq_rels[-1]

    def _confirm_current_last_seq_before_export(self) -> Any:
        """导出 CSV 前，如果光标停在最后一组且该 seq 未标记，则询问是否合格。"""
        if not self._is_current_seq_last_in_tree_order():
            return
        current_rel = self.node_metadata.get(self.current_tree_node)
        if not current_rel or not self._is_seq_unmarked(current_rel):
            return
        display_name = current_rel.replace('\\', '/')
        dialog = SeqQualifiedDialog(self.root, display_name)
        if dialog.result == 'yes':
            self._mark_seq_as_qualified(current_rel)
            self.load_tag_state(self.current_tree_node)

    def save_tag_state(self, node_id: Any) -> Any:
        if not node_id:
            return
        rel_path = self.node_metadata.get(node_id)
        if not rel_path:
            return

        def collect(vars_dict: Any) -> Any:
            result = {}
            for k, v in vars_dict.items():
                checked = bool(v['check'].get())
                result[k] = {'check': checked, 'text': v['text'].get().strip(), 'sub': v['sub'].get().strip() if v['sub'] and checked else '' if v['sub'] else None}
            return result
        self.tag_data[rel_path] = self._normalize_tag_state({'status': self.var_status.get().strip(), 'rerender': bool(self.var_rerender.get()), 'light': collect(self.tag_vars_light), 'comp': collect(self.tag_vars_comp)})

    def load_tag_state(self, node_id: Any) -> Any:
        self.is_loading_state = True
        rel_path = self.node_metadata.get(node_id)
        if not rel_path or rel_path not in self.tag_data:
            self._reset_tag_vars()
            self.var_status.set('')
            self.var_rerender.set(False)
        else:
            state = self._normalize_tag_state(self.tag_data.get(rel_path))
            self.tag_data[rel_path] = state
            for k, v in self.tag_vars_light.items():
                s = state.get('light', {}).get(k, {})
                v['check'].set(bool(s.get('check', False)))
                v['text'].set(s.get('text', ''))
                if v['sub']:
                    v['sub'].set(s.get('sub', ''))
            for k, v in self.tag_vars_comp.items():
                s = state.get('comp', {}).get(k, {})
                v['check'].set(bool(s.get('check', False)))
                v['text'].set(s.get('text', ''))
                if v['sub']:
                    v['sub'].set(s.get('sub', ''))
            self.var_status.set(state.get('status', ''))
            self.var_rerender.set(bool(state.get('rerender', False)))
        self.is_loading_state = False
        self.on_status_change(mark_dirty=False)
