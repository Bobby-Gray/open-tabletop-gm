#!/usr/bin/env python3
"""
xp.py — D&D 5e XP calculation and award.

Codifies the full D&D 5e encounter XP tables (difficulty thresholds per level,
CR → XP, monster count multipliers, level advancement). Reads campaign character
files, updates XP, and pushes to the display sidebar.

Usage:
    # Preview calculation (no file changes):
    python3 systems/dnd5e/xp.py calc --level 3 --players 2 --difficulty hard --type combat
    python3 systems/dnd5e/xp.py calc --level 3 --players 2 --monsters "goblin:1/4:3,orc:1/2:2"

    # Award after a combat encounter — difficulty-rated:
    python3 systems/dnd5e/xp.py award \\
        --campaign my-campaign --characters "Aldric,Vesper" --difficulty hard --type combat

    # Award after a combat encounter — exact CR calculation (preferred):
    python3 systems/dnd5e/xp.py award \\
        --campaign my-campaign --characters "Aldric,Vesper" \\
        --monsters "goblin:1/4:3,orc:1/2:2"

    # Award for a qualifying non-combat encounter:
    python3 systems/dnd5e/xp.py award \\
        --campaign my-campaign --characters "Aldric,Vesper" \\
        --difficulty medium --type noncombat
"""

import sys
import re
import json
import datetime
import argparse
import subprocess
import pathlib

# ── Difficulty thresholds — XP per character per level (Easy/Medium/Hard/Deadly) ──
# Source: D&D 5e DMG encounter difficulty table.
# Both combat and non-combat encounters use this table; the GM rates the difficulty.
XP_THRESHOLDS: dict[int, tuple[int, int, int, int]] = {
    1:  (25,    50,    75,    100),
    2:  (50,    100,   150,   200),
    3:  (75,    150,   225,   400),
    4:  (125,   250,   375,   500),
    5:  (250,   500,   750,   1100),
    6:  (300,   600,   900,   1400),
    7:  (350,   750,   1100,  1700),
    8:  (450,   900,   1400,  2100),
    9:  (550,   1100,  1600,  2400),
    10: (600,   1200,  1900,  2800),
    11: (800,   1600,  2400,  3600),
    12: (1000,  2000,  3000,  4500),
    13: (1100,  2200,  3400,  5100),
    14: (1250,  2500,  3800,  5700),
    15: (1400,  2800,  4300,  6400),
    16: (1600,  3200,  4800,  7200),
    17: (2000,  3900,  5900,  8800),
    18: (2100,  4200,  6300,  9500),
    19: (2400,  4900,  7300,  10900),
    20: (2800,  5700,  8500,  12700),
}

# ── XP by CR ─────────────────────────────────────────────────────────────────
CR_XP: dict[str, int] = {
    "0":   10,    "1/8": 25,    "1/4": 50,    "1/2": 100,
    "1":   200,   "2":   450,   "3":   700,   "4":   1100,
    "5":   1800,  "6":   2300,  "7":   2900,  "8":   3900,
    "9":   4700,  "10":  5900,  "11":  7200,  "12":  8400,
    "13":  10000, "14":  11500, "15":  13000, "16":  15000,
    "17":  18000, "18":  20000, "19":  22000, "20":  25000,
    "21":  33000, "22":  41000, "23":  50000, "24":  62000,
    "25":  75000, "26":  90000, "27":  105000,"28":  120000,
    "29":  135000,"30":  155000,
}

# ── Monster count → XP multiplier ─────────────────────────────────────────────
# Applied to total monster XP to reflect action economy advantage of groups.
MONSTER_MULTIPLIERS: list[tuple[int, float]] = [
    (1,   1.0),
    (2,   1.5),
    (6,   2.0),
    (10,  2.5),
    (14,  3.0),
    (999, 4.0),
]

