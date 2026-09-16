"""Block badges must actually run, and must not be English-only by construction.

WHY
===
The badge feature existed as three disconnected pieces: a keyword table, a
function that built an <img>, and a CSS class. `_addBlockBadge` was never
called from anywhere, and `.block-badge` had no style rule at all. So no player
in any language had ever seen one — the "English-only keyword list" was a
symptom of code that never ran.

Wiring it as-written would have shipped a feature that works only for English
narration. Two things prevent that:

  * block KIND (npc / dice / tutor) is badged with no word list at all, so that
    path works in every language;
  * the semantic word table lives in the system's ui.json, so a system or
    campaign in another language overrides it instead of editing the display.
"""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "display" / "templates" / "index.html"
UI = ROOT / "systems" / "dnd5e" / "ui.json"


class BadgeWiringTests(unittest.TestCase):
    """The failure that hid for as long as this feature has existed."""

    @classmethod
    def setUpClass(cls):
        cls.src = HTML.read_text(encoding="utf-8")

    def test_the_badge_function_is_actually_called(self):
        """Defined-but-never-called is how this shipped dead.

        Counting mentions, not asserting presence: a definition alone is
        exactly the state that looked fine in review.
        """
        mentions = len(re.findall(r"_addBlockBadge", self.src))
        self.assertGreaterEqual(
            mentions, 2,
            "_addBlockBadge appears once — it is defined and never invoked, "
            "which is how the feature was dead in the first place",
        )

    def test_the_badge_class_has_a_style_rule(self):
        """An <img> with no rule renders as an unsized, unplaced image."""
        self.assertRegex(
            self.src, r"\.block-badge\s*\{",
            ".block-badge has no CSS rule, so a created badge would render raw",
        )

    def test_the_manifest_global_matches_the_one_the_server_injects(self):
        """A typo here is a silently unwired override — the same bug again."""
        injected = re.search(r"window\.(\w*UI_MANIFEST)\s*=", self.src)
        self.assertIsNotNone(injected, "no UI manifest is injected at all")
        read_back = re.findall(r"window\.(\w*UI_MANIFEST)\s*\|\|", self.src)
        self.assertIn(
            injected.group(1), read_back,
            f"badges read a different global than the server injects "
            f"({injected.group(1)} vs {set(read_back)})",
        )


class BadgeLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = HTML.read_text(encoding="utf-8")
        cls.ui = json.loads(UI.read_text(encoding="utf-8"))

    def test_kind_badges_use_no_word_list(self):
        """The language-agnostic path. It must not consult prose at all."""
        block = re.search(r"const _KIND_BADGES = \{(.*?)\};", self.src, re.S)
        self.assertIsNotNone(block, "_KIND_BADGES missing")
        body = block.group(1)
        self.assertIn("npc-block", body)
        self.assertNotIn("includes(", body)

    def test_the_word_table_is_overridable_from_the_manifest(self):
        self.assertIn("block_badges", self.ui)
        self.assertTrue(self.ui["block_badges"])
        for entry in self.ui["block_badges"]:
            self.assertIn("icon", entry)
            self.assertIn("words", entry)
            self.assertTrue(entry["words"], entry["icon"])

    def test_every_badge_icon_exists_on_disk(self):
        """A badge naming a missing icon renders as a broken image, silently."""
        icons = ROOT / "display" / "icons"
        for entry in self.ui["block_badges"]:
            self.assertTrue(
                (icons / f"{entry['icon']}.png").exists(),
                f"icons/{entry['icon']}.png missing",
            )

    def test_an_unmatched_block_gets_no_badge(self):
        """Silence, not a wrong guess — and the state every non-English
        narration block lands in until its language has a table."""
        fn = re.search(r"function _addBlockBadge\(el\) \{(.*?)\n\}", self.src, re.S)
        self.assertIsNotNone(fn)
        self.assertIn("if (!icon) return;", fn.group(1))


if __name__ == "__main__":
    unittest.main()
