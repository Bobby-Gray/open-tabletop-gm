"""Racial ability bonuses are applied by the script, not remembered by the DM.

WHY
===
The character-creation flow said "Apply racial bonuses" and then "run
`character.py calc` to derive all secondary stats". `calc` had **no `--race`
parameter at all**, so it never saw the race, could not apply the bonus, and
could not check that the step had happened. The bonus was a request to the
model, and the model is the one thing in the toolchain with no way to be
verified.

This is the failure mode an instruction cannot protect against. A step that
only exists as prose is followed most of the time and silently skipped the
rest, and a skipped ability bonus produces a sheet that is internally
consistent, passes every other check, and is simply wrong — so it survives
until a player works out why their Dwarf is no tougher than the party wizard.

`calc --race` now applies them and prints base / race / final, and an unknown
race exits non-zero instead of applying nothing — a typo that silently applies
no bonus is the exact failure being closed.

TWO SOURCES
===========
The bonus table lives in `character.py` so the calculator works whether or not
the SRD dataset has been built. That is a second copy of upstream data, which
is a drift risk, so `ReconciliationTests` compares it against the built dataset
record by record. Where the dataset is absent the reconciliation SKIPS and says
so — a skip is not a pass, and `DatasetFixtureTests` separately fails a dataset
that exists but predates races, so the reconciliation cannot be quietly
no-oped by a stale build.
"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "systems/dnd5e"))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "character_mod", ROOT / "systems/dnd5e" / "character.py")
character = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(character)

DATASET = ROOT / "systems/dnd5e/data" / "dnd5e_srd.json"

#: A level-1 array with no racial bonus in it, used everywhere below so the
#: only variable is the race.
BASE = {"STR": 15, "DEX": 10, "CON": 14, "INT": 9, "WIS": 13, "CHA": 11}


def _dataset() -> dict | None:
    if not DATASET.is_file():
        return None
    return json.loads(DATASET.read_text(encoding="utf-8"))


class TableShapeTests(unittest.TestCase):
    """Offline assertions — these run with or without a built dataset."""

    def test_the_table_is_not_empty(self):
        """A table that quietly went empty would make every behavioural test
        below pass by applying nothing, which is the original bug."""
        self.assertGreaterEqual(len(character.RACE_BONUSES), 9)
        self.assertGreaterEqual(len(character.SUBRACE_BONUSES), 4)

    def test_every_bonus_targets_a_real_stat(self):
        for race, bonuses in {**character.RACE_BONUSES,
                              **character.SUBRACE_BONUSES}.items():
            for stat, amount in bonuses.items():
                with self.subTest(race=race, stat=stat):
                    self.assertIn(stat, character.STATS)
                    self.assertIsInstance(amount, int)
                    self.assertGreater(amount, 0)

    def test_every_subrace_names_a_race_that_exists(self):
        for sub in character.SUBRACE_BONUSES:
            with self.subTest(subrace=sub):
                self.assertIn(sub, character.SUBRACE_PARENT)
                self.assertIn(character.SUBRACE_PARENT[sub], character.RACE_BONUSES)

    def test_the_keys_are_srd_indexes(self):
        """`lookup.py race <index>` and this table have to agree, so the keys
        are the dataset's own index form: lower-case and hyphenated."""
        for key in {**character.RACE_BONUSES, **character.SUBRACE_BONUSES}:
            with self.subTest(key=key):
                self.assertEqual(key, character._race_key(key))


class DatasetFixtureTests(unittest.TestCase):
    """A dataset that exists must be one that carries races.

    Without this, a checkout holding a dataset built before races existed
    would skip the reconciliation below and report a clean run.
    """

    def test_a_present_dataset_has_races(self):
        data = _dataset()
        if data is None:
            self.skipTest(f"no dataset at {DATASET} — run build_srd.py "
                          f"(it is gitignored in some checkouts)")
        self.assertIn("races", data,
                      "the dataset predates races; rebuild with build_srd.py")
        self.assertIn("subraces", data)
        self.assertGreaterEqual(len(data["races"]), 9)


