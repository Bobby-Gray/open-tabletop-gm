"""
test_milestone_counter.py — server-side mutation logic for the milestone-counter
sidebar feature added in v0.9.0.

The mutation handlers live inside `gm-display-app.py`'s /stats POST handler,
inside a request-context closure, so the cleanest way to exercise them is to
import the module and POST through Flask's test_client. We mock the token
gate so the test doesn't need to scrape one off disk.

Run from repo root:
    python3 -m unittest tests.test_milestone_counter -v
"""
import importlib
import json
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "display"))


def _import_app():
    """Import gm-display-app.py once, regardless of hyphen in filename."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gm_display_app", str(REPO / "display" / "gm-display-app.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class MilestoneCounterTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_app()
        # Bypass token gate
        cls.mod._token_ok = lambda: True
        cls.client = cls.mod.app.test_client()

    def setUp(self):
        # Reset shared stats state between tests
        self.mod._current_stats = {
            "players": [{"name": "Aldric", "milestones": {}}]
        }

    def _post(self, body):
        return self.client.post(
            "/stats", data=json.dumps(body), content_type="application/json"
        )

    def _player(self, name="Aldric"):
        for p in self.mod._current_stats.get("players", []):
            if p["name"] == name:
                return p
        return None

    def test_milestone_inc_creates_label_at_one(self):
        r = self._post({"players": [{"name": "Aldric", "_milestone_inc": "Inspiration"}]})
        self.assertIn(r.status_code, (200, 204), msg=r.data)
        self.assertEqual(self._player()["milestones"], {"Inspiration": 1})

    def test_milestone_inc_increments_existing_label(self):
        for _ in range(3):
            self._post({"players": [{"name": "Aldric", "_milestone_inc": "Bennie"}]})
        self.assertEqual(self._player()["milestones"], {"Bennie": 3})

    def test_milestone_dec_decrements_and_clears_at_zero(self):
        # Increment to 2, then decrement twice — second dec should remove the key
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Hero Point"}]})
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Hero Point"}]})
        self.assertEqual(self._player()["milestones"], {"Hero Point": 2})
        self._post({"players": [{"name": "Aldric", "_milestone_dec": "Hero Point"}]})
        self.assertEqual(self._player()["milestones"], {"Hero Point": 1})
        self._post({"players": [{"name": "Aldric", "_milestone_dec": "Hero Point"}]})
        # Key should be removed when count hits 0 — keeps sidebar clean
        self.assertNotIn("Hero Point", self._player()["milestones"])

    def test_milestone_dec_below_zero_is_floor_zero(self):
        # Decrement on empty milestones — should not go negative
        self._post({"players": [{"name": "Aldric", "_milestone_dec": "Bennie"}]})
        self.assertEqual(self._player().get("milestones", {}).get("Bennie", 0), 0)

    def test_multiple_labels_coexist(self):
        """A character can hold multiple reward types at once (rare but valid)."""
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Inspiration"}]})
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Bennie"}]})
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Bennie"}]})
        ms = self._player()["milestones"]
        self.assertEqual(ms.get("Inspiration"), 1)
        self.assertEqual(ms.get("Bennie"), 2)

    def test_milestone_caps_respected(self):
        """If a player has milestone_caps set, _milestone_inc respects them."""
        self._player()["milestone_caps"] = {"Inspiration": 1}  # D&D 5e binary
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Inspiration"}]})
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Inspiration"}]})
        self.assertEqual(self._player()["milestones"]["Inspiration"], 1)

    def test_dec_without_prior_inc_no_negative(self):
        """If dec arrives before any inc, the count clamps at 0 and key removes."""
        self._post({"players": [{"name": "Aldric", "_milestone_dec": "Fate Point"}]})
        self.assertNotIn("Fate Point", self._player().get("milestones", {}))

    def test_milestone_state_survives_other_mutations(self):
        """Other stat mutations on the same player don't clobber milestones."""
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Bennie"}]})
        self._post({"players": [{"name": "Aldric", "_conditions_add": "Shaken"}]})
        self.assertEqual(self._player()["milestones"], {"Bennie": 1})
        self.assertIn("Shaken", self._player().get("conditions", []))


if __name__ == "__main__":
    unittest.main()
