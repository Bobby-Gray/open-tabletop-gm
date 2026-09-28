"""Milestone 2: maps, the Kairos sheet, enemy options and the GM command line.

The CLI runs in-process against a temporary campaign (GM_CAMPAIGN_ROOT), with
the display switched off. Monster lookups use the real SRD records in
tests/fixtures (the generated SRD dataset is gitignored and needs network).
"""
from __future__ import annotations

import json
import sys

import pytest

from tests.tactics_fixtures import (RULES, ROOT, _build, _RAW, encounter, frog, goblin,
                                    kairos, roller, start)
from tactics import ai, cli, maps, sync

rules_mod = sys.modules[type(RULES).__module__]
sheet_mod = rules_mod._sheet_module()
KAIROS_MD = (ROOT / "tests" / "fixtures" / "Kairos_Level1.md").read_text(encoding="utf-8")


# ─── maps ─────────────────────────────────────────────────────────────────────

def test_every_shipped_map_compiles():
    assert set(maps.available()) >= {"frog-pond", "detention-bog", "firejolt-rooftops",
                                      "mage-tower", "blank"}
    for name in maps.available():
        m = maps.load(name)
        assert m["grid"]["rows"] and m["meta"]["name"]


def test_frog_pond_matches_the_reference_layout():
    rows = maps.load("Frog Pond")["grid"]["rows"]
    assert len(rows) == 14 and len(rows[0]) == 20
    assert rows[6][:3] == "..." and rows[6][3] == "~"        # start bank, then water
    assert rows[3][5] == ","                                 # a lily pad
    assert rows[0][17] == "a" and rows[0][18] == "."          # finish line, finish bank


def test_map_errors_are_specific():
    with pytest.raises(ValueError, match="unknown terrain 'lava'"):
        maps.compile_map({"width": 3, "height": 3, "features": [{"type": "lava", "x": 0, "y": 0}]})
    with pytest.raises(ValueError, match="runs off"):
        maps.compile_map({"width": 3, "height": 3,
                          "features": [{"type": "wall", "x": 2, "y": 0, "w": 2}]})
    with pytest.raises(FileNotFoundError, match="Maps:"):
        maps.load("atlantis")


# ─── the character sheet ─────────────────────────────────────────────────────

def test_kairos_sheet_reads_into_a_token():
    k = sheet_mod.read_sheet(KAIROS_MD, "kairos", (1, 6))
    assert (k.name, k.hp, k.max_hp, k.ac, k.speed, k.dex_mod) == ("Kairos", 8, 8, 12, 30, 2)
    assert k.saves == {"str": -1, "dex": 2, "con": 2, "int": 5, "wis": 3, "cha": -1}
    bolt, dagger = k.attacks
    assert bolt == {"name": "Fire Bolt", "bonus": 5, "type": "ranged", "range": [120, 120],
                    "damage": [{"dice": "1d10", "type": "fire"}], "source": "spell", "flags": []}
    assert dagger["type"] == "melee_or_ranged" and dagger["range"] == [20, 60]
    assert k.extra["slots"] == {"1": {"total": 2, "used": 0}}
    assert k.extra["save_spells"][0]["name"] == "Mind Sliver"
    assert k.controller == "player"


def test_write_back_changes_only_combat_lines():
    k = sheet_mod.read_sheet(KAIROS_MD, "kairos", (0, 0))
    k.hp, k.temp_hp = 3, 0
    k.extra["slots"]["1"]["used"] = 1
    k.death_saves["failures"] = 1
    k.conditions = ["prone", "exhaustion"]
    new = sheet_mod.write_back(KAIROS_MD, k)
    changed = [l for l in new.splitlines() if l not in KAIROS_MD.splitlines()]
    assert changed == ["- **HP:** 3 / 8 | **Temp HP:** 0",
                       "- **Death Saves:** Successes: 0 | Failures: 1",
                       "- **Conditions:** exhaustion",                   # prone dropped
                       "| 1st | 2 | 1 |"]
    assert len(new.splitlines()) == len(KAIROS_MD.splitlines()) + 1


def test_lasting_conditions():
    k = kairos()
    k.conditions = ["prone", "grappled", "poisoned", "exhaustion"]
    assert sheet_mod.lasting_conditions(k) == ["exhaustion"]
    k.extra["durations"] = {"poisoned": "1 hour"}
    assert sheet_mod.lasting_conditions(k) == ["poisoned", "exhaustion"]
    k.dead = True
    assert sheet_mod.lasting_conditions(k) == ["dead"]


# ─── enemy options ───────────────────────────────────────────────────────────

