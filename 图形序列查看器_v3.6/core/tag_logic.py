"""Tkinter bridge for QC tag-state behavior.

Pure filename parsing lives in :mod:`utils.filename_parser`; pure status and
rerender rules live in :mod:`core.tag_engine`. This mixin only connects Tk
variables, UI widgets and application state.
"""
from __future__ import annotations

from typing import Any, Iterator
import tkinter as tk

from core.tag_engine import (
    ActiveTagItem,
    infer_status_from_tags,
    normalize_sub_value,
    normalize_tag_name,
    status_pending_sub_values,
    status_rerender_triggers,
    tags_require_rerender,
)
from utils.filename_parser import extract_current_filename_key_info, extract_filename_key_info


class TagLogicMixin:
    """Mixin implementing tag and status behavior for ``FrameScrubber``."""

    def _init_tag_vars(self, defs: Any, target_dict: dict[str, Any]) -> None:
        """Create Tk variables for tag definitions and attach trace callbacks."""
        for tag_def in defs:
            tag_name = tag_def["name"]
            target_dict[tag_name] = {
                "check": tk.BooleanVar(value=False),
                "text": tk.StringVar(value=""),
                "sub": tk.StringVar(value="") if tag_def.get("has_sub") else None,
            }
            target_dict[tag_name]["check"].trace_add(
                "write",
                lambda *args, tag_name=tag_name, vars_dict=target_dict: self.on_tag_changed(
                    tag_name=tag_name, vars_dict=vars_dict, changed_field="check"
                ),
            )
            target_dict[tag_name]["text"].trace_add(
                "write",
                lambda *args, tag_name=tag_name, vars_dict=target_dict: self.on_tag_changed(
                    tag_name=tag_name, vars_dict=vars_dict, changed_field="text"
                ),
            )
            if target_dict[tag_name]["sub"] is not None:
                target_dict[tag_name]["sub"].trace_add(
                    "write",
                    lambda *args, tag_name=tag_name, vars_dict=target_dict: self.on_tag_changed(
                        tag_name=tag_name, vars_dict=vars_dict, changed_field="sub"
                    ),
                )

    def _any_tag_marked(self) -> bool:
        """Return whether the current UI contains any effective tag content."""
        return any(v["check"].get() or bool(v["text"].get().strip()) for v in self.tag_vars_light.values()) or any(
            v["check"].get() or bool(v["text"].get().strip()) for v in self.tag_vars_comp.values()
        )

    def _reset_tag_vars(self) -> None:
        """Reset all tag controls to an empty state."""
        for vars_obj in self.tag_vars_light.values():
            vars_obj["check"].set(False)
            vars_obj["text"].set("")
            if vars_obj["sub"]:
                vars_obj["sub"].set("")
        for vars_obj in self.tag_vars_comp.values():
            vars_obj["check"].set(False)
            vars_obj["text"].set("")
            if vars_obj["sub"]:
                vars_obj["sub"].set("")

    def _tag_def_by_name(self, tag_name: str) -> Any | None:
        """Return a tag definition by display name."""
        for tag_def in self.light_tags_def + self.comp_tags_def:
            if tag_def["name"] == tag_name:
                return tag_def
        return None

    def _iter_tag_var_items(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield all tag-name / Tk-variable mappings from both tag sections."""
        yield from self.tag_vars_light.items()
        yield from self.tag_vars_comp.items()

    # Backwards-compatible wrappers used by older tests and mixins.
    @staticmethod
    def _normalize_sub_value(tag_name: Any, sub_value: Any) -> str:
        """Normalize legacy sub-option names."""
        return normalize_sub_value(tag_name, sub_value)

    @staticmethod
    def _normalize_tag_name(tag_name: Any) -> str:
        """Normalize legacy tag names."""
        return normalize_tag_name(tag_name)

    @staticmethod
    def _status_pending_sub_values() -> set[tuple[str, str]]:
        """Return pending-only tag/sub pairs."""
        return status_pending_sub_values()

    @staticmethod
    def _status_rerender_triggers() -> set[tuple[str, str | None]]:
        """Return rerender trigger tag/sub pairs."""
        return status_rerender_triggers()

    @staticmethod
    def _extract_filename_key_info(filename: Any) -> str:
        """Extract the QC key from a filename."""
        return extract_filename_key_info(str(filename or ""))

    def _active_tag_items_from_ui(self) -> list[ActiveTagItem]:
        """Return active tag items from current Tk variable values."""
        items: list[ActiveTagItem] = []
        for tag_name, vars_obj in self._iter_tag_var_items():
            checked = bool(vars_obj["check"].get())
            text_value = vars_obj["text"].get().strip()
            sub_var = vars_obj.get("sub")
            sub_value = normalize_sub_value(tag_name, sub_var.get().strip()) if sub_var and checked else ""
            if not checked and not text_value:
                continue
            items.append(ActiveTagItem(tag_name, checked, text_value, sub_value))
        return items

    def _current_tags_require_rerender(self) -> bool:
        """Return whether the current UI state requires rerender."""
        return tags_require_rerender(self._active_tag_items_from_ui())

    def _auto_status_from_current_tags(self) -> str | None:
        """Infer status from the current UI tag state."""
        return infer_status_from_tags(self._active_tag_items_from_ui())

    def on_tag_changed(self, *args: Any, tag_name: Any = None, vars_dict: Any = None, changed_field: Any = None) -> None:
        """Trace callback for tag checkboxes, sub-options and text fields."""
        if self.is_loading_state:
            return

        tag_vars = vars_dict.get(tag_name) if tag_name and vars_dict else None
        if changed_field == "sub" and tag_vars and tag_vars["sub"] is not None:
            normalized_sub = normalize_sub_value(tag_name, tag_vars["sub"].get())
            if normalized_sub != tag_vars["sub"].get():
                old_state = self.is_loading_state
                self.is_loading_state = True
                tag_vars["sub"].set(normalized_sub)
                self.is_loading_state = old_state
            if tag_vars["sub"].get() and not tag_vars["check"].get():
                tag_vars["check"].set(True)

        if changed_field == "check" and tag_vars:
            if tag_vars["check"].get():
                self._auto_fill_tag_text_when_checked(tag_name, vars_dict)
            elif tag_vars.get("sub") is not None and tag_vars["sub"].get():
                old_state = self.is_loading_state
                self.is_loading_state = True
                tag_vars["sub"].set("")
                self.is_loading_state = old_state

        
        # custom rules
        if vars_dict is self.tag_vars_comp and tag_vars and tag_vars["check"].get():
            self.var_status.set("不合格")
            self.var_rerender.set(True)
        if tag_name in ("拖影","光变问题") and tag_vars and tag_vars.get("sub") is not None:
            sv=tag_vars["sub"].get()
            if self.var_status.get() not in ("不合格",) and not self.var_rerender.get():
                if (tag_name=="拖影" and sv=="小范围") or (tag_name=="光变问题" and sv=="＜30%"):
                    self.var_status.set("待定")

        rerender_required = self._current_tags_require_rerender()
        auto_status = self._auto_status_from_current_tags()
        if auto_status and self.var_status.get() != auto_status:
            self.var_status.set(auto_status)
        if rerender_required and not self.var_rerender.get():
            self.var_rerender.set(True)
        self._sync_rerender_widget_state()
        self._mark_export_dirty()
        self._persist_current_tag_state_and_refresh_stats()

    def on_rerender_change(self, *args: Any) -> None:
        """Trace callback for the rerender checkbox."""
        if self.is_loading_state:
            return
        self._mark_export_dirty()
        self._persist_current_tag_state_and_refresh_stats()

    def _sync_rerender_widget_state(self) -> None:
        """Enable rerender only for pending/failed states; otherwise clear it."""
        status = self.var_status.get()
        allowed = status in {"待定", "不合格"}
        if not allowed and self.var_rerender.get():
            old_state = self.is_loading_state
            self.is_loading_state = True
            self.var_rerender.set(False)
            self.is_loading_state = old_state
        if hasattr(self, "chk_rerender"):
            try:
                self.chk_rerender.configure(state="normal" if allowed else "disabled")
            except tk.TclError:
                pass

    def _auto_fill_tag_text_when_checked(self, tag_name: Any, vars_dict: Any) -> None:
        """Fill the tag text box with the current frame's filename key."""
        if not tag_name or not vars_dict:
            return
        tag_vars = vars_dict.get(tag_name)
        if not tag_vars or not tag_vars["check"].get() or tag_vars["text"].get().strip():
            return
        key_info = self._extract_current_filename_key_info()
        if key_info:
            tag_vars["text"].set(key_info)

    def _extract_current_filename_key_info(self) -> str:
        """Extract the filename key for the current frame."""
        return extract_current_filename_key_info(self.current_filepaths, self.current_idx)

    def on_status_change(self, *args: Any, mark_dirty: Any = True) -> None:
        """Trace callback for the top-level QC status radio buttons."""
        if self.is_loading_state:
            return
        if self.var_status.get() == "合格" and self._any_tag_marked():
            old_state = self.is_loading_state
            self.is_loading_state = True
            self._reset_tag_vars()
            self.var_rerender.set(False)
            self.is_loading_state = old_state
        self._sync_rerender_widget_state()
        state = "disabled" if self.var_status.get() == "合格" else "normal"
        self.set_children_state(self.lf_light, state)
        self.set_children_state(self.lf_comp, state)
        if mark_dirty:
            self._mark_export_dirty()
        self._persist_current_tag_state_and_refresh_stats()

    def set_children_state(self, container: Any, state: str) -> None:
        """Recursively set state for a widget subtree when supported."""
        for child in container.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass
            if child.winfo_children():
                self.set_children_state(child, state)
