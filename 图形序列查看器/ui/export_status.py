"""Pure presentation rules for the persistent CSV export state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExportState(str, Enum):
    """User-visible relationship between QC data and the last CSV export."""

    EMPTY = "empty"
    DIRTY = "dirty"
    EXPORTED = "exported"


@dataclass(frozen=True)
class ExportPresentation:
    """Text and semantic styles needed by the export controls."""

    state: ExportState
    text: str
    label_style: str
    button_style: str
    export_enabled: bool


def get_export_presentation(
    *,
    has_exportable_data: bool,
    csv_exported: bool,
) -> ExportPresentation:
    """Return a deterministic presentation without reading Tk widget state."""
    if not has_exportable_data:
        return ExportPresentation(
            state=ExportState.EMPTY,
            text="— 暂无质检数据",
            label_style="PanelMuted.TLabel",
            button_style="TButton",
            export_enabled=False,
        )
    if csv_exported:
        return ExportPresentation(
            state=ExportState.EXPORTED,
            text="✓ 已导出",
            label_style="PanelSuccess.TLabel",
            button_style="TButton",
            export_enabled=True,
        )
    return ExportPresentation(
        state=ExportState.DIRTY,
        text="● 有未导出修改",
        label_style="PanelWarning.TLabel",
        button_style="Primary.TButton",
        export_enabled=True,
    )
