# GM Skill — Scripts Reference (Legacy)

> **Superseded.** This file has been split into focused script reference files that are loaded on demand:
> - `scripts/startup.md` — display push commands (session start with display ON)
> - `scripts/combat.md` — combat.py, tracker.py (loaded at `/gm combat start`)
> - `scripts/general.md` — dice.py, calendar.py, campaign_search.py (loaded on demand)
> - `scripts/character.md` — ability-scores.py, character.py, xp.py (loaded for character commands)
>
> This file is retained for reference only. Do not load it at session start.

**Skill base directory:** the directory containing SKILL.md (referenced below as `<skill-base>`)
**Campaigns directory:** `~/open-tabletop-gm/campaigns/`

Universal scripts live in `<skill-base>/scripts/`. System-specific scripts (character creation, stat calculation, data lookup) live in `<skill-base>/systems/<system>/` — load and use those if present for the active game system.

---

## Dice Script — `scripts/dice.py`

```bash
python3 <skill-base>/scripts/dice.py d20+5
python3 <skill-base>/scripts/dice.py 2d6+3
python3 <skill-base>/scripts/dice.py 4d6kh3        # keep highest 3 of 4d6
python3 <skill-base>/scripts/dice.py d20 adv       # advantage (roll twice, take higher)
python3 <skill-base>/scripts/dice.py d20+3 dis     # disadvantage + modifier
python3 <skill-base>/scripts/dice.py d20 --silent  # returns integer only
```

Flags nat 20 (CRITICAL HIT) and nat 1 (FUMBLE) automatically.

---

## Combat Script — `scripts/combat.py`

```bash
# Roll initiative and print tracker
python3 <skill-base>/scripts/combat.py init '<JSON>'
# JSON: [{"name":"Aldric","dex_mod":1,"hp":134,"ac":20,"type":"pc"}, ...]

# Reprint tracker from saved state
python3 <skill-base>/scripts/combat.py tracker '<JSON>' <round_num>

# Resolve a single attack
python3 <skill-base>/scripts/combat.py attack --atk 10 --ac 20 --dmg 2d6+5
```

`init` outputs a `STATE_JSON:` line — store it in `state.md` under `## Active Combat` between turns.

---

## Tracker Script — `scripts/tracker.py`

Tracks conditions, concentration, timed effects, and death saves. State persists at `~/open-tabletop-gm/campaigns/<name>/tracker.json`.

```bash
CAMP=my-campaign

# Timed effects — duration: 10r (rounds), 60m (minutes), 8h (hours), indef
# Append 'conc' to mark as concentration
python3 <skill-base>/scripts/tracker.py -c $CAMP effect start "Aldric" "Web" 10r conc
python3 <skill-base>/scripts/tracker.py -c $CAMP effect start "Vesper" "Hunter's Mark" indef
python3 <skill-base>/scripts/tracker.py -c $CAMP effect end   "Aldric" "Web"
python3 <skill-base>/scripts/tracker.py -c $CAMP effect tick  "Aldric"   # call on actor's turn; prints expiry warnings

# Conditions
python3 <skill-base>/scripts/tracker.py -c $CAMP condition add    "Vesper" Frightened
python3 <skill-base>/scripts/tracker.py -c $CAMP condition remove "Vesper" Frightened
python3 <skill-base>/scripts/tracker.py -c $CAMP condition clear  "Vesper"

# Concentration (auto-clears previous if switching)
python3 <skill-base>/scripts/tracker.py -c $CAMP concentrate "Vesper" "Bless"
python3 <skill-base>/scripts/tracker.py -c $CAMP concentrate "Vesper" break

# Death saves
python3 <skill-base>/scripts/tracker.py -c $CAMP saves "Aldric" success
python3 <skill-base>/scripts/tracker.py -c $CAMP saves "Aldric" failure
python3 <skill-base>/scripts/tracker.py -c $CAMP saves "Aldric" stable
python3 <skill-base>/scripts/tracker.py -c $CAMP saves "Aldric" reset

# Status / clear
python3 <skill-base>/scripts/tracker.py -c $CAMP status
python3 <skill-base>/scripts/tracker.py -c $CAMP status "Aldric"
python3 <skill-base>/scripts/tracker.py -c $CAMP clear           # conditions + concentration + effects
python3 <skill-base>/scripts/tracker.py -c $CAMP clear --all     # also clears death saves
```

