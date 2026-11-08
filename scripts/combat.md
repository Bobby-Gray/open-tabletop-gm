# Scripts — Combat

Read this file before: `/gm combat start`, processing any combat turn, or applying conditions/death saves.

**Skill base:** `<skill-base>`

---

## Dice — `scripts/dice.py`

```bash
SKILL=<skill-base>

python3 $SKILL/scripts/dice.py d20+5
python3 $SKILL/scripts/dice.py 2d6+3
python3 $SKILL/scripts/dice.py 4d6kh3        # keep highest 3 of 4d6
python3 $SKILL/scripts/dice.py d20 adv       # advantage
python3 $SKILL/scripts/dice.py d20+3 dis     # disadvantage + modifier
python3 $SKILL/scripts/dice.py d20 --silent  # integer only
```

Say what the d20 is for with `--vs check|save|attack`, and optionally `--dc N`
(the AC, for an attack). A natural 20 or 1 is labelled only where the campaign's
system gives it a meaning: in D&D 5e that is attack rolls only (a critical hit,
an automatic miss); in PF2e any check, as a one-step shift in the degree of
success, which `--dc` resolves to all four degrees; in Cities Without Number
saves only (a natural 20 always succeeds, a natural 1 always fails — attacks
have no natural rule). Without `--vs` nothing is labelled — a natural 20 on an
ability check is not a critical hit. The system comes from `-c <campaign>` (its
`**System Module:**`) or `--system <name>`. A multi-die roll resolves against
`--dc` too, which is how a 2d6 skill check is rolled.

```bash
python3 $SKILL/scripts/dice.py d20+6 --vs attack --dc 15 -c $CAMP
python3 $SKILL/scripts/dice.py d20+4 --vs save --dc 18 --system pf2e
python3 $SKILL/scripts/dice.py 2d6+1 --dc 8                      # cwn skill check
python3 $SKILL/scripts/dice.py d20 --vs save --dc 14 --system cwn
```

---

## Combat — `scripts/combat.py`

```bash
SKILL=<skill-base>
CAMP=<campaign-name>

# Order the combatants and print the tracker
python3 $SKILL/scripts/combat.py init '<JSON>' -c $CAMP

# Reprint tracker from saved state
python3 $SKILL/scripts/combat.py tracker '<JSON>' <round_num>

# Resolve a single attack (--crit: a hit is a critical hit)
python3 $SKILL/scripts/combat.py attack --atk 10 --ac 20 --dmg 2d6+5 -c $CAMP
```

`init` outputs a `STATE_JSON:` line — store in `state.md → ## Active Combat` between turns.

**The rules follow the campaign's system.** `-c <campaign>` reads `**System Module:**`
from its `state.md`; `--system <name>` overrides it; with neither, the rules are
D&D 5e. Each system's initiative stat goes in the combatant JSON under its own key:

| System | Initiative | JSON key | Ties | `attack` |
|--------|------------|----------|------|----------|
| `dnd5e` | d20 + DEX modifier | `dex_mod` | higher DEX modifier first | natural 20 hits and crits (dice doubled), natural 1 misses |
| `pf2e` | d20 + Perception modifier | `perception` | foes before PCs | four degrees: beat AC by 10 to crit, natural 20/1 shift one step; a crit doubles all damage |
| `brp` | no roll — DEX rank, highest first | `dex` | listed order (GM's call) | not supported — resolve the percentile attack and defence per `systems/brp/system.md` |
| `cwn` | 1d8 + DEX modifier (individual initiative) | `dex_mod` (NPCs may omit it) | PCs before foes | d20 + bonus vs AC, no natural rule and no crit; `--trauma <die>/x<rating> --tt N` rolls the Trauma Die on a hit, `--shock <pts>/<ac>` applies Shock on a miss |

- **PF2e:** a scene can call for a different initiative skill for one combatant
  (Stealth for an ambusher, Deception for a bluff). Give that combatant
  `"init_mod": <modifier>, "init_label": "Stealth"` and it rolls that instead of
  Perception. Fold the multiple attack penalty (−5 / −10, or −4 / −8 agile)
  into `--atk` yourself.
- **BRP:** `ac` is optional in the JSON (the tracker shows `—`); armour reduces
  damage in this system rather than being a target number.
- **Cities Without Number:** the rules' default is one initiative roll per
  SIDE (1d8 + the side's best DEX modifier); `init` rolls the optional
  individual form. For side initiative roll `dice.py 1d8+<best mod>` once per
  side instead. Pass the target's Ranged or Melee AC to `--ac` as the attack
  requires. Without `--trauma`, a hit prints a reminder to roll the weapon's
  Trauma Die against the target's Trauma Target by hand. `--crit` makes a hit
  Traumatic (an Execution Attack) and needs `--trauma`; `--trauma`, `--tt` and
  `--shock` are refused for any other system.
- **Any other system:** `init` and `attack` refuse with a message rather than
  apply another system's arithmetic. Add a row to `INITIATIVE` (and, for a
  d20-against-AC system, `ATTACK_RESOLVERS`) in `scripts/combat.py`, or run
  with `--system dnd5e` to accept d20 + DEX deliberately.

---

## Tracker — `scripts/tracker.py`

```bash
SKILL=<skill-base>
CAMP=<campaign-name>

# Timed effects (duration: 10r rounds, 60m minutes, 8h hours, indef)
python3 $SKILL/scripts/tracker.py -c $CAMP effect start "NAME" "Effect" 10r conc
python3 $SKILL/scripts/tracker.py -c $CAMP effect start "NAME" "Effect" indef
python3 $SKILL/scripts/tracker.py -c $CAMP effect end   "NAME" "Effect"
python3 $SKILL/scripts/tracker.py -c $CAMP effect tick  "NAME"   # call on actor's turn
python3 $SKILL/scripts/tracker.py -c $CAMP effect advance 30m     # in-game time passed outside the calendar

# Conditions
python3 $SKILL/scripts/tracker.py -c $CAMP condition add    "NAME" Frightened
python3 $SKILL/scripts/tracker.py -c $CAMP condition remove "NAME" Frightened
python3 $SKILL/scripts/tracker.py -c $CAMP condition clear  "NAME"

# Concentration
python3 $SKILL/scripts/tracker.py -c $CAMP concentrate "NAME" "Spell"
python3 $SKILL/scripts/tracker.py -c $CAMP concentrate "NAME" break

# Death saves
python3 $SKILL/scripts/tracker.py -c $CAMP saves "NAME" success
python3 $SKILL/scripts/tracker.py -c $CAMP saves "NAME" failure
python3 $SKILL/scripts/tracker.py -c $CAMP saves "NAME" stable
python3 $SKILL/scripts/tracker.py -c $CAMP saves "NAME" reset

# Status / clear
python3 $SKILL/scripts/tracker.py -c $CAMP status
python3 $SKILL/scripts/tracker.py -c $CAMP clear        # end of encounter: conditions + round effects
python3 $SKILL/scripts/tracker.py -c $CAMP clear --all  # everything, death saves included
```

**When to run:** condition applied/removed; concentration begins/breaks; PC drops to 0 HP; each death save; end of encounter → `clear`.

**Durations are in-game time.** A `60m` or `8h` effect counts down only when
the story spends time: `calendar.py advance` and `calendar.py rest` advance it
automatically (a long rest also ends concentration), and `effect advance <time>`
covers time the calendar does not track. `clear` ends round-measured effects
with the fight and leaves minute/hour effects running. Do **not** run `clear`
for a rest — conditions with their own cure, and death saves, are not erased by
sleeping.

---

## Display updates during combat (from startup.md)

```bash
SKILL=<skill-base>

# Combat start — push turn order
python3 $SKILL/display/push_stats.py \
  --turn-order '[{"name":"NAME","initiative":N,"type":"pc"}]' \
  --turn-current "NAME" --turn-round 1

# Advance turn
python3 $SKILL/display/push_stats.py --turn-current "NEXT_NAME"

# New round
python3 $SKILL/display/push_stats.py --turn-current "NAME" --turn-round N

# HP change
python3 $SKILL/display/push_stats.py --player NAME --hp <current> <max>

# Combat ended
python3 $SKILL/display/push_stats.py --turn-clear
```
