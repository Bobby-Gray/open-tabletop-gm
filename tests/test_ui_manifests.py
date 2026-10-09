"""Every shipped system's `ui.json` must be renderable by the renderer we ship.

WHY
===
A manifest is a declarative contract with one consumer: the sidebar renderer in
`display/templates/index.html`. Nothing validates it at load time — a widget
whose `type` the renderer does not know is skipped silently
(`_renderSidebarWidget` looks the type up in `_SIDEBAR_WIDGETS` and returns if
it misses), and a `class_map` severity the CSS has no rule for renders an
unstyled pill. Both failures look like a working display with one thing quietly
missing, which is the shape that hides for months.

`systems/brp/` shipped for three months with a complete 254-line `system.md`
and NO manifest at all, so BRP characters rendered through the D&D fallback —
an XP bar for a system with no levels, no Power Points, no Sanity. That is what
this file is here to catch, and it is why the population below is DERIVED.

THE POPULATION IS DERIVED, NOT LISTED
=====================================
Every assertion iterates `systems/*/`, and the valid widget types and severity
classes are parsed out of the renderer itself. A hand-maintained list of
systems is exactly how the gap above survived: the one existing manifest test
(`test_block_badges.py`) names `systems/dnd5e/ui.json` explicitly, so it stayed
green through BRP shipping without one. Add a system directory and these tests
cover it without being edited. Add a widget to the renderer and the allowed set
grows on its own.

Break-tested both ways: each assertion was confirmed to FAIL with the defect it
describes injected, and to pass once reverted.
"""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "display" / "templates" / "index.html"
SYSTEMS = ROOT / "systems"
ICONS = ROOT / "display" / "icons"


def _system_dirs() -> list[pathlib.Path]:
    """Every bundled system module, derived from the tree."""
    return sorted(p for p in SYSTEMS.iterdir() if p.is_dir() and (p / "system.md").is_file())


def _manifests() -> list[tuple[str, pathlib.Path, dict]]:
    out = []
    for d in _system_dirs():
        path = d / "ui.json"
        if path.is_file():
            out.append((d.name, path, json.loads(path.read_text(encoding="utf-8"))))
    return out


class ManifestFixtureTests(unittest.TestCase):
    """The fixtures this file reasons about must themselves be non-empty.

    A zero-length population would make every test below vacuously true, which
    is indistinguishable from a passing suite.
    """

    def test_there_are_systems_to_check(self):
        self.assertGreaterEqual(len(_system_dirs()), 2,
                                "systems/ should hold several bundled modules")

    def test_there_are_manifests_to_check(self):
        self.assertGreaterEqual(len(_manifests()), 2,
                                "at least two systems should ship a ui.json")


class RendererContractTests(unittest.TestCase):
    """What the renderer will actually accept, read from the renderer."""

    @classmethod
    def setUpClass(cls):
        src = HTML.read_text(encoding="utf-8")

        # The widget registry: `const _SIDEBAR_WIDGETS = { bar: _wBar, ... }`
        reg = re.search(r"const\s+_SIDEBAR_WIDGETS\s*=\s*\{(.*?)\}", src, re.S)
        assert reg, "renderer no longer declares _SIDEBAR_WIDGETS; update this test"
        cls.widget_types = set(re.findall(r"(\w+)\s*:", reg.group(1)))

        # The severity vocabulary: the values of the renderer's fallback map.
        cmap = re.search(r"const\s+_DEFAULT_CONDITION_CLASS\s*=\s*\{(.*?)\};", src, re.S)
        assert cmap, "renderer no longer declares _DEFAULT_CONDITION_CLASS; update this test"
        cls.severities = set(re.findall(r":\s*'(\w+)'", cmap.group(1)))

    def test_the_registry_parsed(self):
        """If the regex above silently matched nothing, every type is 'invalid'
        and the suite goes red for the wrong reason. If it matched everything,
        the suite goes green for the wrong reason."""
        self.assertIn("bar", self.widget_types)
        self.assertIn("tag_list", self.widget_types)
        self.assertNotIn("nonexistent_widget", self.widget_types)
        self.assertEqual(self.severities, {"danger", "warn", "info", "buff"})

    def test_every_widget_type_is_one_the_renderer_knows(self):
        """An unknown type is skipped silently — no console error, no gap in
        the layout, just a stat the table never sees."""
        for name, path, m in _manifests():
            for i, w in enumerate(m.get("sidebar", [])):
                with self.subTest(system=name, index=i, type=w.get("type")):
                    self.assertIn(w.get("type"), self.widget_types,
                                  f"{path.name}: sidebar[{i}] type "
                                  f"{w.get('type')!r} is not in the renderer's registry")

    def test_every_condition_class_is_one_the_css_styles(self):
        """A severity outside the four renders an unstyled pill: present,
        legible, and carrying none of the urgency it was meant to carry."""
        for name, path, m in _manifests():
            for w in m.get("sidebar", []):
                for cond, cls in (w.get("class_map") or {}).items():
                    with self.subTest(system=name, condition=cond):
                        self.assertIn(cls, self.severities,
                                      f"{path.name}: condition {cond!r} maps to "
                                      f"{cls!r}, which the renderer does not style")

    def test_every_badge_icon_file_exists(self):
        """`img.src = '/icons/' + icon + '.png'`, so a typo is a broken image
        on a narration block rather than a missing badge."""
        for name, path, m in _manifests():
            for entry in m.get("block_badges", []):
                icon = entry.get("icon")
                with self.subTest(system=name, icon=icon):
                    self.assertTrue((ICONS / f"{icon}.png").is_file(),
                                    f"{path.name}: block badge icon {icon!r} has no "
                                    f"display/icons/{icon}.png")