**When to run:** condition applied or removed; concentration begins or breaks; PC drops to 0 HP; each death save rolled; end of encounter — `clear`.

---

## Calendar Script — `scripts/calendar.py`

```bash
# One-time setup (run during /gm new):
python3 <skill-base>/scripts/calendar.py -c $CAMP init \
    --date "15 Harvestmoon 1247" \
    --time "morning" \
    --months "Frostfall,Deepwinter,Thawmonth,Seedtime,Bloomtide,Highsun,Harvestmoon,Duskfall" \
    --month-length 30 \
    --day-names "Sunday,Moonday,Ironday,Windday,Earthday,Fireday,Starday"

# Time advancement
python3 <skill-base>/scripts/calendar.py -c $CAMP advance 8 hours
python3 <skill-base>/scripts/calendar.py -c $CAMP advance 2 days
python3 <skill-base>/scripts/calendar.py -c $CAMP rest short   # +1 hour
python3 <skill-base>/scripts/calendar.py -c $CAMP rest long    # +8 hours

# Query / manual set
python3 <skill-base>/scripts/calendar.py -c $CAMP now
python3 <skill-base>/scripts/calendar.py -c $CAMP set "22 Harvestmoon 1247" evening
python3 <skill-base>/scripts/calendar.py -c $CAMP time night
python3 <skill-base>/scripts/calendar.py -c $CAMP events
```

**When to run:** after every rest; after significant travel or time skip; when updating `state.md` date — use `calendar.py set` to keep them in sync.

---

## Campaign Search — `scripts/campaign_search.py`

Keyword search across campaign files. Use this before loading full files into context when looking up a past event, NPC detail, or plot thread.

```bash
CAMP=my-campaign

# Search all default files (state, log, archive, world, npcs):
python3 <skill-base>/scripts/campaign_search.py -c $CAMP Lasswater

# Narrow to specific files:
python3 <skill-base>/scripts/campaign_search.py -c $CAMP "Vael letter" --files log,archive

# Multi-keyword AND search:
python3 <skill-base>/scripts/campaign_search.py -c $CAMP Vareth Kel

# More context lines around each match:
python3 <skill-base>/scripts/campaign_search.py -c $CAMP Harwick -C 6
```

File keys: `state`, `log`, `archive`, `world`, `seeds`, `npcs`, `npcsfull`
Default: state, log, archive, world, npcs

**When to use:** any time a player asks about a past event, NPC, location, or plot thread not in active context. Run this first — only read the full file if the search returns insufficient context.

---

## Display Companion — `display/push_stats.py`

Pushes character and combat stats to the sidebar. Players are merged by name; partial updates are safe.

