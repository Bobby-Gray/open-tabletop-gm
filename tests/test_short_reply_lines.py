"""A one-word reply in any script is narration, not terminal chrome.

WHY
===
`_is_chrome` drops lines that look like terminal furniture before they reach
the display. Its last rule threw away any line of three characters or fewer
that lacked two consecutive ASCII letters — meant for box-drawing debris and
stray digits, it also matched every short reply outside Latin script. 「好的」,
「はい。」 and 「Да.」 are complete answers from an NPC, and all three vanished
from the screen while "Ok." survived.

A word is now two letters in any script, or one letter in a script written
without word delimiters, where a single character can be a word.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class ShortReplyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "gmapp_chrome", ROOT / "display" / "gm-display-app.py")
        cls.m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(cls.m)
        except Exception as exc:                      # flask/deps absent
            raise unittest.SkipTest(f"display app not importable: {exc}")

    def test_short_replies_in_every_script_survive(self):
        for line in ["好的", "是", "はい。", "네", "Да.", "Да", "Ναι", "Oui", "Ok.", "ok",
                     "نعم", "כן", "ใช่"]:
            with self.subTest(line=line):
                self.assertFalse(self.m._is_chrome(line), f"{line!r} was dropped as chrome")

    def test_debris_is_still_dropped(self):
        for line in ["—", "42", "a.", "::", "─┼─", "│", "é!", "»"]:
            with self.subTest(line=line):
                self.assertTrue(self.m._is_chrome(line), f"{line!r} reached the display")

    def test_clean_keeps_a_short_reply_between_lines(self):
        out = self.m._clean("The innkeeper nods.\nはい。\n42\n")
        self.assertIn("はい。", out)
        self.assertNotIn("42", out)


if __name__ == "__main__":
    unittest.main()
