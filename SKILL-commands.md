# GM Skill — Command Procedures

Full step-by-step procedures for all `/gm` commands. Load this file at `/gm load` or before executing any slash command.

**Campaigns directory:** `~/open-tabletop-gm/campaigns/`
**Characters directory:** `~/open-tabletop-gm/characters/`
**Skill base directory:** the directory containing this file (SKILL.md, scripts/, systems/, etc.)

Do NOT run `git init` or any git commands in campaign directories. Do NOT create files outside the campaigns or characters directories unless explicitly asked.

---

## `/gm new <campaign-name> [system]`

1. If `[system]` not supplied, ask: *"Which game system? (dnd5e / or describe your own)"*
   - Known system → load `systems/<system>/system.md`
   - Unknown → ask player to describe the core dice mechanic; offer to scaffold a new `systems/<system>/system.md` from `systems/TEMPLATE.md`
2. Ask: *"Start the cinematic display companion? [y/n]"*
   - Yes → `bash <skill-base>/display/start-display.sh`; note the URL; set `_display_running = true` in state.md
   - No → continue without display
3. Create campaign directory at the absolute path `$HOME/open-tabletop-gm/campaigns/<name>/characters/` — this is always under the user's home directory, never inside the skill base directory.
   Copy blank templates from `<skill-base>/templates/` into the campaign directory: `state.md`, `world.md`, `npcs.md`, `session-log.md`
4. Ask: **party size** and **starting level**
5. **Tone/Genre Wizard** — present all four choices in one message:
   - Tone: `grimdark / dark fantasy / heroic / horror / political / swashbuckling / cosmic`
   - Magic level: `none / low / medium / high`
   - Setting type: `medieval / renaissance / ancient / nautical / underground`
   - Danger level: `lethal / gritty / standard / heroic`
   *(Randomise any blank with dice.py and log `"d6=N → [result]"` in world.md)*
6. **World Foundations** — geography, biome, climate, magic system, pantheon (2-3 active deities), calendar. Write to `## World Foundations` in world.md. Seed `state.md → ## World State → In-world date`.
7. **Three Truths** — one settlement, one nearby threat, one mystery with a clue trail. Write to respective sections in world.md.
8. **Threat Escalation Arc** — fill the five-stage table in world.md. Set current stage to 1. Write `Threat arc stage: 1` to `state.md → ## World State`.
9. **2 Factions** — archetype, current activity, relationship to party. Write to `## Factions` in world.md and one-line summaries to `state.md → ## World State`.
10. **3 NPCs with relationship web** — full entries: role, demeanor, motivation, secret, speech quirk, faction, current goal. Every NPC needs at least 2 relationships to others. Append to npcs.md.
11. **3-5 Quest Seeds** from threat, factions, mystery, NPC motivations. Write to `## Quest Seed Bank` in world.md.
12. Write state.md: session count 0, starting location, system, `_display_running` flag.
13. Confirm creation. Offer `/gm character new`.

---

## `/gm load <campaign-name>`

1. Read `~/open-tabletop-gm/campaigns/<name>/state.md` — confirm it exists.
2. Ask: *"Start the cinematic display companion? [y/n]"*
   - Yes → `bash <skill-base>/display/start-display.sh`; set `_display_running = true`
   - No → continue
3. Read `SKILL-scripts.md` (for script syntax this session)
4. Read `state.md`, `world.md`, `npcs.md`, and all `characters/*.md` in the campaign directory.
5. Load the system module: read `systems/<system>/system.md` (system is recorded in state.md).
6. If display is running, push full party stats to the sidebar. Push turn order if combat was active.
7. Deliver one in-character paragraph recapping the current situation — where the party is, what is at stake, what was last happening.
8. Enter active GM mode. No `/gm` prefix needed from this point.

---

## `/gm save`

Write session events to `session-log.md`. Update `state.md` (location, active quests, party HP/resources, recent events). Update any `characters/*.md` that changed. Mirror each updated character to `~/open-tabletop-gm/characters/<name>.md`.

Update `## Faction Moves` in state.md: for each active faction, record what they did while the party was occupied. One line per faction.

