"""Table-discipline guidance the core skill gives every system.

WHY
===
SKILL.md said nothing about several failures that a GM model makes at the
table and that no script can catch:

  * starting combat from flirting, sparring, a joke or a figure of speech, or
    from an action aimed at a friendly target, and treating a downed creature as
    a combatant that keeps taking turns;
  * calling for checks whose failure changes nothing;
  * holding a player's mid-session style request until /gm end (the style notes
    said to update them only then), so the request was forgotten by the next
    scene;
  * answering an out-of-character question in the campaign's language rather
    than the one it was asked in;
  * answering level/XP from memory, or saying a sheet was updated when no write
    ran;
  * applying the same damage or loot twice after context compaction;
  * translating one game term several ways across a campaign.

These are prose rules, so the guard is that the text exists in the file the GM
loads, in system-agnostic wording, and that the state template carries the
glossary the last rule points to.
"""
from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TableDisciplineTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        start = text.index("**Table discipline:**")
        cls.block = text[start:text.index("\n\n**", start + 10)]

    def test_each_rule_is_present(self):
        for pattern in [
            r"Flirting, sparring",
            r"friendly or willing target",
            r"down[^\n]*no longer a combatant",
            r"only when failure would change the scene",
            r"Open each turn on what changed",
            r"GM Style Notes` immediately, replacing",
            r"language it was asked in",
            r"from the character sheet[^\n]*never say a sheet was updated",
            r"not already recorded[^\n]*compaction",
            r"One translation per game term",
        ]:
            with self.subTest(pattern=pattern):
                self.assertRegex(self.block, pattern)

    def test_the_wording_is_system_agnostic(self):
        for word in ("D&D", "5e", "PF2e", "BRP", "hit dice", "spell slot"):
            self.assertNotIn(word, self.block)

    def test_the_state_template_has_a_glossary(self):
        tpl = (ROOT / "templates" / "state.md").read_text(encoding="utf-8")
        self.assertIsNotNone(re.search(r"^## Glossary$", tpl, re.M))
        self.assertIn("written here the moment it is made", tpl)


if __name__ == "__main__":
    unittest.main()
