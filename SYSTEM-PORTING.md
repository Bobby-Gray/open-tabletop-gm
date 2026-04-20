# Porting open-tabletop-gm to a New Game System

This guide explains what you need to build to run open-tabletop-gm with any tabletop RPG. The D&D 5e module (`systems/dnd5e/`) is the reference implementation — use it as a concrete example of what a finished system module looks like.

---

## How the architecture works

The skill is split into two layers:

**`SKILL.md` — the GM core.** This file never changes regardless of what game you're playing. It defines how to be a good GM: pacing, improvisation, NPC craft, rewarding bold play. It knows nothing about D&D, Warhammer, or Vampire.

**`systems/<your-system>/system.md` — the rules layer.** This file is loaded alongside `SKILL.md` when you start a session. It tells the GM model everything it needs to know about *your specific game*: how dice work, what stats characters have, how damage is tracked, what happens when a character dies. The better this file is written, the better the GM will play your game.

When you run `/gm load <campaign>`, the skill reads both files. Think of `SKILL.md` as the experienced GM who's played everything, and `system.md` as the rulebook they just read for your specific game.

---

## What's universal — no changes needed

These parts of the skill work identically for any tabletop RPG:

- **Dice rolling** — `dice.py` understands any XdY+Z notation. `2d6`, `d10`, `4d6kh3`, `d100` — all work out of the box.
- **Turn order / initiative** — `combat.py` handles initiative tracking regardless of what stat is used. You just feed it the numbers.
- **Timed effects** — round-based and time-based effect tracking works for any system. Rounds, minutes, hours, indefinite — all supported.
- **Status effect tracking** — `tracker.py` tracks conditions, concentration/sustained effects, and incapacitation state. The condition *names* are configurable.
- **Campaign file structure** — `state.md`, `world.md`, `npcs.md`, `session-log.md` are game-agnostic. A campaign is a campaign.
- **Time and calendar** — `calendar.py` is fully configurable to any calendar system. You define the month names, day names, and month length.
- **The display companion** — the cinematic display, stat sidebar, and effect pills work for any game. Health bars, resource pips, conditions, turn order — all generic.
- **Scene detection** — the display companion's scene keyword system works for any setting. It reads the narration and adjusts the background accordingly.
- **The 12 GM principles** — these apply to every TTRPG. Improvisation, consequence, NPC craft, pacing — universal.
- **Narrative arc system** — both campaign modes work with any game system. *Improvised campaigns* get an auto-generated three-act dynamic arc at `/gm new` (six beats defined by consequence, not event; tracked and revised across sessions). *Structured campaigns* use `/gm import` to ingest a pre-written source document (PDF, markdown, DOCX, or plain text) and extract acts, chapters, key beats, and steering notes automatically. The arc operates above the system layer — it cares about story shape, not game mechanics.
- **Campaign import** — `scripts/import_campaign.py` is fully system-agnostic. It extracts text from any source document and hands it to the GM model for structural analysis. The resulting campaign files use the same format regardless of what game system the source describes.
- **Live State Flags** — the compaction-resilience block in `state.md`; keeps faction stances, NPC dispositions, and cover status anchored in compact key-value form; re-read at any recap to avoid stale impressions from context compression. Universal — works for any campaign.

---

## What you need to configure per system

These parts have D&D defaults that need adjusting for other games.

### 1. Dice resolution logic

This is the most important thing to describe in your `system.md`. The GM needs to know *exactly* how to resolve a roll for your game.

| System | Resolution |
|--------|------------|
| D&D 5e / PF2e | d20 + modifier vs DC or AC |
| Vampire: The Masquerade V5 | Pool of d10s; 6+ = 1 success, 10 = 2 successes; Hunger dice can cause complications |
| Cyberpunk RED | d10 + STAT + Skill vs Difficulty Value (DV) |
| Warhammer 40k: Wrath & Glory | Pool of d6s; 4-5 = 1 Icon (success), 6 = 2 Icons; Wrath die has special rules |
| Warhammer Fantasy Roleplay | Percentile (d100) roll-under a target number |