def test_adjacent_frog_offers_the_bite_first():
    enc = start(encounter([kairos(pos=(0, 0)), frog("frog-1", (1, 0))]), ["frog-1", "kairos"])
    opts = ai.options(enc, "frog-1")
    assert opts[0]["kind"] == "attack" and opts[0]["label"].startswith("Bite Kairos from here")
    assert "60% to hit" in opts[0]["label"]


def test_frog_moves_in_and_bites_when_it_can():
    enc = start(encounter([kairos(pos=(0, 0)), frog("frog-1", (5, 0))]), ["frog-1", "kairos"])
    first = ai.options(enc, "frog-1")[0]
    assert first["kind"] == "attack" and first["move_to"] == "B1"


def test_badly_hurt_creatures_flee_first():
    f = frog("frog-1", (1, 0))
    f.hp = 4                                                    # below 25% of 18
    enc = start(encounter([kairos(pos=(0, 0)), f]), ["frog-1", "kairos"])
    first = ai.options(enc, "frog-1")[0]
    assert first["kind"] == "retreat" and first["disengage"]
    assert "flee" in first["label"] and first["label"].startswith("Disengage")


def test_ranged_creatures_step_out_of_melee_to_shoot():
    g = goblin("goblin-1", (1, 0))
    g.attacks = [a for a in g.attacks if a["name"] == "Shortbow"]
    k = kairos(pos=(0, 0))
    k.attacks = [a for a in k.attacks if a["name"] == "Fire Bolt"]    # no melee: no OA risk
    enc = start(encounter([k, g]), ["goblin-1", "kairos"])
    first = ai.options(enc, "goblin-1")[0]
    assert first["kind"] == "attack" and first["move_to"] is not None
    assert "disadvantage" not in first["label"]
    # With a dagger in Kairos's hand, stepping away provokes; shooting from here wins.
    enc = start(encounter([kairos(pos=(0, 0)), goblin("goblin-1", (1, 0))]), ["goblin-1", "kairos"])
    assert all(not o.get("tags") or "provokes Kairos" not in o["tags"]
               for o in ai.options(enc, "goblin-1")[:1])


def test_choose_runs_the_numbered_option():
    enc = start(encounter([kairos(pos=(0, 0)), frog("frog-1", (1, 0))]), ["frog-1", "kairos"])
    res = ai.choose(enc, roller(15, 4), "frog-1", 1)
    assert "Bite -> Kairos" in res["text"] and enc.tokens["kairos"].hp == 3
    assert "Kairos is grappled and restrained (escape DC 11)." in res["text"]
    assert "GM decides: The frog can't bite another target." in res["text"]


# ─── the command line ─────────────────────────────────────────────────────────

@pytest.fixture
def camp(tmp_path, monkeypatch):
    root = tmp_path / "root"
    d = root / "campaigns" / "demo"
    (d / "characters").mkdir(parents=True)
    (d / "characters" / "Kairos.md").write_text(KAIROS_MD, encoding="utf-8")
    (d / "state.md").write_text("# Campaign: demo\n\n## Active Combat\n*(none)*\n\n"
                                "## Session Flags\nroll_mode: players\n", encoding="utf-8")
    (d / "session-log.md").write_text("# Session Log\n", encoding="utf-8")
    monkeypatch.setenv("GM_CAMPAIGN_ROOT", str(root))
    monkeypatch.setenv("TACTICS_NO_DISPLAY", "1")
    monkeypatch.setattr(rules_mod, "_lookup_monster",
                        lambda name: _build._norm_monster(_RAW[name.lower().replace(" ", "-")]))
    return d


def run(capsys, *argv):
    code = cli.main(["-c", "demo", *argv])
    return code, capsys.readouterr().out.strip()


def begin(capsys, *extra):
    return run(capsys, "start", "frog-pond", "--pc", "Kairos@B7", "--monster", "giant frog@J5",
               "--monster", "giant frog@M11", "--seed", "3", *extra)


def test_start_status_and_state_md(camp, capsys):
    code, out = begin(capsys)
    assert code == 0 and out.startswith("Grid combat on Frog Pond. Initiative:")
    assert (camp / "combat" / "encounter.json").exists()
    assert "combat/encounter.json" in (camp / "state.md").read_text(encoding="utf-8")
    code, out = run(capsys, "status")
    assert "Giant Frog 1 J5 18/18" in out and "Kairos B7 8/8" in out
    code, out = begin(capsys)
    assert code == 1 and "already running" in out