```bash
# Full stats push on /gm load (use --replace-players to clear stale characters):
python3 <skill-base>/display/push_stats.py --replace-players --json '{
  "players": [{
    "name": "Aldric", "race": "Human", "class": "Fighter", "level": 16,
    "hp": {"current": 134, "max": 134, "temp": 0},
    "ac": 20, "initiative": "+1", "speed": 30,
    "hit_dice": {"remaining": 16, "max": 16, "die": "d10"},
    "ability_scores": {
      "str": {"score": 20, "mod": "+5"}, "dex": {"score": 12, "mod": "+1"},
      "con": {"score": 18, "mod": "+4"}, "int": {"score": 10, "mod": "+0"},
      "wis": {"score": 12, "mod": "+1"}, "cha": {"score": 12, "mod": "+1"}
    },
    "sheet": {
      "attacks": [
        {"name": "Greatsword", "bonus": "+10", "damage": "2d6+5", "type": "Slashing", "notes": "Crit 19-20; 4 attacks"}
      ],
      "spells": null,
      "features": [
        {"name": "Action Surge", "text": "2/rest: take one additional action on your turn."},
        {"name": "Second Wind",  "text": "Bonus action: regain 1d10+16 HP. 1/rest."}
      ],
      "inventory": ["Greatsword", "Plate Armour", "Belt of Giant Strength", "Potion of Superior Healing x2"]
    }
  }]
}'

# Partial updates (use whenever values change mid-session):
python3 <skill-base>/display/push_stats.py --player Aldric --hp 98 134
python3 <skill-base>/display/push_stats.py --player Aldric --temp-hp 8     # set temp HP
python3 <skill-base>/display/push_stats.py --player Aldric --temp-hp 0     # clear temp HP

# Hit dice:
python3 <skill-base>/display/push_stats.py --player Aldric --hit-dice-use
python3 <skill-base>/display/push_stats.py --player Aldric --hit-dice-restore 2

# Conditions:
python3 <skill-base>/display/push_stats.py --player Aldric --conditions-add "Frightened"
python3 <skill-base>/display/push_stats.py --player Aldric --conditions-remove "Frightened"
python3 <skill-base>/display/push_stats.py --player Aldric --conditions ""   # clear all

# Concentration:
python3 <skill-base>/display/push_stats.py --player Vesper --concentrate "Bless"
python3 <skill-base>/display/push_stats.py --player Vesper --concentrate ""  # clear

# Spell slots — full replace on /gm load:
python3 <skill-base>/display/push_stats.py --player Vesper \
  --spell-slots '{"1":{"current":4,"max":4},"2":{"current":3,"max":3},"3":{"current":3,"max":3}}'

# Spell slots — granular mid-session:
python3 <skill-base>/display/push_stats.py --player Vesper --slot-use 3      # expend one 3rd-level slot
python3 <skill-base>/display/push_stats.py --player Vesper --slot-restore 3  # restore one 3rd-level slot

# Inventory:
python3 <skill-base>/display/push_stats.py --player Aldric --inventory-add "Iron key"
python3 <skill-base>/display/push_stats.py --player Aldric --inventory-remove "Potion of Superior Healing"

# Faction standings (required at /gm load to show faction panel):
python3 <skill-base>/display/push_stats.py \
  --factions '[{"name":"Ironhelm Guild","standing":"Allied"},{"name":"City Watch","standing":"Neutral"}]'
python3 <skill-base>/display/push_stats.py --factions '[]'   # clear all

# Quest tracker (required at /gm load to show quest panel):
python3 <skill-base>/display/push_stats.py \
  --quests '[{"name":"The Missing Shipment","status":"active"},{"name":"Verun the Betrayer","status":"threat"}]'
python3 <skill-base>/display/push_stats.py --quests '[]'   # clear all

# Combat turn order (on /gm combat start):
python3 <skill-base>/display/push_stats.py --turn-order \
  '[{"name":"Vesper","initiative":22,"type":"pc"},{"name":"Goblin","initiative":14,"type":"enemy"},{"name":"Aldric","initiative":11,"type":"pc"}]' \
  --turn-current "Vesper" --turn-round 1

# Advance turn pointer:
python3 <skill-base>/display/push_stats.py --turn-current "Goblin"

# New round:
python3 <skill-base>/display/push_stats.py --turn-current "Vesper" --turn-round 2

# Combat ended:
python3 <skill-base>/display/push_stats.py --turn-clear

# World time clock:
python3 <skill-base>/display/push_stats.py --world-time \
  '{"date":"19 Ashveil 1312","day_name":"Moonday","time":"morning","season":"Long Hollow","weather":"calm"}'

# Clear display:
python3 <skill-base>/display/push_stats.py --clear
```

**Quest status values:** `active` (amber) · `threat` (red) · `resolved` (green) · `failed` (muted). The quest panel only appears when at least one quest is present.

**When to push stats:**
- `/gm load` — `--replace-players --json` (full stats) + `--spell-slots` + `--world-time` + `--factions` + `--quests`
- HP change — `--player NAME --hp <current> <max>`
- Temp HP — `--player NAME --temp-hp N` (0 to clear)
- Spell slot used — `--slot-use <level>`; restored — `--slot-restore <level>`
- Condition gained — `--conditions-add "Name"`; removed — `--conditions-remove "Name"`
- Concentration starts — `--concentrate "Spell"`; ends — `--concentrate ""`
- Item gained — `--inventory-add "Item"`; spent — `--inventory-remove "Item"`
- Faction changes — `--factions '[...]'` (full replace)
- Quest status changes — `--quests '[...]'` (full replace; use `[]` to clear all)
- Combat start — `--turn-order`; each turn — `--turn-current`; end — `--turn-clear`
- Any rest or time advance — `--world-time`

---

## Display Companion — `display/send.py`

Sends narration, dice results, NPC dialogue, and player actions to the display. See SKILL.md Active GM Mode for the full per-turn sequence and stat flag reference.

