"""Tests for the persistent CSV export-status presentation."""

from __future__ import annotations

import unittest

from ui.app import FrameScrubber
from ui.export_status import ExportState, get_export_presentation


class ExportStatusTests(unittest.TestCase):
    def test_empty_state_disables_export(self) -> None:
        presentation = get_export_presentation(
            has_exportable_data=False,
            csv_exported=False,
        )

        self.assertEqual(presentation.state, ExportState.EMPTY)
        self.assertEqual(presentation.text, "— 暂无质检数据")
        self.assertFalse(presentation.export_enabled)
        self.assertEqual(presentation.button_style, "TButton")

    def test_dirty_state_emphasizes_export(self) -> None:
        presentation = get_export_presentation(
            has_exportable_data=True,
            csv_exported=False,
        )

        self.assertEqual(presentation.state, ExportState.DIRTY)
        self.assertEqual(presentation.text, "● 有未导出修改")
        self.assertTrue(presentation.export_enabled)
        self.assertEqual(presentation.button_style, "Primary.TButton")

    def test_exported_state_keeps_export_available_without_emphasis(self) -> None:
        presentation = get_export_presentation(
            has_exportable_data=True,
            csv_exported=True,
        )

        self.assertEqual(presentation.state, ExportState.EXPORTED)
        self.assertEqual(presentation.text, "✓ 已导出")
        self.assertTrue(presentation.export_enabled)
        self.assertEqual(presentation.button_style, "TButton")

    def test_exported_flag_does_not_override_empty_state(self) -> None:
        presentation = get_export_presentation(
            has_exportable_data=False,
            csv_exported=True,
        )

        self.assertEqual(presentation.state, ExportState.EMPTY)
        self.assertFalse(presentation.export_enabled)


class _FakeWidget:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}
        self.states: list[str] = []

    def configure(self, **options: object) -> None:
        self.options.update(options)

    def state(self, states: list[str]) -> None:
        self.states = states


class ExportStatusUiBridgeTests(unittest.TestCase):
    def test_dirty_marker_updates_label_and_export_button(self) -> None:
        app = FrameScrubber.__new__(FrameScrubber)
        app.csv_exported = True
        app.lbl_export_status = _FakeWidget()
        app.btn_export_csv = _FakeWidget()
        app._has_exportable_tag_data = lambda: True

        app._mark_export_dirty()

        self.assertFalse(app.csv_exported)
        self.assertEqual(app.lbl_export_status.options["text"], "● 有未导出修改")
        self.assertEqual(app.lbl_export_status.options["style"], "PanelWarning.TLabel")
        self.assertEqual(app.btn_export_csv.options["style"], "Primary.TButton")
        self.assertEqual(app.btn_export_csv.states, ["!disabled"])


if __name__ == "__main__":
    unittest.main()
