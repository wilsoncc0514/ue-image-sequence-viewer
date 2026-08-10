"""Application configuration and runtime tuning dataclasses.

The UI, render controller and packaging code receive a single ``AppConfig``
instance. This keeps performance values, window metadata and layout constants
out of the controller implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PerformanceConfig:
    """Runtime-tunable rendering, preloading and debug-overlay settings."""

    preload_worker_min: int = 4
    preload_worker_max: int = 32
    max_render_cache_size: int = 640
    max_original_cache_size: int = 192
    preload_radius: int = 112
    drag_preload_radius: int = 48
    keyboard_preload_radius: int = 128
    keyboard_reverse_radius: int = 16
    keyboard_preview_settle_ms: int = 180
    resize_debounce_ms: int = 120
    slider_debounce_ms: int = 10
    preload_delay_drag_ms: int = 0
    preload_delay_idle_ms: int = 0
    debug_cache_stats: bool = False
    render_result_poll_ms: int = 8
    render_result_poll_idle_ms: int = 32
    render_result_poll_max_idle_ms: int = 96
    render_result_empty_slowdown_after: int = 3
    render_result_poll_batch_size: int = 12
    max_preload_pending_tasks: int = 512
    max_render_result_queue_size: int = 32
    folder_scan_poll_ms: int = 50
    tree_build_batch_size: int = 200
    file_reveal_poll_ms: int = 100
    file_reveal_handoff_ms: int = 2_000

    def __post_init__(self) -> None:
        positive_values = (
            self.preload_worker_min,
            self.preload_worker_max,
            self.max_render_cache_size,
            self.max_original_cache_size,
            self.render_result_poll_batch_size,
            self.max_preload_pending_tasks,
            self.max_render_result_queue_size,
            self.folder_scan_poll_ms,
            self.tree_build_batch_size,
            self.file_reveal_poll_ms,
            self.file_reveal_handoff_ms,
        )
        if any(value <= 0 for value in positive_values):
            raise ValueError("性能配置中的容量、批量和延迟必须为正数")
        if self.preload_worker_min > self.preload_worker_max:
            raise ValueError("preload_worker_min 不能大于 preload_worker_max")

    def preload_worker_count(self, cpu_count: int | None) -> int:
        """Return a bounded worker count for the current host CPU count."""
        cores = cpu_count or self.preload_worker_min
        return max(self.preload_worker_min, min(self.preload_worker_max, cores))


@dataclass(frozen=True)
class WindowConfig:
    """Main window metadata and geometry."""

    title: str = "图形序列查看器"
    version: str = "v3.7.0"
    default_geometry: str = "1450x900"
    min_width: int = 1180
    min_height: int = 760


@dataclass(frozen=True)
class SidebarConfig:
    """Left file-tree sizing policy."""

    initial_width: int = 380
    min_width: int = 300
    max_width: int = 540
    tree_min_width: int = 240


@dataclass(frozen=True)
class TagPanelConfig:
    """Right-side tag panel layout policy."""

    canvas_window_min_width: int = 250


@dataclass(frozen=True)
class UIConfig:
    """Shared UI spacing and visual behavior settings."""

    corner_radius_hint: int = 12
    card_padding_x: int = 10
    card_padding_y: int = 8
    status_columns: int = 2
    motion_fast_ms: int = 120
    motion_standard_ms: int = 180
    motion_emphasis_ms: int = 240
    motion_frame_interval_ms: int = 16
    feedback_hold_ms: int = 1200
    main_view_min_width: int = 420
    reduce_motion: bool = False

    def __post_init__(self) -> None:
        if min(self.motion_fast_ms, self.motion_standard_ms, self.motion_emphasis_ms, self.feedback_hold_ms) < 0:
            raise ValueError("动效和反馈时长不能为负数")
        if self.motion_frame_interval_ms <= 0:
            raise ValueError("动效帧间隔必须为正数")
        if self.main_view_min_width <= 0:
            raise ValueError("主画布最小宽度必须为正数")


@dataclass(frozen=True)
class SafetyConfig:
    """Bound untrusted files and directory scans before allocating resources."""

    max_csv_bytes: int = 16 * 1024 * 1024
    max_csv_rows: int = 200_000
    max_scan_entries: int = 200_000
    max_scan_depth: int = 32
    max_image_pixels: int = 200_000_000
    image_extensions: tuple[str, ...] = (
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".bmp",
        ".webp",
    )

    def __post_init__(self) -> None:
        if any(
            value <= 0
            for value in (
                self.max_csv_bytes,
                self.max_csv_rows,
                self.max_scan_entries,
                self.max_image_pixels,
            )
        ):
            raise ValueError("安全资源上限必须为正数")
        if self.max_scan_depth < 0:
            raise ValueError("max_scan_depth 不能为负数")
        if not self.image_extensions or any(not item.startswith(".") for item in self.image_extensions):
            raise ValueError("图片扩展名必须是以点开头的非空集合")


@dataclass(frozen=True)
class AppConfig:
    """Dependency-injected configuration object used across modules."""

    window: WindowConfig = field(default_factory=WindowConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    sidebar: SidebarConfig = field(default_factory=SidebarConfig)
    tag_panel: TagPanelConfig = field(default_factory=TagPanelConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)

    @property
    def version(self) -> str:
        """Return the public application version."""
        return self.window.version