def test_a_player_roll_is_asked_for_and_nothing_changes_meanwhile(camp, capsys):
    begin(capsys, "--roll-mode", "players")
    path = camp / "combat" / "encounter.json"
    enc = json.loads(path.read_text(encoding="utf-8"))
    enc["order"] = ["kairos", "frog-1", "frog-2"]               # Kairos first, for the test
    enc["turn_index"] = 0
    enc["turn"]["actor"] = "kairos"
    enc["turn"]["movement_budget"] = 30
    path.write_text(json.dumps(enc), encoding="utf-8")
    before = path.read_text(encoding="utf-8")

    code, out = run(capsys, "attack", "kairos", "frog-1", "fire", "bolt")
    assert code == 2 and "Kairos rolls 1d20+5" in out and "--roll" in out
    assert path.read_text(encoding="utf-8") == before
    code, out = run(capsys, "attack", "kairos", "frog-1", "fire", "bolt", "--roll", "14")
    assert code == 2 and "--roll 14 --roll <the dice total" in out
    code, out = run(capsys, "attack", "kairos", "frog-1", "fire", "bolt", "--roll", "14", "--roll", "7")
    assert code == 0 and "hit" in out and "7 fire damage" in out
    rolls = json.loads(path.read_text(encoding="utf-8"))["log"][-1]["rolls"]
    assert [r["source"] for r in rolls] == ["verbal", "verbal"]


def test_a_paused_roll_is_mirrored_to_the_display(camp, capsys, monkeypatch):
    pushed = []
    monkeypatch.setattr(sync, "push_display",
                        lambda enc, meta=None: pushed.append(sync.snapshot(enc, meta)))
    begin(capsys, "--roll-mode", "players")
    path = camp / "combat" / "encounter.json"
    enc = json.loads(path.read_text(encoding="utf-8"))
    enc["order"] = ["kairos", "frog-1", "frog-2"]               # Kairos first, for the test
    enc["turn_index"] = 0
    enc["turn"]["actor"] = "kairos"
    enc["turn"]["movement_budget"] = 30
    path.write_text(json.dumps(enc), encoding="utf-8")
    before = path.read_text(encoding="utf-8")

    code, out = run(capsys, "attack", "kairos", "frog-1", "fire", "bolt")
    assert code == 2 and "Kairos rolls 1d20+5" in out
    assert [p["turn"]["pending"] for p in pushed] == ["", "roll:1d20+5"]
    assert path.read_text(encoding="utf-8") == before           # paused: pushed, not saved


def test_a_reaction_ask_is_mirrored_to_the_display(camp, capsys, monkeypatch):
    import random as _random
    pushed = []
    monkeypatch.setattr(sync, "push_display",
                        lambda enc, meta=None: pushed.append(sync.snapshot(enc, meta)))
    begin(capsys)
    _edit(camp, actor="frog-1", pos={"frog-1": (2, 6)})
    hit = next(s for s in range(500) if 9 <= _random.Random(s).randint(1, 20) <= 16)
    monkeypatch.setattr(cli.random, "randrange", lambda n: hit)
    code, out = run(capsys, "attack", "frog-1", "kairos")
    assert code == 2 and "Silvery Barbs" in out
    assert any(p["turn"]["pending"] == "react:kairos:silvery barbs" for p in pushed)


def test_enemy_turn_through_options_and_choose(camp, capsys):
    code, out = begin(capsys)
    assert "Next: options frog-1" in out
    code, out = run(capsys, "options", "frog-1")
    assert code == 0 and "\n1. " in out and "choose frog-1 <n>" in out
    code, out = run(capsys, "choose", "frog-1", "1", "--seed", "4")
    assert code == 0 and out.startswith("1. ") and out.endswith("Then: end-turn")
    code, out = run(capsys, "options", "kairos")
    assert code == 1 and "player-controlled" in out


def test_end_writes_the_sheet_backup_session_log_and_tracker(camp, capsys):
    begin(capsys)
    code, out = run(capsys, "adjust", "kairos", "hp=5")
    assert code == 0
    code, out = run(capsys, "end")
    assert code == 0 and "Combat ended" in out
    assert "+- **HP:** 5 / 8 | **Temp HP:** 0" in out                  # the short diff
    sheet = (camp / "characters" / "Kairos.md").read_text(encoding="utf-8")
    assert "**HP:** 5 / 8" in sheet
    assert (camp / "characters" / "Kairos.md.bak").read_text(encoding="utf-8") == KAIROS_MD
    log = (camp / "session-log.md").read_text(encoding="utf-8")
    assert "### Grid combat: Frog Pond" in log and "- Kairos: 5/8 HP." in log
    assert 3 <= len(log.split("### Grid combat")[1].strip().splitlines()) <= 5
    assert "*(none)*" in (camp / "state.md").read_text(encoding="utf-8")
    tracker = json.loads((camp / "tracker.json").read_text(encoding="utf-8"))
    assert set(tracker) == {"kairos"}                                 # monsters dropped
    code, out = run(capsys, "end")
    assert code == 1 and "already ended" in out


