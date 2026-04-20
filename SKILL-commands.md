# GM Skill — Command Reference

Command signatures and brief descriptions. All procedures, script loading, and state transitions are defined in `SKILL-branches.md`, which is always in context.

**Campaigns directory:** `~/open-tabletop-gm/campaigns/`
**Characters directory:** `~/open-tabletop-gm/characters/`
**Skill base:** `<skill-base>/`

Do NOT run `git init` or any git commands in campaign directories.

---

## Command Signatures

| Command | Description |
|---|---|
| `/gm new <name> [system]` | Create a new campaign. See world-gen procedure below. |
| `/gm load <name>` | Load an existing campaign. Follow `/gm load` branch in SKILL-branches.md. |
| `/gm save` | Save session state. Follow `/gm save` branch. |
| `/gm end` | End session with calibration. Follow `/gm end` branch. |
| `/gm abandon` | Exit without saving. Confirm first. |
| `/gm list` | List all campaigns. Follow `/gm list` branch. |
| `/gm roll <notation>` | Roll dice. Follow `/gm roll` branch. |
| `/gm combat start` | Start combat. Follow `/gm combat start` branch. |
| `/gm rest <short\|long>` | Process a rest. Follow `/gm rest` branch. |
| `/gm recap` | Read session-log.md; deliver 3-5 sentence in-character recap. |
| `/gm world` | Read and display world.md for the current campaign. |
| `/gm quests` | Read and display active quests from state.md. |
| `/gm character new [campaign]` | Create a character. Follow `/gm character new` branch. |
| `/gm character sheet [name]` | Read and display characters/<name>.md. |
| `/gm characters` | List all characters in the global roster. |
| `/gm tutor on\|off` | Toggle tutor mode. Write `tutor_mode: true\|false` to state.md. |
| `/gm display <on\|off> [--lan]` | Start or stop the display companion. Follow `/gm display` branch. Start before `/gm load` if you want it active. |
| `/gm npc <name>` | Generate or retrieve an NPC. Write to npcs.md / npcs-full.md. |
| `/gm import <filepath> [campaign-name]` | Import a pre-written campaign source (PDF, MD, DOCX, TXT). See `/gm import` procedure below. |
| `/gm arc [status\|advance\|revise\|view]` | Manage the dynamic campaign arc. See `/gm arc` procedure below. |

---

## `/gm new` — World Generation Procedure

1. If `[system]` not supplied, ask which game system
2. Create campaign directory at `~/open-tabletop-gm/campaigns/<name>/characters/`
4. Copy blank templates from `systems/<system>/` and `templates/` into the campaign directory
5. Ask: party size and starting level
6. **Tone/Genre Wizard** — present all four in one message: tone · magic level · setting type · danger level. Randomise any blank with dice.py.
7. **World Foundations** — geography, biome, climate, magic system, pantheon, calendar → write to `## World Foundations` in world.md
8. **Three Truths** — one settlement, one nearby threat, one mystery → write to world.md
9. **Threat Arc** — five-stage table in world.md; set stage 1; write to state.md
10. **2 Factions** — archetype, activity, relationship to party → world.md + state.md summary
11. **3 NPCs** — one-line index in npcs.md; full detail in npcs-full.md; each needs 2+ relationships
12. **3-5 Quest Seeds** → write to `## Quest Seed Bank` in world.md
13. Write state.md: session count 0, starting location, system, display flag
14. **Dynamic Campaign Arc** — optional arc generation. Ask: *"Generate a committed narrative arc? [y/n — recommended]"*

   **If yes:** Drawing from theme, threat arc stages, factions, Three Truths, NPC motivations, and quest seeds, derive:
   - `theme` — one sentence: what this story is ultimately about (not what happens, but what it means)
   - `resolution` — the committed endpoint shape: not specific events, but the emotional/thematic truth if the party succeeds
   - Six beats across three acts (Inciting Incident, Complication, Midpoint Shift, All Is Lost, Final Confrontation, Resolution)
   - For each beat: `label`, `what_changes` (consequence, not event), `world_pressure` (faction/NPC move that delivers it)

   Write to `state.md → ## Campaign Arc` with `type: dynamic`. Deliver a one-paragraph arc summary. A capable model (Opus-class or equivalent) is recommended for this step — the quality of the arc depends on synthesising all world data into a coherent thematic shape.

   **If no:** Write `type: sandbox` to `## Campaign Arc`. Story remains open-ended with no arc tracking.

15. Confirm creation. Offer `/gm character new`.

---

## `/gm save` — Session Save Procedure

