# GM Skill — Branch Router

This file is always in context. When any command or state transition occurs, look up the branch below. It tells you exactly which script file to read (if any) and what the terminal action is. Do not proceed to the terminal action until all listed steps are complete.

---

## `/gm load <name>`

**No questions. Six steps. Do them in order and stop.**

**Step 1 — Check display state:**
```
bash -c 'f=<skill-base>/display/app.pid; test -f "$f" && kill -0 $(cat "$f") 2>/dev/null && echo ON || echo OFF'
```
Store result as `display=ON` or `display=OFF`. Do not run `start-display.sh`.

**Step 2 — If `display=ON`, sync campaign and replay previous session tail:**

Skip this step entirely if `display=OFF`.

1. Register the active campaign (writes `.campaign` and reloads the per-campaign tail buffer):
   ```
   python3 <skill-base>/display/send.py --set-campaign <name> < /dev/null
   ```
2. Read `~/open-tabletop-gm/campaigns/<name>/session_tail.json`. **The campaign-side path is the authoritative one — do NOT read** the legacy/fallback at `<skill-base>/display/session_tail.json`; that file may exist from older sessions or other campaigns and will mislead the replay. If the campaign-side file does not exist, skip the rest of this step (display starts blank).
3. For each entry in the tail array, send it via `send.py` using the entry's keys:
   - `player` key present → `send.py --player <name>` with text via stdin
   - `npc` key present → `send.py --npc <name>` with text via stdin
   - `dice` key present → `send.py --dice` with text via stdin
   - `tutor` key present → `send.py --tutor` with text via stdin
   - `action` key present → `send.py --action <name>` with text via stdin
   - none of the above → `send.py` with text via stdin (plain narration)

   Send entries in array order. The display will render them as the previous session's last exchanges, restoring continuity for any reconnecting browser.

**Step 3 — Read these three files:**
1. `~/open-tabletop-gm/campaigns/<name>/state.md`
2. `~/open-tabletop-gm/campaigns/<name>/world.md`
3. `~/open-tabletop-gm/campaigns/<name>/npcs.md`

**Step 4 — Pull scene-context from the campaign graph.** Always run, even if you suspect `graph.json` doesn't exist — the script exits cleanly with a notice when uninitialized.
```
python3 <skill-base>/scripts/gm_graph.py scene-context \
  --campaign <name> \
  --place "<current-location-name-or-id>" \
  --present "<comma-separated-NPC-names-likely-present>" \
  --hops 2 \
  --at-session <current-session-N>
```
Identify `<current-location>` from `state.md → ## World State → location` (or the most recent location in `## Recent Events`). Identify `<present>` from the NPCs likely on-scene per `state.md` / `session-log.md`. `<current-session-N>` is `state.md → ## Session Count`.

Output is a focused subgraph (nodes by type + relationships block). **Internalize this subgraph before delivering the narration** — it is the authoritative source for who-relates-to-whom in the current scene. Do not re-read `npcs-full.md` for relationships you can answer from the subgraph.

If output reads `# graph not initialized` — graph hasn't been seeded for this campaign yet. Offer the GM the auto-init flow before delivering the narration:

> *"This campaign doesn't have a relationship graph yet. I can initialize one now — it improves long-session continuity recall when full NPC files fall out of context. As a safety precaution, I'll back up the campaign first to `~/open-tabletop-gm/campaigns/<name>.backup-YYYYMMDD-HHMMSS/`. Proceed? [y/n]"*

- `y` → snapshot the campaign directory, then run `/gm graph init <name>` (which proposes seed nodes/edges and asks for GM approval before writing). After init completes, re-run scene-context.
  ```
  cp -R ~/open-tabletop-gm/campaigns/<name> \
        ~/open-tabletop-gm/campaigns/<name>.backup-$(date +%Y%m%d-%H%M%S)
  ```
- `n` → continue without graph for this session; do not re-prompt this session. The GM can run `/gm graph init` later at their convenience.

**Step 5 — Deliver opening narration as plain text.** Do not run any bash commands. Do not read any more files. Just write the narration. Set the scene from what you read. End with a question to the player.

**Step 6 — Enter active GM mode.** `/gm` prefix not needed. Characters and system rules load on demand during the session.

---

## `/gm display <on|off> [--lan]`

Start or stop the display companion independently of session load.
- `on` → run `bash <skill-base>/display/start-display.sh`
- `on --lan` → run `bash <skill-base>/display/start-display.sh --lan`
- `off` → `kill $(cat <skill-base>/display/app.pid 2>/dev/null) 2>/dev/null`

---

## `/gm path [<new-path> | reset]`

View or configure where campaign and character data is stored. Wraps the `GM_CAMPAIGN_ROOT` env var (default `~/open-tabletop-gm`).

- No args → `python3 <skill-base>/scripts/path_config.py` and show output.
- New path → `python3 <skill-base>/scripts/path_config.py set <path>`. Confirm to user, then remind them the change only takes effect in new shells (or after they `source` their rc on macOS/Linux).
- `reset` → `python3 <skill-base>/scripts/path_config.py reset`.

Persistence is via shell rc on macOS/Linux and via `setx` on Windows. Existing campaigns are not auto-migrated; `paths.find_campaign()` handles legacy fallback + copy-on-access.

---

## `/gm update [--check]`

Pull the latest skill changes from `origin/main`.

- No args → `python3 <skill-base>/scripts/update_skill.py` and stream output (script prompts before pulling).
- `--check` → `python3 <skill-base>/scripts/update_skill.py --check` — report status without pulling.
- The script refuses to update if the working tree is dirty and uses `--ff-only` so it never silently merges divergent history.
- After a successful pull, remind the user to restart their GM session so the new `SKILL.md` and `SKILL-branches.md` are reloaded.

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
4. **Campaign-graph relationship-shift sweep.** Skip if `graph.json` doesn't exist for this campaign. Otherwise scan this session's narration for relationship shifts that weren't captured live via `/gm graph add-edge` / `close-edge`. Look for moments matching:
   - New alliance, betrayal, or rivalry between named NPCs / factions
   - An NPC moving into / out of a location
   - A faction taking control of (or losing) a place
   - A character learning a secret
   - A quest / thread ending or being blocked

   For each candidate, draft an `add-edge` or `close-edge` call. Then **present the batch to the GM as a numbered list** and ask: *"Apply all? [y / pick / skip]"*

   - `y` → run all proposed calls via `python3 <skill-base>/scripts/gm_graph.py ...`
   - `pick` → GM names the numbers to apply (e.g. `1, 3, 5`); skip the rest
   - `skip` → don't apply any

   Always supply `--since <current-session-N>` from state.md. Never write proposed edges silently.

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
