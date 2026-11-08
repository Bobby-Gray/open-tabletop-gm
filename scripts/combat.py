#!/usr/bin/env python3
"""
combat.py — combat tracker (initiative, attack resolution)

Usage:
    python3 combat.py init <combatants_json> [-c CAMPAIGN | --system NAME]
        Orders all combatants by the system's initiative rule and prints turn
        order. combatants_json: JSON array of
        {"name": str, "hp": int, "ac": int, "type": "pc"|"npc", <stat>}
        where <stat> is the system's initiative statistic:
            dnd5e  "dex_mod"     d20 + DEX modifier
            pf2e   "perception"  d20 + Perception modifier; give a combatant
                                 "init_mod" (and "init_label") to roll another
                                 skill instead, e.g. Stealth for an ambusher
            brp    "dex"         no roll; DEX rank, highest first

    python3 combat.py tracker <state_json>
        Prints the current combat tracker table from a JSON state blob.

    python3 combat.py attack --atk <bonus> --ac <target_ac> --dmg <notation> [--crit]
                             [-c CAMPAIGN | --system NAME]
        Resolves a single attack roll and damage. --crit makes a hit a
        critical hit (an attack on a paralysed target from within reach, an
        expanded critical range the GM has already checked).

The system is read from `**System Module:**` in the campaign's state.md (the
resolution scripts/paths.py uses everywhere else), or given with --system. With
neither, it is dnd5e.

Input / Output is JSON-friendly so the GM agent can pipe state between turns.

Example:
    python3 combat.py init '[{"name":"Flerb","dex_mod":0,"hp":12,"ac":16,"type":"pc"},
                              {"name":"Goblin","dex_mod":1,"hp":7,"ac":15,"type":"npc"}]'
"""

import json
import re
import secrets
import sys

try:
    from paths import resolve_system
except ImportError:              # imported from outside scripts/
    def resolve_system(campaign="", override="", default="dnd5e"):
        return (override or default).strip().lower()

try:
    from dice import pf2e_degree, PF2E_DEGREES
except ImportError:
    import importlib.util as _ilu
    import pathlib as _pl
    _spec = _ilu.spec_from_file_location("dice", _pl.Path(__file__).with_name("dice.py"))
    _dice = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_dice)
    pf2e_degree, PF2E_DEGREES = _dice.pf2e_degree, _dice.PF2E_DEGREES


def _d(sides: int) -> int:
    # secrets, like the display's own roller: game dice should not come from a
    # seedable, predictable generator.
    return secrets.randbelow(sides) + 1


def roll(n, sides):
    return [_d(sides) for _ in range(n)]


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


# ── Per-system initiative ─────────────────────────────────────────────────────
#
# One row per system module. Supporting a new system's initiative is adding a
# row here; nothing below branches on a system name except through this table
# and ATTACK_RESOLVERS.
#
#   die       sides of the initiative die, or None when the order is a straight
#             ranking by the stat with no roll (BRP: DEX rank)
#   stat      the combatant JSON key added to the die, or ranked by
#   label     how the stat is named in the printout ("" prints the bare number)
#   ties      how equal results are ordered:
#               "stat"        higher stat first, then input order
#               "foes_first"  anything that is not a PC goes before a PC
#               "pcs_first"   PCs go before anything that is not a PC
#               "none"        input order (simultaneous, or the GM's call)
#   choose    True when the rules let the GM roll a different statistic for a
#             particular combatant, carried as "init_mod" / "init_label"
#   required  True to refuse a combatant with no `stat` rather than treat it as 0
INITIATIVE = {
    "dnd5e": {"die": 20, "stat": "dex_mod", "label": "", "ties": "stat",
              "choose": False, "required": False},
    "pf2e":  {"die": 20, "stat": "perception", "label": "Perception",
              "ties": "foes_first", "choose": True, "required": True},
    "brp":   {"die": None, "stat": "dex", "label": "DEX", "ties": "none",
              "choose": False, "required": True},
}


class CombatError(Exception):
    """A request this system's rules cannot answer. Printed; exit 2."""


