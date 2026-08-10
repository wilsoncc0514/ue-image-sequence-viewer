"""Bounded folder scanner tests."""
from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from core.folder_scanner import ScanCancelled, ScanLimitExceeded, scan_image_folder


class FolderScannerTests(unittest.TestCase):
    def test_groups_images_and_ignores_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="中文 路径 ") as tmp:
            root = Path(tmp)
            (root / "seq 01").mkdir()
            for name in ("shot_0002.png", "shot_0001.png", "other_1.jpg", ".DS_Store", "notes.txt"):
                (root / "seq 01" / name).touch()
            result = scan_image_folder(
                tmp,
                image_extensions=(".png", ".jpg"),
                max_entries=20,
                max_depth=4,
            )
            scanned = next(item for item in result.directories if item.rel_path == "seq 01")
            self.assertEqual([name for name, _ in scanned.groups], ["other", "shot"])
            self.assertEqual([Path(path).name for path in scanned.groups[1][1]], ["shot_0001.png", "shot_0002.png"])
            self.assertEqual(result.image_count, 3)

    def test_rejects_entry_count_over_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for index in range(3):
                (Path(tmp) / f"frame_{index}.png").touch()
            with self.assertRaisesRegex(ScanLimitExceeded, "超过上限"):
                scan_image_folder(tmp, image_extensions=(".png",), max_entries=2, max_depth=2)

    def test_honors_cancellation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cancel = threading.Event()
            cancel.set()
            with self.assertRaises(ScanCancelled):
                scan_image_folder(
                    tmp,
                    image_extensions=(".png",),
                    max_entries=10,
                    max_depth=2,
                    cancel_event=cancel,
                )

    def test_stops_below_depth_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            deep = Path(tmp) / "one" / "two"
            deep.mkdir(parents=True)
            (deep / "frame_1.png").touch()
            result = scan_image_folder(tmp, image_extensions=(".png",), max_entries=10, max_depth=1)
            self.assertEqual(result.image_count, 0)


if __name__ == "__main__":
    unittest.main()
