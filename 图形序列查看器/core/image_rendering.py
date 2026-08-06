"""Image resize and fit helpers used by render workers."""
from typing import Any

from PIL import Image


def render_image_to_fit(img: Any, cw: Any, ch: Any) -> Any:
    """Render a PIL image to fit a canvas while preserving aspect ratio."""
    iw, ih = img.size
    if iw <= 0 or ih <= 0:
        raise ValueError(f"Invalid image dimensions: {iw}x{ih}")
    if cw <= 0 or ch <= 0:
        raise ValueError(f"Invalid canvas dimensions: {cw}x{ch}")
    ratio = min(cw / iw, ch / ih)
    nw, nh = (max(1, int(iw * ratio)), max(1, int(ih * ratio)))
    if ratio > 1.0:
        return img.resize((nw, nh), Image.Resampling.BICUBIC)
    t = img.copy()
    t.thumbnail((nw, nh), Image.Resampling.BILINEAR)
    return t
