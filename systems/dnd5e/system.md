# System Module — D&D 5e

This file is loaded alongside `SKILL.md` at session start. It defines the mechanical rules, character structure, and dice conventions for D&D 5th Edition. Everything here is specific to 5e — generic GM principles are in `SKILL.md`.

---

## Dice Convention

- Most checks, attacks, and saves: `d20 + ability modifier + proficiency bonus (if applicable)` vs a Difficulty Class (DC) or Armor Class (AC)
- Damage: dice expression defined per weapon/spell (e.g. `1d8+3 slashing`)
- Advantage: roll `d20` twice, take higher — `dice.py d20 adv`
- Disadvantage: roll `d20` twice, take lower — `dice.py d20 dis`
- Critical hit on natural 20: double all damage dice

Example inline combat narration:
`Goblin attacks Aldric: d20+4 = 17 vs AC 16 — hit! 1d6+2 = 5 piercing damage`

---

## Ability Scores

Six scores: **STR, DEX, CON, INT, WIS, CHA**

Modifier = `floor((score - 10) / 2)`. Ranges: score 1 = −5, score 10/11 = +0, score 20 = +5.

Proficiency bonus by level: +2 (1–4), +3 (5–8), +4 (9–12), +5 (13–16), +6 (17–20).

**Generation scripts:**
```bash
python3 systems/dnd5e/ability-scores.py roll                       # 3 arrays of 4d6kh3
python3 systems/dnd5e/ability-scores.py pointbuy                   # show 27-point cost table
python3 systems/dnd5e/ability-scores.py pointbuy --check STR=15 DEX=10 CON=14 INT=8 WIS=12 CHA=13
python3 systems/dnd5e/ability-scores.py modifiers STR=15 DEX=10 CON=14 INT=8 WIS=12 CHA=13
```

---

## Character Structure

Key fields on every character sheet:

| Field | Notes |
|-------|-------|
| Race / Class / Level | Class determines hit die, features, spell progression |
| HP / Max HP / Temp HP | Hit die = class die (d6–d12) + CON mod per level |
| AC | Armor + DEX mod (if applicable) + shield + magic |
| Proficiency Bonus | See table above |
| Saving Throws | Proficiency in two saves per class |
| Spell Slots | Levels 1–9; used and max tracked per level |
| Hit Dice | Remaining / max; spent on short rest for HP recovery |
| Second Wind | Fighter feature; tracked boolean |
| Death Saves | 3 successes = stable; 3 failures = dead |
| Conditions | See conditions list below |
| Concentration | One sustained spell at a time |
| Inventory | Items, currency, attunement slots |
| XP | Current / threshold for next level |

**Character scripts:**
```bash
python3 systems/dnd5e/character.py calc --class fighter --level 1 \
    STR=15 DEX=10 CON=14 INT=9 WIS=11 CHA=13 \
    --proficient STR CON Athletics Intimidation

python3 systems/dnd5e/character.py levelup --class fighter --from 1 --hp-roll 7 --con-mod 2
python3 systems/dnd5e/character.py xp --level 1 --gained 150
```

---

## XP Thresholds

| Level | XP | Level | XP |
|-------|----|-------|----|
| 2 | 300 | 11 | 85,000 |
| 3 | 900 | 12 | 100,000 |
| 4 | 2,700 | 13 | 120,000 |
| 5 | 6,500 | 14 | 140,000 |
| 6 | 14,000 | 15 | 165,000 |
| 7 | 23,000 | 16 | 195,000 |
| 8 | 34,000 | 17 | 225,000 |
| 9 | 48,000 | 18 | 265,000 |
| 10 | 64,000 | 19 | 305,000 |
|    |        | 20 | 355,000 |

---

## Rests

**Short rest (1 hour):** Spend any number of Hit Dice; roll each + CON mod → recover that much HP. Second Wind and some class features recharge. Advance time: `calendar.py rest short`

**Long rest (8 hours):** Restore all HP, restore half max Hit Dice (round up), restore all spell slots, restore most features. Advance time: `calendar.py rest long`. Clear tracker state: `tracker.py clear --all`

---

## Death Saves

At 0 HP a PC is unconscious and must roll death saves at the start of each turn (`d20`, no modifiers):
- **10+:** success (3 = stable)
- **9 or lower:** failure (3 = dead)
- **Natural 20:** regain 1 HP, regain consciousness
- **Natural 1:** counts as 2 failures

Track via `tracker.py saves <name> success/failure/stable/reset`

---

## Conditions

| Condition | Severity |
|-----------|----------|
| Unconscious, Paralyzed, Petrified, Stunned | Critical (red) |
| Incapacitated, Frightened, Poisoned, Charmed, Exhausted | Warning (amber) |
| Grappled, Restrained, Prone, Blinded, Deafened | Info (blue) |
| Invisible | Buff (green) |

Apply via `tracker.py condition add <name> <condition>` or `send.py --stat-condition-add`.

---

## Inspiration

Award Inspiration immediately when a player makes a bold roleplay choice, acts on their character's flaws/bonds, or does something that elevates the scene. Say why, then move on. A character can hold only one Inspiration — they lose it if they haven't used it when the next one would be awarded.

---

## SRD Data Lookup

The bundled dataset covers 1,453 records: spells, equipment, magic items, conditions, monsters, class features.

```bash
python3 systems/dnd5e/lookup.py spell "fireball"
python3 systems/dnd5e/lookup.py item "cloak of protection"
python3 systems/dnd5e/lookup.py feature "sneak attack"
python3 systems/dnd5e/lookup.py condition "poisoned"
python3 systems/dnd5e/lookup.py monster "goblin"
python3 systems/dnd5e/lookup.py monster "dragon" --all
```

Sync dataset from upstream sources when needed:
```bash
python3 systems/dnd5e/sync_srd.py           # rebuild if upstream has new commits
python3 systems/dnd5e/sync_srd.py --force   # always rebuild
python3 systems/dnd5e/build_srd.py --status # show current dataset metadata
```

---

## Bold Play Reward

Award **Inspiration** — `push_stats.py --player <name> --inspiration true` if tracking on display.
