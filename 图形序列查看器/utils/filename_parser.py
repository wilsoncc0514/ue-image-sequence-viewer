"""Filename parsing helpers used by QC tag auto-fill rules."""
from __future__ import annotations

import os
import re
from typing import Sequence


def extract_filename_key_info(filename: str) -> str:
    """Extract the QC key from an image filename.

    Examples:
        ``seq_01_960_CineCameraActor0_FinalImage_0010.png`` -> ``seq01_960_0``
        ``seq_03_1600_seq03CineCameraActor2_FinalImage_0011.png`` -> ``seq03_1600_2``
    """
    base_name = os.path.splitext(os.path.basename(str(filename or "")))[0]
    camera_match = re.search(r"CineCameraActor[_\-\s]*(\d+)", base_name, re.IGNORECASE)
    camera_no = camera_match.group(1) if camera_match else ""
    search_part = base_name[: camera_match.start()] if camera_match else base_name

    seq_match = re.search(
        r"(?:^|[_\-\s])seq[_\-\s]*(\d+)[_\-\s]+(\d+)",
        search_part,
        re.IGNORECASE,
    )
    if seq_match:
        seq_no, value_no = seq_match.group(1), seq_match.group(2)
        return f"seq{seq_no}_{value_no}_{camera_no}" if camera_no else f"seq{seq_no}_{value_no}"

    nums_before_camera = re.findall(r"\d+", search_part)
    if len(nums_before_camera) >= 2 and camera_no:
        return f"seq{nums_before_camera[0]}_{nums_before_camera[1]}_{camera_no}"

    nums = re.findall(r"\d+", base_name)
    if len(nums) >= 3:
        return f"seq{nums[0]}_{nums[1]}_{nums[2]}"
    if nums:
        return "seq" + "_".join(nums)
    return ""


def extract_current_filename_key_info(filepaths: Sequence[str], current_index: int) -> str:
    """Extract a QC key for ``filepaths[current_index]`` if it is valid."""
    if not filepaths or current_index < 0 or current_index >= len(filepaths):
        return ""
    return extract_filename_key_info(filepaths[current_index])