1. **Update session-log.md** — append a new session entry with date, key events, NPC interactions, decisions, and consequences.
2. **Increment session count** in state.md header. Update `last session` date.
3. **Sync World State** — update `state.md → ## World State`: advance in-world date if time passed, update faction states if they shifted, advance the threat arc stage if events warrant it.
4. **Update `## Live State Flags`** — review and update the compact key-value block: cover/party position, faction stances toward the party (non-neutral only), NPC dispositions (changed or notable only). This section must be accurate after every save — it is the compaction-resilience anchor for future sessions.
5. **Arc check** (dynamic arcs only — skip for sandbox and structured):
   - If `## Campaign Arc` has `type: dynamic`, review this session's key events against `outstanding_beats`.
   - Ask: *"Did any arc beats land this session? [beat id(s) like '1b 2a', or 'none']"*
   - If beats landed: run `/gm arc advance <beat-id>` for each. Update `steering_notes` for the next outstanding beat.
6. **Session log archival** (after session count > 3): keep only the 2 most recent full entries in session-log.md. Move older entries to `session-log-archive.md` (append only, never delete). Before archiving each entry, extract a 3–5 bullet continuity summary and write it to `## Continuity Archive` in state.md.

---

## `/gm import <filepath> [campaign-name]`

Import a pre-written campaign source and build a structured campaign from it.

**Supported formats:** PDF, markdown (.md), DOCX, plain text (.txt)

**Step 1 — Extract and assess the source:**
```bash
python3 scripts/import_campaign.py "<filepath>" --info
python3 scripts/import_campaign.py "<filepath>" --chunks  # total chunks
python3 scripts/import_campaign.py "<filepath>" --chunk 0  # read first chunk
```
For large sources (> 1 chunk), read subsequent chunks until you have enough to assess structure. You do not need to read every chunk before writing files — return to the source as needed.

**Step 2 — Determine campaign name** (use `[campaign-name]` if provided, otherwise derive from source title).

**Step 3 — Identify structure type:**
- `linear` — scene-chain A→B→C (dungeon crawl, one-shot, heist)
- `hub-and-spoke` — central hub + spoke locations in player-driven order (hexcrawl, published adventure module)
- `faction-web` — multi-faction city/complex with overlapping arcs (political, intrigue)

**Step 4 — Show a structured summary before writing any files:**
```
Source:   <title and author if present>
Campaign: <proposed name>
System:   <detected game system>
Type:     structured / <structure type>
Acts:     <N acts, N chapters>
NPCs:     <N named characters identified>
Factions: <N factions identified>
```
Confirm before proceeding.

**Step 5 — Create campaign files** at `~/open-tabletop-gm/campaigns/<name>/`:

- **world.md** — setting, geography, factions (with archetype, activity, goals), key locations, quest seeds
- **npcs.md** — one-line index (name | role | one trait | status); full entries with voice, goals, relationships, secrets in **npcs-full.md**
- **session-log.md** — Session 0 import record: source title, structure type, import date, summary of campaign premise
- **state.md** — from template; populate:
  - `## World State` — in-world start date if given, faction states, threat arc stage 1
  - `## Campaign Arc` — full act/chapter structure with key beats, telegraph scenes, and steering notes (use `type: structured` format)
  - `## Live State Flags` — empty at import, populated as sessions run

**Step 6 — Deliver a one-paragraph campaign brief** covering premise, tone, opening situation, and how the first session should begin.

---

## `/gm arc [status|advance|revise|view]`

Manage the dynamic campaign arc. Active only when `state.md → ## Campaign Arc` has `type: dynamic` — no-op for sandbox and structured campaigns.

- **`/gm arc`** or **`/gm arc status`** — print current act, current beat label, `what_changes` for the current beat, and `steering_notes`. Quick reference, one screen.

- **`/gm arc advance [beat-id]`** — mark the named beat complete (current beat if omitted). Remove from `outstanding_beats`. Advance `current_beat` to the next pending beat. If all beats in an act are complete, advance `current_act`. Update `steering_notes` to describe how to reach the newly current beat without forcing it.

  **When the final beat (3b) is marked complete — arc continuation:**
  `outstanding_beats` is now empty. Ask: *"The arc is complete. Continue the campaign with a new arc? [y/n]"*
  - **Yes** → run `/gm arc new` (see below).
  - **No** → mark campaign concluded. The arc stays in state.md as a record.

- **`/gm arc revise`** — revise the arc when a player choice significantly redirects the story. Update outstanding beats to fit the new direction. Log the revision in `revision_log`. The committed `resolution` shape should bend to the story, not break — revise beats, not the endpoint.

- **`/gm arc view`** — print the full arc yaml from state.md.

- **`/gm arc new`** — generate a new arc for a campaign that has completed its previous arc. A capable model (Opus-class or equivalent) is recommended for this step.

  The new arc must be **intentionally distinct** — not a continuation of the same conflict, but a new chapter that grows from the changed world. The resolution of arc N is the status quo of arc N+1.

  1. Read the completed arc's `resolution` field — this is now the world's baseline.
  2. Read `## World State` — faction shifts, threat changes, NPC status changes from the completed arc.
  3. Generate a new arc from this evolved world state following the same six-beat structure.
  4. Write it to `state.md → ## Campaign Arc` with `arc_number` incremented.
  5. Move the completed arc to `## Arc History` (append, never delete).
  6. Deliver a one-paragraph brief on the new arc's theme and opening pressure.
