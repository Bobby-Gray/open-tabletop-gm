"""PF2e advancement and level-1 numbers the GM applies at the table.

WHY
===
systems/pf2e/system.md gave the advancement schedule as "skill increases at
even levels; ancestry feats at odd levels". In the rules skill increases come
at 3, 5, 7 ... 19 and ancestry feats at 1, 5, 9, 13, 17; skill feats are the
even-level stream (every level for a rogue), class feats come at every even
level (and at 1 for some classes), general feats at 3, 7, 11, 15, 19 and
attribute boosts at 5, 10, 15, 20. A GM following the old line awarded ten
ancestry feats instead of five and moved skill ranks on the wrong levels.

It also gave no guidance on the knock-on effects of a level-up — a CON boost
raises max HP by the character's level, not by one; a DEX boost raises AC only
within the armour's cap — or on level-1 starting points: a Focus Point pool of
1 only for a class that starts with a focus spell, and class-specific
proficiency ranks.
"""
from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYSTEM = ROOT / "systems" / "pf2e" / "system.md"


def _row(table: str, label: str) -> str:
    m = re.search(rf"^\|\s*{re.escape(label)}\s*\|([^\n]*)\|\s*$", table, re.M)
    return m.group(1).strip() if m else ""


class AdvancementTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        text = SYSTEM.read_text(encoding="utf-8")
        cls.full = text
        start = text.index("## Advancement")
        cls.adv = text[start:text.index("\n## ", start + 5)]

    def test_the_old_schedule_is_gone(self):
        self.assertNotIn("skill increases at even levels", self.full)
        self.assertNotIn("ancestry feats at odd levels", self.full)

    def test_schedule(self):
        self.assertEqual(_row(self.adv, "Ancestry feat"), "1, 5, 9, 13, 17")
        self.assertEqual(_row(self.adv, "General feat"), "3, 7, 11, 15, 19")
        self.assertEqual(_row(self.adv, "Attribute boosts (four)"), "5, 10, 15, 20")
        self.assertTrue(_row(self.adv, "Skill increase").startswith("3, 5, 7"))
        self.assertIn("every even level", _row(self.adv, "Skill feat"))
        self.assertIn("every even level", _row(self.adv, "Class feat"))
        self.assertIn("level 1", _row(self.adv, "Class feat"))

    def test_rogue_and_investigator_exceptions(self):
        self.assertRegex(self.adv, r"rogue\*\*[^\n]*skill feat at every level")
        self.assertIn("investigator", self.adv)

    def test_level_up_knock_on_effects(self):
        self.assertRegex(self.adv, r"CON boost[^\n]*retroactively[^\n]*level")
        self.assertRegex(self.adv, r"DEX boost[^\n]*Dex cap")
        self.assertRegex(self.adv, r"Key attribute boost[^\n]*class DC")

    def test_level_one_focus_pool_and_ranks(self):
        self.assertRegex(self.adv, r"Focus Points:\*\*[^\n]*pool of \*\*1\*\*")
        self.assertRegex(self.adv, r"starts at \*\*0\*\*")
        self.assertRegex(self.adv, r"fighter starts \*\*expert\*\* in Perception")

    def test_the_module_keeps_its_licensed_label(self):
        self.assertIn("PF2e-compatible (ORC)", self.full)


if __name__ == "__main__":
    unittest.main()
