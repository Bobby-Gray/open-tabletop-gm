"""Timed effects count down in game time, and a rest does not cure what it cannot.

WHY
===
`effect start ... 60m` stored a wall-clock timestamp, so a one-hour spell
lasted one real hour: it expired over a coffee break mid-combat, and survived a
narrated eight-hour rest if the rest took two minutes to type. Nothing in the
toolchain could spend in-game time on an effect at all.

The rest procedure then papered over it by running `tracker.py clear`, which
wiped every effect, every condition and all concentration — so an eight-hour
ward vanished at a short rest, and a curse or a disease ended because the party
sat down for an hour. `clear` at the end of every encounter did the same to
every hour-long effect still running.

Now: minute/hour durations are in-game minutes, spent by `effect advance` and
by calendar.py's advance/rest; a long rest also ends concentration; rests leave
conditions and death saves alone; `clear` ends only round-measured effects.
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
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("tracker_under_test", SCRIPTS / "tracker.py")
tracker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tracker)


class TrackerTestBase(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._d.name)
        self._orig = tracker._CAMPAIGNS_DIR
        tracker._CAMPAIGNS_DIR = self.root / "campaigns"
        self._push, self._announce = tracker._push_conditions, tracker._send_announce
        tracker._push_conditions = lambda *a, **k: None
        tracker._send_announce = lambda *a, **k: None

    def tearDown(self):
        tracker._CAMPAIGNS_DIR = self._orig
        tracker._push_conditions, tracker._send_announce = self._push, self._announce
        self._d.cleanup()

    def quiet(self, fn, *a, **k):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*a, **k)

    def effects(self, who="ava"):
        return {e["name"]: e for e in tracker._load("c")[who]["effects"]}


class GameTimeTests(TrackerTestBase):

    def test_real_time_passing_does_not_expire_a_minute_effect(self):
        self.quiet(tracker.cmd_effect, "c", "start", "Ava", "Bless", "1m")
        state = tracker._load("c")
        eff = state["ava"]["effects"][0]
        self.assertNotIn("started_at", eff, "duration is still tied to the wall clock")
        self.assertEqual(tracker._remaining_minutes(eff), 1)

    def test_advance_spends_game_time(self):
        self.quiet(tracker.cmd_effect, "c", "start", "Ava", "Mage Armor", "8h")
        self.quiet(tracker.cmd_effect, "c", "start", "Ava", "Shield of Faith", "10m", True)
        self.quiet(tracker.advance_time, "c", 30)
        eff = self.effects()
        self.assertEqual(eff["Mage Armor"]["remaining_minutes"], 450)
        self.assertNotIn("Shield of Faith", eff)
        self.assertIsNone(tracker._load("c")["ava"]["concentration"],
                          "an expired concentration effect must end the concentration")

    def test_round_effects_count_down_by_the_rounds_in_the_time(self):
        self.quiet(tracker.cmd_effect, "c", "start", "Ava", "Bless", "10r")
        self.quiet(tracker.cmd_effect, "c", "start", "Ava", "Long Ward", "100r")
        self.quiet(tracker.advance_time, "c", 1)
        eff = self.effects()
        self.assertNotIn("Bless", eff)
        self.assertEqual(eff["Long Ward"]["duration_remaining"], 90)

    def test_a_turn_tick_does_not_spend_minutes(self):
        self.quiet(tracker.cmd_effect, "c", "start", "Ava", "Mage Armor", "8h")
        self.quiet(tracker.cmd_effect, "c", "tick", "Ava")
        self.assertEqual(self.effects()["Mage Armor"]["remaining_minutes"], 480)

    def test_advance_leaves_conditions_and_death_saves(self):
        self.quiet(tracker.cmd_condition, "c", "Ava", "add", "poisoned")
        self.quiet(tracker.cmd_saves, "c", "Ava", "failure")
        self.quiet(tracker.advance_time, "c", 480, end_concentration=True)
        ent = tracker._load("c")["ava"]
        self.assertEqual(ent["conditions"], ["poisoned"])
        self.assertEqual(ent["death_saves"]["failures"], 1)

    def test_long_rest_ends_concentration(self):
        self.quiet(tracker.cmd_effect, "c", "start", "Ava", "Hex", "24h", True)
        self.quiet(tracker.advance_time, "c", 480, end_concentration=True)
        self.assertNotIn("Hex", self.effects())
        self.assertIsNone(tracker._load("c")["ava"]["concentration"])

    def test_legacy_wall_clock_effects_keep_what_they_had_left(self):
        legacy = {"ava": {"name": "Ava", "conditions": [], "concentration": None,
                          "death_saves": {"successes": 0, "failures": 0, "stable": False},
                          "effects": [{"name": "Old Ward", "concentration": False,
                                       "duration_type": "hours", "duration_seconds": 7200,
                                       "started_at": time.time() - 1800}]}}
        tracker._save("c", legacy)
        self.quiet(tracker.advance_time, "c", 30)
        eff = self.effects()["Old Ward"]
        self.assertNotIn("started_at", eff)
        self.assertIn(eff["remaining_minutes"], (59, 60))


class ClearTests(TrackerTestBase):

    def test_clear_ends_round_effects_and_keeps_hour_effects(self):
        self.quiet(tracker.cmd_effect, "c", "start", "Ava", "Bless", "10r", True)
        self.quiet(tracker.cmd_effect, "c", "start", "Bo", "Hunter's Mark", "1h", True)
        self.quiet(tracker.cmd_effect, "c", "start", "Bo", "Mage Armor", "8h")
        self.quiet(tracker.cmd_condition, "c", "Ava", "add", "prone")
        self.quiet(tracker.cmd_clear, "c")
        state = tracker._load("c")
        self.assertEqual(state["ava"]["effects"], [])
        self.assertIsNone(state["ava"]["concentration"])
        self.assertEqual(state["ava"]["conditions"], [])
        self.assertEqual({e["name"] for e in state["bo"]["effects"]},
                         {"Hunter's Mark", "Mage Armor"})
        self.assertEqual(state["bo"]["concentration"], "Hunter's Mark")

    def test_clear_all_still_wipes_everything(self):
        self.quiet(tracker.cmd_effect, "c", "start", "Bo", "Mage Armor", "8h")
        self.quiet(tracker.cmd_saves, "c", "Bo", "failure")
        self.quiet(tracker.cmd_clear, "c", True)
        bo = tracker._load("c")["bo"]
        self.assertEqual(bo["effects"], [])
        self.assertEqual(bo["death_saves"]["failures"], 0)


class CliTests(unittest.TestCase):
    """Drive the scripts the rest procedure actually runs."""

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.env = dict(os.environ, GM_CAMPAIGN_ROOT=self._d.name)

    def tearDown(self):
        self._d.cleanup()

    def run_script(self, script, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), "-c", "c", *args],
                           capture_output=True, text=True, encoding="utf-8", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def state(self):
        p = pathlib.Path(self._d.name) / "campaigns" / "c" / "tracker.json"
        return json.loads(p.read_text(encoding="utf-8"))

    def test_effect_advance_from_the_cli(self):
        self.run_script("tracker.py", "effect", "start", "Ava", "Ward", "1h")
        self.run_script("tracker.py", "effect", "advance", "45m")
        self.assertEqual(self.state()["ava"]["effects"][0]["remaining_minutes"], 15)
        out = self.run_script("tracker.py", "effect", "advance", "15")
        self.assertIn("EXPIRED", out)
        self.assertEqual(self.state()["ava"]["effects"], [])

    def test_calendar_rests_drive_the_tracker(self):
        self.run_script("calendar.py", "init", "--date", "1 Frostfall 1200",
                        "--months", "Frostfall,Thaw")
        self.run_script("tracker.py", "effect", "start", "Ava", "Mage Armor", "8h")
        self.run_script("tracker.py", "effect", "start", "Ava", "Hex", "24h", "conc")
        self.run_script("tracker.py", "condition", "add", "Ava", "cursed")
        self.run_script("calendar.py", "rest", "short")
        ava = self.state()["ava"]
        self.assertEqual({e["name"]: e["remaining_minutes"] for e in ava["effects"]},
                         {"Mage Armor": 420, "Hex": 1380})
        self.assertEqual(ava["concentration"], "Hex", "a short rest does not end concentration")
        self.run_script("calendar.py", "rest", "long")
        ava = self.state()["ava"]
        self.assertEqual(ava["effects"], [])
        self.assertIsNone(ava["concentration"])
        self.assertEqual(ava["conditions"], ["cursed"], "a rest does not cure a lasting condition")

    def test_calendar_advance_drives_the_tracker(self):
        self.run_script("calendar.py", "init")
        self.run_script("tracker.py", "effect", "start", "Ava", "Ward", "8h")
        self.run_script("calendar.py", "advance", "2", "hours")
        self.assertEqual(self.state()["ava"]["effects"][0]["remaining_minutes"], 360)


class RestProcedureDocTests(unittest.TestCase):
    """The rest branch was the thing calling `clear`."""

    def test_the_rest_branch_does_not_run_clear(self):
        text = (ROOT / "SKILL-branches.md").read_text(encoding="utf-8")
        branch = text.split("## `/gm rest <short|long>`", 1)[1].split("\n## ", 1)[0]
        for line in branch.splitlines():
            if "tracker.py clear" in line:
                self.assertIn("not", line.lower(), f"rest step runs clear: {line}")


if __name__ == "__main__":
    unittest.main()