# ── Total XP required to reach each level ────────────────────────────────────
LEVEL_XP: dict[int, int] = {
    1: 0,       2: 300,    3: 900,    4: 2700,   5: 6500,
    6: 14000,   7: 23000,  8: 34000,  9: 48000,  10: 64000,
    11: 85000,  12: 100000,13: 120000,14: 140000, 15: 165000,
    16: 195000, 17: 225000,18: 265000,19: 305000, 20: 355000,
}

DIFF_IDX: dict[str, int] = {"easy": 0, "medium": 1, "hard": 2, "deadly": 3}

# ── Path resolution ───────────────────────────────────────────────────────────
# Script lives at <skill-base>/systems/dnd5e/xp.py
_SKILL_BASE   = pathlib.Path(__file__).parent.parent.parent
CAMPAIGNS_DIR = pathlib.Path("~/open-tabletop-gm/campaigns").expanduser()
DISPLAY_SCRIPT = _SKILL_BASE / "display" / "push_stats.py"


# ── Table helpers ─────────────────────────────────────────────────────────────

def _normalise_cr(s: str) -> str:
    s = s.strip()
    try:
        f = float(s)
        if abs(f - 0.125) < 0.001: return "1/8"
        if abs(f - 0.25)  < 0.001: return "1/4"
        if abs(f - 0.5)   < 0.001: return "1/2"
        return str(int(round(f)))
    except ValueError:
        pass
    return s


def _monster_multiplier(count: int) -> float:
    for threshold, mult in MONSTER_MULTIPLIERS:
        if count <= threshold:
            return mult
    return 4.0


def _parse_monsters(s: str) -> list[tuple[str, str, int]]:
    result = []
    for entry in s.split(","):
        parts = [p.strip() for p in entry.strip().split(":")]
        if len(parts) == 2:
            name, cr_raw, count = parts[0], parts[1], 1
        elif len(parts) == 3:
            name, cr_raw, count = parts[0], parts[1], int(parts[2])
        else:
            print(f"  Warning: skipping malformed entry '{entry.strip()}'", file=sys.stderr)
            continue
        cr_key = _normalise_cr(cr_raw)
        if cr_key not in CR_XP:
            print(f"  Warning: unknown CR '{cr_raw}' for '{name}' — skipping", file=sys.stderr)
            continue
        result.append((name, cr_key, count))
    return result


def _calc_monster_xp(monsters: list[tuple[str, str, int]]) -> tuple[int, float, int]:
    raw  = sum(CR_XP[cr] * cnt for _, cr, cnt in monsters)
    n    = sum(cnt for _, _, cnt in monsters)
    mult = _monster_multiplier(n)
    return raw, mult, int(raw * mult)


def _classify(adj_per_player: int, level: int) -> str:
    t = XP_THRESHOLDS.get(level, XP_THRESHOLDS[20])
    if adj_per_player >= t[3]: return "deadly"
    if adj_per_player >= t[2]: return "hard"
    if adj_per_player >= t[1]: return "medium"
    if adj_per_player >= t[0]: return "easy"
    return "trivial"


def _xp_per_player(difficulty: str, level: int) -> int:
    t   = XP_THRESHOLDS.get(level, XP_THRESHOLDS[20])
    idx = DIFF_IDX.get(difficulty.lower(), 1)
    return t[idx]


def _next_level_xp(level: int) -> int:
    return LEVEL_XP.get(level + 1, 999_999_999)


# ── Character file I/O ────────────────────────────────────────────────────────

def _find_char_path(campaign: str, name: str) -> pathlib.Path:
    char_dir = CAMPAIGNS_DIR / campaign / "characters"
    exact = char_dir / f"{name.lower()}.md"
    if exact.exists():
        return exact
    if char_dir.exists():
        for p in char_dir.glob("*.md"):
            if p.stem.lower() == name.lower():
                return p
    raise FileNotFoundError(
        f"Character file not found for '{name}' in campaign '{campaign}'.\n"
        f"  Expected: {char_dir / (name.lower() + '.md')}"
    )


