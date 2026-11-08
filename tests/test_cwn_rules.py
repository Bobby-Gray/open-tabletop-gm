"""Cities Without Number combat and dice follow that system's own rules.

WHY
===
`combat.py` and `dice.py` refuse a system they have no row for, so a campaign
declaring `**System Module:** cwn` could not roll initiative or resolve an
attack until the rows existed. The rows have to say what the SRD says, which
differs from both d20 systems already bundled:

  * initiative is 1d8 + DEX modifier, PCs winning ties — not a d20;
  * an attack is d20 + bonus against AC and NOTHING else decides it: no
    natural 20 hits, no natural 1 misses, no critical hit;
  * the big hit is the Trauma Die, rolled on a hit against the target's Trauma
    Target, multiplying the whole damage by the weapon's Trauma Rating;
  * a melee weapon's Shock lands on a miss against a low enough AC, and is the
    floor of a hit;
  * on a SAVE a natural 20 always succeeds and a natural 1 always fails.

Dice are pinned through secrets.randbelow so every outcome is exact; the CLI is
also driven through a real campaign directory so the system is resolved the
way scripts/paths.py resolves it everywhere else.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
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


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


combat = _load("combat_cwn_under_test", SCRIPTS / "combat.py")
dice = _load("dice_cwn_under_test", SCRIPTS / "dice.py")


@contextlib.contextmanager
def faces(module, *values):
    """The next die rolls come up as `values`, whatever their size."""
    it = iter(values)
    orig = module.secrets.randbelow
    module.secrets.randbelow = lambda n: next(it) - 1
    try:
        yield
    finally:
        module.secrets.randbelow = orig


class CwnInitiativeTests(unittest.TestCase):

    def test_initiative_is_1d8_plus_dex_and_pcs_win_ties(self):
        party = [
            {"name": "Ganger", "dex_mod": 1, "hp": 7, "ac": 12, "type": "npc"},
            {"name": "Vex", "dex_mod": 0, "hp": 6, "ac": 13, "type": "pc"},
        ]
        with faces(combat, 4, 5):
            ordered = combat.initiative_order(party, "cwn")
        self.assertEqual([c["initiative"] for c in ordered], [5, 5])
        self.assertEqual(ordered[0]["name"], "Vex", "the SRD gives ties to PCs")
        self.assertEqual(combat.format_initiative_line(ordered[0], "cwn"),
                         "  Vex: d8(5) + 0 DEX = 5",
                         "the line names the die and the stat, so it cannot read as 5e")

    def test_an_npc_with_no_dex_mod_adds_nothing(self):
        with faces(combat, 6):
            ordered = combat.initiative_order(
                [{"name": "Guard", "hp": 10, "ac": 16, "type": "npc"}], "cwn")
        self.assertEqual(ordered[0]["initiative"], 6)


class CwnAttackTests(unittest.TestCase):

    def test_a_natural_20_that_misses_ac_misses(self):
        with faces(combat, 20):
            r = combat.resolve_attack_cwn(0, 22, "1d8")
        self.assertFalse(r["hit"], "no natural-20 rule on a CWN attack")
        self.assertFalse(r["crit"])

    def test_a_natural_1_that_beats_ac_hits(self):
        with faces(combat, 1, 5):
            r = combat.resolve_attack_cwn(15, 13, "1d8+1")
        self.assertTrue(r["hit"], "no natural-1 rule on a CWN attack")
        self.assertEqual(r["damage"], 6)

    def test_a_traumatic_hit_multiplies_the_whole_damage(self):
        # d20 14 hits AC 13; heavy pistol 1d8+1 rolls 5 -> 6; Trauma 1d6 rolls 6 vs TT 6.
        with faces(combat, 14, 5, 6):
            r = combat.resolve_attack_cwn(2, 13, "1d8+1", trauma="1d6/x3", tt=6)
        self.assertTrue(r["traumatic"])
        self.assertEqual(r["damage"], 18, "(5 + 1) x 3, modifier included")

    def test_a_trauma_roll_under_the_target_is_ordinary_damage(self):
        with faces(combat, 14, 5, 6):
            r = combat.resolve_attack_cwn(2, 13, "1d8+1", trauma="1d6/x3", tt=8)
        self.assertFalse(r["traumatic"], "armour raised the Trauma Target to 8")
        self.assertEqual(r["damage"], 6)

    def test_a_miss_never_rolls_the_trauma_die(self):
        with faces(combat, 2):                     # a further roll would raise
            r = combat.resolve_attack_cwn(0, 13, "1d8", trauma="1d6/x3")
        self.assertFalse(r["hit"])
        self.assertNotIn("damage", r)

    def test_shock_lands_on_a_miss_at_or_under_its_ac(self):
        with faces(combat, 3):
            r = combat.resolve_attack_cwn(0, 13, "1d8", shock="2/13")
        self.assertFalse(r["hit"])
        self.assertEqual(r["damage"], 2)

    def test_shock_does_not_land_above_its_ac(self):
        with faces(combat, 3):
            r = combat.resolve_attack_cwn(0, 14, "1d8", shock="2/13")
        self.assertNotIn("damage", r)

    def test_dash_shock_applies_at_any_ac(self):
        with faces(combat, 3):
            r = combat.resolve_attack_cwn(0, 20, "1d8", shock="5/-")
        self.assertEqual(r["damage"], 5)

    def test_a_hit_never_deals_less_than_its_shock(self):
        with faces(combat, 15, 1):
            r = combat.resolve_attack_cwn(0, 12, "1d4", shock="2/13")
        self.assertEqual(r["damage"], 2)

    def test_crit_is_an_execution_attack_and_needs_the_trauma_die(self):
        with faces(combat, 15, 4, 1):
            r = combat.resolve_attack_cwn(0, 12, "1d8", is_crit=True, trauma="1d8/x2")
        self.assertTrue(r["traumatic"], "an Execution Attack always counts as Traumatic")
        self.assertEqual(r["damage"], 8)
        with self.assertRaises(combat.CombatError):
            combat.resolve_attack_cwn(0, 12, "1d8", is_crit=True)

    def test_without_trauma_the_output_names_the_manual_step(self):
        with faces(combat, 15, 4):
            out = combat.attack("cwn", 0, 12, "1d8")
        self.assertIn("Trauma Die", out)

    def test_cwn_options_are_refused_for_other_systems(self):
        for system in ("dnd5e", "pf2e"):
            with self.subTest(system=system):
                with self.assertRaises(combat.CombatError):
                    combat.attack(system, 3, 13, "1d8", trauma="1d6/x3")


class CwnDiceTests(unittest.TestCase):

    def _roll(self, notation, natural, **kw):
        out = io.StringIO()
        with faces(dice, natural, natural, natural), contextlib.redirect_stdout(out):
            dice.run(notation, system="cwn", **kw)
        return out.getvalue()

    def test_a_natural_20_save_succeeds_under_the_target(self):
        out = self._roll("d20-5", 20, vs="save", dc=18)
        self.assertIn("SUCCESS", out)
        self.assertIn("natural 20", out)

    def test_a_natural_1_save_fails_over_the_target(self):
        out = self._roll("d20+20", 1, vs="save", dc=10)
        self.assertIn("FAILURE", out)
        self.assertIn("natural 1", out)

    def test_an_attack_has_no_natural_number_rule(self):
        """The SRD gives naturals a meaning on saves only, so an attack roll is
        left unlabelled and resolves on the total alone."""
        for natural in (1, 20):
            with self.subTest(natural=natural):
                out = self._roll("d20", natural, vs="attack")
                self.assertNotIn("natural", out)
                self.assertNotIn("CRITICAL", out)
        self.assertIn("MISS", self._roll("d20", 20, vs="attack", dc=25))
        self.assertIn("HIT", self._roll("d20+30", 1, vs="attack", dc=25))

    def test_a_2d6_skill_check_resolves_against_dc(self):
        out = io.StringIO()
        with faces(dice, 3, 4), contextlib.redirect_stdout(out):
            dice.run("2d6+1", dc=8)
        self.assertIn("= 8  vs DC 8 — SUCCESS", out.getvalue())


class CwnCampaignResolutionTests(unittest.TestCase):
    """A real `**System Module:** cwn` campaign, through the real CLIs."""

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._d.name)
        d = self.root / "campaigns" / "neon"
        d.mkdir(parents=True)
        (d / "state.md").write_text("# Campaign: neon\n**System Module:** cwn  "
                                    "**Session count:** 1\n", encoding="utf-8")

    def tearDown(self):
        self._d.cleanup()

    def _run(self, script, *args):
        env = dict(os.environ, GM_CAMPAIGN_ROOT=str(self.root))
        return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                              capture_output=True, text=True, encoding="utf-8", env=env)

    def test_init_rolls_a_d8(self):
        party = [{"name": "Vex", "dex_mod": 1, "hp": 6, "ac": 13, "type": "pc"}]
        r = self._run("combat.py", "init", json.dumps(party), "-c", "neon")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"Vex: d8\([1-8]\) \+ 1 DEX = \d")

    def test_attack_resolves_with_the_trauma_die(self):
        r = self._run("combat.py", "attack", "--atk", "40", "--ac", "13", "--dmg", "1d8+1",
                      "--trauma", "1d6/x3", "--tt", "6", "-c", "neon")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("Attack: d20("), r.stdout)
        self.assertIn("— HIT", r.stdout)
        self.assertRegex(r.stdout, r"Trauma: 1d6\([1-6]\) vs TT 6")

    def test_a_save_reads_the_campaign(self):
        # d20+40 against 15 passes on every face but a natural 1, which the
        # cwn row fails outright; a 5e campaign prints "vs DC 15 — SUCCESS"
        # for every face, natural 1 included.
        r = self._run("dice.py", "d20+40", "--vs", "save", "--dc", "15", "-c", "neon")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"vs save 15 — (SUCCESS|FAILURE \(natural 1: always fails\))")


if __name__ == "__main__":
    unittest.main()
