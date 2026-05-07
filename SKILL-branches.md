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

If output reads `# graph not initialized` — graph hasn't been seeded for this campaign yet. **Graph init is a hard requirement, not deferrable.** The going-forward Continuity Archive compression rule (see `/gm save` Step 4) assumes graph.json is present and canonical for relational state; deferring init creates state-archive drift that compounds session-over-session. Run the init flow before delivering the narration:

1. **Detect legacy.** A campaign is "legacy" if any of: `Session count > 1` in state.md header, OR `## Continuity Archive` has at least one `### Session N` entry, OR session-log.md is > 100 lines. A freshly-created campaign at `/gm new` time fails all three signals — do NOT classify it as legacy.

2. **Backup the campaign directory** (always — both fresh and legacy):
   ```
   cp -R ~/open-tabletop-gm/campaigns/<name> \
         ~/open-tabletop-gm/campaigns/<name>.backup-$(date +%Y%m%d-%H%M%S)
   ```
   Tell the GM the backup path explicitly so they can revert if needed.

3. **Run `/gm graph init <name>`** — propose seed nodes/edges from `npcs.md`, `world.md`, and `state.md` (Live State Flags + Active Quests + recent NPC dispositions). Show the GM a single approval block (counts by type + named entries) and ask for one go/no-go. After approval, batch-execute the `add-node` and `add-edge` calls. Use `--since N` matching when each node/edge first became canon.

4. **Validate** with a `scene-context` query at the current location to confirm the subgraph is reachable.

5. **(Legacy only)** Offer the one-time Continuity Archive compression pass:

   > *"This campaign is legacy ({session_count} sessions, {archive_count} archive entries). Now that `graph.json` is the canonical source for faction memberships, NPC dispositions, and typed-edge relationships, I can do a one-time pass to trim the existing `## Continuity Archive` entries of relational restatements that the graph now answers. Mechanical changes, plot beats, atmospheric/decision moments, and disclosed information stay in full. Estimated reduction: 5–30% of archive bytes. Backup is already at `<backup-path>`. Proceed? [y/n]"*

   - `y` → trim each archive entry surgically; keep the bullet structure; remove ONLY pure-relational restatements that have a corresponding edge in the just-initialized graph. Preserve: mechanical changes, plot beats, atmospheric moments, disclosed content, calibration material, off-screen world events. Add a one-line note at the top of `## Continuity Archive`: *"Compressed YYYY-MM-DD (graph init pass). Relational state is canonical in graph.json — entries below preserve mechanical changes, plot beats, disclosed content, atmospheric/decision moments, and calibration material."*
   - `n` → leave the archive untouched. The going-forward rule (per `/gm save`) still applies to NEW entries from this session forward.

   For fresh (non-legacy) campaigns: skip the offer entirely — there's nothing to compress yet, and the going-forward rule covers all future entries.

6. Re-run scene-context (now populated). Then proceed to Step 5 (narration).

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

1. Read `scripts/character.md`. Ask the player for the character's name.

   **Name uniqueness check:** run `python3 <skill-base>/scripts/name_registry.py check "<name>"`. Exit 1 (duplicate) prints which prior campaign / session used the name; surface as a non-blocking warning and ask the player to confirm or change. After write (step 4), call `name_registry.py add --name "<name>" --type pc --campaign <name> --session <current>`.
2. Follow character creation procedure from `systems/<system>/system.md`
3. Run `ability-scores.py` and `character.py calc`
4. Write character file; mirror to global roster; record name in registry (see step 1)

---

## `/gm save`

No script reads needed.
1. Write session events to `session-log.md`
2. Update `state.md` (location, quests, HP/resources, recent events, faction moves)
3. Update any `characters/*.md` that changed; mirror to `~/open-tabletop-gm/characters/`

   **Going-forward Continuity Archive compression rule (when `graph.json` exists for the campaign):** Continuity Archive bullets in state.md must NOT restate relational state the graph holds canonically.

   **Omit:**
   - "X is allied with Y" / "X is hostile to Y" — already a typed edge with `--since N`
   - "X is a member of faction F" / "X works for Y" / "X reports to Y" — already a `member_of` / `works_for` / `reports_on` edge
   - "Z saw the party's faces" — already a `hostile_to` / `surveils` edge
   - Faction memberships and NPC dispositions that haven't changed this session
   - Restated NPC profiles already in node tags + summary

   **Keep:**
   - Mechanical changes (XP, levels, items gained/spent, slots burned, HP deltas)
   - Plot beats (arc beat completions, named turning points)
   - Atmospheric / decision moments with no graph edge
   - Disclosed content (the WHAT was learned) even when the relational fact is graph-captured
   - Off-screen world events / faction moves
   - Calibration / GM Notes / cliffhangers

   Treat each bullet as one sentence with one job. If the only job is restating a graph edge, drop it. If it carries content + edge, keep the content half. The graph is queried at `/gm load` Step 4; the archive is queried for chronological narrative + mechanical state — they should not overlap.

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
