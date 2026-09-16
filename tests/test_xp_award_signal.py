"""An XP award must tell the truth about whether it landed.

WHY
===
`_write_xp` used `re.sub` and never checked whether the pattern matched. Two
consequences, and the second is the expensive one:

1. A sheet whose XP field is missing or malformed got its award silently
   discarded — re.sub returned the text unchanged, that was written straight
   back, and nothing said so.
2. A FRESH sheet holds "**XP:** / 2700" with nothing before the slash. The
   pattern required digits there, so the very first award against a new
   character was exactly case 1.

The fix is `re.subn`, because the substitution count is the only value that
distinguishes "the field was not there" from "the field was there and the
rendered value did not change" — and the second is every award that leaves the
total where it was.
"""
from __future__ import annotations

import importlib.util
import io
import pathlib
import unittest
from contextlib import redirect_stderr

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("xp", ROOT / "systems" / "dnd5e" / "xp.py")
xp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xp)


def _sheet(tmp: pathlib.Path, body: str) -> pathlib.Path:
    p = tmp / "char.md"
    p.write_text(body, encoding="utf-8")
    return p


class XpWriteSignalTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._d = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._d.name)

    def tearDown(self):
        self._d.cleanup()

    def test_a_populated_field_is_written_without_warning(self):
        p = _sheet(self.tmp, "# Hero\n\n**XP:** 300 / 900\n")
        err = io.StringIO()
        with redirect_stderr(err):
            xp._write_xp(p, 500, 2)
        self.assertIn("500", p.read_text(encoding="utf-8"))
        self.assertNotIn("warning", err.getvalue())

    def test_an_award_that_changes_nothing_does_not_warn(self):
        """The bug this guard exists for: same value, field present."""
        p = _sheet(self.tmp, "# Hero\n\n**XP:** 300 / 900\n")
        err = io.StringIO()
        with redirect_stderr(err):
            xp._write_xp(p, 300, 2)
        self.assertNotIn(
            "warning", err.getvalue(),
            "an award that leaves the total unchanged is not a missing field",
        )

    def test_a_fresh_template_sheet_is_written_not_silently_skipped(self):
        """"**XP:** / 2700" — nothing before the slash. First award ever."""
        p = _sheet(self.tmp, "# Hero\n\n**XP:** / 2700\n")
        err = io.StringIO()
        with redirect_stderr(err):
            xp._write_xp(p, 450, 3)
        self.assertIn("450", p.read_text(encoding="utf-8"))
        self.assertNotIn("warning", err.getvalue())

    def test_a_genuinely_missing_field_warns_loudly(self):
        p = _sheet(self.tmp, "# Hero\n\nNo experience line here at all.\n")
        err = io.StringIO()
        with redirect_stderr(err):
            xp._write_xp(p, 450, 3)
        out = err.getvalue()
        self.assertIn("warning", out)
        self.assertIn("NOT written", out)
        self.assertIn("450", out)


if __name__ == "__main__":
    unittest.main()