def _read_char(path: pathlib.Path) -> tuple[int, int]:
    """Returns (current_xp, level)."""
    text    = path.read_text(encoding="utf-8")
    xp_m    = re.search(r"\*\*XP:\*\*\s*(\d+)", text)
    level_m = re.search(r"\*\*Level:\*\*\s*(\d+)", text)
    return (int(xp_m.group(1)) if xp_m else 0,
            int(level_m.group(1)) if level_m else 1)


def _write_xp(path: pathlib.Path, new_xp: int, current_level: int) -> bool:
    """Update XP field; return True if level-up threshold crossed."""
    text     = path.read_text(encoding="utf-8")
    next_lvl = _next_level_xp(current_level)
    leveled  = new_xp >= next_lvl

    if leveled:
        new_next    = _next_level_xp(current_level + 1)
        replacement = f"**XP:** {new_xp} / {new_next} ⚠ LEVEL UP PENDING (Level {current_level + 1})"
    else:
        replacement = f"**XP:** {new_xp} / {next_lvl}"

    # subn, not sub. `updated == text` cannot tell "the regex did not match"
    # from "it matched and the rendered value did not change", and the second
    # is every award that leaves the total where it was. The substitution COUNT
    # is the only thing that answers "did the field exist", which is what a
    # warning here is actually about.
    #
    # The digits before the slash are optional because a fresh template sheet
    # holds "**XP:** / 2700". Requiring them meant the very first award against
    # a new character silently did nothing: re.sub returned the text unchanged,
    # it was written straight back, and the award was gone with no signal.
    updated, hits = re.subn(
        r"\*\*XP:\*\*\s*(?:\d+)?\s*/\s*\d+[^\n|]*", replacement, text, count=1
    )
    if hits == 0:
        print(
            f"xp.py: warning — no XP field found in {path.name}; "
            f"{new_xp} XP was NOT written",
            file=sys.stderr,
        )
    path.write_text(updated, encoding="utf-8")
    return leveled


def _push_display(name: str, new_xp: int, current_level: int) -> None:
    if not DISPLAY_SCRIPT.exists():
        return
    subprocess.run(
        [sys.executable, str(DISPLAY_SCRIPT),
         "--player", name, "--xp", str(new_xp), str(_next_level_xp(current_level))],
        capture_output=True,
    )


# ── Subcommands ───────────────────────────────────────────────────────────────

def cmd_calc(args: argparse.Namespace) -> None:
    level, players = args.level, args.players

    if args.monsters:
        monsters = _parse_monsters(args.monsters)
        if not monsters:
            print("No valid monsters parsed.", file=sys.stderr); sys.exit(1)
        raw, mult, adj = _calc_monster_xp(monsters)
        n          = sum(c for _, _, c in monsters)
        per_player = adj // players
        diff       = _classify(per_player, level)

        print(f"\n  Combat — CR-based ({n} monsters, ×{mult})")
        for name, cr, count in monsters:
            print(f"    {count}× {name} (CR {cr}): {CR_XP[cr] * count:,} XP")
        print(f"\n  Raw {raw:,} × {mult} = Adjusted {adj:,}")
        print(f"  Difficulty:  {diff.upper()}  (Level {level} party of {players})")
        print(f"  Per player:  {per_player:,} XP")

    elif args.difficulty:
        per_player = _xp_per_player(args.difficulty, level)
        enc_type   = (args.type or "combat").upper()
        print(f"\n  {args.difficulty.upper()} {enc_type} — Level {level} party of {players}")
        print(f"  Per player:  {per_player:,} XP  |  Total: {per_player * players:,} XP")

    else:
        print("Provide --difficulty or --monsters.", file=sys.stderr); sys.exit(1)