class ReconciliationTests(unittest.TestCase):
    """The hardcoded table against the built dataset, record by record."""

    @classmethod
    def setUpClass(cls):
        cls.data = _dataset()
        if cls.data is None or "races" not in cls.data:
            raise unittest.SkipTest(
                f"RECONCILIATION SKIPPED: no races in {DATASET}. The table in "
                f"character.py is UNVERIFIED in this run — build the dataset "
                f"to check it for drift.")

    def test_every_race_in_the_dataset_is_in_the_table(self):
        for rec in self.data["races"]:
            with self.subTest(race=rec["index"]):
                self.assertIn(rec["index"], character.RACE_BONUSES)

    def test_every_race_in_the_table_is_in_the_dataset(self):
        indexes = {r["index"] for r in self.data["races"]}
        for key in character.RACE_BONUSES:
            with self.subTest(race=key):
                self.assertIn(key, indexes)

    def test_the_bonuses_match_the_dataset(self):
        """The drift check. A wrong number here produces a sheet that looks
        right and is not."""
        for rec in self.data["races"]:
            with self.subTest(race=rec["index"]):
                self.assertEqual(character.RACE_BONUSES[rec["index"]],
                                 rec["ability_bonuses"])

    def test_the_subrace_bonuses_match_the_dataset(self):
        for rec in self.data["subraces"]:
            with self.subTest(subrace=rec["index"]):
                self.assertIn(rec["index"], character.SUBRACE_BONUSES)
                self.assertEqual(character.SUBRACE_BONUSES[rec["index"]],
                                 rec["ability_bonuses"])

    def test_the_subrace_parents_match_the_dataset(self):
        for rec in self.data["subraces"]:
            with self.subTest(subrace=rec["index"]):
                self.assertEqual(character.SUBRACE_PARENT[rec["index"]],
                                 character._race_key(rec["race"]))


class ApplicationTests(unittest.TestCase):

    def test_a_dwarf_and_an_elf_differ(self):
        """The symptom, stated as a test: same base array, different sheets."""
        dwarf, _, _ = character.apply_racial_bonuses(BASE, "dwarf")
        elf, _, _ = character.apply_racial_bonuses(BASE, "elf")
        self.assertEqual(dwarf["CON"], 16)
        self.assertEqual(elf["CON"], 14)
        self.assertEqual(elf["DEX"], 12)
        self.assertEqual(dwarf["DEX"], 10)
        self.assertNotEqual(dwarf, elf)

    def test_a_subrace_stacks_on_its_race(self):
        scores, applied, _ = character.apply_racial_bonuses(BASE, "dwarf", "hill-dwarf")
        self.assertEqual(applied, {"CON": 2, "WIS": 1})
        self.assertEqual(scores["CON"], 16)
        self.assertEqual(scores["WIS"], 14)

    def test_a_subrace_alone_implies_its_race(self):
        """A caller who passes only `--subrace` still gets both bonuses."""
        scores, applied, _ = character.apply_racial_bonuses(BASE, "", "high-elf")
        self.assertEqual(applied, {"DEX": 2, "INT": 1})

    def test_names_are_accepted_in_the_form_a_player_types_them(self):
        for spelling in ["Hill Dwarf", "hill dwarf", "HILL-DWARF", " hill_dwarf "]:
            with self.subTest(spelling=spelling):
                _, applied, _ = character.apply_racial_bonuses(BASE, "", spelling)
                self.assertEqual(applied, {"CON": 2, "WIS": 1})

    def test_the_human_spread_is_all_six(self):
        _, applied, _ = character.apply_racial_bonuses(BASE, "human")
        self.assertEqual(applied, {s: 1 for s in character.STATS})

    def test_a_choice_the_table_cannot_hold_is_reported(self):
        """Half-Elf grants +1 to two abilities of the player's choice. A table
        cannot express that, so it must be surfaced rather than dropped."""
        _, applied, notes = character.apply_racial_bonuses(BASE, "half-elf")
        self.assertEqual(applied, {"CHA": 2})
        self.assertTrue(notes, "the Half-Elf free choice was silently dropped")
        self.assertIn("choice", notes[0].lower())

    def test_no_race_changes_nothing(self):
        """Back-compat: the existing call with no --race must behave as before."""
        scores, applied, notes = character.apply_racial_bonuses(BASE)
        self.assertEqual(scores, BASE)
        self.assertEqual(applied, {})
        self.assertEqual(notes, [])

    def test_the_input_is_not_mutated(self):
        before = dict(BASE)
        character.apply_racial_bonuses(BASE, "dwarf")
        self.assertEqual(BASE, before)


class RefusalTests(unittest.TestCase):
    """Fail closed. A typo must not produce a sheet that is quietly wrong."""

    def test_an_unknown_race_raises(self):
        with self.assertRaises(ValueError):
            character.apply_racial_bonuses(BASE, "dwarfe")

    def test_an_unknown_subrace_raises(self):
        with self.assertRaises(ValueError):
            character.apply_racial_bonuses(BASE, "dwarf", "mountain-dwarf")

    def test_a_subrace_from_the_wrong_race_raises(self):
        with self.assertRaises(ValueError):
            character.apply_racial_bonuses(BASE, "elf", "hill-dwarf")

    def test_the_error_names_what_is_accepted(self):
        with self.assertRaises(ValueError) as ctx:
            character.apply_racial_bonuses(BASE, "dwarfe")
        self.assertIn("dwarf", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
