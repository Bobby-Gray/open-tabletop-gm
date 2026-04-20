# System Module — [Your Game Name Here]

<!--
This is the scaffold for building a new system module for open-tabletop-gm.
Copy this file to systems/<your-system>/system.md and fill in each section.
Delete these comments as you go.

This file is loaded alongside SKILL.md at session start. It tells the GM model
the mechanical rules of YOUR game. The better you fill this in, the better the
GM will understand how to resolve actions, handle combat, and manage resources.

See SYSTEM-PORTING.md for a detailed guide on what each section means and
examples from multiple game systems.
-->

---

## Dice Convention

<!--
Describe the core dice resolution mechanic for your system. This is one of the
most important sections — the GM needs to know exactly how to resolve a roll.

Examples:
  D&D 5e:        d20 + modifier vs DC or AC
  Pathfinder 2e: d20 + modifier vs DC; degree of success matters (crit/success/fail/crit fail)
  VtM V5:        Pool of d10s; count dice showing 6+ as successes; Hunger dice replace some
  Cyberpunk RED: d10 + STAT + Skill vs Difficulty Value (DV)
  Wrath & Glory: Pool of d6s; 4-5 = Icon (1 success), 6 = Exalted Icon (2 successes), Wrath die
-->

**Core resolution:** [describe the basic roll here]

**Success thresholds:** [what counts as a success, failure, critical]

**Advantage/disadvantage equivalent:** [if your system has one]

**Example inline combat narration:**
`[Character] attacks [target]: [roll] = [result] vs [defense] — [outcome]! [damage roll] = [X] [type] damage`

---

## Ability Scores / Statistics

<!--
List the character statistics used in your game. Include:
- The stat names and abbreviations
- How modifiers are derived (if applicable)
- How many stats there are and how they're grouped (if grouped)

Examples:
  D&D 5e: 6 stats (STR/DEX/CON/INT/WIS/CHA), modifier = (score-10)/2
  VtM V5: 9 stats in 3 groups (Physical/Social/Mental), each rated 1-5, no modifier conversion
  Cyberpunk RED: 10 stats (INT/REF/DEX/TECH/COOL/WILL/LUCK/MOVE/BODY/EMP), direct values
-->

| Stat | Description |
|------|-------------|
| [STAT] | [what it governs] |

[Describe how modifiers/bonuses are derived if applicable]

---

## Character Structure

<!--
List the key tracked fields for a character in your system. Focus on what changes
during play and needs to be tracked turn-to-turn.
-->

| Field | Notes |
|-------|-------|
| [Health / HP / Wounds] | [how damage is tracked] |
| [Defense / AC / Armor] | [how attacks target this] |
| [Primary resource] | [spell slots / blood / luck / etc.] |
| [Secondary resource] | [if applicable] |
| [Advancement] | [levels / XP / milestones] |
| [Status effects] | [see conditions list below] |

<!--
If your system has character creation scripts, document them here:
  python3 systems/<your-system>/character.py [command]
-->

---

## Health and Damage

<!--
Describe how HP/health works in your system.
  - Is there a single HP pool, or multiple tracks?
  - Are there wound thresholds (e.g. Seriously Wounded in Cyberpunk)?
  - Is there a distinction between damage types (Superficial vs Aggravated in VtM)?
  - How does recovery work?
-->

[Describe health/damage model here]

---

## Primary Resource

<!--
What is the main limited resource characters spend during play?
  D&D: spell slots (level 1-9)
  VtM: Hunger (1-5 scale, not spent but managed)
  Cyberpunk: Luck points
  Wrath & Glory: Glory / Wrath

The display companion maps this to the "spell slots" sidebar UI — pips that drain and refill.
If your resource doesn't map cleanly to "slots per level", describe the nearest equivalent
and how you want it tracked.
-->