# ─── Award ledger ─────────────────────────────────────────────────────────────
#
# An award used to leave no trace except a number on a sheet. So when one did
# not happen — the GM moved to the next scene without running this, or the
# write was silently discarded — there was nothing to compare against and no
# way to find out except a player noticing weeks later that their total had not
# moved, by which point the encounters that should have fed it are gone.
#
# The ledger is append-only and additive: a new file per campaign, no existing
# format changed. `xp.py check` reconciles it against the sheets.

LEDGER_NAME = "xp-ledger.jsonl"


def _ledger_path(campaign: str) -> pathlib.Path:
    return CAMPAIGNS_DIR / campaign / LEDGER_NAME


def _record_award(campaign: str, entries: list, note: str) -> None:
    """Append one line per character. Never raises — a ledger write must not
    cost a player their XP, which is already written by the time we get here."""
    try:
        path = _ledger_path(campaign)
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds")
        with open(path, "a", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps({
                    "at": stamp,
                    "character": e["name"],
                    "awarded": e["awarded"],
                    "total_after": e["total_after"],
                    "note": note,
                }, ensure_ascii=False) + "\n")
    except Exception as exc:                      # noqa: BLE001
        print(f"xp.py: warning — could not write the award ledger: {exc}",
              file=sys.stderr)


def _read_ledger(campaign: str) -> list:
    path = _ledger_path(campaign)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue                              # a torn line is not fatal
    return rows


def cmd_check(args: argparse.Namespace) -> None:
    """Reconcile the ledger against the sheets and report drift.

    This does NOT fill gaps. It answers "did every award we recorded actually
    land", which is the question nobody could ask before. Filling
    automatically would need to know which encounters happened, and nothing in
    the campaign format records that yet.
    """
    campaign = args.campaign
    rows = _read_ledger(campaign)
    if not rows:
        print(f"  No award ledger for '{campaign}' yet "
              f"({_ledger_path(campaign)}).")
        print("  It starts filling from the next `xp.py award`.")
        return

    by_char = {}
    for r in rows:
        by_char.setdefault(r.get("character", "?"), []).append(r)

    print(f"\n  XP ledger — {campaign}  ({len(rows)} awards recorded)\n")
    drift = 0
    for name, entries in sorted(by_char.items()):
        last = entries[-1]
        expected = last.get("total_after")
        try:
            actual, _level = _read_char(_find_char_path(campaign, name))
        except (FileNotFoundError, ValueError):
            print(f"    {name:<16} ledger says {expected}, no character file")
            drift += 1
            continue
        if expected is not None and actual != expected:
            # A sheet BELOW the ledger is the silent-discard case. A sheet
            # ABOVE it just means XP was awarded some other way, which is
            # normal and worth showing rather than flagging.
            marker = "  ← sheet is BEHIND the ledger" if actual < expected else ""
            print(f"    {name:<16} sheet {actual:<7} ledger {expected:<7}{marker}")
            if actual < expected:
                drift += 1
        else:
            print(f"    {name:<16} sheet {actual:<7} matches")
    print()
    if drift:
        print(f"  {drift} character(s) hold less XP than the ledger recorded.")
        print("  Re-run the missing award, or correct the sheet by hand.")
        sys.exit(1)
    print("  Every recorded award is reflected on its sheet.")


