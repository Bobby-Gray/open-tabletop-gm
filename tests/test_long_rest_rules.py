"""The D&D 5e long rest the GM is told to run must be the long rest in the rules.

WHY
===
systems/dnd5e/system.md said a long rest restores "half max Hit Dice (round
up)" and all HP, and ended with `tracker.py clear --all`. Each part was wrong
in a way that changes play:

  * 2014 restores half the character's total Hit Dice rounded DOWN, minimum
    one; 2024 restores all of them. "Round up" gave a level-5 character three
    back instead of two under 2014, and short-changed every 2024 character.
  * A character at 0 HP gains nothing from a long rest; the text healed them
    to full.
  * `clear --all` erased lasting conditions (a curse, a disease, petrification)
    and death-save tallies, which sleeping does not do.
  * It said nothing of exhaustion (one level recovers) or of concentration
    (sleep ends it).

These assertions read the rules text the GM actually loads.
"""
from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYSTEM = ROOT / "systems" / "dnd5e" / "system.md"


class LongRestTextTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        text = SYSTEM.read_text(encoding="utf-8")
        start = text.index("**Long rest")
        cls.rest = text[start:text.index("\n## ", start)]

    def test_hit_dice_by_edition(self):
        self.assertNotIn("round up", self.rest.lower())
        self.assertRegex(self.rest, r"2014\*\*[^\n]*half[^\n]*rounded down[^\n]*minimum 1")
        self.assertRegex(self.rest, r"2024\*\*[^\n]*all of them")

    def test_zero_hp_gains_nothing(self):
        self.assertRegex(self.rest, r"at least 1 HP")

    def test_exhaustion_and_concentration(self):
        self.assertRegex(self.rest, r"exhaustion by 1")
        self.assertRegex(self.rest, r"Concentration ends")

    def test_the_rest_does_not_wipe_the_tracker(self):
        for line in self.rest.splitlines():
            if re.search(r"tracker\.py clear", line):
                self.assertRegex(line, r"[Dd]o \*\*not\*\*|not run",
                                 f"the long rest still clears the tracker: {line}")


if __name__ == "__main__":
    unittest.main()
