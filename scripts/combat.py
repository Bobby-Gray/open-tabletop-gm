#!/usr/bin/env python3
"""
combat.py — D&D 5e combat tracker

Usage:
    python3 combat.py init <combatants_json>
        Rolls initiative for all combatants and prints turn order.
        combatants_json: JSON array of {"name": str, "dex_mod": int, "hp": int, "ac": int, "type": "pc"|"npc"}

    python3 combat.py tracker <state_json>
        Prints the current combat tracker table from a JSON state blob.

    python3 combat.py attack --atk <bonus> --ac <target_ac> --dmg <notation> [--crit]
        Resolves a single attack roll and damage.

Input / Output is JSON-friendly so the DM (Claude) can pipe state between turns.

Example:
    python3 combat.py init '[{"name":"Flerb","dex_mod":0,"hp":12,"ac":16,"type":"pc"},
                              {"name":"Goblin","dex_mod":1,"hp":7,"ac":15,"type":"npc"}]'
"""

import json
import random
import sys
import re


def roll(n, sides):
    return [random.randint(1, sides) for _ in range(n)]


def dice(notation: str) -> tuple[int, list[int]]:
    """Parse NdS+M notation, return (total, individual_rolls)."""
    m = re.match(r'^(\d*)d(\d+)([+-]\d+)?$', notation.strip().lower())
    if not m:
        raise ValueError(f"Bad dice notation: {notation}")
    n = int(m.group(1)) if m.group(1) else 1
    s = int(m.group(2))
    mod = int(m.group(3)) if m.group(3) else 0
    rolls = roll(n, s)
    return sum(rolls) + mod, rolls


def initiative_order(combatants: list[dict]) -> list[dict]:
    """Roll d20+dex_mod for each combatant, sort descending."""
    for c in combatants:
        raw = random.randint(1, 20)
        c["initiative_roll"] = raw
        c["initiative"] = raw + c.get("dex_mod", 0)
        c["conditions"] = []
        c["temp_hp"] = 0
    return sorted(combatants, key=lambda x: (x["initiative"], x.get("dex_mod", 0)), reverse=True)


def print_tracker(combatants: list[dict], round_num: int = 1):
    print(f"\n{'='*68}")
    print(f"  COMBAT — Round {round_num}")
    print(f"{'='*68}")
    print(f"  {'#':<3} {'Name':<18} {'Init':>5} {'HP':>8} {'AC':>4}  Conditions")
    print(f"  {'-'*62}")
    for i, c in enumerate(combatants, 1):
        hp_str = f"{c['hp']}/{c.get('max_hp', c['hp'])}"
        cond = ", ".join(c.get("conditions", [])) or "—"
        marker = "► " if i == 1 else "  "
        print(f"  {marker}{i:<2} {c['name']:<18} {c['initiative']:>5} {hp_str:>8} {c['ac']:>4}  {cond}")
    print(f"{'='*68}\n")


def resolve_attack(atk_bonus: int, target_ac: int, dmg_notation: str, is_crit: bool = False) -> dict:
    raw = random.randint(1, 20)
    total_atk = raw + atk_bonus
    hit = raw == 20 or (raw != 1 and total_atk >= target_ac)
    crit = raw == 20

    result = {
        "d20": raw,
        "attack_bonus": atk_bonus,
        "total": total_atk,
        "target_ac": target_ac,
        "hit": hit,
        "crit": crit,
        "fumble": raw == 1,
    }

    if hit:
        dmg, rolls = dice(dmg_notation)
        if crit:
            # Double the dice rolls on crit
            extra, extra_rolls = dice(dmg_notation.split("+")[0].split("-")[0])
            dmg += extra
            rolls += extra_rolls
        result["damage"] = dmg
        result["damage_rolls"] = rolls
        result["damage_notation"] = dmg_notation

    return result


def format_attack(r: dict) -> str:
    lines = []
    flag = ""
    if r["crit"]:
        flag = " *** CRITICAL HIT! ***"
    elif r["fumble"]:
        flag = " *** FUMBLE — automatic miss ***"

    atk_str = f"d20({r['d20']}) + {r['attack_bonus']} = {r['total']} vs AC {r['target_ac']}"
    outcome = "HIT" if r["hit"] else "MISS"
    lines.append(f"Attack: {atk_str} — {outcome}{flag}")

    if r.get("damage") is not None:
        note = " (crit: doubled dice)" if r["crit"] else ""
        lines.append(f"Damage: {r['damage_rolls']} + mod = {r['damage']} {r['damage_notation'].split('+')[0].split('-')[0][1:]}dmg{note}")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        combatants = json.loads(sys.argv[2])
        # Store max_hp
        for c in combatants:
            c["max_hp"] = c["hp"]
        ordered = initiative_order(combatants)
        print_tracker(ordered)
        print("Initiative rolls:")
        for c in ordered:
            print(f"  {c['name']}: d20({c['initiative_roll']}) + {c.get('dex_mod',0)} = {c['initiative']}")
        print()
        print("STATE_JSON:", json.dumps(ordered))

    elif cmd == "tracker":
        state = json.loads(sys.argv[2])
        round_num = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        print_tracker(state, round_num)

    elif cmd == "attack":
        args = sys.argv[2:]
        atk = int(args[args.index("--atk") + 1])
        ac = int(args[args.index("--ac") + 1])
        dmg = args[args.index("--dmg") + 1]
        crit = "--crit" in args
        result = resolve_attack(atk, ac, dmg, crit)
        print(format_attack(result))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
