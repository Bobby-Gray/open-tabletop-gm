"""A natural 20 is a critical hit only on an attack, and only where the system says so.

WHY
===
dice.py printed "*** CRITICAL HIT (nat 20)! ***" and "*** FUMBLE (nat 1)! ***"
on every single d20 it rolled — ability checks, saving throws, initiative. In
D&D 5e a natural 20 on a check is just a 20, and "fumble" is not a rule at all;
a GM reading the label narrates a critical success the rules do not give. PF2e
has a rule for naturals on every check — a one-step shift in the degree of
success — which the label also misdescribed.

`--vs check|save|attack` says what the roll is for, `--dc N` resolves it, and
the system (from the campaign or `--system`) decides what a natural means.

Also covers the move from `random` to `secrets` for game dice, the generator the
display's own roller already used.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("dice_under_test", SCRIPTS / "dice.py")
dice = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dice)


@contextlib.contextmanager
def faces(*values):
    it = iter(values)
    orig = dice.secrets.randbelow
    dice.secrets.randbelow = lambda n: next(it) - 1
    try:
        yield
    finally:
        dice.secrets.randbelow = orig


def roll(notation, *, natural, **kw) -> str:
    out = io.StringIO()
    with faces(natural, natural), contextlib.redirect_stdout(out):
        dice.run(notation, **kw)
    return out.getvalue()


class Dnd5eTests(unittest.TestCase):

    def test_a_natural_20_on_a_check_is_not_a_critical_hit(self):
        for vs in ("", "check", "save"):
            with self.subTest(vs=vs):
                out = roll("d20+3", natural=20, vs=vs, system="dnd5e")
                self.assertNotIn("CRITICAL", out)
                self.assertNotIn("FUMBLE", out)

    def test_a_natural_1_on_a_save_is_not_a_fumble(self):
        out = roll("d20+3", natural=1, vs="save", system="dnd5e")
        self.assertNotIn("FUMBLE", out)
        self.assertNotIn("MISS", out)

    def test_attack_naturals_are_labelled(self):
        self.assertIn("CRITICAL HIT", roll("d20+3", natural=20, vs="attack", system="dnd5e"))
        self.assertIn("AUTOMATIC MISS", roll("d20+30", natural=1, vs="attack", system="dnd5e"))

    def test_a_dc_resolves_success_and_failure(self):
        self.assertIn("vs DC 15 — SUCCESS", roll("d20+3", natural=12, vs="check", dc=15, system="dnd5e"))
        self.assertIn("vs DC 15 — FAILURE", roll("d20+3", natural=11, vs="save", dc=15, system="dnd5e"))
        self.assertIn("vs AC 15 — HIT", roll("d20+3", natural=12, vs="attack", dc=15, system="dnd5e"))

    def test_the_label_follows_the_kept_die_with_advantage(self):
        out = io.StringIO()
        with faces(20, 4), contextlib.redirect_stdout(out):
            dice.run("d20+2 adv", vs="attack", system="dnd5e")
        self.assertIn("CRITICAL HIT", out.getvalue())


class Pf2eTests(unittest.TestCase):

    def test_degrees_with_the_natural_shift(self):
        cases = [
            # (natural, mod, dc, expected)
            (15, 10, 15, "CRITICAL SUCCESS"),       # 25 >= 15 + 10
            (20, 0, 25, "SUCCESS"),                 # 20 fails 25, shifted up
            (1, 20, 15, "FAILURE"),                 # 21 succeeds, shifted down
            (2, 0, 15, "CRITICAL FAILURE"),         # 2 <= 15 - 10
            (10, 3, 15, "FAILURE"),
        ]
        for natural, mod, dc, want in cases:
            with self.subTest(natural=natural, mod=mod, dc=dc):
                out = roll(f"d20+{mod}", natural=natural, vs="check", dc=dc, system="pf2e")
                self.assertRegex(out, rf"— {want}(\s|\(|$)")

    def test_a_natural_without_a_dc_is_described_as_a_shift(self):
        out = roll("d20+5", natural=20, vs="save", system="pf2e")
        self.assertIn("one degree of success better", out)
        self.assertNotIn("CRITICAL HIT", out)


class OtherSystemTests(unittest.TestCase):

    def test_a_system_with_no_d20_crit_rule_gets_no_label(self):
        for natural in (1, 20):
            with self.subTest(natural=natural):
                out = roll("d20", natural=natural, vs="attack", system="brp")
                self.assertNotIn("CRITICAL", out)
                self.assertNotIn("MISS", out)


class NaturalRulesSeamTests(unittest.TestCase):

    def test_a_new_row_is_honoured(self):
        dice.NATURAL_RULES["d20test"] = "attack_crit"
        try:
            self.assertIn("CRITICAL HIT", roll("d20", natural=20, vs="attack", system="d20test"))
            self.assertNotIn("CRITICAL", roll("d20", natural=20, vs="check", system="d20test"))
        finally:
            del dice.NATURAL_RULES["d20test"]


class CliTests(unittest.TestCase):

    def _run(self, *args, env=None):
        return subprocess.run([sys.executable, str(SCRIPTS / "dice.py"), *args],
                              capture_output=True, text=True, encoding="utf-8",
                              env=env or os.environ.copy())

    def test_notation_with_spaces_still_parses_beside_flags(self):
        r = self._run("d20", "adv", "--vs", "check", "--dc", "10")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[ADV]", r.stdout)

    def test_silent_still_prints_only_the_integer(self):
        r = self._run("2d6+3", "--silent")
        self.assertRegex(r.stdout.strip(), r"^\d+$")

    def test_bad_vs_is_rejected(self):
        r = self._run("d20", "--vs", "initiative")
        self.assertNotEqual(r.returncode, 0)

    def test_the_campaign_decides_the_system(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td) / "campaigns" / "pf"
            d.mkdir(parents=True)
            (d / "state.md").write_text("**System Module:** pf2e\n", encoding="utf-8")
            env = dict(os.environ, GM_CAMPAIGN_ROOT=td)
            # d20+40 vs DC 15 beats the DC by 10 on any natural, so PF2e says
            # CRITICAL SUCCESS — or, on a natural 1, SUCCESS with the shift
            # named. 5e would print a bare SUCCESS either way.
            r = self._run("d20+40", "--vs", "check", "--dc", "15", "-c", "pf", env=env)
            self.assertRegex(r.stdout, r"— (CRITICAL SUCCESS|SUCCESS \(natural 1)", r.stderr)


class SecretsTests(unittest.TestCase):
    """Game dice come from `secrets`, like the display's server-side roller."""

    GAME_DICE = [SCRIPTS / "dice.py", SCRIPTS / "combat.py",
                 ROOT / "systems" / "dnd5e" / "ability-scores.py"]

    def test_no_game_dice_script_imports_random(self):
        for path in self.GAME_DICE:
            with self.subTest(script=path.name):
                src = path.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"^\s*(import random|from random )", src, re.M))
                self.assertIn("secrets", src)

    def test_roll_dice_draws_from_secrets(self):
        with faces(4, 6, 1):
            self.assertEqual(dice.roll_dice(3, 6), [4, 6, 1])

    def test_rolls_stay_in_range(self):
        rolls = dice.roll_dice(2000, 20)
        self.assertEqual(min(rolls), 1)
        self.assertEqual(max(rolls), 20)


if __name__ == "__main__":
    unittest.main()
