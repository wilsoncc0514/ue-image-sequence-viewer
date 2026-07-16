"""tests/test_tag_definitions.py module."""
from __future__ import annotations
from typing import Any
import unittest
from models.tag_definitions import get_default_comp_tags, get_default_light_tags

class TagDefinitionTests(unittest.TestCase):
    """Validate current QC tag vocabulary."""

    def test_light_tags_include_new_rules(self) -> None:
        names = [item['name'] for item in get_default_light_tags()]
        self.assertIn('漏光', names)
        self.assertIn('反光白噪点', names)

    def test_comp_tags_include_composition_avoidance(self) -> None:
        names = [item['name'] for item in get_default_comp_tags()]
        self.assertIn('构图规避光变', names)
        self.assertNotIn('漏光', names)
if __name__ == '__main__':
    unittest.main()
