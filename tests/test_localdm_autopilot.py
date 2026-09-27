"""autopilot.py: the player's line to engine commands, and templated narration."""
from __future__ import annotations

import re
import sys

import pytest

from tests.localdm_fakes import FakeClient
from tests.tactics_fixtures import ROOT, RULES, _RAW, _build, encounter, frog, kairos, start
from localdm import autopilot, llm
from localdm.play import Session

NULLS = '\n{"escalate": null, "command": null}'


def two_frogs(k_pos=(0, 0), f1=(1, 0), f2=(5, 5), hp=8):
    enc = encounter([kairos(k_pos, hp=hp), frog("frog-1", f1, "Giant Frog 1"),
                     frog("frog-2", f2, "Giant Frog 2")])
    return start(enc, ["kairos", "frog-1", "frog-2"])


@pytest.mark.parametrize("line,cmds", [
    ("Fire Bolt on Giant Frog 2. Burn it.", [["attack", "kairos", "frog-2", "Fire Bolt"]]),
    ("I blast the second frog with fire bolt!", [["attack", "kairos", "frog-2", "Fire Bolt"]]),
    ("I throw my dagger at the frog.", [["attack", "kairos", "frog-1", "Dagger"]]),
    ("I attack the nearest one", [["attack", "kairos", "frog-1"]]),
    ("firebolt frog-2", [["attack", "kairos", "frog-2", "Fire Bolt"]]),
])
def test_attacks(line, cmds):
    assert autopilot.plan(line, two_frogs(), "kairos").cmds == cmds + [["end-turn"]]


def test_equal_targets_ask_which_one():
    p = autopilot.plan("I attack the frog", two_frogs(f1=(2, 0), f2=(0, 2)), "kairos")
    assert p.cmds == [] and p.ask.startswith("Which one? 1) Giant Frog")


def test_it_means_the_last_target():
    p = autopilot.plan("hit it again with fire bolt", two_frogs(), "kairos", last_target="frog-2")
    assert p.cmds[0] == ["attack", "kairos", "frog-2", "Fire Bolt"]


def test_talk_goes_to_the_model():
    assert autopilot.plan("Who sent you, frog?", two_frogs(), "kairos") is None


def test_a_move_keeps_the_turn_open():
    assert autopilot.plan("I move to C3", two_frogs(), "kairos").cmds == [["move", "kairos", "C3"]]


def test_backing_away_from_an_adjacent_foe_disengages_first():
    p = autopilot.plan("I back away from the frog", two_frogs(), "kairos")
    assert p.cmds[0] == ["disengage", "kairos"]
    assert p.cmds[1][0] == "move" and p.cmds[-1] == ["end-turn"]


def test_dodge_and_end_turn():
    assert autopilot.plan("I dodge", two_frogs(), "kairos").cmds == [["dodge", "kairos"], ["end-turn"]]
    assert autopilot.plan("end turn", two_frogs(), "kairos").cmds == [["end-turn"]]


def test_at_zero_hp_any_line_is_a_death_save_or_a_pass():
    enc = two_frogs(hp=0)
    enc.turn.pending = "death_save"
    assert autopilot.plan("I attack!", enc, "kairos").cmds == [["death-save", "kairos"]]
    enc.turn.pending = None                      # stable: nothing to roll
    assert autopilot.plan("I attack!", enc, "kairos").cmds == [["end-turn"]]
    enc.tokens["kairos"].dead = True
    assert autopilot.plan("I attack!", enc, "kairos").ask == "Kairos is dead."


# ── narration ───────────────────────────────────────────────────────────────

def test_a_hit_keeps_the_engines_numbers():
    s = autopilot.narrate("Kairos Fire Bolt -> Giant Frog 1: 23 vs AC 11, disadvantage, hit. "
                          "6 fire damage; Giant Frog 1 12/18 HP.", seed="1")
    assert "6 fire damage" in s and "Giant Frog 1" in s
    assert set(re.findall(r"\d+", s)) <= {"1", "6", "12", "18"}