class ManifestShapeTests(unittest.TestCase):
    """Structural requirements that hold for every system."""

    def test_system_field_matches_its_directory(self):
        """`_load_ui_manifest` resolves by directory name, so a mismatch means
        the campaign loads a manifest that describes a different game."""
        for name, path, m in _manifests():
            with self.subTest(system=name):
                self.assertEqual(m.get("system"), name,
                                 f"{path}: 'system' is {m.get('system')!r}, directory is {name!r}")

    def test_version_and_label_are_present(self):
        for name, path, m in _manifests():
            with self.subTest(system=name):
                self.assertEqual(m.get("manifest_version"), 1)
                self.assertTrue(str(m.get("label", "")).strip(),
                                f"{path}: 'label' is what the UI shows; it cannot be empty")

    def test_every_widget_binds_to_something(self):
        """A widget with no binding can never draw. `stat_lines` and
        `feature_flags` carry their bindings per entry instead of at the top."""
        nested = {"stat_lines": "lines", "feature_flags": "flags"}
        for name, path, m in _manifests():
            for i, w in enumerate(m.get("sidebar", [])):
                wtype = w.get("type")
                with self.subTest(system=name, index=i, type=wtype):
                    if wtype in nested:
                        entries = w.get(nested[wtype]) or []
                        self.assertTrue(entries, f"{path}: {wtype} has no {nested[wtype]}")
                        for e in entries:
                            self.assertTrue(str(e.get("bind", "")).strip(),
                                            f"{path}: a {wtype} entry has no bind")
                    elif wtype == "effects":
                        self.assertTrue(str(w.get("bind", "")).strip())
                    else:
                        self.assertTrue(str(w.get("bind", "")).strip(),
                                        f"{path}: sidebar[{i}] ({wtype}) has no bind")

    def test_stat_grid_cells_are_complete(self):
        for name, path, m in _manifests():
            grid = (m.get("sheet") or {}).get("stat_grid")
            if not grid:
                continue
            with self.subTest(system=name):
                self.assertTrue(str(grid.get("bind", "")).strip(),
                                f"{path}: stat_grid has no bind")
                self.assertTrue(grid.get("stats"), f"{path}: stat_grid has no stats")
                for cell in grid["stats"]:
                    self.assertTrue(str(cell.get("key", "")).strip(), f"{path}: stat with no key")
                    self.assertTrue(str(cell.get("label", "")).strip(), f"{path}: stat with no label")


class BundledSystemsShipManifestTests(unittest.TestCase):
    """A bundled system module ships its own manifest.

    The D&D fallback exists so a THIRD-PARTY system works before anyone writes
    a manifest. Relying on it for a system we ship ourselves means shipping the
    wrong sidebar: BRP has no levels, so the fallback drew it an XP bar, and
    its Power Points and Sanity had nowhere to go. Issue #32 sat open for three
    months because nothing asserted this.
    """

    def test_every_bundled_system_has_a_ui_json(self):
        missing = [d.name for d in _system_dirs() if not (d / "ui.json").is_file()]
        self.assertEqual(missing, [],
                         f"bundled system(s) with no ui.json: {missing}. The renderer "
                         f"falls back to the D&D layout, which is wrong for any system "
                         f"with different resources. See systems/UI-MANIFEST.md.")

    def test_every_bundled_system_has_a_notice_when_it_cites_a_licence(self):
        """A module derived from licensed rules content must carry attribution
        next to the content, not only in a changelog entry."""
        for d in _system_dirs():
            text = (d / "system.md").read_text(encoding="utf-8")
            if re.search(r"\bORC\b|ORC Licen[cs]e", text):
                with self.subTest(system=d.name):
                    self.assertTrue((d / "NOTICE").is_file(),
                                    f"systems/{d.name}/system.md cites the ORC Licence "
                                    f"but systems/{d.name}/NOTICE is missing")


if __name__ == "__main__":
    unittest.main()
