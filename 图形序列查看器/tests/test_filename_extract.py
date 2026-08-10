"""Filename parser tests."""
from __future__ import annotations

import unittest

from utils.filename_parser import extract_current_filename_key_info, extract_filename_key_info


class FilenameExtractTests(unittest.TestCase):
    """Validate filename-to-QC-key extraction rules."""

    def test_standard_filename(self) -> None:
        value = extract_filename_key_info("seq_01_960_CineCameraActor0_FinalImage_0010.png")
        self.assertEqual(value, "seq01_960_0")

    def test_repeated_seq_filename(self) -> None:
        value = extract_filename_key_info("seq_03_1600_seq03CineCameraActor2_FinalImage_0011.png")
        self.assertEqual(value, "seq03_1600_2")

    def test_current_filename_bounds(self) -> None:
        self.assertEqual(extract_current_filename_key_info([], 0), "")
        self.assertEqual(extract_current_filename_key_info(["a.png"], 9), "")


if __name__ == "__main__":
    unittest.main()
