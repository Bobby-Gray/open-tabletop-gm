"""A system manifest may bring its own scene set, and the sets never mix.

WHY
===
The display's scene backgrounds were one fantasy set — an inn, a crypt, a
temple — scored against every campaign's narration. A cyberpunk campaign got
"The Inn" as its resting background and could only ever move to another
fantasy room. Four lines of a neon street fight scored one point, for "The
Town"; a hacker in a network node scored nothing on any of the 17 scenes. The
background never moved.

A manifest (systems/<name>/ui.json) can now declare `scenes` and
`default_scene`. A campaign on that system scores against that set INSTEAD of
the built-in one; a system that declares nothing keeps the built-in set
exactly. The tests below hold both directions — a fantasy campaign never gets
a cyberpunk scene, a cyberpunk campaign never gets a fantasy one — and that a
system with no declared scenes is untouched.

Every declared scene, built-in or manifest, must also be drawable: a two-stop
gradient, an accent, a particle type the renderer actually has, and a label.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "display" / "templates" / "index.html"
SYSTEMS = ROOT / "systems"

CYBERPUNK = [
    "Rain hammers the alley. Neon bleeds across the puddles on the sidewalk.",
    "Traffic hisses past the overpass as you cross the street.",
    "A streetlight flickers over the gutter.",
]
FANTASY = [
    "You step into the temple. Incense drifts past the altar,",
    "and the pews stand empty before the shrine.",
    "A priest kneels at the altar of the temple.",
]


def _manifest(system: str) -> dict:
    return json.loads((SYSTEMS / system / "ui.json").read_text(encoding="utf-8"))


def _drawable_particles() -> set:
    src = HTML.read_text(encoding="utf-8")
    m = re.search(r"const\s+PARTICLE_COUNT\s*=\s*\{(.*?)\};", src, re.S)
    assert m, "renderer no longer declares PARTICLE_COUNT; update this test"
    return set(re.findall(r"(\w+)\s*:", m.group(1)))


class SceneScopingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._td = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls._td.name)
        cls._env = os.environ.get("GM_CAMPAIGN_ROOT")
        os.environ["GM_CAMPAIGN_ROOT"] = str(cls.root)
        for name, system in (("neon", "cwn"), ("keep", "dnd5e"),
                             ("strike", "pf2e"), ("legacy", "")):
            d = cls.root / "campaigns" / name
            d.mkdir(parents=True)
            header = f"**System Module:** {system}\n" if system else ""
            (d / "state.md").write_text(f"# Campaign: {name}\n{header}", encoding="utf-8")
        sys.path.insert(0, str(ROOT / "display"))
        spec = importlib.util.spec_from_file_location(
            "gmapp_scenes", ROOT / "display" / "gm-display-app.py")
        cls.m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(cls.m)
        except Exception as exc:                      # flask/deps absent
            raise unittest.SkipTest(f"display app not importable: {exc}")
        cls._orig_active = cls.m._active_campaign_name
        cls._orig_broadcast = cls.m._broadcast

    @classmethod
    def tearDownClass(cls):
        cls.m._active_campaign_name = cls._orig_active
        cls.m._broadcast = cls._orig_broadcast
        if cls._env is None:
            os.environ.pop("GM_CAMPAIGN_ROOT", None)
        else:
            os.environ["GM_CAMPAIGN_ROOT"] = cls._env
        cls._td.cleanup()

    def _campaign(self, name):
        self.m._active_campaign_name = lambda: name
        self.m._scene_buffer = []
        scenes, _, default = self.m._active_scene_set()
        self.m._current_scene_name = default
        return scenes

    def _narrate(self, lines):
        got = []
        for line in lines:
            s = self.m._detect_scene(line)
            if s:
                got.append(s["name"])
        return got

    def test_a_cwn_campaign_scores_against_its_own_set(self):
        scenes = self._campaign("neon")
        self.assertEqual(set(scenes), set(_manifest("cwn")["scenes"]))
        self.assertEqual(self.m._current_scene()["name"], "cp_street",
                         "the manifest's default_scene is what a new viewer sees")
        self.m._current_scene_name = "cp_tower"
        self.assertEqual(self._narrate(CYBERPUNK)[-1:], ["cp_street"])

    def test_a_cwn_campaign_never_gets_a_fantasy_scene(self):
        self._campaign("neon")
        got = self._narrate(FANTASY * 3)
        self.assertFalse(set(got) & set(self.m.SCENES),
                         f"a cwn campaign switched to fantasy scene(s) {got}")

    def test_a_fantasy_campaign_never_gets_a_cwn_scene(self):
        for camp in ("keep", "legacy"):
            with self.subTest(campaign=camp):
                self._campaign(camp)
                got = self._narrate(CYBERPUNK * 3)
                self.assertFalse([g for g in got if g.startswith("cp_")],
                                 f"{camp} switched to cwn scene(s) {got}")
                self.assertEqual(self._narrate(FANTASY), ["temple"],
                                 "the positive control: fantasy narration still moves it")

    def test_a_system_with_no_declared_scenes_keeps_the_builtin_set(self):
        """pf2e's manifest declares no scenes, so nothing about its backgrounds
        changes: the same 17 scenes, the same order, the same default."""
        self.assertNotIn("scenes", _manifest("pf2e"))
        for camp in ("strike", "keep", "legacy"):
            with self.subTest(campaign=camp):
                self._campaign(camp)
                scenes, priority, default = self.m._active_scene_set()
                self.assertIs(scenes, self.m.SCENES)
                self.assertIs(priority, self.m.SCENE_PRIORITY)
                self.assertEqual(default, "tavern")
        self.assertEqual(len(self.m.SCENES), 17)

    def test_a_viewer_connecting_mid_session_gets_the_set_default(self):
        """The scene name left over from a fantasy campaign is not in the cwn
        set, so the first scene a cwn viewer is sent must be cwn's default,
        not a KeyError and not The Inn."""
        self.m._active_campaign_name = lambda: "neon"
        self.m._current_scene_name = "tavern"
        self.assertEqual(self.m._current_scene()["name"], "cp_street")

    def test_switching_campaign_puts_the_new_set_on_screen(self):
        sent = []
        self.m._broadcast = sent.append
        try:
            self.m._active_campaign_name = lambda: "neon"
            self.m._current_scene_name = "crypt"
            self.m._switch_scene_set()
            self.assertEqual(self.m._current_scene_name, "cp_street")
            self.assertEqual(sent, [{"scene": self.m._current_scene()}])
            sent.clear()
            self.m._switch_scene_set()           # already in the set: no broadcast
            self.assertEqual(sent, [])
        finally:
            self.m._broadcast = self._orig_broadcast

    def test_an_unusable_declaration_falls_back_to_the_builtin_set(self):
        parse = self.m._manifest_scene_set
        self.assertIsNone(parse({}))
        self.assertIsNone(parse({"scenes": []}))
        self.assertIsNone(parse({"scenes": {"x": {"keywords": ["a"]}}}),
                          "a scene without colours, accent, particles and label is dropped")
        good = {"keywords": ["a"], "colors": ["#000000", "#111111"], "accent": "#222222",
                "particles": "rain", "label": "A"}
        scenes, priority, default = parse({"scenes": {"bad": {"label": "B"}, "ok": good},
                                           "default_scene": "missing"})
        self.assertEqual(priority, ["ok"])
        self.assertEqual(default, "ok", "an unknown default falls back to the first scene")


class SceneDrawabilityTests(unittest.TestCase):
    """Every scene a campaign can be shown, on every system."""

    def _all_scene_sets(self):
        sets = {}
        for d in sorted(SYSTEMS.iterdir()):
            if (d / "ui.json").is_file():
                m = _manifest(d.name)
                if "scenes" in m:
                    sets[d.name] = m
        return sets

    def test_declared_sets_exist(self):
        self.assertIn("cwn", self._all_scene_sets(),
                      "systems/cwn/ui.json should declare its own scenes")

    def test_every_declared_scene_is_drawable(self):
        particles = _drawable_particles()
        self.assertIn("rain", particles)
        self.assertNotIn("neon", particles)
        hexcolor = re.compile(r"^#[0-9a-fA-F]{6}$")
        for system, m in self._all_scene_sets().items():
            self.assertIn(m.get("default_scene"), m["scenes"],
                          f"{system}: default_scene is not one of its scenes")
            for name, s in m["scenes"].items():
                with self.subTest(system=system, scene=name):
                    self.assertTrue(s.get("keywords"))
                    self.assertEqual(len(s.get("colors", [])), 2)
                    for c in s["colors"] + [s.get("accent", "")]:
                        self.assertRegex(c, hexcolor)
                    self.assertIn(s.get("particles"), particles,
                                  f"{system}/{name}: the renderer draws no "
                                  f"{s.get('particles')!r} particles")
                    self.assertTrue(str(s.get("label", "")).strip())


if __name__ == "__main__":
    unittest.main()