def cmd_award(args: argparse.Namespace) -> None:
    campaign   = args.campaign
    char_names = [c.strip() for c in args.characters.split(",")]
    enc_type   = (args.type or ("combat" if args.monsters else "noncombat")).lower()

    chars = []
    for name in char_names:
        try:
            path = _find_char_path(campaign, name)
        except FileNotFoundError as e:
            print(f"  Error: {e}", file=sys.stderr); sys.exit(1)
        xp, level = _read_char(path)
        chars.append({"name": name, "xp": xp, "level": level, "path": path})

    avg_level  = round(sum(c["level"] for c in chars) / len(chars))
    players    = len(chars)

    if args.monsters:
        monsters   = _parse_monsters(args.monsters)
        if not monsters:
            print("No valid monsters parsed.", file=sys.stderr); sys.exit(1)
        raw, mult, adj = _calc_monster_xp(monsters)
        n          = sum(c for _, _, c in monsters)
        per_player = adj // players
        diff       = _classify(per_player, avg_level)

        print(f"\n  Combat — CR-based  [{n} monsters, ×{mult}]")
        for name, cr, count in monsters:
            print(f"    {count}× {name} (CR {cr}): {CR_XP[cr] * count:,} XP")
        print(f"  Raw {raw:,} × {mult} = Adjusted {adj:,} | {diff.upper()} | Per player: {per_player:,} XP")

    else:
        if not args.difficulty:
            print("Provide --difficulty or --monsters.", file=sys.stderr); sys.exit(1)
        diff       = args.difficulty.lower()
        per_player = _xp_per_player(diff, avg_level)
        type_label = f" [{enc_type}]" if enc_type == "noncombat" else ""
        print(f"\n  {diff.upper()} {enc_type.upper()}{type_label} — Level {avg_level} party of {players}")
        print(f"  Per player: {per_player:,} XP")

    print()
    any_levelup = False
    _ledger_entries = []
    for c in chars:
        new_xp  = c["xp"] + per_player
        leveled = _write_xp(c["path"], new_xp, c["level"])
        _push_display(c["name"], new_xp, c["level"])
        _ledger_entries.append({"name": c["name"], "awarded": per_player,
                                "total_after": new_xp})

        next_lvl  = _next_level_xp(c["level"])
        remaining = max(0, next_lvl - new_xp)
        rem_note  = "" if leveled else f"  ({remaining:,} to Level {c['level'] + 1})"
        up_tag    = f"  ⚠ LEVEL {c['level'] + 1} UP!" if leveled else ""
        print(f"  {c['name']}: {c['xp']:,} + {per_player:,} = {new_xp:,} / {next_lvl:,}{rem_note}{up_tag}")
        if leveled:
            any_levelup = True

    if any_levelup:
        print("\n  Level-up pending — run /gm character level-up")


# ── Entry point ───────────────────────────────────────────────────────────────

    # Recorded AFTER the sheets are written, so the ledger never claims an
    # award that did not land.
    _record_award(campaign, _ledger_entries, note=f"{diff} {enc_type}")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="D&D 5e XP calculation and award.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    calc_p = sub.add_parser("calc", help="Preview XP — no files modified")
    calc_p.add_argument("--level",      type=int, default=1,  metavar="N")
    calc_p.add_argument("--players",    type=int, default=4,  metavar="N")
    calc_p.add_argument("--difficulty", choices=["easy", "medium", "hard", "deadly"])
    calc_p.add_argument("--type",       choices=["combat", "noncombat"], default="combat")
    calc_p.add_argument("--monsters",   metavar="LIST",
                        help="name:cr:count,... e.g. 'goblin:1/4:3,orc:1/2:2'")

    award_p = sub.add_parser("award", help="Award XP — updates character files and display")
    award_p.add_argument("--campaign",   required=True, metavar="NAME")
    award_p.add_argument("--characters", required=True, metavar="NAMES",
                         help="Comma-separated names matching campaign character files")
    award_p.add_argument("--difficulty", choices=["easy", "medium", "hard", "deadly"])
    award_p.add_argument("--type",       choices=["combat", "noncombat"])
    award_p.add_argument("--monsters",   metavar="LIST",
                         help="name:cr:count,... for exact CR-based calculation")

    check_p = sub.add_parser(
        "check", help="Reconcile the award ledger against the character sheets")
    check_p.add_argument("--campaign", required=True, metavar="NAME")

    args = parser.parse_args()
    if   args.command == "calc":  cmd_calc(args)
    elif args.command == "award": cmd_award(args)
    elif args.command == "check": cmd_check(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