def _rules(system: str) -> dict:
    if system not in INITIATIVE:
        known = ", ".join(sorted(INITIATIVE))
        raise CombatError(
            f"no initiative rule for system '{system}' (known: {known}). Add a "
            f"row to INITIATIVE in scripts/combat.py, or pass --system dnd5e "
            f"to force d20 + DEX.")
    return INITIATIVE[system]


def _init_stat(c: dict, rules: dict) -> tuple:
    """Return (modifier or rank, label) for one combatant."""
    if rules["choose"] and "init_mod" in c:
        return int(c["init_mod"]), str(c.get("init_label") or "")
    if rules["required"] and rules["stat"] not in c:
        hint = ' (or "init_mod" to roll another statistic)' if rules["choose"] else ""
        raise CombatError(
            f"'{c.get('name', '?')}' has no \"{rules['stat']}\" — initiative in "
            f"this system uses {rules['label'] or rules['stat']}{hint}")
    return c.get(rules["stat"], 0), rules["label"]


def initiative_order(combatants: list[dict], system: str = "dnd5e") -> list[dict]:
    """Order combatants by the system's initiative rule, first to act first."""
    rules = _rules(system)
    for c in combatants:
        value, label = _init_stat(c, rules)
        if rules["die"]:
            raw = _d(rules["die"])
            c["initiative_roll"] = raw
            c["initiative"] = raw + value
        else:
            c["initiative_roll"] = None
            c["initiative"] = value
        if label:
            c["initiative_label"] = label
        c["conditions"] = []
        c["temp_hp"] = 0

    ties = rules["ties"]
    if ties == "stat":
        key = lambda x: (x["initiative"], x.get(rules["stat"], 0))
    elif ties == "foes_first":
        key = lambda x: (x["initiative"], x.get("type") != "pc")
    elif ties == "pcs_first":
        key = lambda x: (x["initiative"], x.get("type") == "pc")
    else:
        key = lambda x: x["initiative"]
    # sorted() stays stable under reverse=True, so "none" keeps input order.
    return sorted(combatants, key=key, reverse=True)


def format_initiative_line(c: dict, system: str = "dnd5e") -> str:
    rules = _rules(system)
    label = c.get("initiative_label", "")
    if not rules["die"]:
        lead = f"{label} " if label else ""
        return f"  {c['name']}: {lead}{c['initiative']}"
    mod = c["initiative"] - c["initiative_roll"]
    if not label:
        # The pre-table D&D 5e line, unchanged.
        return f"  {c['name']}: d{rules['die']}({c['initiative_roll']}) + {mod} = {c['initiative']}"
    return f"  {c['name']}: d{rules['die']}({c['initiative_roll']}) + {mod} {label} = {c['initiative']}"


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
        print(f"  {marker}{i:<2} {c['name']:<18} {c['initiative']:>5} {hp_str:>8} {c.get('ac', '—'):>4}  {cond}")
    print(f"{'='*68}\n")


# ── Per-system attack resolution ──────────────────────────────────────────────

def resolve_attack(atk_bonus: int, target_ac: int, dmg_notation: str, is_crit: bool = False) -> dict:
    """D&D 5e: a natural 20 always hits and crits, a natural 1 always misses.

    `is_crit` makes any hit a critical hit — the rule for an attack on a
    paralysed or unconscious target from within 5 feet. It cannot turn a miss
    into a hit.
    """
    raw = _d(20)
    total_atk = raw + atk_bonus
    hit = raw == 20 or (raw != 1 and total_atk >= target_ac)
    crit = raw == 20 or (is_crit and hit)

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


