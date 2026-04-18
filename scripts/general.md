# Scripts — General

Read this file before: `/gm roll`, calendar advancement, or searching campaign history.

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

Flags nat 20 (CRITICAL HIT) and nat 1 (FUMBLE) automatically.

---

## Calendar — `scripts/calendar.py`

```bash
SKILL=<skill-base>
CAMP=<campaign-name>

# One-time setup (run during /gm new)
python3 $SKILL/scripts/calendar.py -c $CAMP init \
    --date "15 Harvestmoon 1247" \
    --time "morning" \
    --months "Frostfall,Deepwinter,Thawmonth,Seedtime,Bloomtide,Highsun,Harvestmoon,Duskfall" \
    --month-length 30 \
    --day-names "Sunday,Moonday,Ironday,Windday,Earthday,Fireday,Starday"

# Time advancement
python3 $SKILL/scripts/calendar.py -c $CAMP advance 8 hours
python3 $SKILL/scripts/calendar.py -c $CAMP advance 2 days
python3 $SKILL/scripts/calendar.py -c $CAMP rest short   # +1 hour
python3 $SKILL/scripts/calendar.py -c $CAMP rest long    # +8 hours

# Query / manual set
python3 $SKILL/scripts/calendar.py -c $CAMP now
python3 $SKILL/scripts/calendar.py -c $CAMP set "22 Harvestmoon 1247" evening
python3 $SKILL/scripts/calendar.py -c $CAMP time night
python3 $SKILL/scripts/calendar.py -c $CAMP events
```

**When to run:** after every rest; after significant travel or time skip; keep in sync with `state.md` in-world date.

---

## Campaign Search — `scripts/campaign_search.py`

Search campaign files before loading them in full. Use this first when a player asks about a past event, NPC, or location.

```bash
SKILL=<skill-base>
CAMP=<campaign-name>

# Search all default files (state, log, archive, world, npcs)
python3 $SKILL/scripts/campaign_search.py -c $CAMP Lasswater

# Narrow to specific files
python3 $SKILL/scripts/campaign_search.py -c $CAMP "Vael letter" --files log,archive

# Multi-keyword AND search
python3 $SKILL/scripts/campaign_search.py -c $CAMP Vareth Kel

# More context around matches
python3 $SKILL/scripts/campaign_search.py -c $CAMP Harwick -C 6
```

File keys: `state` `log` `archive` `world` `seeds` `npcs` `npcsfull`
Default: state, log, archive, world, npcs
