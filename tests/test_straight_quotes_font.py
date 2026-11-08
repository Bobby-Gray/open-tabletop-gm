"""Straight quotes must not render as closing curly quotes.

WHY
===
IM Fell English draws the ASCII double quote (U+0022) and apostrophe (U+0027)
with curly CLOSING-quote glyphs. Narration written with straight quotes — which
is most text a model produces — rendered "Stay back," she said as
”Stay back,” she said, and 'tis as ’tis. The quotation opened the wrong way on
every line of dialogue.

The fix is a font face that covers only those two code points with a neutral
serif already on the device, listed ahead of IM Fell wherever IM Fell is used.
The test reads the template rather than trusting that it was edited
everywhere, so a new rule that names IM Fell without the face fails here.
"""
from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "display" / "templates" / "index.html"


class StraightQuoteFaceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = HTML.read_text(encoding="utf-8")
        cls.faces = re.findall(r"@font-face\s*\{(.*?)\}", cls.src, re.S)

    def _quote_faces(self):
        out = []
        for body in self.faces:
            fam = re.search(r"font-family:\s*'([^']+)'", body)
            rng = re.search(r"unicode-range:\s*([^;]+);", body)
            if fam and rng:
                out.append((fam.group(1), rng.group(1), body))
        return out

    def test_a_face_maps_exactly_the_two_straight_quotes(self):
        faces = self._quote_faces()
        self.assertTrue(faces, "no @font-face with a unicode-range")
        for fam, rng, body in faces:
            points = {p.strip().upper() for p in rng.split(",")}
            self.assertEqual(points, {"U+0022", "U+0027"},
                             "the face must cover only the straight quotes; anything "
                             "wider replaces IM Fell's own letters")
            self.assertIn("local(", body, "the substitute must be a local font, no download")
            self.assertNotIn("Fell", body)

    def test_every_im_fell_stack_lists_the_quote_face_first(self):
        families = {fam for fam, _, _ in self._quote_faces()}
        stacks = re.findall(r"font-family:\s*([^;]*IM Fell English[^;]*);", self.src)
        self.assertTrue(stacks)
        for stack in stacks:
            with self.subTest(stack=stack):
                first = stack.split(",")[0].strip().strip("'\"")
                self.assertIn(first, families,
                              f"IM Fell is used without the quote face ahead of it: {stack}")


if __name__ == "__main__":
    unittest.main()
