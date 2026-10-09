#!/usr/bin/env python3
"""
character.py — D&D 5e character stat calculator

Derives all secondary stats from raw inputs. Used by the GM agent
to verify and generate character sheets without manual arithmetic.

Usage:
    python3 character.py calc --class fighter --level 1 \\
        STR=15 DEX=10 CON=15 INT=9 WIS=11 CHA=14 \\
        --proficient STR CON Athletics Intimidation Perception Survival

    python3 character.py calc --class cleric --level 1 --race dwarf \\
        --subrace hill-dwarf STR=15 DEX=10 CON=14 INT=9 WIS=13 CHA=11
        Scores given are the BASE array; racial bonuses are applied here and
        shown as base / race / final. An unknown race exits non-zero rather
        than applying nothing.

    python3 character.py levelup --class fighter --from 1 --to 2 \\
        --hp-roll 6 --con-mod 2

    python3 character.py xp --level 1 --gained 150
        Print XP total and whether level-up threshold is reached.
"""

import sys
import re


# ─── Racial ability bonuses (SRD, 2014 rules) ────────────────────────────────
#
# THESE ARE APPLIED HERE, NOT REMEMBERED. The character-creation flow used to
# say "Apply racial bonuses" and then "run character.py calc" -- but calc had no
# `--race` parameter at all, so it never saw the race and could not check the
# step had happened. A Dwarf and an Elf built the same way came out with the
# same Constitution, and nothing in the toolchain could notice.
#
# Keyed by SRD index (lower-case, hyphenated), which is what `lookup.py race`
# reports, so the two agree by construction. Reconciled against the built SRD
# dataset by tests/test_racial_bonuses.py -- a drifted value fails there rather
# than silently producing a wrong sheet.
RACE_BONUSES = {
    "dwarf":      {"CON": 2},
    "elf":        {"DEX": 2},
    "halfling":   {"DEX": 2},
    "human":      {"STR": 1, "DEX": 1, "CON": 1, "INT": 1, "WIS": 1, "CHA": 1},
    "dragonborn": {"STR": 2, "CHA": 1},
    "gnome":      {"INT": 2},
    "half-elf":   {"CHA": 2},
    "half-orc":   {"STR": 2, "CON": 1},
    "tiefling":   {"INT": 1, "CHA": 2},
}

#: Subrace bonuses STACK on top of the parent race's. Half-Elf is the SRD's
#: one irregular case -- it grants +1 to two abilities of the player's choice
#: on top of its +2 CHA, which no table can express, so it is passed through
#: as a prompt rather than a number (see apply_racial_bonuses).
SUBRACE_BONUSES = {
    "hill-dwarf":         {"WIS": 1},
    "high-elf":           {"INT": 1},
    "lightfoot-halfling": {"CHA": 1},
    "rock-gnome":         {"CON": 1},
}

SUBRACE_PARENT = {
    "hill-dwarf": "dwarf", "high-elf": "elf",
    "lightfoot-halfling": "halfling", "rock-gnome": "gnome",
}

#: Races whose SRD entry grants a player CHOICE the tables above cannot hold.
#: Reported so the sheet writer is told to resolve it, instead of the choice
#: being silently dropped.
RACE_CHOICES = {
    "half-elf": "+1 to two abilities of your choice (SRD Half-Elf)",
}


def _race_key(name: str) -> str:
    """Normalise a race or subrace name to its SRD index."""
    return re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")


def apply_racial_bonuses(scores: dict, race: str = "", subrace: str = "") -> tuple:
    """Return (final_scores, applied, notes).

    `applied` maps stat -> total bonus added, so the caller can show base,
    racial and final rather than only the result. An unknown race RAISES: a
    typo that silently applied nothing is the whole defect this exists to
    stop, and a sheet that is quietly wrong is worse than a command that
    refuses.
    """
    out = dict(scores)
    applied: dict = {}
    notes: list = []
    if not race and not subrace:
        return out, applied, notes

    rkey = _race_key(race)
    skey = _race_key(subrace)

    if skey:
        if skey not in SUBRACE_BONUSES:
            raise ValueError(
                f"Unknown subrace {subrace!r}. Known: "
                f"{', '.join(sorted(SUBRACE_BONUSES))}")
        parent = SUBRACE_PARENT[skey]
        if rkey and rkey != parent:
            raise ValueError(
                f"Subrace {subrace!r} belongs to {parent!r}, not {race!r}")
        rkey = parent

    if rkey not in RACE_BONUSES:
        raise ValueError(
            f"Unknown race {race!r}. Known: {', '.join(sorted(RACE_BONUSES))}")

    for stat, bonus in RACE_BONUSES[rkey].items():
        applied[stat] = applied.get(stat, 0) + bonus
    if skey:
        for stat, bonus in SUBRACE_BONUSES[skey].items():
            applied[stat] = applied.get(stat, 0) + bonus

    for stat, bonus in applied.items():
        out[stat] = out.get(stat, 10) + bonus
    if rkey in RACE_CHOICES:
        notes.append(RACE_CHOICES[rkey])
    return out, applied, notes