def test_kill_miss_move_and_hints():
    text = ("1. Giant Frog 2 moves M11 to C6 (50 ft, 10 ft left).\nThen: end-turn\n"
            "Kairos Dagger -> Giant Frog 2: 5 vs AC 11, miss.\n"
            "Kairos Fire Bolt -> Giant Frog 1: 19 vs AC 11, hit (CRIT). 12 fire damage; "
            "Giant Frog 1 dies.\nRound 2. Kairos's turn.\nWaiting for Kairos.")
    s = autopilot.narrate(text, seed="x")
    assert "C6" in s and "12 fire damage" in s and "Then:" not in s and "Waiting" not in s
    assert autopilot.big_moment(text)
    assert not autopilot.big_moment("Kairos Dagger -> Giant Frog 2: 5 vs AC 11, miss.")


def test_opportunity_attack_multiword_name():
    raw = ("Opportunity attack: Giant Frog 1 Bite -> Kairos: 14 vs AC 12, hit. "
           "4 piercing damage; Kairos 8/12 HP.")
    s = autopilot.narrate(raw, seed="1", names=["Giant Frog 1", "Kairos"])
    assert "Giant Frog 1" in s and "Bite" in s and "Opportunity attack:" in s
    assert "Opportunity's attack" not in s


# ── the session, on the real engine ─────────────────────────────────────────

def test_engine_combat_needs_no_model_for_actions_or_enemies(tmp_path, monkeypatch):
    root = tmp_path / "root"
    camp = root / "campaigns" / "demo"
    (camp / "characters").mkdir(parents=True)
    (camp / "characters" / "Kairos.md").write_text(
        (ROOT / "tests" / "fixtures" / "Kairos_Level1.md").read_text(encoding="utf-8"),
        encoding="utf-8")
    (camp / "state.md").write_text("# Campaign: demo\n\n## Session Flags\nroll_mode: players\n"
                                   "council: off\n", encoding="utf-8")
    monkeypatch.setenv("GM_CAMPAIGN_ROOT", str(root))
    monkeypatch.setenv("TACTICS_NO_DISPLAY", "1")
    monkeypatch.setattr(sys.modules[type(RULES).__module__], "_lookup_monster",
                        lambda name: _build._norm_monster(_RAW[name.lower().replace(" ", "-")]))
    c = FakeClient(lambda m, msgs, role: "Wow." + NULLS)
    s = Session("demo", c, llm.Models("dm-local", "dm-advisor", "dm-council"),
                camp_dir=camp, combat="engine", flavor="off")
    s.handle('/c start frog-pond --pc Kairos@B7 --monster "giant frog@J5" --seed 3')
    said = []
    for _ in range(16):
        if s.bridge.snapshot()["status"] != "active":
            break
        said += s.handle("4" if s.pending else "Fire Bolt the frog!")
    assert any("Fire Bolt" in x for x in said)
    assert not {"enemy-pick", "dm"} & set(c.roles())


def test_the_enemy_menu_label_is_not_narrated():
    text = "Retreat to P2 [keep distance] [beast]. Giant Frog moves J5 to P2 (30 ft, 0 ft left)."
    out = autopilot.narrate(text, seed="1")
    assert "[" not in out and "keep distance" not in out and "P2" in out
    assert autopilot.narrate("Move to A12 and Bite Kairos (60% to hit, ~2.7 dmg) [beast].") == ""


def test_attack_and_step_back_runs_the_attack_first_then_the_move():
    p = autopilot.plan("I attack the frog with my dagger and try to step back", two_frogs(),
                       "kairos")
    kinds = [c[0] for c in p.cmds]
    assert kinds[0] == "attack" and "move" in kinds and "disengage" not in kinds
    assert kinds.index("attack") < kinds.index("move") and kinds[-1] == "end-turn"


def test_a_plain_retreat_still_disengages():
    p = autopilot.plan("I back away", two_frogs(), "kairos")
    assert [c[0] for c in p.cmds][:2] == ["disengage", "move"]


def test_a_multi_word_attacker_is_not_split():
    raw = "Giant Frog 2 Bite -> Kairos: 9 vs AC 12, miss."
    text = autopilot.narrate(raw, names=["Kairos", "Giant Frog 2"])
    assert "Giant Frog 2" in text and "Giant's" not in text and "Frog 2 Bite" not in text.replace(
        "Giant Frog 2's Bite", "")
