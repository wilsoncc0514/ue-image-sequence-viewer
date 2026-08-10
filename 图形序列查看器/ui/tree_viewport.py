"""Pure viewport calculations for comfortable Treeview navigation."""

from __future__ import annotations


def centered_yview_fraction(
    *,
    first: float,
    last: float,
    item_y: int,
    item_height: int,
    viewport_height: int,
    target_ratio: float = 0.5,
) -> float:
    """Return a bounded yview start that places an item near the viewport center."""
    if viewport_height <= 0 or last <= first:
        return max(0.0, min(first, 1.0))
    visible_fraction = last - first
    item_center = item_y + item_height / 2
    target_y = viewport_height * min(max(target_ratio, 0.0), 1.0)
    target = first + ((item_center - target_y) / viewport_height) * visible_fraction
    return max(0.0, min(target, max(0.0, 1.0 - visible_fraction)))
