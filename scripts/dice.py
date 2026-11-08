#!/usr/bin/env python3
"""
dice.py — dice roller

Usage:
    python3 dice.py <notation> [--silent] [--vs check|save|attack] [--dc N]
                    [-c CAMPAIGN | --system NAME]

Notation supported:
    d20               single d20
    2d6               2 six-sided dice, sum
    d20+5             roll + flat modifier
    4d6kh3            roll 4d6, keep highest 3 (ability score generation)
    4d6kl3            roll 4d6, keep lowest 3
    d20 adv           advantage: roll twice, take higher
    d20 dis           disadvantage: roll twice, take lower
    d20+3 adv         advantage with modifier
    2d6+3             multiple dice + modifier

Options:
    --vs check|save|attack   what the d20 is for. Natural 20 / natural 1 are
                             labelled only where the active system gives them
                             a meaning for that kind of roll (D&D 5e: attacks
                             only; PF2e: any check, as a one-step shift in the
                             degree of success; cwn: saves only, where a
                             natural 20 always succeeds and a natural 1
                             always fails). Without --vs nothing is
                             labelled, because a natural 20 on an ability
                             check is not a critical hit.
    --dc N                   resolve against a DC (or AC, with --vs attack;
                             a save target, with --vs save). Multi-die rolls
                             such as a 2d6 skill check resolve against it too
    -c, --campaign NAME      read the system from the campaign's state.md
    --system NAME            override the system (dnd5e, pf2e, brp, ...)

Output (unless --silent):
    Rolls: [x, x, x]  →  Total: N
    For advantage/disadvantage, shows both rolls and which was taken.
"""

import re
import secrets
import sys

try:
    from paths import resolve_system
except ImportError:              # imported from outside scripts/
    def resolve_system(campaign="", override="", default="dnd5e"):
        return (override or default).strip().lower()


def parse_notation(notation: str):
    """Parse dice notation string. Returns (num_dice, die_size, modifier, keep_mode, keep_count)."""
    notation = notation.strip().lower()

    # Strip advantage/disadvantage suffix
    adv = "adv" in notation or "advantage" in notation
    dis = "dis" in notation or "disadvantage" in notation
    notation = re.sub(r'\s*(adv|dis|advantage|disadvantage)\w*', '', notation).strip()

    # Match: [N]d[S][kh/kl N][+/-M]
    pattern = r'^(\d*)d(\d+)(?:(kh|kl)(\d+))?([+-]\d+)?$'
    m = re.match(pattern, notation.replace(' ', ''))
    if not m:
        raise ValueError(f"Cannot parse dice notation: '{notation}'")

    num_dice = int(m.group(1)) if m.group(1) else 1
    die_size = int(m.group(2))
    keep_mode = m.group(3)       # 'kh' or 'kl' or None
    keep_count = int(m.group(4)) if m.group(4) else None
    modifier = int(m.group(5)) if m.group(5) else 0

    return num_dice, die_size, modifier, keep_mode, keep_count, adv, dis


def roll_dice(num_dice, die_size):
    # secrets, like the display's own roller: game dice should not come from a
    # seedable, predictable generator.
    return [secrets.randbelow(die_size) + 1 for _ in range(num_dice)]


# ── What a natural 20 / natural 1 means, per system ──────────────────────────

VS_KINDS = ("check", "save", "attack")

PF2E_DEGREES = ("CRITICAL FAILURE", "FAILURE", "SUCCESS", "CRITICAL SUCCESS")


def pf2e_degree(natural: int, total: int, dc: int) -> int:
    """PF2e degree of success, 0 (critical failure) .. 3 (critical success).

    Beat the DC by 10 for a critical success, miss it by 10 for a critical
    failure; a natural 20 then moves the result one step up and a natural 1
    one step down. Applies to every check, save and attack in that system.
    """
    if total >= dc + 10:
        degree = 3
    elif total >= dc:
        degree = 2
    elif total <= dc - 10:
        degree = 0
    else:
        degree = 1
    if natural == 20:
        degree = min(3, degree + 1)
    elif natural == 1:
        degree = max(0, degree - 1)
    return degree


# What a natural 20 / natural 1 means on a single d20, per system:
#   "attack_crit"  natural 20 on an ATTACK is a critical hit, natural 1 an
#                  automatic miss; on checks and saves a natural means nothing
#   "degrees"      every check, save and attack has four degrees of success,
#                  and a natural 20 / 1 moves the degree one step
#   "save_auto"    a natural 20 on a SAVE always succeeds and a natural 1
#                  always fails; attacks and checks have no natural rule
# A system with no row gets no natural-number label at all — a DC still
# resolves to success or failure. Supporting a system is adding a row.
NATURAL_RULES = {
    "dnd5e": "attack_crit",
    "pf2e": "degrees",
    "cwn": "save_auto",
}


