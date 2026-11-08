"""Two characters answering to the same first name, and names outside ASCII.

WHY
===
`name_registry.py check` compared whole names only. An NPC called "Captain Mira
Thorne" passed as unique at a table whose PC is "Mira Voss" — and from then on
every "Mira said" in the narration was ambiguous, which is worse at the table
than a reused full name from some other campaign. The check now also flags a
proposal whose first name, honorifics stripped, is already a PC's.

The prose scan's name pattern was `[A-Z][a-z]+`, so it could not see
"Élodie Marchand", "Ярослав Мудрый" or "Νίκος Παππάς", and cut "Ana Núñez" to
nothing because "Núñez" fails `[a-z]+`. It now uses the Unicode case classes.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("name_registry_under_test",
                                               SCRIPTS / "name_registry.py")
reg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reg)


class FirstNameTests(unittest.TestCase):

    def test_honorifics_are_stripped(self):
        self.assertEqual(reg.first_name("Captain Mira Thorne"), "mira")
        self.assertEqual(reg.first_name("Sir Aldric"), "aldric")
        self.assertEqual(reg.first_name("Dr. Ада Лис"), "ада")
        self.assertEqual(reg.first_name("Mira"), "mira")
        self.assertEqual(reg.first_name("Lady"), "")


class ClashTests(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self._env = os.environ.get("GM_CAMPAIGN_ROOT")
        os.environ["GM_CAMPAIGN_ROOT"] = self._d.name
        reg.add("Mira Voss", "pc", "tide", 1)
        reg.add("Ярослав Мудрый", "pc", "steppe", 1)
        reg.add("Bram Hollow", "npc", "tide", 1)

    def tearDown(self):
        if self._env is None:
            os.environ.pop("GM_CAMPAIGN_ROOT", None)
        else:
            os.environ["GM_CAMPAIGN_ROOT"] = self._env
        self._d.cleanup()

    def test_an_npc_sharing_a_pcs_first_name_is_flagged(self):
        r = reg.check("Captain Mira Thorne")
        self.assertFalse(r["is_duplicate"])
        self.assertEqual([e["name"] for e in r["first_name_clash"]], ["Mira Voss"])
        self.assertIn("Mira Voss", r["message"])

    def test_the_check_works_outside_latin_script(self):
        r = reg.check("Ярослав Кузнецов")
        self.assertEqual([e["name"] for e in r["first_name_clash"]], ["Ярослав Мудрый"])

    def test_an_npcs_first_name_is_not_a_clash(self):
        self.assertEqual(reg.check("Bram Ashdown")["first_name_clash"], [])

    def test_campaign_limits_the_check(self):
        self.assertEqual(reg.check("Mira Thorne", campaign="steppe")["first_name_clash"], [])
        self.assertTrue(reg.check("Mira Thorne", campaign="tide")["first_name_clash"])

    def test_an_exact_duplicate_is_reported_once_as_a_duplicate(self):
        r = reg.check("Mira Voss")
        self.assertTrue(r["is_duplicate"])
        self.assertEqual(r["first_name_clash"], [])

    def test_cli_exits_nonzero_on_a_first_name_clash(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "name_registry.py"),
                            "check", "Sister Mira Ashe"],
                           capture_output=True, text=True, encoding="utf-8",
                           env=dict(os.environ))
        self.assertEqual(r.returncode, 1)
        self.assertIn("FIRST NAME", r.stdout)


class ProsePatternTests(unittest.TestCase):

    def _names(self, text):
        return [m.group(1) for m in reg._PROSE_NAME_PAT.finditer(text)]

    def test_names_outside_ascii_are_found(self):
        text = ("Élodie Marchand met Ярослав Мудрый and Νίκος Παππάς "
                "at the inn kept by Ana Núñez.")
        self.assertEqual(self._names(text),
                         ["Élodie Marchand", "Ярослав Мудрый", "Νίκος Παππάς", "Ana Núñez"])

    def test_ascii_behaviour_is_unchanged(self):
        self.assertEqual(self._names("Then Aldric Voss spoke to the Pale Court."),
                         ["Then Aldric Voss", "Pale Court"])
        self.assertEqual(self._names("ALL CAPS HEADER and lowercase words"), [])


if __name__ == "__main__":
    unittest.main()