# ─── Proficiency bonus by level ──────────────────────────────────────────────
PROF_BONUS = {1:2, 2:2, 3:2, 4:2, 5:3, 6:3, 7:3, 8:3,
              9:4, 10:4, 11:4, 12:4, 13:5, 14:5, 15:5, 16:5,
              17:6, 18:6, 19:6, 20:6}

# ─── XP thresholds (total XP needed to reach level) ─────────────────────────
XP_THRESHOLDS = {
    1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500, 6: 14000,
    7: 23000, 8: 34000, 9: 48000, 10: 64000, 11: 85000,
    12: 100000, 13: 120000, 14: 140000, 15: 165000,
    16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000,
}

# ─── Hit dice by class ───────────────────────────────────────────────────────
HIT_DICE = {
    "barbarian": 12, "fighter": 10, "paladin": 10, "ranger": 10,
    "bard": 8, "cleric": 8, "druid": 8, "monk": 8, "rogue": 8, "warlock": 8,
    "sorcerer": 6, "wizard": 6,
}

# ─── Saving throw proficiencies by class ─────────────────────────────────────
SAVE_PROFS = {
    "fighter":   ["STR", "CON"],
    "barbarian": ["STR", "CON"],
    "ranger":    ["STR", "DEX"],
    "paladin":   ["WIS", "CHA"],
    "rogue":     ["DEX", "INT"],
    "bard":      ["DEX", "CHA"],
    "cleric":    ["WIS", "CHA"],
    "druid":     ["INT", "WIS"],
    "monk":      ["STR", "DEX"],
    "warlock":   ["WIS", "CHA"],
    "sorcerer":  ["CON", "CHA"],
    "wizard":    ["INT", "WIS"],
}

# ─── All skills with governing ability ───────────────────────────────────────
SKILLS = {
    "Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT",
    "Athletics": "STR", "Deception": "CHA", "History": "INT",
    "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT",
    "Medicine": "WIS", "Nature": "INT", "Perception": "WIS",
    "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT",
    "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS",
}

STATS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]


def mod(score: int) -> int:
    return (score - 10) // 2


