# Scripts — Character

Read this file before: `/gm character new`, `/gm character level-up`, or any system-specific stat calculation.

**Skill base:** `<skill-base>`

---

## Ability Scores — `systems/dnd5e/ability-scores.py`

```bash
SKILL=<skill-base>

# Random roll (4d6 drop lowest, six times)
python3 $SKILL/systems/dnd5e/ability-scores.py roll

# Validate a point-buy array
python3 $SKILL/systems/dnd5e/ability-scores.py pointbuy \
    --check STR=15 DEX=10 CON=15 INT=8 WIS=11 CHA=12
```

---

## Character Stats — `systems/dnd5e/character.py`

```bash
SKILL=<skill-base>

# Calculate full stat block at character creation
python3 $SKILL/systems/dnd5e/character.py calc \
    --class fighter --level 1 \
    STR=15 DEX=10 CON=15 INT=9 WIS=11 CHA=14 \
    --proficient STR CON Athletics Intimidation

# Level up
python3 $SKILL/systems/dnd5e/character.py levelup \
    --class fighter --from 1 --hp-roll 7 --con-mod 2
```

---

## SRD Lookup — `systems/dnd5e/lookup.py`

```bash
SKILL=<skill-base>

python3 $SKILL/systems/dnd5e/lookup.py spell "fireball"
python3 $SKILL/systems/dnd5e/lookup.py monster "goblin"
python3 $SKILL/systems/dnd5e/lookup.py condition "frightened"
python3 $SKILL/systems/dnd5e/lookup.py feature "sneak attack"
python3 $SKILL/systems/dnd5e/lookup.py item "cloak of protection"
```

---

## XP Awards — `systems/dnd5e/xp.py`

```bash
SKILL=<skill-base>

# Preview XP (no file writes)
python3 $SKILL/systems/dnd5e/xp.py calc --level 3 --players 2 --difficulty hard --type combat
python3 $SKILL/systems/dnd5e/xp.py calc --level 3 --players 2 \
    --monsters "goblin:1/4:3,orc:1/2:2"

# Award XP (updates character files + display sidebar)
python3 $SKILL/systems/dnd5e/xp.py award \
    --campaign <name> --characters "Aldric,Vesper" --difficulty hard --type combat
python3 $SKILL/systems/dnd5e/xp.py award \
    --campaign <name> --characters "Aldric,Vesper" \
    --monsters "goblin:1/4:3,orc:1/2:2"
python3 $SKILL/systems/dnd5e/xp.py award \
    --campaign <name> --characters "Aldric,Vesper" \
    --difficulty medium --type noncombat
```

**Difficulty tiers:** `easy` `medium` `hard` `deadly`
**Monster format:** `name:cr:count` — CR accepts `1/4`, `0.25`, `1/2`, integers. Count defaults to 1.
**Monster multiplier (auto-applied):** ×1 (1) · ×1.5 (2) · ×2 (3–6) · ×2.5 (7–10) · ×3 (11–14) · ×4 (15+)