**Resource name:** [e.g. Spell Slots / Blood Pool / Luck]
**Range:** [e.g. 1-9 levels / 0-5 scale / 0-N points]
**Tracking:** [how it's spent and restored]

---

## Rests and Recovery

<!--
How do characters recover between scenes or sessions?
  D&D: Short rest (1hr, Hit Dice) / Long rest (8hr, full restore)
  VtM: Feeding to reduce Hunger / Resting to heal Superficial damage
  Cyberpunk: Time + medical attention

Map to calendar.py commands if applicable:
  calendar.py rest short  → +1 hour
  calendar.py rest long   → +8 hours
  calendar.py advance N hours/days
-->

[Describe recovery mechanics here]

---

## Incapacitation and Death

<!--
What happens when a character reaches 0 HP / is taken out?
  D&D: unconscious → death saves (3/3 threshold)
  VtM: Torpor (vampire sleep) vs Final Death
  Cyberpunk: Critical Injury table, BODY check to avoid instant death

tracker.py has built-in death save support (D&D style 3/3).
For other systems, use tracker.py conditions to track incapacitation state.
-->

[Describe incapacitation / death mechanics here]

---

## Status Effects / Conditions

<!--
List the status effects used in your system with severity tiers for colour-coding:
  critical  → red pills in display sidebar
  warn      → amber pills
  info      → blue pills
  buff      → green pills

You will need to update CONDITION_COLOURS in tracker.py for your system's conditions.
See SYSTEM-PORTING.md for instructions.
-->

| Condition | Severity | Effect summary |
|-----------|----------|----------------|
| [condition] | critical/warn/info/buff | [brief rule note] |

---

## Advancement

<!--
How do characters improve over time?
  D&D / PF2e: XP thresholds → level up → new class features
  VtM: XP spent directly on traits, no levels
  Cyberpunk: Improvement Points spent on skills

If using XP thresholds, list them here so the GM can track progress accurately.
-->

[Describe advancement here]

---

## Bold Play Reward

<!--
What is the mechanical reward for outstanding roleplay or bold choices?
  D&D: Inspiration (one-use bonus on a roll)
  VtM: Willpower (re-roll some dice)
  Cyberpunk: Luck (add to a roll)

This tells the GM what to award and how to track it.
-->

**Reward name:** [e.g. Inspiration / Willpower / Edge]
**Effect:** [what it does mechanically]
**How to award:** [criteria]

---

## Campaign Arc Preferences

<!--
Optional. If your system has strong conventions around campaign structure, note them here.
The GM will use this to calibrate how it generates or enforces narrative arcs.

Examples:
  D&D 5e (published adventure): use /gm import to create a structured campaign from the
    source PDF — arc beats and chapters are extracted automatically.
  D&D 5e (homebrew): use /gm new for an improvised dynamic arc — auto-generated from
    the world's threat, factions, and Three Truths at campaign creation.
  VtM V5 (chronicle): improvised dynamic arc; faction-web structure suits the political
    focus of most chronicles; hub-and-spoke if running a published module.
  Cyberpunk RED: improvised arcs with a strong act-2 pressure point recommended;
    "All Is Lost" beat often lands as a corpo betrayal or mission failure.
  Narrative / diceless: dynamic arc; beats are thematic rather than mechanical.

If you always import pre-written sources for this system, note the typical structure type:
  linear         — A→B→C scene chain (dungeon crawl, heist)
  hub-and-spoke  — central hub + spoke locations in player-driven order (hexcrawl, published modules)
  faction-web    — multi-faction city/complex with overlapping arcs (political, intrigue)
-->

**Preferred campaign mode:** [improvised / imported / either]
**Typical arc structure:** [dynamic / structured — and if structured: linear / hub-and-spoke / faction-web]
**Genre conventions:** [any pacing or arc notes specific to this system's genre]

---

## Additional System Notes

<!--
Anything else the GM needs to know that doesn't fit above:
  - Faction mechanics specific to this setting
  - Special combat rules (action economy, reactions, etc.)
  - Unique character features common to this system
  - Any scripts or data files you've added to systems/<your-system>/
-->