**Session log archival (after session count > 3):**
Keep only the 2 most recent full entries in session-log.md. Older entries move to `session-log-archive.md` (append only, never delete). Before archiving, extract a 3-5 bullet continuity summary into `## Continuity Archive` in state.md:

```markdown
### Session N — [date] — [one-line label]
- [Key fact that may resurface]
- [NPC revelation or exact wording of something important]
- [Roll outcome that changed the fiction]
- [Relationship shift, item acquired with story significance]
```

---

## `/gm end`

1. Run `/gm save`, then:
   a. Append a Session Recap block to session-log.md with key events and open threads.
   b. Ask: *"Quick calibration — what worked this session, and what would you adjust?"* Write to `### DM Calibration`. Skip if no answer.
   c. Update `## World State` in state.md: check threat arc stage, faction states, in-world date.
2. If `_display_running = true`, stop the display:
   ```bash
   kill $(cat <skill-base>/display/app.pid 2>/dev/null) 2>/dev/null && rm -f <skill-base>/display/app.pid
   ```

---

## `/gm abandon`

Exit the session without saving any state changes.

1. Confirm: *"Abandon session? All unsaved changes will be lost. Type 'yes' to confirm."*
2. Do NOT write to any campaign files.
3. Confirm: *"Session abandoned. Run `/gm load <campaign>` to reload from the last saved state."*

---

## `/gm list`

Read `~/open-tabletop-gm/campaigns/*/state.md`. Print a summary table: campaign name | system | last session date | session count.

---

## `/gm character new [campaign-name]`

1. Ask: name, race/species, class/role, background
2. Ask: *"In a sentence, what should the GM know about [Name]?"*
   - If answered: derive ONE pillar — Bond, Flaw, Ideal, or Goal. Store the raw sentence and derived pillar in `## Character Pillar`.
   - If skipped: leave blank. Do not invent one.
3. Follow the character creation procedure in `systems/<system>/system.md` for ability scores, derived stats, and starting equipment.
4. Write to `characters/<name>.md` using `<skill-base>/templates/character-sheet.md` as the base.
5. Add to `state.md` party line.
6. Mirror to global roster: `~/open-tabletop-gm/characters/<name>.md`

---

## `/gm character sheet [name]`

Read `characters/<name>.md` and display it cleanly. If name is omitted and only one character exists, show that one.

---

## `/gm characters`

List all characters in `~/open-tabletop-gm/characters/`. Display: name, race/class/level, origin campaign, last updated.

---

## `/gm roll <notation>`

Run `python3 <skill-base>/scripts/dice.py <notation>`. Display output verbatim. Examples: `d20`, `2d6+3`, `d20 adv`, `4d6kh3`.

---

## `/gm combat start`

1. Identify all combatants; collect name, initiative modifier, HP, AC, type (pc/enemy) for each.
2. Run `python3 <skill-base>/scripts/combat.py init '<JSON>'` to auto-roll initiative. Display the tracker and per-combatant roll breakdown.
3. Write active combat state to `state.md → ## Active Combat`.
4. Step through turns using the per-turn combat sequence in SKILL.md.
5. On combat end: update HP in character sheets, clear `## Active Combat`, narrate aftermath, award XP or equivalent.

---

## `/gm rest <short|long>`

Follow the rest procedure defined in `systems/<system>/system.md` for HP recovery, resource recharge, and time advancement. Run `python3 <skill-base>/scripts/tracker.py` to clear expired conditions. Update `state.md` in-world date.

---

## `/gm recap`

Read session-log.md. Deliver a 3-5 sentence in-character narrator recap of the most recent session entry.

---

## `/gm world`

Read and display `world.md` for the current campaign.

---

## `/gm quests`

Read `state.md`. Display the Active Quests and Open Threads sections.

---

## `/gm tutor on` / `/gm tutor off`

Toggle tutor/learning mode. Write `tutor_mode: true/false` to `state.md → ## Session Flags`. Session-scoped. (Full tutor mode behavior is in SKILL.md.)

---

## `/gm display [start|stop|status]`

- `start` → `bash <skill-base>/display/start-display.sh`; print URL
- `stop` → `kill $(cat <skill-base>/display/app.pid) 2>/dev/null && rm -f <skill-base>/display/app.pid`
- `status` → `curl -sk https://localhost:5001/ping`
