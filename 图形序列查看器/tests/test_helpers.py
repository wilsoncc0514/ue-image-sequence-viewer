"""tests/test_helpers.py module."""
from __future__ import annotations

import unittest

from utils.helpers import natural_key


class NaturalKeyTests(unittest.TestCase):
    """Validate natural sorting behavior."""

    def test_natural_numeric_order(self) -> None:
        values = ['frame_10', 'frame_2', 'frame_1']
        self.assertEqual(sorted(values, key=natural_key), ['frame_1', 'frame_2', 'frame_10'])
if __name__ == '__main__':
    unittest.main()
