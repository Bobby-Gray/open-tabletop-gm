"""Armour class must be written the way the rules compute it.

WHY
===
Upstream describes armour with three fields: `base`, `dex_bonus` and
`max_bonus`. The normaliser read only `base` and appended `+ DEX` to every
piece, so the built dataset said plate was "AC 18 + DEX" and a shield was
"AC 2 + DEX". A GM who trusted the lookup gave a DEX 16 fighter in plate AC 21
instead of 18, and a medium-armour wearer an uncapped bonus.

The dataset is gitignored, so these tests drive the normaliser with records
shaped exactly like upstream's — one per armour category.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "build_srd_armor", ROOT / "systems" / "dnd5e" / "build_srd.py"
)
build_srd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_srd)


def _armor(name, category, base, dex_bonus, max_bonus=None):
    return {
        "index": name.lower().replace(" ", "-"),
        "name": name,
        "equipment_category": {"index": "armor", "name": "Armor"},
        "armor_category": category,
        "armor_class": {"base": base, "dex_bonus": dex_bonus, "max_bonus": max_bonus},
    }


class ArmorClassTests(unittest.TestCase):
    def test_light_armor_adds_the_full_dex_modifier(self):
        out = build_srd._norm_equipment(_armor("Leather Armor", "Light", 11, True))
        self.assertEqual(out["ac"], "AC 11 + DEX")

    def test_medium_armor_caps_the_dex_modifier(self):
        out = build_srd._norm_equipment(_armor("Breastplate", "Medium", 14, True, 2))
        self.assertEqual(out["ac"], "AC 14 + DEX (max 2)")

    def test_heavy_armor_adds_no_dex_at_all(self):
        out = build_srd._norm_equipment(_armor("Plate Armor", "Heavy", 18, False))
        self.assertEqual(out["ac"], "AC 18")
        self.assertNotIn("DEX", out["ac"])

    def test_a_shield_is_a_bonus_not_a_base(self):
        out = build_srd._norm_equipment(_armor("Shield", "Shield", 2, False))
        self.assertEqual(out["ac"], "AC +2")

    def test_non_armor_has_no_ac(self):
        out = build_srd._norm_equipment({"name": "Rope", "index": "rope"})
        self.assertEqual(out["ac"], "")


if __name__ == "__main__":
    unittest.main()