```bash
# Player action
python3 <skill-base>/display/send.py --player "Aldric" << 'GMEND'
Aldric charges toward the nearest Wight Knight.
GMEND

# Dice result
python3 <skill-base>/display/send.py --dice << 'GMEND'
Aldric — Greatsword: d20+10 = 28 vs AC 14 → HIT — 2d6+5 = 16 slashing damage
GMEND

# GM narration (bundle all stat changes on the same call):
python3 <skill-base>/display/send.py \
  --stat-hp "Aldric:126:134" \
  --stat-condition-add "Aldric:Frightened" << 'GMEND'
[full narration text — never summarise or condense]
GMEND

# NPC dialogue
python3 <skill-base>/display/send.py --npc "Aldrath" << 'GMEND'
"You have made a grave error coming here."
GMEND
```

**ONE bash call per response.** Multiple `send.py` invocations inside a single bash block. Block order: `--player` then `--dice` then narration (with `--stat-*`) then `--npc`.

---

## Display Companion — `display/check_input.py`

Called at the start of each turn before processing the player's message. Drains any actions queued from the display companion input panel.

```bash
python3 <skill-base>/display/check_input.py
# Output: "[Aldric]: I charge the wight" — empty if nothing queued
```

If output is present, use it as the player action for this turn. If both queued input and a terminal message exist, merge them. Empty output — proceed normally.

---

## Display Companion Setup

```bash
cd <skill-base>/display
pip3 install -r requirements.txt

# Start display (force-kills any previous instance):
bash <skill-base>/display/start-display.sh

# Open browser before /gm load so it is connected when opening narration streams in:
open https://localhost:5001
```

---

## System-Specific Scripts — `systems/<system>/`

Scripts for character creation, stat calculation, ability scores, and data lookup are in the active system module directory. For D&D 5e:

```bash
# Ability scores
python3 <skill-base>/systems/dnd5e/ability-scores.py roll
python3 <skill-base>/systems/dnd5e/ability-scores.py pointbuy --check STR=15 DEX=10 CON=15 INT=8 WIS=11 CHA=12

# Character stat block
python3 <skill-base>/systems/dnd5e/character.py calc --class fighter --level 1 \
    STR=15 DEX=10 CON=15 INT=9 WIS=11 CHA=14 \
    --proficient STR CON Athletics Intimidation

# Level up
python3 <skill-base>/systems/dnd5e/character.py levelup --class fighter --from 1 --hp-roll 7 --con-mod 2

# SRD lookup
python3 <skill-base>/systems/dnd5e/lookup.py spell "fireball"
python3 <skill-base>/systems/dnd5e/lookup.py monster "goblin"
python3 <skill-base>/systems/dnd5e/lookup.py condition "frightened"
python3 <skill-base>/systems/dnd5e/lookup.py feature "sneak attack"
python3 <skill-base>/systems/dnd5e/lookup.py item "cloak of protection"

# XP awards — calc (preview) or award (updates character files + display)
python3 <skill-base>/systems/dnd5e/xp.py calc --level 3 --players 2 --difficulty hard --type combat
python3 <skill-base>/systems/dnd5e/xp.py calc --level 3 --players 2 --monsters "goblin:1/4:3,orc:1/2:2"
python3 <skill-base>/systems/dnd5e/xp.py award \
  --campaign my-campaign --characters "Aldric,Vesper" --difficulty hard --type combat
python3 <skill-base>/systems/dnd5e/xp.py award \
  --campaign my-campaign --characters "Aldric,Vesper" \
  --monsters "goblin:1/4:3,orc:1/2:2"
python3 <skill-base>/systems/dnd5e/xp.py award \
  --campaign my-campaign --characters "Aldric,Vesper" \
  --difficulty medium --type noncombat
```

`calc` — preview XP with no file writes. `award` — updates campaign character files and pushes XP to the display sidebar.

**Difficulty tiers:** `easy` `medium` `hard` `deadly` (both combat and non-combat use the same table)
**Monster format:** `name:cr:count` — CR accepts `1/4`, `0.25`, `1/2`, `0.5`, or integers. Count defaults to 1.
**Monster multiplier** (auto-applied): ×1 (1 monster) · ×1.5 (2) · ×2 (3–6) · ×2.5 (7–10) · ×3 (11–14) · ×4 (15+)
