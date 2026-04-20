# open-tabletop-gm

An LLM-agnostic Game Master framework for persistent tabletop RPG campaigns. Built to run on any model available through [OpenCode](https://opencode.ai), locally hosted models via [LM Studio](https://lmstudio.ai), or any other LLM service.

D&D 5e is included as the reference system. Any other tabletop RPG can be added by writing a system module — see [SYSTEM-PORTING.md](SYSTEM-PORTING.md).

> **Using Claude?** This framework was extracted from [`claude-dnd-skill`](https://github.com/Bobby-Gray/claude-dnd-skill), a Claude Code-specific version with deeper integration. If you're running Claude Code, that repo will give you a more optimised experience.

![open-tabletop-gm demo](docs/screenshots/demo-v2.gif)

---

## What it is

A GM framework that offloads everything mechanical to Python so the LLM can focus on narration and judgment:

- **Persistent campaigns** — state, world, NPCs, and character sheets survive across sessions in plain Markdown files
- **Python toolchain** — dice, combat initiative, HP tracking, timed effects, conditions, calendar, campaign search; all run locally with zero LLM involvement
- **Cinematic display companion** — optional Flask web app that renders your session as a live display on any browser or TV, with a real-time stat sidebar, effect pills, and player input panel
- **System plugin architecture** — D&D 5e ships as the reference implementation; swap in any TTRPG by writing a system module

---

## System plugin architecture

The framework is split into two layers:

```
SKILL.md                    ← GM core: pacing, NPCs, improvisation, world craft
                               Never changes. Works for any game.

systems/<your-system>/
  system.md                 ← Your game's rules: dice, stats, health, resources
                               Loaded alongside SKILL.md at session start.
```

`SKILL.md` contains everything about *being a good GM*. `system.md` contains everything about *your specific game*. The GM model reads both at session start — it brings the craft, your system module brings the rules.

**D&D 5e ships as the reference implementation.** It demonstrates what a complete system module looks like: dice conventions, ability scores, spell slots, conditions, death saves, SRD lookup, and character scripts.

**Building a new system module** takes one file to start — a filled-in `systems/TEMPLATE.md` for your game. You can start with just dice resolution and health, play a session, then iterate. Full porting guide: [SYSTEM-PORTING.md](SYSTEM-PORTING.md).

---

## Supported games (out of the box)

| System | Module | Notes |
|--------|--------|-------|
| D&D 5e | `systems/dnd5e/` | Full support — scripts, SRD dataset, character tools |

**Adding your own:** Copy `systems/TEMPLATE.md` to `systems/<your-system>/system.md` and fill it in. See [SYSTEM-PORTING.md](SYSTEM-PORTING.md) for a compatibility breakdown of popular systems (Pathfinder 2e, Vampire: The Masquerade, Cyberpunk RED, Warhammer 40k).

---

## Setup

### 1. Install OpenCode

[opencode.ai](https://opencode.ai) — supports Anthropic, OpenAI, Google, Ollama, LM Studio, and any OpenAI-compatible endpoint.

### 2. Clone this repo

```bash
git clone https://github.com/Bobby-Gray/open-tabletop-gm
cd open-tabletop-gm
```

### 3. Install Python dependencies (display companion only)

The core scripts have no dependencies. The optional display companion requires:

```bash
cd display
pip3 install -r requirements.txt
```

### 4. Configure OpenCode

Point OpenCode at this skill by adding the following to your OpenCode config (`~/.config/opencode/opencode.json`):

```json
{
  "instructions": [
    "/path/to/open-tabletop-gm/no_think.md",
    "/path/to/open-tabletop-gm/paths.md",
    "/path/to/open-tabletop-gm/SKILL-commands.md",
    "/path/to/open-tabletop-gm/SKILL-branches.md"
  ]
}
```

`SKILL.md` (the GM persona) is not loaded at startup — it is read from disk the first time a session is loaded, keeping the standing system prompt lean (~2,300 tokens). See [docs/LLM-GUIDE.md](docs/LLM-GUIDE.md) for why this matters on smaller models.

For a local model via LM Studio, add your provider config:

```json
{
  "provider": {
    "lmstudio": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LM Studio (local)",
      "options": {
        "baseURL": "http://localhost:1234/v1"
      },
      "models": {
        "your-model-id": {
          "name": "Your Model Name"
        }
      }
    }
  }
}
```

### 5. Start a campaign

```
/gm new <campaign-name>
```

The skill walks you through world creation, tone selection, and character setup. Everything is saved to plain Markdown files you can read and edit directly.

---

## Quick Start

**Improvised campaign** — GM generates world and narrative arc:

```
/gm new my-campaign          # generates world, factions, NPCs, optional story arc
/gm character new            # create a character
/gm load my-campaign         # start a session
```

**Structured campaign** — import a pre-written module:

```
/gm import module.pdf my-campaign   # extract structure and build campaign files
/gm load my-campaign                # start a session — GM enforces the arc beats
```

Once loaded, type naturally — no `/gm` prefix needed. The GM interprets all input as in-game action.

---

## Commands

| Command | What it does |
|---------|-------------|
| `/gm new <name> [system]` | Create a new campaign with world generation |
| `/gm load <name>` | Load an existing campaign and resume |
| `/gm save` | Write session events to log, update state |
| `/gm end` | Save and close session |
| `/gm abandon` | Exit without saving — discards all unsaved changes from this session |
| `/gm list` | List all campaigns |
| `/gm import <filepath> [name]` | Import a pre-written campaign from PDF, markdown, DOCX, or plain text |
| `/gm character new` | Create a new character (uses system module for rules) |
| `/gm character sheet [name]` | Display character sheet |
| `/gm character import <name>` | Import a character from another campaign |
| `/gm characters` | List all characters in the global roster |
| `/gm level up [name]` | Level up a character (D&D / level-based systems) |
| `/gm npc [name]` | Generate or portray an NPC |
| `/gm roll <notation>` | Roll dice: `d20`, `2d6+3`, `d20 adv` |
| `/gm combat start` | Start combat with initiative |
| `/gm rest short\|long` | Short or long rest |
| `/gm recap` | In-character session recap |
| `/gm world` | Display world notes |
| `/gm quests` | Display active quests and open threads |
| `/gm tutor on\|off` | Toggle learning mode hints |
| `/gm arc [status\|advance\|revise\|view]` | Manage the campaign narrative arc |
| `/gm display on [--lan]` | Start the cinematic display companion (optionally in LAN mode) |
| `/gm display off` | Stop the display companion |

---

## Narrative arc system

Both campaign modes use the same six-beat three-act structure tracked in `state.md`. Arc type determines how it's populated.

### Improvised (type: dynamic)

Generated at `/gm new` from the world's threat, factions, and setting. Beats are defined by `what_changes` — the narrative consequence that must land — not by a specific scene or event. The GM stays flexible on *how* each beat arrives while committing to *that* it must.

| Act | Beat | What it marks |
|-----|------|---------------|
| 1 | Inciting Incident | The threat becomes personal |
| 1 | Complication | The problem is bigger than it first appeared |
| 2 | Midpoint Shift | What the party thought they were doing changes |
| 2 | All Is Lost | A genuine setback — something fails or collapses |
| 3 | Final Confrontation | The decisive moment the campaign turns on |
| 3 | Resolution | What's different about the world and characters after |

Arc beats are tracked at `/gm end` and marked complete via `/gm arc advance`. When a player choice redirects the story, `/gm arc revise` updates outstanding beats to fit the new direction. When all six beats resolve, a new arc can be generated from the consequences of the first — same world, new story question.

### Structured (type: structured)

Populated by `/gm import` from the source material. Acts contain chapter-level key beats, telegraph scenes that set up each beat naturally, and branching notes. The GM telegraphs before delivering any required beat and steers with world pressure rather than hard walls when players drift.

Both arc types are fully compatible with all system modules and the display companion.

---

## Display companion

An optional Flask web app that renders your session as a cinematic full-screen display — stat sidebar, live effect tracking, player input panel, animated backgrounds.

```bash
bash display/start-display.sh          # localhost, HTTP (default)
bash display/start-display.sh --lan    # LAN mode (phones, tablets, TV), HTTP
bash display/start-display.sh --lan --tls  # LAN mode, HTTPS (public/untrusted networks)
open http://localhost:5001
```

Runs entirely independently of the LLM. If the display isn't running, all scripts fail silently — nothing breaks.

> Screenshots below show the D&D 5e system module (included). The display companion works identically with any system module.

![Session display with stat sidebar and NPC dialogue](docs/screenshots/screenshot-npc-dialogue.png)

![Full display view with combat roll and player input panel](docs/screenshots/screenshot-display.png)

| Stat sidebar | Character sheet |
|---|---|
| ![Stat sidebar](docs/screenshots/sidebar-card.png) | ![Character sheet modal](docs/screenshots/character-sheet-modal.png) |

### Viewing options

| Option | How |
|--------|-----|
| **TV — Cast tab** | Chrome → three-dot menu → Cast → Cast tab; select your Chromecast or smart TV |
| **TV — Screen mirror** | macOS: Control Centre → Screen Mirroring → Apple TV / AirPlay receiver |
| **iPad / tablet** | Start with `--lan`, open `http://<your-ip>:5001` in Safari or Chrome; works in landscape |
| **Second monitor** | Open `http://localhost:5001` in a browser window and drag it to the second display |

### TLS / HTTPS (optional)

HTTP is the default. Use `--tls` only on public or untrusted networks. When passed:
- A self-signed cert is auto-generated if `cert.pem` is not present
- A plain HTTP server starts on `:8080` to serve `cert.pem` for download
- Per-platform install instructions are printed to the terminal (iOS, Android, Mac)

For iOS: open `http://<your-ip>:8080/cert.pem` in Safari → tap Allow → Settings → General → VPN & Device Management → install profile → Certificate Trust Settings → enable full trust.

### Player input from the companion UI

Players open the companion on their phone browser. The **Party Input** panel lets each player:

1. **Stage** an action — type it and hit Stage. It appears in the panel visible to everyone.
2. **Mark Ready** — confirms the action is final.
3. **Skip** — passes the turn without typing.

When a submission is picked up, three pulsing dots confirm the GM received it. If the player's device has not been seen before, the GM's screen shows a one-time approval card — approved devices are remembered across restarts.

Staged input text is cached in the browser — if the page reloads before the GM picks it up, the text is restored automatically.

### Scene detection

The server scans narration text for keywords and crossfades the background gradient to match the current environment. Scenes change automatically as the story moves.

| Scene | Trigger keywords | Particles |
|-------|-----------------|-----------|
| Tavern | inn, hearth, ale, tallow, barkeep | embers |
| Dungeon | corridor, torch, portcullis, dank | dust |
| Ocean / Docks | dock, harbour, wave, tide, ship | ripples |
| Forest | tree, canopy, moss, thicket, grove | leaves |
| Crypt | tomb, undead, skeleton, burial | smoke |
| Arcane | ritual, rune, sigil, incantation | sparks |
| Mountain | glacier, frost, blizzard, ridge | snow |
| Cave | stalactite, grotto, echo, drip | mist |
| Night | midnight, moon, constellation | stars |
| City / Town | market, cobble, district, crowd | rain |
| + 7 more | mine, castle, ruins, desert, fire, temple, swamp | — |

Scene transitions crossfade over ~2.5 seconds. The server maintains a 20-chunk rolling window so scenes don't flicker on single matches.

### Dynamic sky canvas

A canvas layer above the scene background renders a live sky driven by `world_time` data:

- **Time of day** — sun arcs from dawn through midday to dusk; crescent moon and stars at night; orange horizon at twilight
- **Weather** — calm: light clouds; overcast: heavy dark clouds; rainy: dense cover, muted palette; stormy: near-black sky
- **Clouds** — five objects each built from overlapping circles; drift slowly and wrap

Push world time after session load and after any rest or time advance:

```bash
python3 display/push_stats.py --world-time \
  '{"date":"Day 7","day_name":"Starday","time":"morning","season":"Winter","weather":"overcast"}'
```

Valid `time` values: `dawn`, `morning`, `midday`, `afternoon`, `evening`, `dusk`, `night`  
Valid `weather` values: `calm`, `clear`, `overcast`, `rainy`, `stormy`

### Sound effects

Narration text is scanned server-side for 11 SFX categories. Matches trigger a synthesized WAV played via Web Audio API on any device with the tab open — no server audio output.

```
impact · sword · arrow · shout · thud · magic · coins · door · low_hum · fire · breath
```

SFX synthesis requires numpy. If numpy is not installed the feature degrades silently. Toggle via the **Sound Effects** switch in the top-right of the display.

### Character sheet modal

Click or tap any character card in the sidebar to open a full character sheet — attacks, features, and inventory. Works on desktop and on phones/tablets connected via LAN.

Include a `sheet` field when pushing stats to populate the modal:

```bash
python3 display/push_stats.py --replace-players --json '{
  "players": [{
    "name": "Aldric",
    "hp": {"current": 14, "max": 18},
    "sheet": {
      "attacks": [{"name": "Longsword", "bonus": "+5", "damage": "1d8+3", "type": "Slashing"}],
      "features": [{"name": "Second Wind", "text": "Bonus action: regain HP. Short rest recharge."}],
      "inventory": ["Longsword", "Chain Mail", "Shield", "15 gp"]
    }
  }]
}'
```

Close with **Esc**, clicking outside the panel, or the ✕ button.

### Session replay buffer

The server buffers the last 60 narration chunks to disk (`text_log.json`). Reconnecting browsers — Chromecast drops, tab refreshes — replay the full session history automatically. No narration is lost on reconnect.

### GM Help button

A **◈ GM Help** button sits in the bottom-right corner of the display. Click it and within a few seconds a contextual hint is generated from the current scene state and pushed to the display — no CLI command needed. Hint blocks are collapsed by default; click to expand. Warnings use an amber border to flag irreversible choices.

See [display/README.md](display/README.md) for full documentation.

---

## File layout

```
open-tabletop-gm/
  SKILL.md              ← GM persona and craft (read at session load, not startup)
  SKILL-commands.md     ← command signature reference (always in context)
  SKILL-branches.md     ← branch router: maps each command to its procedure (always in context)
  no_think.md           ← suppresses chain-of-thought preamble on local models
  paths.md              ← absolute path constants for this installation
  SYSTEM-PORTING.md     ← guide for adding new game systems
  systems/
    dnd5e/              ← D&D 5e reference implementation
      system.md         ← D&D 5e rules context
      ability-scores.py
      character.py
      lookup.py
      data/             ← bundled SRD dataset
    TEMPLATE.md         ← scaffold for building a new system module
  scripts/              ← universal scripts (dice, combat, tracker, calendar, search)
    startup.md          ← display push syntax (loaded only when display is ON at session start)
    combat.md           ← combat script syntax (loaded only at /gm combat start)
    general.md          ← dice, calendar, search syntax (loaded on demand)
    character.md        ← character creation script syntax (loaded on demand)
  display/              ← cinematic display companion (Flask)
  templates/            ← blank campaign file templates
  probe/                ← model probe tool for testing instruction-following
    probe.py            ← runs 5 test cases against any OpenAI-compatible endpoint
    run-openrouter.sh   ← sequential runner for OpenRouter free/paid models
```

Campaign data lives outside the repo:
```
~/.local/share/open-tabletop-gm/campaigns/<name>/
  state.md / world.md / npcs.md / session-log.md / characters/
```

---

## Performance on local / smaller models

The Python toolchain offloads everything mechanical — dice, HP math, initiative, timed effects, conditions — so the LLM only handles narration and judgment calls. This means smaller models remain functional even when creative output is limited.

The main constraint for local models is **agentic tool-call depth**. open-tabletop-gm is not a chatbot — it executes sequences of tool calls (bash, file reads) before responding. Models below ~70B parameters degrade after 4–5 sequential tool calls, drifting from their instructions toward the most recently read content. The routing architecture in SKILL-branches.md reduces the standing system prompt to ~2,300 tokens (down from ~18,000) to mitigate this, but it does not eliminate it at 24B and below.

**Practical hardware guidance:**
- **MacBook Air / 24GB unified memory:** Local inference below 70B is unreliable for session load. Use OpenRouter instead — 10 models tested, all scored cleanly, cost is ~$0.01–0.05/session on paid endpoints.
- **64GB+ machine (M3 Max, M4 Max, or equivalent):** Local inference becomes viable at 70B. Qwen3-70B is the recommended starting point.
- **Multi-GPU workstation:** All local models viable.

See [docs/LLM-GUIDE.md](docs/LLM-GUIDE.md) for full probe results, token usage data, and hardware recommendations.

See [SYSTEM-PORTING.md — What to expect from smaller/local models](SYSTEM-PORTING.md#what-to-expect-from-smallerlocal-models) for details.

---

## Looking for the Claude-optimised version?

If you're running Claude Code, [`claude-dnd-skill`](https://github.com/Bobby-Gray/claude-dnd-skill) is the dedicated version with model routing, deeper tool integration, and features built specifically for Claude's capabilities.

---

## Contributing

System modules for new games are the most valuable contribution. If you've built and tested a module for a system not listed here, a PR adding `systems/<your-system>/` is welcome. Include at minimum a filled-in `system.md` and a note in the PR about what you tested and how well it worked.
