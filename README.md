# open-tabletop-gm

An LLM-agnostic Game Master framework for persistent tabletop RPG campaigns. Built to run on any model available through [OpenCode](https://opencode.ai), locally hosted models via [LM Studio](https://lmstudio.ai), or any other LLM service.

D&D 5e is included as the reference system. Any other tabletop RPG can be added by writing a system module — see [SYSTEM-PORTING.md](SYSTEM-PORTING.md).

> **Using Claude?** This framework was extracted from [`claude-dnd-skill`](https://github.com/Bobby-Gray/claude-dnd-skill), a Claude Code-specific version with deeper integration. If you're running Claude Code, that repo will give you a more optimised experience.

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
  "instructions": "/path/to/open-tabletop-gm/SKILL.md"
}
```

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

## Commands

| Command | What it does |
|---------|-------------|
| `/gm new <name>` | Create a new campaign with world generation |
| `/gm load <name>` | Load an existing campaign and resume |
| `/gm save` | Write session events to log, update state |
| `/gm end` | Save and close session |
| `/gm list` | List all campaigns |
| `/gm character new` | Create a new character (uses system module for rules) |
| `/gm character sheet [name]` | Display character sheet |
| `/gm character import <name>` | Import a character from another campaign |
| `/gm level up [name]` | Level up a character (D&D / level-based systems) |
| `/gm npc [name]` | Generate or portray an NPC |
| `/gm roll <notation>` | Roll dice: `d20`, `2d6+3`, `d20 adv` |
| `/gm combat start` | Start combat with initiative |
| `/gm rest short\|long` | Short or long rest |
| `/gm recap` | In-character session recap |
| `/gm world` | Display world notes |
| `/gm quests` | Display active quests and open threads |
| `/gm tutor on\|off` | Toggle learning mode hints |
| `/gm display start\|stop` | Start/stop the cinematic display companion |

---

## Display companion

An optional Flask web app that renders your session as a cinematic full-screen display — stat sidebar, live effect tracking, player input panel, animated backgrounds.

```bash
bash display/start-display.sh          # localhost
bash display/start-display.sh --lan    # LAN mode (phones, tablets, TV)
open https://localhost:5001
```

Runs entirely independently of the LLM. If the display isn't running, all scripts fail silently — nothing breaks.

See [display/README.md](display/README.md) for full documentation.

---

## File layout

```
open-tabletop-gm/
  SKILL.md              ← GM core (load this in OpenCode)
  SKILL-commands.md     ← full command procedures
  SKILL-scripts.md      ← script syntax reference
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
  display/              ← cinematic display companion (Flask)
  templates/            ← blank campaign file templates
```

Campaign data lives outside the repo:
```
~/.local/share/open-tabletop-gm/campaigns/<name>/
  state.md / world.md / npcs.md / session-log.md / characters/
```

---

## Performance on local / smaller models

The Python toolchain offloads everything mechanical — dice, HP math, initiative, timed effects, conditions — so the LLM only handles narration and judgment calls. This means smaller models remain functional even when creative output is limited.

Tested on Qwen3 14B (local via LM Studio): combat mechanics, campaign state, and skill checks all functioned correctly. Narration quality and NPC distinctiveness were reduced compared to larger models but sessions were playable. For local models, writing a more directive `system.md` with explicit step-by-step procedures improves consistency.

See [SYSTEM-PORTING.md — What to expect from smaller/local models](SYSTEM-PORTING.md#what-to-expect-from-smallerlocal-models) for details.

---

## Looking for the Claude-optimised version?

If you're running Claude Code, [`claude-dnd-skill`](https://github.com/Bobby-Gray/claude-dnd-skill) is the dedicated version with model routing, deeper tool integration, and features built specifically for Claude's capabilities.

---

## Contributing

System modules for new games are the most valuable contribution. If you've built and tested a module for a system not listed here, a PR adding `systems/<your-system>/` is welcome. Include at minimum a filled-in `system.md` and a note in the PR about what you tested and how well it worked.
