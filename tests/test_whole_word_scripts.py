"""Whole-word matching has to work in the languages campaigns are played in.

WHY
===
`_whole_word_pattern` in `npc_rename.py` anchored with `\\b`, which is the right
guard for a Latin name and an IMPOSSIBLE condition for a Chinese, Japanese,
Korean or Thai one: Python's `\\w` counts Han, Kana, Hangul and Thai as word
characters, and those scripts put no delimiter between a word and the text
around it, so the lookbehind can never be satisfied.

The consequence was not a visible error. `/gm npc rename` would resolve, report
success, and leave the narration log, world.md, state.md and npcs.md all
carrying the old name — a campaign inconsistent with itself rather than a clean
failure.

The same substring-versus-word question decides the display's scene background,
where it was wrong in the other direction: scoring used `window.count(kw)`, so
the arcane keyword `ward` matched inside "deputy warden".

Every assertion below was confirmed to fail with the fix reverted.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import script_ranges  # noqa: E402
import npc_rename  # noqa: E402


#: (locale, name, a line of narration containing it). The four at the bottom
#: are the ones the anchored pattern could never match.
CORPUS = [
    ("en", "Gorruk", "You see Gorruk walking toward you."),
    ("fr", "Gorruk", "Vous voyez Gorruk s'approcher."),
    ("de", "Gorruk", "Du siehst, wie Gorruk näher kommt."),
    ("ru", "Горрук", "Вы видите, как Горрук подходит."),
    ("uk", "Горрук", "Ви бачите, як Горрук підходить."),
    ("el", "Γκορούκ", "Βλέπεις τον Γκορούκ να πλησιάζει."),
    ("zh", "哥布林首領", "你看到哥布林首領走過來。"),
    ("ja", "田中", "あなたは田中さんを見る。"),
    ("ko", "문지기", "당신은 문지기를 봅니다."),
    ("th", "ผู้เฝ้าประตู", "คุณเห็นผู้เฝ้าประตูเดินมา"),
]


class CorpusFixtureTests(unittest.TestCase):
    """A corpus that quietly went empty would make every test below vacuous."""

    def test_the_corpus_covers_both_kinds_of_script(self):
        delimited = [c for c in CORPUS if script_ranges.needs_anchors(c[1])]
        undelimited = [c for c in CORPUS if not script_ranges.needs_anchors(c[1])]
        self.assertGreaterEqual(len(delimited), 5)
        self.assertGreaterEqual(len(undelimited), 4)


class RenameMatchesEveryScriptTests(unittest.TestCase):

    def test_the_name_is_found_in_every_locale(self):
        """The four no-delimiter scripts are the regression; the other six are
        the control that the anchors were not simply thrown away."""
        for loc, name, line in CORPUS:
            with self.subTest(locale=loc, name=name):
                self.assertRegex(line, npc_rename._whole_word_pattern(name),
                                 f"{loc}: the rename pattern does not match its own name")

    def test_a_rename_actually_rewrites_the_prose(self):
        for loc, name, line in CORPUS:
            with self.subTest(locale=loc):
                out = npc_rename._whole_word_pattern(name).sub("REPLACED", line)
                self.assertNotIn(name, out, f"{loc}: the old name survived the rename")
                self.assertIn("REPLACED", out)


class AnchorsStillGuardDelimitedScriptsTests(unittest.TestCase):
    """The reason the anchors were there has not gone away."""

    def test_a_short_name_does_not_match_inside_a_longer_word(self):
        for name, text in [("Sera", "The Seraphim watches."),
                           ("Ann", "She announces the terms."),
                           ("Ro", "The road bends north."),
                           ("Горрук", "Горруковский обоз стоит рядом.")]:
            with self.subTest(name=name):
                self.assertNotRegex(text, npc_rename._whole_word_pattern(name))

    def test_a_name_followed_by_punctuation_still_matches(self):
        for name, text in [("Sera", "Sera, wait."), ("Sera", "Where is Sera?"),
                           ("Aldric Voss", "Aldric  Voss nods.")]:
            with self.subTest(name=name, text=text):
                self.assertRegex(text, npc_rename._whole_word_pattern(name))

    def test_a_single_character_name_keeps_its_anchors(self):
        """A lone Han character is a morpheme, not a name: 王 occurs inside 王國
        ("kingdom"). Over-matching rewrites the player's transcript, which is
        not recoverable; under-matching leaves a stale name, which is."""
        self.assertTrue(script_ranges.needs_anchors("王"))
        self.assertNotRegex("他回到王國。", npc_rename._whole_word_pattern("王"))


class SceneKeywordTests(unittest.TestCase):
    """The display's background, which the same question decides."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        import os
        import tempfile
        os.environ.setdefault("GM_CAMPAIGN_ROOT", tempfile.mkdtemp())
        sys.path.insert(0, str(ROOT / "display"))
        spec = importlib.util.spec_from_file_location(
            "gmapp", ROOT / "display" / "gm-display-app.py")
        cls.m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(cls.m)
        except Exception as exc:                      # flask/deps absent
            raise unittest.SkipTest(f"display app not importable: {exc}")

    def _detect(self, text, current=None):
        self.m._scene_buffer = []
        self.m._current_scene_name = current
        got = self.m._detect_scene(text)
        return got and got["name"]

    # These two are written at THREE mentions on purpose. At one mention the
    # hysteresis below blocks the switch on its own, so the keyword decides
    # nothing and the test passes with `lantern` and `cleric` restored --
    # break-testing caught exactly that. Three is where the keyword is the
    # only variable: as shipped it scores 0 and nothing happens; with the word
    # restored it scores 3, clears the margin, and takes the room.

    def test_a_carried_lantern_is_not_a_temple(self):
        """`lantern` was a temple keyword, and a lantern is a thing a
        character CARRIES, so it scored wherever the party went."""
        self.assertIsNone(self._detect(
            "She lifts the lantern. The lantern gutters as she turns. "
            "Lantern light slides along the wall."))

    def test_a_cleric_is_not_a_place(self):
        """`cleric` named a thing a character IS."""
        self.assertIsNone(self._detect(
            "The cleric walks beside you. The cleric says nothing for a long "
            "while. At the ford the cleric finally stops."))

    def test_a_challenger_two_points_up_is_not_enough(self):
        """Isolates the margin and the incumbent bonus, which no other case
        here does: a two-hit challenger against an aged-out incumbent scoring
        0 is blocked by `0 + BONUS + MARGIN = 3`. Remove either constant and
        this switches."""
        self.assertIsNone(
            self._detect("A market stall stands beside the city wall.",
                         current="crypt"))

    def test_a_real_temple_still_detects(self):
        """The positive control. A guard with no case that must PASS cannot
        tell you it is reading the wrong thing."""
        self.assertEqual(
            self._detect("You step into the temple. Incense drifts past the altar, "
                         "and the pews stand empty before the shrine."),
            "temple")

    def test_a_keyword_does_not_match_inside_a_longer_word(self):
        """`ward` is an arcane keyword and was counted as a substring, so a
        prison fight against a deputy warden scored as arcane."""
        pat = self.m._cached_keyword_pattern("ward")
        for text in ["the deputy warden", "a wardrobe", "pressed forward", "the steward"]:
            with self.subTest(text=text):
                self.assertEqual(len(pat.findall(text)), 0)
        self.assertEqual(len(pat.findall("a ward of fire")), 1,
                         "the keyword must still match when it IS the word")

    def test_a_genuine_arrival_still_takes_the_room(self):
        """Hysteresis must not block a real transition. Scored against this
        repo's own keyword lists, not imported on faith: a three-chunk arrival
        at a city scores 4 against an aged-out incumbent's 0 + 1."""
        arrival = " ".join([
            "The road opens and the city gate rises ahead.",
            "Its streets are packed, market stalls everywhere.",
            "A city watch patrol shoulders past you toward the square.",
        ])
        self.assertEqual(self._detect(arrival, current="crypt"), "city")

    def test_incidental_noise_does_not_take_the_room(self):
        """Two night words while at sea. The incumbent keeps the background."""
        noise = ("Night has fallen. The dark water slaps the hull. "
                 "You keep the lantern low and watch the swell.")
        self.assertIsNone(self._detect(noise, current="ocean"))

    def test_a_lone_keyword_cannot_switch_anything(self):
        """Held by the margin, not by a separate floor — see the note on the
        constants in gm-display-app.py for why there is no floor."""
        self.assertIsNone(self._detect("A single tavern sign creaks.", current="forest"))


if __name__ == "__main__":
    unittest.main()