def test_helpful_errors(camp, capsys):
    code, out = run(capsys, "status")
    assert code == 1 and "No grid combat is running" in out
    code, out = run(capsys, "start", "atlantis", "--pc", "Kairos@B7")
    assert code == 1 and "no map 'atlantis'" in out
    code, out = run(capsys, "start", "frog-pond", "--pc", "Nobody@B7")
    assert code == 1 and "No sheet for Nobody" in out
    code, out = run(capsys, "start", "frog-pond", "--pc", "Kairos@Z99")
    assert code == 1 and "off the map" in out


def test_the_terminal_demo_plays_a_whole_fight(camp, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("tactics_demo", ROOT / "scripts" / "tactics" / "demo.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    res = demo.play(camp, seed=4)
    out = capsys.readouterr().out
    assert res["ok"] and "$ combat.py start frog-pond" in out and "$ combat.py end" in out
    assert "### Grid combat: Frog Pond" in (camp / "session-log.md").read_text(encoding="utf-8")


# ─── milestone 4: spells and reactions on the command line ────────────────────

def _edit(camp, **turn):
    """Rewrite encounter.json: Kairos's turn by default, tokens moved as asked."""
    path = camp / "combat" / "encounter.json"
    enc = json.loads(path.read_text(encoding="utf-8"))
    for tid, (x, y) in turn.pop("pos", {}).items():
        enc["tokens"][tid]["x"], enc["tokens"][tid]["y"] = x, y
    actor = turn.pop("actor", "kairos")
    enc["turn_index"] = enc["order"].index(actor)
    enc["turn"] = {"actor": actor, "movement_budget": 30}
    path.write_text(json.dumps(enc), encoding="utf-8")
    return path


def test_the_kairos_sheet_carries_his_spellcasting():
    k = sheet_mod.read_sheet(KAIROS_MD, "kairos", (0, 0))
    assert k.extra["spell_dc"] == 13 and k.extra["spell_attack"] == 5 and k.extra["level"] == 1
    assert {"Fire Bolt", "Mind Sliver", "Shield", "Silvery Barbs", "Mage Armor",
            "Magic Missile"} <= set(k.extra["spells"])
    assert not any("choice" in s.lower() for s in k.extra["spells"])      # notes are not spells
    assert k.extra["skills"]["stealth"] == 4 and k.extra["passive_perception"] == 11


def test_cast_from_the_command_line_with_loose_spell_words(camp, capsys):
    begin(capsys)
    _edit(camp, pos={"frog-1": (6, 6)})
    code, out = run(capsys, "cast", "kairos", "magic", "missile", "frog-1")
    assert code == 2 and "Kairos rolls 1d4+1" in out
    code, out = run(capsys, "cast", "kairos", "magic", "missile", "frog-1", "--roll", "3")
    assert code == 0 and "3 darts hit Giant Frog 1 for 4 force each" in out
    code, out = run(capsys, "status")
    assert "Giant Frog 1 G7 6/18" in out


def test_spells_and_preview_area_are_read_only(camp, capsys):
    begin(capsys)
    _edit(camp, pos={"frog-1": (6, 6)})
    code, out = run(capsys, "spells", "kairos", "--json")
    rows = {r["name"]: r for r in json.loads(out)["result"]["spells"]}
    assert rows["Magic Missile"]["targeting"] == "darts" and not rows["Shield"]["ok"]
    code, out = run(capsys, "preview-area", "kairos", "mind sliver", "frog-1")
    assert code == 0 and out.startswith("Mind Sliver: Giant Frog 1 ") and "% to fail" in out


def test_a_paused_reaction_replays_the_same_enemy_roll(camp, capsys, monkeypatch):
    import random as _random
    begin(capsys)
    _edit(camp, actor="frog-1", pos={"frog-1": (2, 6)})       # next to Kairos on B7
    hit = next(s for s in range(500) if 9 <= _random.Random(s).randint(1, 20) <= 16)
    miss = next(s for s in range(500) if _random.Random(s).randint(1, 20) <= 3)
    seeds = iter([hit, miss, miss, miss])
    monkeypatch.setattr(cli.random, "randrange", lambda n: next(seeds))
    code, out = run(capsys, "attack", "frog-1", "kairos")
    assert code == 2 and "Silvery Barbs" in out and "Nothing has happened yet" in out
    assert (camp / "combat" / "pending.json").exists()
    total = out.split("(")[1].split(")")[0]
    answers = ["--react", "no"]
    for _ in range(3):
        code, out = run(capsys, "attack", "frog-1", "kairos", *answers)
        if code == 0:
            break
        assert "--react no --react yes or --react no" in out      # prior answers repeated
        answers += ["--react", "no"]
    assert code == 0 and f"Kairos: {total} vs AC 12, hit" in out   # the same roll, not a reroll
    assert not (camp / "combat" / "pending.json").exists()


def test_reactions_setting_and_status_reminders(camp, capsys):
    begin(capsys)
    _edit(camp, pos={"frog-1": (10, 6)})
    code, out = run(capsys, "reactions", "kairos", "off")
    assert code == 0 and "spell reactions off" in out
    code, out = run(capsys, "ready", "kairos", "cast", "fire", "bolt", "--target", "frog-1",
                    "--trigger", "a frog leaves the water")
    assert code == 0 and "trigger kairos" in out
    code, out = run(capsys, "status")
    assert "concentrating: Fire Bolt (readied)" in out
    assert "Kairos readied Fire Bolt at frog-1 when a frog leaves the water (trigger kairos)." in out


def test_the_mephit_demo_shows_spells_and_a_breath_weapon(camp, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("tactics_demo_m", ROOT / "scripts" / "tactics" / "demo.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    res = demo.play(camp, seed=2, scenario="mephit")
    out = capsys.readouterr().out
    assert res["ok"] and "$ combat.py cast kairos \"fire bolt\" mephit-1" in out
    assert "Frost Breath: 15 ft cone" in out and "preview-area" in out


def test_an_up_front_react_does_not_shift_onto_the_next_question(camp, capsys, monkeypatch):
    import random as _random
    begin(capsys)
    _edit(camp, actor="frog-1", pos={"frog-1": (2, 6)})
    hit = next(s for s in range(500) if 9 <= _random.Random(s).randint(1, 20) <= 16)
    monkeypatch.setattr(cli.random, "randrange", lambda n: hit)
    code, out = run(capsys, "attack", "frog-1", "kairos", "--react", "yes")
    assert code == 2 and "Silvery Barbs" in out
    code, out = run(capsys, "attack", "frog-1", "kairos", "--react", "yes", "--react", "no",
                    "--react", "no")
    assert "casts Silvery Barbs" not in out


def test_multiattack_takes_the_players_reaction_answers(camp, capsys, monkeypatch):
    import random as _random
    begin(capsys)
    path = _edit(camp, actor="frog-1", pos={"frog-1": (2, 6)})
    enc = json.loads(path.read_text(encoding="utf-8"))
    enc["tokens"]["frog-1"]["extra"]["actions"].append(
        {"name": "Multiattack", "kind": "multiattack", "flags": [],
         "multiattack": [[{"action": "Bite", "count": 1}]]})
    path.write_text(json.dumps(enc), encoding="utf-8")
    hit = next(s for s in range(500) if 9 <= _random.Random(s).randint(1, 20) <= 16)
    monkeypatch.setattr(cli.random, "randrange", lambda n: hit)
    code, out = run(capsys, "multiattack", "frog-1", "kairos")
    assert code == 2 and "Silvery Barbs" in out
    answers = ["--react", "no"]
    for _ in range(4):                      # Silvery Barbs, then Shield: one answer each
        code, out = run(capsys, "multiattack", "frog-1", "kairos", *answers)
        if code != 2:
            break
        answers += ["--react", "no"]
    assert code == 0 and "Multiattack (Bite)" in out, out


def test_removing_a_condition_ends_the_effect_behind_it(camp, capsys):
    begin(capsys)
    path = _edit(camp, pos={"frog-1": (2, 6)})
    enc = json.loads(path.read_text(encoding="utf-8"))
    enc["tokens"]["kairos"]["conditions"] = ["grappled", "restrained"]
    enc["tokens"]["kairos"]["effects"] = [{"name": "grapple", "source": "frog-1",
                                           "grapple": {"escape_dc": 11},
                                           "conditions": ["grappled", "restrained"],
                                           "granted": ["grappled", "restrained"]}]
    path.write_text(json.dumps(enc), encoding="utf-8")
    code, out = run(capsys, "condition", "kairos", "remove", "grappled")
    assert code == 0 and "ends grapple" in out
    code, out = run(capsys, "status")
    assert "grappled" not in out and "restrained" not in out
