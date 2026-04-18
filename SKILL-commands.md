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
14. Confirm creation. Offer `/gm character new`.

---

## `/gm save` — Session Log Archival

After session count > 3: keep only 2 most recent full entries in session-log.md. Older entries move to `session-log-archive.md` (append only). Extract 3-5 bullet continuity summary into `## Continuity Archive` in state.md per archived session.