For **dice pool systems** (VtM, W&G), `dice.py` still handles the raw rolls (`5d10`, `6d6`). You describe the success-counting logic in `system.md` so the GM knows how to interpret the numbers.

### 2. Ability scores / statistics

Every game has character statistics but they vary significantly:

| System | Stats |
|--------|-------|
| D&D 5e | 6 stats (STR/DEX/CON/INT/WIS/CHA), modifiers derived from score |
| VtM V5 | 9 stats in 3 groups (Physical/Social/Mental), rated 1-5, used directly |
| Cyberpunk RED | 10 stats (INT/REF/DEX/TECH/COOL/WILL/LUCK/MOVE/BODY/EMP), used directly |
| Wrath & Glory | Attributes rated 1-12, no modifier conversion |

List your stats in `system.md`. If there's no modifier conversion (stat IS the modifier), say so.

### 3. The primary resource (spell slots → your system)

The display sidebar shows "spell slots" as pips that drain and refill. This UI works for any limited resource — the label is cosmetic. What you're actually tracking is *a pool of limited-use abilities that characters spend during play*.

| System | Resource |
|--------|----------|
| D&D 5e | Spell slots (9 levels, used and max per level) |
| VtM V5 | Hunger (1-5 scale — not spent but managed; higher = worse complications) |
| Cyberpunk RED | Luck (points spent on rolls, restored at start of session) |
| Wrath & Glory | Glory / Wrath (variable; Wrath accumulates danger) |

Describe your resource in `system.md` and map it to what the display tracks. If your resource doesn't map cleanly to slots, note how you want it displayed and we can adjust the push_stats calls accordingly.

### 4. Health and damage

All games have a health concept but the model varies:

| System | Model |
|--------|-------|
| D&D 5e | Single HP pool + optional Temp HP |
| VtM V5 | Damage track (boxes); Superficial damage fills half, Aggravated fills fully |
| Cyberpunk RED | HP pool with a Seriously Wounded threshold at half max |
| Wrath & Glory | Wounds pool + Shock (mental damage) |

The display tracks `current / max` HP plus optional temp HP. For systems with multiple damage tracks, use the primary pool as HP and track secondary damage via conditions.

### 5. Conditions / status effects

`tracker.py` has a colour-coded condition list hardcoded for D&D. To use it with your system, update the `CONDITION_COLOURS` dictionary near the top of `scripts/tracker.py`:

```python
CONDITION_COLOURS = {
    "unconscious":  "danger",   # red
    "stunned":      "danger",
    "frightened":   "warn",     # amber
    "poisoned":     "warn",
    "grappled":     "info",     # blue
    "prone":        "info",
    "invisible":    "buff",     # green
}
```

Replace these with your system's status effects. The four severity levels are `danger`, `warn`, `info`, `buff`. You don't need to use all four — use whichever make sense.

### 6. Recovery / rests

Describe how characters recover in your `system.md`. If your system has structured rest mechanics, map them to `calendar.py rest short` / `calendar.py rest long` (which advance time by 1 hour and 8 hours respectively). If recovery is freeform or requires feeding/healing scenes, describe the narrative trigger instead.

### 7. Incapacitation and death

`tracker.py` has built-in D&D death save tracking (3 successes / 3 failures). For other systems:
- Use `tracker.py condition add <name> incapacitated` to flag a character as down
- Describe your system's incapacitation rules in `system.md` so the GM knows what to narrate and roll
- For systems with more complex death mechanics (VtM's Torpor, Cyberpunk's Critical Injury table), document them in `system.md` and the GM will handle them narratively

---

## What's a full replacement

These scripts are D&D specific and live in `systems/dnd5e/`. You don't need to replace them unless your system needs equivalent tools — the GM can handle these manually from `system.md` for simpler cases.

