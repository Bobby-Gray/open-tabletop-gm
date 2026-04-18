# GM Skill — Branch Router

This file is always in context. When any command or state transition occurs, look up the branch below. It tells you exactly which script file to read (if any) and what the terminal action is. Do not proceed to the terminal action until all listed steps are complete.

---

## `/gm load <name>`

**No questions. Four steps. Do them in order and stop.**

**Step 1 — Check display state:**
```
bash -c 'f=<skill-base>/display/app.pid; test -f "$f" && kill -0 $(cat "$f") 2>/dev/null && echo ON || echo OFF'
```
Store result as `display=ON` or `display=OFF`. Do not run `start-display.sh`.

**Step 2 — Read these three files:**
1. `~/open-tabletop-gm/campaigns/<name>/state.md`
2. `~/open-tabletop-gm/campaigns/<name>/world.md`
3. `~/open-tabletop-gm/campaigns/<name>/npcs.md`

**Step 3 — Deliver opening narration as plain text.** Do not run any bash commands. Do not read any more files. Just write the narration. Set the scene from what you read. End with a question to the player.

**Step 4 — Enter active GM mode.** `/gm` prefix not needed. Characters and system rules load on demand during the session.

---

## `/gm display <on|off> [--lan]`

Start or stop the display companion independently of session load.
- `on` → run `bash <skill-base>/display/start-display.sh`
- `on --lan` → run `bash <skill-base>/display/start-display.sh --lan`
- `off` → `kill $(cat <skill-base>/display/app.pid 2>/dev/null) 2>/dev/null`

---

## ACTIVE — Narration Turn

Each player message during an active session:

1. If display running: run `check_input.py` first; merge any queued input with the player's message
2. Resolve the action narratively
3. If dice are needed: read `scripts/general.md` → run `dice.py` → narrate result
4. If display running: send narration via `send.py` (bundle all stat flags in one call)
5. If HP/conditions/slots changed: update display with the relevant `push_stats.py` partial flags

**Do not read scripts/general.md unless a roll is needed. Do not read scripts/startup.md unless sending to display.**

---

## `/gm combat start`

1. Read `<skill-base>/scripts/combat.md`
2. Collect combatants: name, dex_mod, HP, AC, type (pc/enemy)
3. Run `combat.py init` → store STATE_JSON in `state.md → ## Active Combat`
4. If display running: push turn order via `push_stats.py --turn-order`
5. Enter COMBAT state

## COMBAT — Turn

Each turn in combat:
1. Run `combat.py attack` or `dice.py` as needed (scripts/combat.md already in context)
2. Run `tracker.py effect tick` for the active combatant
3. If display running: update HP, conditions, turn pointer via `push_stats.py`
4. If display running: send narration via `send.py`

## COMBAT — End

1. Run `tracker.py clear`
2. Clear turn order: `push_stats.py --turn-clear`
3. Narrate aftermath, award XP (read `scripts/character.md` for `xp.py`)
4. Clear `## Active Combat` in state.md
5. Return to ACTIVE state

---

## `/gm rest <short|long>`

1. Read `scripts/general.md` (calendar.py) + `scripts/combat.md` (tracker.py)
2. Follow rest procedure from `systems/<system>/system.md`
3. Run `tracker.py clear` (expired conditions/effects)
4. Run `calendar.py rest short|long`
5. Update state.md in-world date
6. If display running: `push_stats.py --world-time` + HP/slot updates

---

## `/gm roll <notation>`

1. Read `scripts/general.md`
2. Run `python3 <skill-base>/scripts/dice.py <notation>`
3. Display output verbatim

---

## `/gm character new`

1. Read `scripts/character.md`
2. Follow character creation procedure from `systems/<system>/system.md`
3. Run `ability-scores.py` and `character.py calc`
4. Write character file; mirror to global roster

---

## `/gm save`

No script reads needed.
1. Write session events to `session-log.md`
2. Update `state.md` (location, quests, HP/resources, recent events, faction moves)
3. Update any `characters/*.md` that changed; mirror to `~/open-tabletop-gm/characters/`

---

## `/gm end`

1. Run `/gm save`
2. Ask calibration question; update `## GM Style Notes` if new pattern emerged
3. Update `## World State` in state.md (threat arc, factions, in-world date)
4. If display running: `kill $(cat <skill-base>/display/app.pid 2>/dev/null) 2>/dev/null`

---

## `/gm list`

1. Glob `*/state.md` in `~/open-tabletop-gm/campaigns/`
2. Print table: campaign name | system | last session date | session count

---

## Past event / NPC lookup

When the player asks about something not in active context:
1. Read `scripts/general.md`
2. Run `campaign_search.py` with relevant keywords
3. Only read the full file if search returns insufficient context