def resolve_attack_pf2e(atk_bonus: int, target_ac: int, dmg_notation: str,
                        is_crit: bool = False) -> dict:
    """PF2e Strike: four degrees of success against AC.

    Beat AC by 10 for a critical hit; a natural 20 or 1 then moves the degree
    one step. A critical hit doubles the damage, modifiers included. `is_crit`
    upgrades a hit to a critical hit. The multiple attack penalty is folded
    into --atk by the caller.
    """
    raw = _d(20)
    total = raw + atk_bonus
    degree = pf2e_degree(raw, total, target_ac)
    if is_crit and degree == 2:
        degree = 3
    result = {
        "d20": raw,
        "attack_bonus": atk_bonus,
        "total": total,
        "target_ac": target_ac,
        "degree": degree,
        "hit": degree >= 2,
        "crit": degree == 3,
        "fumble": False,
    }
    if degree >= 2:
        dmg, rolls = dice(dmg_notation)
        result["damage_rolled"] = dmg
        result["damage"] = dmg * 2 if degree == 3 else dmg
        result["damage_rolls"] = rolls
        result["damage_notation"] = dmg_notation
    return result


def format_attack_pf2e(r: dict) -> str:
    shift = ""
    if r["d20"] == 20:
        shift = " (natural 20: one step better)"
    elif r["d20"] == 1:
        shift = " (natural 1: one step worse)"
    lines = [f"Strike: d20({r['d20']}) + {r['attack_bonus']} = {r['total']} vs AC "
             f"{r['target_ac']} — {PF2E_DEGREES[r['degree']]}{shift}"]
    if r.get("damage") is not None:
        if r["crit"]:
            lines.append(f"Damage: {r['damage_rolls']} + mod = {r['damage_rolled']} "
                         f"x2 = {r['damage']} (critical hit: double damage)")
        else:
            lines.append(f"Damage: {r['damage_rolls']} + mod = {r['damage']}")
    return "\n".join(lines)


# system -> (resolver, formatter). A system with no row has no d20-against-AC
# attack (BRP rolls a percentile skill against a defence), and `attack` says so
# rather than applying another system's arithmetic.
ATTACK_RESOLVERS = {
    "dnd5e": (resolve_attack, format_attack),
    "pf2e":  (resolve_attack_pf2e, format_attack_pf2e),
}


def attack(system: str, atk_bonus: int, target_ac: int, dmg_notation: str,
           is_crit: bool = False) -> str:
    if system not in ATTACK_RESOLVERS:
        known = ", ".join(sorted(ATTACK_RESOLVERS))
        raise CombatError(
            f"`attack` has no resolver for system '{system}' (known: {known}). "
            f"Resolve the attack as systems/{system}/system.md describes, "
            f"rolling with dice.py.")
    resolver, formatter = ATTACK_RESOLVERS[system]
    return formatter(resolver(atk_bonus, target_ac, dmg_notation, is_crit))


def _split_system_flags(argv: list) -> tuple:
    """Pull -c/--campaign and --system out of argv wherever they appear."""
    rest, campaign, system = [], "", ""
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-c", "--campaign", "--system") and i + 1 < len(argv):
            if a == "--system":
                system = argv[i + 1]
            else:
                campaign = argv[i + 1]
            i += 2
            continue
        rest.append(a)
        i += 1
    return rest, campaign, system


def main(argv: list) -> int:
    argv, campaign, override = _split_system_flags(argv)
    if len(argv) < 1:
        print(__doc__)
        return 1

    system = resolve_system(campaign, override)
    cmd = argv[0]

    try:
        if cmd == "init":
            combatants = json.loads(argv[1])
            # Store max_hp
            for c in combatants:
                c["max_hp"] = c["hp"]
            ordered = initiative_order(combatants, system)
            print_tracker(ordered)
            print("Initiative rolls:" if _rules(system)["die"] else "Initiative order:")
            for c in ordered:
                print(format_initiative_line(c, system))
            print()
            print("STATE_JSON:", json.dumps(ordered))

        elif cmd == "tracker":
            state = json.loads(argv[1])
            round_num = int(argv[2]) if len(argv) > 2 else 1
            print_tracker(state, round_num)

        elif cmd == "attack":
            args = argv[1:]
            atk = int(args[args.index("--atk") + 1])
            ac = int(args[args.index("--ac") + 1])
            dmg = args[args.index("--dmg") + 1]
            crit = "--crit" in args
            print(attack(system, atk, ac, dmg, crit))

        else:
            print(f"Unknown command: {cmd}")
            return 1
    except CombatError as e:
        print(f"combat.py: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
