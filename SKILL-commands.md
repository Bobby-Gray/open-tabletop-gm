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
| `/gm npc <name>` | Generate or retrieve an NPC. Write to npcs.md / npcs-full.md. **New:** before write, run `name_registry.py check` and surface any prior use; record after write. |
| `/gm npc rename "Old Name" <"New Name"\|random> [--type pc] [--dry-run] [--yes] [--include-archive]` | Rename a character across npcs.md, npcs-full.md, state.md, session-log.md, world.md, session_tail.json, graph.json (node + edges preserved), and `characters/<slug>.md` if `--type pc`. Backs up the campaign first. `--random` picks from a bundled fantasy-name corpus, rejecting any slug already in the registry. session-log-archive.md left untouched by default + audit note added. Maps to: `python3 <skill-base>/scripts/npc_rename.py --campaign <current> --old "..." --new "..."`. |
| `/gm registry <subcommand>` | Cross-campaign name registry stored at `<GM_CAMPAIGN_ROOT>/.name_registry.json`. Subcommands: `rebuild [--include-prose]`, `list [--campaign C] [--type] [--source canonical\|prose]`, `lookup <name>`, `check <name> [--json]` (exit 0 unique, 1 duplicate), `add`, `retire`. Maps to `python3 <skill-base>/scripts/name_registry.py <subcommand>`. Severity (`warn`\|`strict`\|`none`) configurable via `<GM_CAMPAIGN_ROOT>/.name_registry_config.json`. |
| `/gm import <filepath> [campaign-name]` | Import a pre-written campaign source (PDF, MD, DOCX, TXT). See `/gm import` procedure below. |
| `/gm arc [status\|advance\|revise\|view]` | Manage the dynamic campaign arc. See `/gm arc` procedure below. |
| `/gm path [<new-path>\|reset]` | View or configure where campaign data is stored (`GM_CAMPAIGN_ROOT`). Follow `/gm path` branch. |
| `/gm update [--check]` | Pull the latest skill changes from origin/main. Follow `/gm update` branch. |
| `/gm graph <subcommand>` | Campaign relationship graph: `init`, `add-node`, `add-edge`, `close-edge`, `supersede-edge`, `list`, `show`, `subgraph`, `scene-context`, `extract`, `extract-apply`. See `/gm graph` procedure below. |

---

## `/gm new` — World Generation Procedure