| Script | What it does | Notes |
|--------|-------------|-------|
| `ability-scores.py` | Generates D&D ability scores (roll arrays, point buy) | Build your own if character creation needs scripting |
| `character.py` | D&D stat block calculation and level-up | Build your own for systems with different math |
| `lookup.py` + `build_srd.py` + `sync_srd.py` | D&D 5e SRD dataset lookup | Build your own data layer if your system has open licensing; skip if proprietary |
| `build_supplemental.py` | Fetches non-SRD D&D spells/features from wikidot and caches to `systems/dnd5e/data/dnd5e_supplemental.json` | Already ported — run after `build_srd.py` to populate the supplemental dataset |

For most systems, you can start without any system-specific scripts and rely entirely on `system.md` for rules context. Add scripts later when you identify specific calculations the GM gets wrong repeatedly.

---

## Step-by-step: building a new system module

### Step 1 — Copy the template
```bash
cp systems/TEMPLATE.md systems/<your-system>/system.md
```

### Step 2 — Fill in system.md
Work through each section of the template. The minimum viable system module has:
- Dice resolution (how to resolve a roll)
- Ability scores / statistics (what stats characters have)
- Health model (how damage works)
- Primary resource (what gets spent)
- Conditions list (status effects)

You don't need to fill in everything before starting to play. Start with dice and health, play a session, note what the GM gets wrong, then fill in the gaps.

### Step 3 — Update tracker.py conditions (optional)
If your system has a specific set of named conditions and you want them colour-coded in the display, update `CONDITION_COLOURS` in `scripts/tracker.py` as shown above.

### Step 4 — Create a campaign
Run `/gm new <campaign-name>` and specify your system when prompted. The skill will load your `system.md` alongside `SKILL.md` for every session.

### Step 5 — Iterate
The first session will reveal gaps. A dice pool system where the GM isn't counting successes correctly, a resource the GM isn't tracking — these are quick fixes in `system.md`. Over time your system module becomes a complete rules reference the GM can rely on.

---

## Compatibility expectations by system type

**D&D 5e / Pathfinder 2e** — highest compatibility. The entire toolchain was built for d20 systems. Near-zero friction, mostly rename work.

**Skill-based d10 systems (Cyberpunk RED, World of Darkness)** — medium compatibility. Core skills (dice, combat, tracker, display) all work. Character creation and stat math need a custom `system.md` and possibly light scripting. The narrative and campaign engine carries over completely.

**Dice pool success-counting systems (VtM V5, Wrath & Glory)** — medium-high compatibility. `dice.py` handles the raw rolls. The success interpretation logic is described in `system.md` for the GM to apply. Combat tracker and display work as-is.

**Percentile systems (WFRP 4e, Call of Cthulhu)** — medium compatibility. `dice.py` handles `d100` rolls directly. Resolution (roll-under target number) is described in `system.md`. Everything else works.

**Narrative / diceless systems (Amber, Fiasco)** — lower but functional. The mechanical tracking layer is less relevant; the GM core (`SKILL.md`) carries essentially all the value. Use the campaign file structure, NPC system, and display companion — skip the scripts.

---

## What to expect from smaller/local models

The GM core (`SKILL.md`) is demanding — it expects creative narration, reactive NPCs, consistent world logic. Larger models handle this well. Smaller local models (7B–14B parameter range) may show:

- Shorter, less atmospheric narration
- Simpler NPC voices
- Less consistent long-term memory across a session
- Occasional rule misapplication

The Python toolchain compensates for a lot: dice rolls are exact, HP math is exact, turn order is exact, timed effects track correctly regardless of model capability. The model's job is narration and judgment — the scripts handle the math.

For local models, consider writing a more directive `system.md` with explicit step-by-step combat resolution, rather than relying on the model to infer procedure from prose.
