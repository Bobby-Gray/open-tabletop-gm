"""
test_lookup_suggest.py — near-miss "did you mean?" suggestions for the dnd5e
lookup module.

The SRD dataset is not committed to the repo (it's built on demand via
`systems/dnd5e/build_srd.py`), so these tests inject a small synthetic dataset
directly into the module's cache and exercise the pure `suggest()` logic: a
mistyped rule, condition, spell, or monster should surface the closest real
name instead of dead-ending, and category scoping must be honored.

Run from repo root:
    python3 -m unittest tests.test_lookup_suggest -v
"""
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "systems" / "dnd5e"))

import lookup  # noqa: E402


# A minimal stand-in for the built dataset, keyed like the real one.
_FIXTURE = {
    "spells":     [{"name": "Fireball"}, {"name": "Fire Bolt"}, {"name": "Cure Wounds"}],
    "equipment":  [{"name": "Rapier"}, {"name": "Longsword"}],
    "magic_items": [{"name": "Cloak of Protection"}],
    "conditions": [{"name": "Poisoned"}, {"name": "Prone"}, {"name": "Frightened"}],
    "monsters":   [{"name": "Goblin"}, {"name": "Gnoll"}],
    "features":   [{"name": "Cunning Action"}, {"name": "Sneak Attack"}],
}


def _names(hints):
    return [nm.lower() for nm, _cat in hints]


class SuggestTests(unittest.TestCase):

    def setUp(self):
        # Inject the fixture and mark the module loaded so suggest()/_load()
        # use it instead of trying to read the (absent) SRD dataset.
        self._saved_data = lookup._data
        self._saved_loaded = lookup._loaded
        lookup._data = {k: list(v) for k, v in _FIXTURE.items()}
        lookup._loaded = True

    def tearDown(self):
        lookup._data = self._saved_data
        lookup._loaded = self._saved_loaded

    def test_condition_typo(self):
        hints = lookup.suggest("poisonned", category="condition")
        self.assertIn("poisoned", _names(hints))

    def test_spell_typo(self):
        hints = lookup.suggest("fireballl", category="spell")
        self.assertIn("fireball", _names(hints))

    def test_monster_typo(self):
        hints = lookup.suggest("gobblin", category="monster")
        self.assertIn("goblin", _names(hints))

    def test_feature_typo(self):
        hints = lookup.suggest("cunnning action", category="feature")
        self.assertIn("cunning action", _names(hints))

    def test_cross_category_typo(self):
        # No category given — should still find the near-miss across categories.
        hints = lookup.suggest("poisonned")
        self.assertIn("poisoned", _names(hints))

    def test_respects_result_cap(self):
        hints = lookup.suggest("fireballl", category="spell", n=1)
        self.assertLessEqual(len(hints), 1)

    def test_garbage_query_returns_list_never_raises(self):
        hints = lookup.suggest("zzzxqqywv", category="condition")
        self.assertIsInstance(hints, list)

    def test_category_scoping(self):
        # A condition typo scoped to spells must not return the condition.
        hints = lookup.suggest("poisonned", category="spell")
        self.assertNotIn("poisoned", _names(hints))

    def test_item_pseudo_category_spans_equipment_and_magic(self):
        # The `item` alias searches equipment + magic_items.
        hints = lookup.suggest("rapierr", category="item")
        self.assertIn("rapier", _names(hints))

    def test_returns_name_category_tuples(self):
        hints = lookup.suggest("fireballl", category="spell")
        self.assertTrue(hints)
        nm, cat = hints[0]
        self.assertIsInstance(nm, str)
        self.assertEqual(cat, "spells")


if __name__ == "__main__":
    unittest.main()