def fmt(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def parse_scores(args: list[str]) -> dict[str, int]:
    scores = {}
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            if k.upper() in STATS:
                scores[k.upper()] = int(v)
    return scores


def parse_proficient(args: list[str]) -> list[str]:
    """Everything after --proficient until next -- flag."""
    if "--proficient" not in args:
        return []
    idx = args.index("--proficient")
    profs = []
    for a in args[idx + 1:]:
        if a.startswith("--"):
            break
        profs.append(a)
    return profs


def do_calc(args: list[str]):
    cls = args[args.index("--class") + 1].lower() if "--class" in args else "fighter"
    lvl = int(args[args.index("--level") + 1]) if "--level" in args else 1
    base_scores = parse_scores(args)
    proficient = parse_proficient(args)  # list of stat names + skill names
    race = args[args.index("--race") + 1] if "--race" in args else ""
    subrace = args[args.index("--subrace") + 1] if "--subrace" in args else ""

    # The scores passed in are the BASE array, before racial bonuses. Applying
    # them here is what makes the step verifiable: an unknown race raises
    # rather than applying nothing.
    try:
        scores, racial, race_notes = apply_racial_bonuses(base_scores, race, subrace)
    except ValueError as exc:
        print(f"character.py: {exc}", file=sys.stderr)
        sys.exit(2)

    prof = PROF_BONUS.get(lvl, 2)
    hd = HIT_DICE.get(cls, 8)
    con_mod = mod(scores.get("CON", 10))
    hp = hd + con_mod  # level 1 max
    save_profs = SAVE_PROFS.get(cls, [])

    print(f"\n{'='*50}")
    print(f"  {cls.title()} Level {lvl}  |  Proficiency Bonus: +{prof}")
    print(f"{'='*50}")

    if racial:
        label = (subrace or race).strip()
        print(f"\n  Ability Scores  (base + {label} racial bonus):")
        print(f"  {'Stat':<6} {'Base':>6} {'Race':>6} {'Score':>6} {'Mod':>5}")
        print(f"  {'-'*33}")
        for s in STATS:
            base = base_scores.get(s, 10)
            bonus = racial.get(s, 0)
            score = scores.get(s, 10)
            print(f"  {s:<6} {base:>6} {fmt(bonus) if bonus else '—':>6} "
                  f"{score:>6} {fmt(mod(score)):>5}")
        for note in race_notes:
            print(f"\n  ! Still to assign: {note}")
    else:
        print(f"\n  Ability Scores:")
        print(f"  {'Stat':<6} {'Score':>6} {'Mod':>5}")
        print(f"  {'-'*20}")
        for s in STATS:
            score = scores.get(s, 10)
            print(f"  {s:<6} {score:>6} {fmt(mod(score)):>5}")

    print(f"\n  Combat Stats:")
    print(f"  HP (level 1): {hp}  ({hd} + CON {fmt(con_mod)})")
    print(f"  Hit Dice: {lvl}d{hd}")
    print(f"  Initiative: {fmt(mod(scores.get('DEX', 10)))}")

    print(f"\n  Saving Throws (* = proficient):")
    for s in STATS:
        score = scores.get(s, 10)
        is_prof = s in save_profs or s in proficient
        bonus = mod(score) + (prof if is_prof else 0)
        marker = "*" if is_prof else " "
        print(f"  {marker} {s:<4} {fmt(bonus)}")

    print(f"\n  Skills (* = proficient):")
    for skill, ability in sorted(SKILLS.items()):
        score = scores.get(ability, 10)
        is_prof = skill in proficient or skill.lower() in [p.lower() for p in proficient]
        bonus = mod(score) + (prof if is_prof else 0)
        marker = "*" if is_prof else " "
        print(f"  {marker} {skill:<22} ({ability})  {fmt(bonus)}")

    print(f"\n  XP to next level: {XP_THRESHOLDS.get(lvl+1, 'MAX')} total")
    print()


def do_levelup(args: list[str]):
    cls = args[args.index("--class") + 1].lower() if "--class" in args else "fighter"
    from_lvl = int(args[args.index("--from") + 1]) if "--from" in args else 1
    to_lvl = from_lvl + 1
    hp_roll = int(args[args.index("--hp-roll") + 1]) if "--hp-roll" in args else None
    con_mod_val = int(args[args.index("--con-mod") + 1]) if "--con-mod" in args else 0

    hd = HIT_DICE.get(cls, 8)
    prof_old = PROF_BONUS.get(from_lvl, 2)
    prof_new = PROF_BONUS.get(to_lvl, 2)

    print(f"\n  Level Up: {cls.title()} {from_lvl} → {to_lvl}")
    print(f"  Proficiency bonus: +{prof_old} → +{prof_new}")

    if hp_roll is not None:
        hp_gained = hp_roll + con_mod_val
        print(f"  HP gained: d{hd}({hp_roll}) + CON({fmt(con_mod_val)}) = {hp_gained}")
    else:
        avg = (hd // 2 + 1) + con_mod_val
        print(f"  HP gained (avg): {avg}  ({hd//2+1} + CON {fmt(con_mod_val)})")

    print(f"  XP threshold for level {to_lvl}: {XP_THRESHOLDS.get(to_lvl, 'MAX')}")
    print()


def do_xp(args: list[str]):
    lvl = int(args[args.index("--level") + 1]) if "--level" in args else 1
    gained = int(args[args.index("--gained") + 1]) if "--gained" in args else 0
    current = XP_THRESHOLDS.get(lvl, 0)
    next_lvl = XP_THRESHOLDS.get(lvl + 1)
    new_total = current + gained

    print(f"\n  XP: {current} + {gained} gained = {new_total}")
    if next_lvl:
        if new_total >= next_lvl:
            print(f"  *** Level up available! Reached {next_lvl} (Level {lvl+1} threshold) ***")
        else:
            print(f"  Next level ({lvl+1}) at: {next_lvl}  ({next_lvl - new_total} XP remaining)")
    else:
        print("  Maximum level reached.")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "calc":
        do_calc(args)
    elif cmd == "levelup":
        do_levelup(args)
    elif cmd == "xp":
        do_xp(args)
    else:
        print(f"Unknown command: {cmd}. Use: calc | levelup | xp")
        sys.exit(1)
