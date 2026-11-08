"""Combat follows the campaign's system, and `--crit` does what it says.

WHY
===
combat.py ran D&D 5e arithmetic for every campaign. `init` rolled d20 + DEX for
a PF2e party (whose initiative is a Perception check) and for a BRP party (which
rolls nothing at all and acts in DEX order), and `attack` crit only on a
natural 20 for a system where a critical hit is beating AC by 10. Nothing said
so: the output looked authoritative in all three.

`attack --crit` was parsed and passed to resolve_attack(), which never read it,
so the flag the docs offer for an attack on a paralysed target changed nothing.

These tests pin the dice (secrets.randbelow) so every outcome is exact, and
drive the CLI through a real campaign directory so the system is resolved the
way scripts/paths.py resolves it for everything else.
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

_spec = importlib.util.spec_from_file_location("combat_under_test", SCRIPTS / "combat.py")
combat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(combat)


@contextlib.contextmanager
def dice(*faces):
    """Make the next die rolls come up as `faces`, whatever their size."""
    it = iter(faces)
    orig = combat.secrets.randbelow
    combat.secrets.randbelow = lambda n: next(it) - 1
    try:
        yield
    finally:
        combat.secrets.randbelow = orig


def run_main(*argv) -> tuple:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = combat.main(list(argv))
    return code, out.getvalue(), err.getvalue()


PARTY_5E = [
    {"name": "Flerb", "dex_mod": 0, "hp": 12, "ac": 16, "type": "pc"},
    {"name": "Goblin", "dex_mod": 2, "hp": 7, "ac": 15, "type": "npc"},
]


class Dnd5eUnchangedTests(unittest.TestCase):
    """D&D 5e output is pinned byte for byte: the table must not move it."""

    def test_init_output_is_the_pre_table_output(self):
        with dice(11, 9):
            code, out, _ = run_main("init", json.dumps(PARTY_5E))
        self.assertEqual(code, 0)
        self.assertIn("Initiative rolls:\n"
                      "  Goblin: d20(9) + 2 = 11\n"
                      "  Flerb: d20(11) + 0 = 11\n", out)
        state = json.loads(out.split("STATE_JSON: ", 1)[1])
        self.assertEqual([c["name"] for c in state], ["Goblin", "Flerb"],
                         "5e ties go to the higher DEX modifier")
        self.assertNotIn("initiative_label", state[0])

    def test_attack_output_is_the_pre_table_output(self):
        with dice(14, 5):
            code, out, _ = run_main("attack", "--atk", "5", "--ac", "15", "--dmg", "1d8+3")
        self.assertEqual(out, "Attack: d20(14) + 5 = 19 vs AC 15 — HIT\n"
                              "Damage: [5] + mod = 8 d8dmg\n")

    def test_natural_20_still_crits_and_natural_1_still_misses(self):
        with dice(20, 3, 4):
            r = combat.resolve_attack(0, 30, "1d8+1")
        self.assertTrue(r["hit"] and r["crit"])
        self.assertEqual(r["damage"], 3 + 1 + 4)
        with dice(1):
            r = combat.resolve_attack(50, 2, "1d8")
        self.assertFalse(r["hit"])


class CritFlagTests(unittest.TestCase):

    def test_crit_flag_makes_a_hit_a_critical_hit(self):
        with dice(12, 6, 2):
            r = combat.resolve_attack(4, 15, "1d8+3", is_crit=True)
        self.assertTrue(r["hit"])
        self.assertTrue(r["crit"], "--crit was ignored on a hit")
        self.assertEqual(r["damage"], 6 + 3 + 2, "crit damage doubles the dice, not the modifier")

    def test_crit_flag_cannot_turn_a_miss_into_a_hit(self):
        with dice(3):
            r = combat.resolve_attack(4, 15, "1d8+3", is_crit=True)
        self.assertFalse(r["hit"])
        self.assertFalse(r["crit"])

    def test_crit_flag_reaches_the_resolver_from_the_cli(self):
        with dice(12, 6, 2):
            _, out, _ = run_main("attack", "--atk", "4", "--ac", "15", "--dmg", "1d8+3", "--crit")
        self.assertIn("CRITICAL HIT", out)


class Pf2eTests(unittest.TestCase):

    def test_initiative_is_perception_and_foes_win_ties(self):
        party = [
            {"name": "Val", "perception": 7, "hp": 20, "ac": 18, "type": "pc"},
            {"name": "Goblin", "perception": 5, "hp": 7, "ac": 15, "type": "npc"},
        ]
        with dice(10, 12):
            ordered = combat.initiative_order(party, "pf2e")
        self.assertEqual([c["initiative"] for c in ordered], [17, 17])
        self.assertEqual(ordered[0]["name"], "Goblin", "on a tie, foes act before PCs")
        self.assertEqual(ordered[0]["initiative_label"], "Perception")

    def test_dex_mod_is_not_used_for_pf2e_initiative(self):
        """The 5e key must not be silently read as the PF2e stat."""
        with self.assertRaises(combat.CombatError):
            combat.initiative_order([{"name": "G", "dex_mod": 3, "hp": 1, "ac": 10}], "pf2e")

    def test_a_scene_can_roll_another_skill(self):
        with dice(5):
            ordered = combat.initiative_order(
                [{"name": "Sneak", "perception": 2, "init_mod": 9, "init_label": "Stealth",
                  "hp": 5, "ac": 14, "type": "npc"}], "pf2e")
        self.assertEqual(ordered[0]["initiative"], 14)
        self.assertEqual(combat.format_initiative_line(ordered[0], "pf2e"),
                         "  Sneak: d20(5) + 9 Stealth = 14")

    def test_beating_ac_by_10_is_a_critical_hit_without_a_natural_20(self):
        with dice(15, 4):
            r = combat.resolve_attack_pf2e(10, 15, "1d8+4")
        self.assertEqual(r["total"], 25)
        self.assertEqual(r["degree"], 3)
        self.assertEqual(r["damage"], (4 + 4) * 2, "a PF2e critical doubles all damage")

    def test_natural_20_is_one_step_better_not_an_automatic_crit(self):
        with dice(20, 4):
            r = combat.resolve_attack_pf2e(0, 25, "1d8")
        self.assertEqual(r["degree"], 2, "20 vs AC 25 is a failure, shifted up to a success")

    def test_natural_1_is_one_step_worse(self):
        with dice(1):
            r = combat.resolve_attack_pf2e(20, 15, "1d8")
        self.assertEqual(r["total"], 21)
        self.assertEqual(r["degree"], 1, "21 vs AC 15 is a success, shifted down to a failure")
        self.assertFalse(r["hit"])


class BrpTests(unittest.TestCase):

    def test_initiative_is_dex_rank_with_no_roll(self):
        party = [
            {"name": "Ada", "dex": 14, "hp": 12, "type": "pc"},
            {"name": "Thug", "dex": 16, "hp": 12, "type": "npc"},
            {"name": "Bo", "dex": 14, "hp": 11, "type": "pc"},
        ]
        with dice():                       # any roll would raise StopIteration
            ordered = combat.initiative_order(party, "brp")
        self.assertEqual([c["name"] for c in ordered], ["Thug", "Ada", "Bo"])
        self.assertIsNone(ordered[0]["initiative_roll"])
        self.assertEqual(combat.format_initiative_line(ordered[0], "brp"), "  Thug: DEX 16")

    def test_attack_refuses_rather_than_running_d20_math(self):
        code, out, err = run_main("attack", "--atk", "5", "--ac", "15", "--dmg", "1d8",
                                  "--system", "brp")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("brp", err)


class UnknownSystemTests(unittest.TestCase):

    def test_an_unknown_system_is_refused_not_given_5e_rules(self):
        code, out, err = run_main("init", json.dumps(PARTY_5E), "--system", "homebrew")
        self.assertEqual(code, 2)
        self.assertNotIn("STATE_JSON", out)
        self.assertIn("homebrew", err)


class SeamTests(unittest.TestCase):
    """The table is the extension point: a new row must be enough."""

    def test_a_new_row_is_honoured_without_other_changes(self):
        combat.INITIATIVE["d8test"] = {"die": 8, "stat": "dex_mod", "label": "",
                                       "ties": "pcs_first", "choose": False,
                                       "required": False}
        try:
            party = [{"name": "Foe", "dex_mod": 1, "hp": 5, "ac": 12, "type": "npc"},
                     {"name": "Hero", "dex_mod": 0, "hp": 9, "ac": 13, "type": "pc"}]
            with dice(3, 4):
                ordered = combat.initiative_order(party, "d8test")
            self.assertEqual([c["initiative"] for c in ordered], [4, 4])
            self.assertEqual(ordered[0]["name"], "Hero", "pcs_first tie order")
            self.assertEqual(combat.format_initiative_line(ordered[0], "d8test"),
                             "  Hero: d8(4) + 0 = 4")
        finally:
            del combat.INITIATIVE["d8test"]

    def test_every_attack_resolver_has_an_initiative_row(self):
        for system in combat.ATTACK_RESOLVERS:
            self.assertIn(system, combat.INITIATIVE)


class CampaignResolutionTests(unittest.TestCase):
    """Drive the real CLI against campaigns declaring each system."""

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._d.name)

    def tearDown(self):
        self._d.cleanup()

    def _campaign(self, name, system):
        d = self.root / "campaigns" / name
        d.mkdir(parents=True)
        header = f"**System Module:** {system}  " if system else ""
        (d / "state.md").write_text(f"# Campaign: {name}\n{header}**Session count:** 1\n",
                                    encoding="utf-8")

    def _run(self, *args):
        env = dict(os.environ, GM_CAMPAIGN_ROOT=str(self.root))
        return subprocess.run([sys.executable, str(SCRIPTS / "combat.py"), *args],
                              capture_output=True, text=True, encoding="utf-8", env=env)

    def test_each_system_is_read_from_state_md(self):
        self._campaign("dd", "dnd5e")
        self._campaign("pf", "pf2e")
        self._campaign("br", "brp")
        self._campaign("old", "")          # predates the header: 5e, as before
        cases = {
            "dd": ([{"name": "A", "dex_mod": 1, "hp": 5, "ac": 12, "type": "pc"}], "d20("),
            "old": ([{"name": "A", "dex_mod": 1, "hp": 5, "ac": 12, "type": "pc"}], "d20("),
            "pf": ([{"name": "A", "perception": 6, "hp": 5, "ac": 12, "type": "pc"}], "Perception"),
            "br": ([{"name": "A", "dex": 13, "hp": 5, "type": "pc"}], "A: DEX 13"),
        }
        for camp, (party, marker) in cases.items():
            with self.subTest(camp=camp):
                r = self._run("init", json.dumps(party), "-c", camp)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn(marker, r.stdout)
        r = self._run("attack", "--atk", "5", "--ac", "15", "--dmg", "1d6", "-c", "pf")
        self.assertTrue(r.stdout.startswith("Strike:"), r.stdout)
        r = self._run("attack", "--atk", "5", "--ac", "15", "--dmg", "1d6", "-c", "br")
        self.assertEqual(r.returncode, 2)

    def test_system_flag_overrides_the_campaign(self):
        self._campaign("pf", "pf2e")
        r = self._run("init", json.dumps(PARTY_5E), "-c", "pf", "--system", "dnd5e")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Goblin: d20(", r.stdout)

    def test_a_mistyped_campaign_warns_instead_of_silently_using_5e(self):
        self._campaign("pf", "pf2e")
        r = self._run("init", json.dumps(PARTY_5E), "-c", "pff")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no campaign 'pff'", r.stderr)
        r = self._run("init", json.dumps([{"name": "A", "perception": 6, "hp": 5,
                                           "ac": 12, "type": "pc"}]), "-c", "pf")
        self.assertNotIn("warning", r.stderr)


if __name__ == "__main__":
    unittest.main()
