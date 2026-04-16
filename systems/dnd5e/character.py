#!/usr/bin/env python3
"""
character.py — D&D 5e character stat calculator

Derives all secondary stats from raw inputs. Used by the DM (Claude)
to verify and generate character sheets without manual arithmetic.

Usage:
    python3 character.py calc --class fighter --level 1 \\
        STR=15 DEX=10 CON=15 INT=9 WIS=11 CHA=14 \\
        --proficient STR CON Athletics Intimidation Perception Survival

    python3 character.py levelup --class fighter --from 1 --to 2 \\
        --hp-roll 6 --con-mod 2

    python3 character.py xp --level 1 --gained 150
        Print XP total and whether level-up threshold is reached.
"""

import sys
import re


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
    scores = parse_scores(args)
    proficient = parse_proficient(args)  # list of stat names + skill names

    prof = PROF_BONUS.get(lvl, 2)
    hd = HIT_DICE.get(cls, 8)
    con_mod = mod(scores.get("CON", 10))
    hp = hd + con_mod  # level 1 max
    save_profs = SAVE_PROFS.get(cls, [])

    print(f"\n{'='*50}")
    print(f"  {cls.title()} Level {lvl}  |  Proficiency Bonus: +{prof}")
    print(f"{'='*50}")

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