def d20_verdict(natural: int, total: int, vs: str = "", dc=None,
                system: str = "dnd5e") -> str:
    """Return the label for a single kept d20, or "" when nothing applies."""
    rule = NATURAL_RULES.get(system)
    if rule == "attack_crit":
        if vs == "attack":
            if natural == 20:
                return "  *** CRITICAL HIT (nat 20)! ***"
            if natural == 1:
                return "  *** AUTOMATIC MISS (nat 1) ***"
            if dc is not None:
                return f"  vs AC {dc} — {'HIT' if total >= dc else 'MISS'}"
            return ""
    elif rule == "save_auto" and vs == "save":
        if dc is not None:
            if natural in (1, 20):
                ok = natural == 20
                return (f"  vs save {dc} — {'SUCCESS' if ok else 'FAILURE'} "
                        f"(natural {natural}: always {'succeeds' if ok else 'fails'})")
            return f"  vs save {dc} — {'SUCCESS' if total >= dc else 'FAILURE'}"
        if natural == 20:
            return "  (natural 20: the save succeeds)"
        if natural == 1:
            return "  (natural 1: the save fails)"
        return ""
    elif rule == "save_auto" and vs == "attack":
        # No natural rule on an attack: total against AC and nothing else.
        if dc is not None:
            return f"  vs AC {dc} — {'HIT' if total >= dc else 'MISS'}"
        return ""
    elif rule == "degrees" and vs:
        if dc is not None:
            degree = pf2e_degree(natural, total, dc)
            what = "AC" if vs == "attack" else "DC"
            shift = ""
            if natural == 20:
                shift = " (natural 20: one step better)"
            elif natural == 1:
                shift = " (natural 1: one step worse)"
            return f"  vs {what} {dc} — {PF2E_DEGREES[degree]}{shift}"
        if natural == 20:
            return "  (natural 20: one degree of success better)"
        if natural == 1:
            return "  (natural 1: one degree of success worse)"
        return ""
    if dc is not None:
        return f"  vs DC {dc} — {'SUCCESS' if total >= dc else 'FAILURE'}"
    return ""


def _dc_verdict(total: int, dc) -> str:
    """A multi-die roll against --dc: a 2d6 skill check, or 3d6kh2. No
    natural-number rule applies to these in any bundled system."""
    if dc is None:
        return ""
    return f"  vs DC {dc} — {'SUCCESS' if total >= dc else 'FAILURE'}"


def format_modifier(mod):
    if mod == 0:
        return ""
    return f" + {mod}" if mod > 0 else f" - {abs(mod)}"


def run(notation: str, silent: bool = False, vs: str = "", dc=None,
        system: str = "dnd5e") -> int:
    num_dice, die_size, modifier, keep_mode, keep_count, adv, dis = parse_notation(notation)
    single_d20 = num_dice == 1 and die_size == 20

    # Advantage / disadvantage (only meaningful for single d20)
    if adv or dis:
        roll_a = roll_dice(num_dice, die_size)
        roll_b = roll_dice(num_dice, die_size)
        total_a = sum(roll_a) + modifier
        total_b = sum(roll_b) + modifier
        chosen = max(total_a, total_b) if adv else min(total_a, total_b)
        label = "ADV" if adv else "DIS"
        if not silent:
            print(f"[{label}] Roll A: {roll_a} = {total_a}{format_modifier(modifier)}")
            print(f"[{label}] Roll B: {roll_b} = {total_b}{format_modifier(modifier)}")
            taken = "A" if (adv and total_a >= total_b) or (dis and total_a <= total_b) else "B"
            flag = ""
            if single_d20:
                natural = (roll_a if taken == "A" else roll_b)[0]
                flag = d20_verdict(natural, chosen, vs, dc, system)
            print(f"Takes roll {taken} → Total: {chosen}{flag}")
        return chosen

    rolls = roll_dice(num_dice, die_size)

    # Keep highest / lowest
    if keep_mode and keep_count:
        sorted_rolls = sorted(rolls, reverse=(keep_mode == 'kh'))
        kept = sorted_rolls[:keep_count]
        dropped = sorted_rolls[keep_count:]
        result = sum(kept) + modifier
        if not silent:
            kept_str = " + ".join(str(r) for r in kept)
            drop_str = f"  (dropped: {dropped})" if dropped else ""
            mod_str = format_modifier(modifier)
            print(f"Rolls: {rolls}{drop_str}")
            print(f"Kept ({keep_mode}{keep_count}): [{kept_str}]{mod_str} = {result}"
                  f"{_dc_verdict(result, dc)}")
        return result

    result = sum(rolls) + modifier
    if not silent:
        if single_d20:
            raw = rolls[0]
            flag = d20_verdict(raw, result, vs, dc, system)
            mod_str = format_modifier(modifier)
            print(f"Roll: {raw}{mod_str} = {result}{flag}")
        else:
            mod_str = format_modifier(modifier)
            print(f"Rolls: {rolls}{mod_str} = {result}{_dc_verdict(result, dc)}")
    return result


def _parse_cli(argv: list) -> dict:
    """Split option flags from the notation, which may itself contain spaces."""
    opts = {"silent": False, "vs": "", "dc": None, "campaign": "", "system": ""}
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--silent":
            opts["silent"] = True
        elif a in ("--vs", "--dc", "-c", "--campaign", "--system"):
            if i + 1 >= len(argv):
                raise SystemExit(f"dice.py: {a} needs a value")
            val = argv[i + 1]
            i += 1
            if a == "--vs":
                if val.lower() not in VS_KINDS:
                    raise SystemExit(f"dice.py: --vs must be one of {', '.join(VS_KINDS)}")
                opts["vs"] = val.lower()
            elif a == "--dc":
                try:
                    opts["dc"] = int(val)
                except ValueError:
                    raise SystemExit(f"dice.py: --dc needs a number, got {val!r}")
            elif a in ("-c", "--campaign"):
                opts["campaign"] = val
            else:
                opts["system"] = val
        else:
            rest.append(a)
        i += 1
    opts["notation"] = " ".join(rest)
    return opts


if __name__ == "__main__":
    opts = _parse_cli(sys.argv[1:])

    if not opts["notation"]:
        print("Usage: python3 dice.py <notation>  e.g. d20+5  2d6  4d6kh3  d20 adv")
        sys.exit(1)

    system = resolve_system(opts["campaign"], opts["system"])
    result = run(opts["notation"], silent=opts["silent"], vs=opts["vs"],
                 dc=opts["dc"], system=system)
    if opts["silent"]:
        print(result)
