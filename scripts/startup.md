# Scripts — Session Startup

Read this file before: `/gm load` display push, sending any narration, or calling check_input.

**Skill base:** `<skill-base>`
**Campaigns:** `~/open-tabletop-gm/campaigns/`

---

## Display Push — `display/push_stats.py`

Run at `/gm load` after reading campaign files. Use a single bash block for all push calls.

```bash
SKILL=<skill-base>

# Clear display first
python3 $SKILL/display/push_stats.py --clear

# Full party stats (--replace-players clears stale characters)
python3 $SKILL/display/push_stats.py --replace-players --json '{
  "players": [{
    "name": "NAME", "race": "RACE", "class": "CLASS", "level": N,
    "hp": {"current": N, "max": N, "temp": 0},
    "ac": N, "initiative": "+N", "speed": 30,
    "hit_dice": {"remaining": N, "max": N, "die": "dN"},
    "ability_scores": {
      "str": {"score": N, "mod": "+N"}, "dex": {"score": N, "mod": "+N"},
      "con": {"score": N, "mod": "+N"}, "int": {"score": N, "mod": "+N"},
      "wis": {"score": N, "mod": "+N"}, "cha": {"score": N, "mod": "+N"}
    }
  }]
}'

# Spell slots (spellcasters only)
python3 $SKILL/display/push_stats.py --player NAME \
  --spell-slots '{"1":{"current":4,"max":4},"2":{"current":3,"max":3}}'

# Factions (use [] if none)
python3 $SKILL/display/push_stats.py \
  --factions '[{"name":"FACTION","standing":"Allied"}]'

# Quests (use [] if none). Status: active | threat | resolved | failed
python3 $SKILL/display/push_stats.py \
  --quests '[{"name":"QUEST","status":"active"}]'

# World time
python3 $SKILL/display/push_stats.py --world-time \
  '{"date":"DAY MONTH YEAR","day_name":"DAY","time":"morning","season":"SEASON","weather":"calm"}'

# If combat was active in state.md, restore turn order
python3 $SKILL/display/push_stats.py \
  --turn-order '[{"name":"NAME","initiative":N,"type":"pc"}]' \
  --turn-current "NAME" --turn-round N
```

**Mid-session stat updates (partial — use whenever values change):**
```bash
python3 $SKILL/display/push_stats.py --player NAME --hp 98 134
python3 $SKILL/display/push_stats.py --player NAME --temp-hp 8      # 0 to clear
python3 $SKILL/display/push_stats.py --player NAME --hit-dice-use
python3 $SKILL/display/push_stats.py --player NAME --hit-dice-restore 2
python3 $SKILL/display/push_stats.py --player NAME --conditions-add "Frightened"
python3 $SKILL/display/push_stats.py --player NAME --conditions-remove "Frightened"
python3 $SKILL/display/push_stats.py --player NAME --conditions ""   # clear all
python3 $SKILL/display/push_stats.py --player NAME --concentrate "Bless"
python3 $SKILL/display/push_stats.py --player NAME --concentrate ""  # clear
python3 $SKILL/display/push_stats.py --player NAME --slot-use 3
python3 $SKILL/display/push_stats.py --player NAME --slot-restore 3
python3 $SKILL/display/push_stats.py --player NAME --inventory-add "Iron key"
python3 $SKILL/display/push_stats.py --player NAME --inventory-remove "Potion"
python3 $SKILL/display/push_stats.py --factions '[...]'   # full replace
python3 $SKILL/display/push_stats.py --quests '[...]'     # full replace; [] to clear
```

---

## Narration — `display/send.py`

Send all narration, dice results, NPC dialogue to the display. ONE bash block per response.

```bash
SKILL=<skill-base>

# Player action
python3 $SKILL/display/send.py --player "NAME" << 'GMEND'
Player action text here.
GMEND

# Dice result
python3 $SKILL/display/send.py --dice << 'GMEND'
NAME — Greatsword: d20+10 = 28 vs AC 14 → HIT — 2d6+5 = 16 slashing
GMEND

# GM narration (bundle stat flags on the same call)
python3 $SKILL/display/send.py \
  --stat-hp "NAME:current:max" \
  --stat-condition-add "NAME:Frightened" << 'GMEND'
Full narration text — never summarise.
GMEND

# NPC dialogue
python3 $SKILL/display/send.py --npc "NPCNAME" << 'GMEND'
"Dialogue here."
GMEND
```

Block order within one bash call: `--player` → `--dice` → narration with `--stat-*` → `--npc`.

---

## Player Input — `display/check_input.py`

Call at the start of each turn before processing the player's message.

```bash
python3 <skill-base>/display/check_input.py
# Output: "[NAME]: action text" — empty string if nothing queued
```

If output is non-empty, use it as the player action for this turn. Merge with any terminal message if both exist.