1. If `[system]` not supplied, ask which game system
2. **System version selection** — if the chosen system has more than one supported version (consult `systems/<system>/system.md → ## System Versions`), ask which to use. The default if the GM has no preference is whatever the system module declares as default. The chosen value is stamped into `state.md` header as `**System Version:** <value>` at step 13. Skip this step if the system module declares no versions.
3. Create campaign directory at `~/open-tabletop-gm/campaigns/<name>/characters/`
4. Copy blank templates from `systems/<system>/` and `templates/` into the campaign directory
5. Ask: party size and starting level
6. **Tone/Genre Wizard** — present all four in one message: tone · magic level · setting type · danger level. Randomise any blank with dice.py.
7. **World Foundations** — geography, biome, climate, magic system, pantheon, calendar → write to `## World Foundations` in world.md
8. **Three Truths** — one settlement, one nearby threat, one mystery → write to world.md
9. **Threat Arc** — five-stage table in world.md; set stage 1; write to state.md
10. **2 Factions** — archetype, activity, relationship to party → world.md + state.md summary
11. **3 NPCs** — one-line index in npcs.md; full detail in npcs-full.md; each needs 2+ relationships
12. **3-5 Quest Seeds** → write to `## Quest Seed Bank` in world.md
13. Write state.md: session count 0, starting location, system, display flag, and the chosen `**System Version:**` value on the header line (from step 2; omit the field if the system has no versions)
14. **Dynamic Campaign Arc** — optional arc generation. Ask: *"Generate a committed narrative arc? [y/n — recommended]"*

   **If yes:** Drawing from theme, threat arc stages, factions, Three Truths, NPC motivations, and quest seeds, derive:
   - `theme` — one sentence: what this story is ultimately about (not what happens, but what it means)
   - `resolution` — the committed endpoint shape: not specific events, but the emotional/thematic truth if the party succeeds
   - Six beats across three acts (Inciting Incident, Complication, Midpoint Shift, All Is Lost, Final Confrontation, Resolution)
   - For each beat: `label`, `what_changes` (**CRITICAL: write as a CONSEQUENCE, not an event** — a state-of-the-world AFTER the beat, not one specific thing that happens. Consequences survive when players pre-empt the obvious delivery; events break and the beat goes stale. Example contrast for an All Is Lost beat: ❌ event-shaped *"the antagonist's preferred candidate takes the open council seat"* — fragile, can't land if the party flips the clerk in time; ✅ consequence-shaped *"the party experiences a concrete cost from the antagonist's escalation that they cannot reverse"* — survives multiple delivery paths), `world_pressure` (the faction/NPC move that delivers it — MAY be event-shaped, but if pre-empted, expect to revise per SKILL.md rule 8)

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
   - If `## Campaign Arc` has `type: dynamic`, do all of:
     - Ask: *"Did any arc beats land this session? [beat id(s) like '1b 2a', or 'none']"*
     - If beats landed: run `/gm arc advance <beat-id>` for each.
     - **Pre-emption check** (added 2026-05-01): for each remaining outstanding beat whose `world_pressure` was visibly delivered this session (the named world event actually appeared in narration or Faction Moves), evaluate whether the beat's `what_changes` consequence ALSO landed. Three possible states:
       - **Landed cleanly** → mark beat complete via `/gm arc advance`.
       - **Pressure absorbed without consequence** → the beat is overdue and its current shape no longer fits. **Run `/gm arc revise` immediately**; do not just update `steering_notes`. The beat's `what_changes` was event-shaped when it should be consequence-shaped — revise both `what_changes` and `world_pressure` to fit a path that DOES land. The committed shape bends; it does not break.
       - **Pressure not yet delivered** → leave beat alone; expected to deliver next session.
     - Update `steering_notes` for the next outstanding beat with the *consequence shape* expected, not the specific event.
6. **Session log archival** (after session count > 3): keep only the 2 most recent full entries in session-log.md. Move older entries to `session-log-archive.md` (append only, never delete). Before archiving each entry, extract a 3–5 bullet continuity summary and write it to `## Continuity Archive` in state.md.
7. **Tail verification** (added 2026-05-01): if the display companion is running, verify the campaign-side `session_tail.json` is healthy before closing the session:
   ```bash
   bash display/verify_tail.sh <campaign-name>
   ```
   Exit 0 = healthy. Exit 1 = missing/empty/corrupt → write a canonical replacement to `<GM_CAMPAIGN_ROOT>/<name>/session_tail.json` from session context (5–8 entries, each `{"text": "...", "_camp": "<name>"}`) using `display/write_canonical_tail.py`. The display's own `_persist_tail` has skip-on-empty + atomic-write guards (since 2026-05-01), but the backstop ensures a worst-case file state is impossible. After display kill (if applicable), re-run `verify_tail.sh` to catch any final-write race; restore from the canonical version if needed.

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

- **`/gm arc revise`** — revise the arc when a player choice significantly redirects the story OR when the auto-trigger from /gm save's pre-emption check fires (most common case). The committed `resolution` shape should bend to the story, not break — revise beats, not the endpoint.
  1. Show all outstanding beats with their current `what_changes` and `world_pressure`.
  2. Ask: *"What's changed in the story that the arc doesn't reflect?"* — or, when auto-triggered by pre-emption, name the pre-empted beat directly: *"Beat 2b's pressure delivered but the consequence didn't land. Picking a revision path…"*
  3. **Apply one of three landing-path templates** (per SKILL.md rule 8):
     - **Cost path** — `what_changes` becomes "the party paid a concrete cost for moving fast"; `world_pressure` becomes the specific cost (cover blown, ally compromised, position lost). Best when the party pre-empted cleanly.
     - **Secondary consequence path** — `what_changes` becomes "the world responded to being pre-empted in a way the party didn't anticipate"; `world_pressure` becomes the new escalation. Best when the antagonist is intelligent and adaptive.
     - **Deferred path** — keep the original `what_changes` shape; rewrite `world_pressure` to a NEW pressure pointing at the same consequence, scheduled for the next 1–2 sessions. Best when the original consequence is still narratively essential and only the timing slipped.
  4. Rewrite `what_changes` (consequence-shaped per the rule in /gm new step 14) and `world_pressure` (event-shaped is fine) for the affected beat. Do NOT modify completed beats.
  5. Append to `revision_log`: `"<date>: <beat-id> — <path: cost/secondary/deferred> — <one-sentence why>"`
  6. Update `steering_notes` to describe the next session's expected delivery.
  7. Confirm what was revised. Show before/after for `what_changes` and `world_pressure`.

- **`/gm arc view`** — print the full arc yaml from state.md.

- **`/gm arc new`** — generate a new arc for a campaign that has completed its previous arc. A capable model (Opus-class or equivalent) is recommended for this step.

  The new arc must be **intentionally distinct** — not a continuation of the same conflict, but a new chapter that grows from the changed world. The resolution of arc N is the status quo of arc N+1.

  1. Read the completed arc's `resolution` field — this is now the world's baseline.
  2. Read `## World State` — faction shifts, threat changes, NPC status changes from the completed arc.
  3. Generate a new arc from this evolved world state following the same six-beat structure.
  4. Write it to `state.md → ## Campaign Arc` with `arc_number` incremented.
  5. Move the completed arc to `## Arc History` (append, never delete).
  6. Deliver a one-paragraph brief on the new arc's theme and opening pressure.

---

## `/gm graph <subcommand>` — campaign relationship graph

Local-only typed-edge relationship graph supplementing markdown. Stored at `~/open-tabletop-gm/campaigns/<name>/graph.json` (or wherever `GM_CAMPAIGN_ROOT` points). Supplements `npcs-full.md` / `session-log.md` — does not replace them. Edges are time-stamped (`since_session` / `until_session`), so historical state is recoverable.

**Auto-pulled at `/gm load`** (scene-context, see SKILL-branches.md → `/gm load` → Step 4) and **swept at `/gm save`** (relationship-shift extraction, see SKILL-branches.md → `/gm save` → Step 4). The GM also uses `/gm graph scene-context` on demand mid-session, especially before heavy social or political scenes.

This fork ships a **manual + query-only** graph. The Haiku-backed `extract` / `extract-apply` subcommands from the upstream claude-dnd-skill are intentionally not included — they require Claude API access. When the deterministic Phase 2 verb-table extractor is built it will land here as a fully local replacement.

All subcommands invoke `python3 <skill-base>/scripts/gm_graph.py <subcommand> --campaign <name> [args]`.

### `/gm graph init [campaign-name]`
First-time bootstrap. Read existing `npcs.md` / `world.md` / `state.md` for the campaign. Propose a node list (NPCs as `npc_*`, factions as `faction_*`, key locations as `place_*`) and a starter edge list (faction membership from npcs.md tables, NPC location from "Lives in / Based at" fields, faction relationships from world.md). Display the proposed list to the GM and **ask for approval** before writing — do not silently extract. After approval, run `add-node` and `add-edge` for each. Use `--since` matching state.md's current session count.

For existing campaigns being initialized for the first time, the `/gm load` flow offers to back the campaign directory up first; honour that flow rather than running init from a cold prompt.

### `/gm graph add-node --type T --name N [--tags ...] [--summary ...]`
Add a single node. Type is open vocab; suggested: `npc`, `faction`, `place`, `item`, `thread`. Default id is `<type>_<name-slug>`.

### `/gm graph add-edge --from <id> --to <id> --type T [--since N] [--note ...]`
Add a typed edge between two existing nodes. Edge type is open vocab; common: `loyal_to`, `opposes`, `allied_with`, `member_of`, `lives_in`, `controls`, `knows_about`, `friends_with`, `lover_of`, `owes`, `rules`, `related_by_blood`, `advances_thread`, `blocks_thread`. Always supply `--since` (the current session number from state.md) so historical replay works.

### `/gm graph close-edge --id <edge-id> --at-session N [--anchor "..."]`
Mark an edge as ended at session N (e.g. when an alliance breaks). Original edge is preserved with `until_session` set; it remains visible in historical queries but is excluded from "active at session ≥ N" results. The optional `--anchor "..."` records the verbatim phrase that justifies the closure as a `closed_anchor` field on the edge.

### `/gm graph supersede-edge --id <edge-id> [--by <correct-edge-id>] [--reason "..."]`
Mark an edge as wrong (hard retcon) — use when canon explicitly contradicts a prior extraction. The wrong edge stays in the graph for audit trail; `scene-context` filters it out, but `subgraph` and `show` queries can still surface it. Distinct from `close-edge`: closing ends a real relationship cleanly; superseding says the original was wrong. Optional `--by` links to the corrected edge.

### `/gm graph list [--type T] [--at-session N]`
Print a compact node table grouped by type. With `--at-session`, also reports active edge count at that session.

### `/gm graph show --id <node-id>`
Print one node with all incoming and outgoing edges.

### `/gm graph scene-context --place <id> [--present id1,id2] [--threads id1,id2] [--hops H] [--at-session N]`
**Primary query for in-session use.** Returns a focused subgraph from the current scene (place + present NPCs + active threads) bounded by hop count, optionally filtered to edges active at a given session. Output is grouped: nodes by type, then a relationships block. Default `--hops 2`. Use this when you need to recall who-relates-to-whom in the current scene without re-reading `npcs-full.md` or session-log archives.

### `/gm graph subgraph --seed <id> [--seed <id>] [--hops H] [--at-session N]`
Lower-level traversal — same as `scene-context` but with arbitrary seed nodes. Use when the scene framing doesn't fit (e.g. tracing faction politics independent of any specific place).

### `/gm graph extract [--write FILE] [--last-session-only]`
Pattern-match the campaign's session-log against the verb-table seed (`data/graph/verb_table_seed.yaml`) and propose edges with verbatim source-anchors. **LLM-free** — uses the deterministic extractor only. Output JSON has the same schema as the upstream Haiku extractor. With `--write FILE`, writes proposals to disk for `extract-apply` to consume; without, prints to stdout. `--last-session-only` narrows the scan to the most recent `## Session N` block.

### `/gm graph extract-apply --proposals FILE [--pick N1,N2,...] [--review] [--no-auto-nodes]`
Apply edge proposals from a JSON file produced by `extract --write`. Default behaviour: apply all. `--pick "1,3,5"` applies only the listed proposal numbers. `--review` walks proposals one at a time with `y / n / q` prompts (mutually exclusive with `--pick`). Categorical proposals automatically create category nodes (`type: category`, `category_node: true`); other unknown entities are auto-created as placeholder npcs unless `--no-auto-nodes` is set.

### Suggested GM workflow

1. **First session after install:** `/gm load` will offer to initialize the graph (with a backup-first prompt). Accept; review the proposed seed; approve.
2. **During session:** when a relationship shifts in narration, run `/gm graph add-edge` (or `close-edge`) with `--since` set to the current session number. Don't batch this — record at the moment of the narrative change so you don't forget.
3. **Before a heavy social/political scene:** run `/gm graph scene-context --place <current-place> --present <key-NPCs>` to refresh which relationships matter right now.
4. **At `/gm save`:** review the session log and add any edges you missed during play (the save flow runs an automatic sweep and presents proposals for approval).
