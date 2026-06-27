# System UI manifest (`ui.json`)

Lets the display companion render a character sidebar and sheet for any game
system without touching the front-end. It's the UI-layer companion to
[`SYSTEM-PORTING.md`](../SYSTEM-PORTING.md) (the rules layer, `system.md`).

## The design

One renderer, many manifests. The front-end (`display/templates/index.html`) is a
single generic renderer. Each system ships a small declarative
`systems/<name>/ui.json` describing *what to show* — which stat widgets sit in the
sidebar, what the combat strip and attribute grid contain. The renderer reads the
manifest for the loaded campaign's system and draws from it.

Why declarative manifest instead of per-system HTML: shipping HTML/CSS per system
fragments the front-end and forces every contributor to write display code. A
manifest makes a new system a ~40-line JSON file, and the renderer stays one place
to maintain.

## Resolution and fallback

1. A campaign declares its system module in `state.md`:
   `**System Module:** <name>` (e.g. `dnd5e`, `shadowrun5e`). This is distinct
   from the human-readable `**System:**` label some campaigns carry ("D&D 5e") —
   that's for display, `**System Module:**` is for resolution. Campaigns without
   the field default to `dnd5e`.
2. The server (`_load_ui_manifest`) reads `systems/<module>/ui.json` and injects it
   into the page as `window.GM_UI_MANIFEST`.
3. If there's no campaign, no `ui.json`, or the file is invalid, it injects `null`
   and the renderer falls back to its **built-in default manifest** — which
   reproduces the D&D 5e layout exactly. So the display renders identically with or
   without a manifest file; authoring one is an upgrade, never a prerequisite.

Resolved at page render. Switching systems takes effect on the next display load,
and the display is force-restarted each session, so this is a non-issue in normal
use.

**Self-hiding widgets:** every widget renders nothing when its bound field is
absent or empty. So the manifest declares the *superset* of what can appear, and
the pushed stats decide what's actually drawn — a D&D caster with no spell slots
pushed simply shows no slot widget; a system that never pushes `spell_slots` never
shows it.

## Top-level shape

```jsonc
{
  "manifest_version": 1,
  "system": "dnd5e",          // must match the systems/<dir> name
  "label": "D&D 5e",          // human label
  "sidebar": [ <widget>, ... ],    // ordered, top to bottom under the name/identity header
  "sheet": {
    "combat_strip": [ <cell>, ... ],   // the stat row at the top of the sheet modal
    "stat_grid": <stat_grid>           // the attribute grid
  }
}
```

The card's name / race·class·level / background header is universal and rendered
for every system (fields self-hide when empty), so it isn't in the manifest.
Faction, quest, and turn-order panels are global and system-agnostic — also out of
scope for `ui.json`.

## Sidebar widget catalog

Each widget has a `type` plus a `bind` (a key in the pushed player object;
dot-paths like `hp.current` work). The data shapes below are what the player object
carries (see `display/push_stats.py`).

| `type` | Renders | Binds to (shape) | Key options |
|--------|---------|------------------|-------------|
| `bar` | Labelled value + fill bar | `{current, max, temp?}` | `cur`,`max` (field names), `color:"hp"` for HP's dynamic colour, `temp`, `icon`, `fill_class`, `require_cur` (only draw when current present) |
| `stat_lines` | Inline `Label value` lines | each line binds a scalar | `lines:[{label,bind,format?}]`; `format:"hd"` reads `{remaining,max,die}` |
| `tag_list` | List of tags | `[ "name", ... ]` | `class_map` (tag → severity class: `danger`/`warn`/`info`/`buff`) |
| `tag_single` | One tag, or hidden if empty | `string \| null` | `prefix` (e.g. `"◈ "`) |
| `effects` | Timed-effect pills | `[ effect, ... ]` | — (uses the built-in effect-pill renderer) |
| `badge_set` | Labelled count badges | `{ "<label>": count }` | — (the generic milestone map: Inspiration / Edge / Bennie / Fate Point all ride this) |
| `pip_levels` | Pip rows grouped by level | `{ "<level>": {used, max}, ... }` | — (D&D spell slots; any level-banded resource) |
| `feature_flags` | Boolean ✓/✗ lines | each flag binds a boolean | `flags:[{label,bind}]` |
| `badge` | A single badge, shown when truthy | boolean | `label` |

Notes:
- `bar` covers HP (dynamic colour via `color:"hp"`, `temp` row) and XP (`max:"next"`,
  `require_cur:true`).
- For a **single-pool resource** like Shadowrun Edge or Cyberpunk Luck, use a `bar`
  (`{current,max}`) or model it as a level-1 `pip_levels`/`badge_set` entry,
  whichever reads better.
- `badge_set` is already system-agnostic in the backend (`milestones` is a free
  `{label:count}` map with per-label caps and generic award/spend events).

## Sheet: `combat_strip` and `stat_grid`

```jsonc
"combat_strip": [
  { "label": "HP",        "bind": "hp",        "format": "ratio" },   // {current,max}; a Temp HP cell auto-follows when hp.temp is set
  { "label": "AC",        "bind": "ac" },
  { "label": "Speed",     "bind": "speed",     "suffix": " ft" },
  { "label": "Hit Dice",  "bind": "hit_dice",  "format": "hd" }       // {remaining,max,die}
]
```
Cell `format`: `"ratio"` → `current/max`; `"hd"` → `remaining/max die`; omitted →
the raw value plus optional `suffix`. Missing data renders `—`.

```jsonc
"stat_grid": {
  "label": "Ability Scores",
  "bind": "ability_scores",          // { "str": {score, mod}, ... }  OR  { "BOD": 5, ... } for raw ratings
  "show_modifier": true,             // D&D: show derived modifier under the score
  "stats": [ { "key": "str", "label": "STR" }, ... ]
}
```
Each `stats` entry maps a key in the bound object to a labelled cell. Per-entry
`show_modifier` overrides the grid default. With `show_modifier:false` the cell
shows the value directly — the right behaviour for dice-pool systems where the stat
*is* the rating (Shadowrun, VtM, Wrath & Glory). The renderer accepts both a
`{score, mod}` object (D&D) and a plain number (raw ratings) per key.

The rest of the sheet modal (attacks / spells / features / inventory /
relationships) is already field-driven and self-hiding — it renders whatever the
pushed `sheet` object contains, for any system, no manifest needed.

## Illustrative target — Shadowrun 5e

```jsonc
{
  "manifest_version": 1,
  "system": "shadowrun5e",
  "label": "Shadowrun 5e",
  "sidebar": [
    { "type": "bar", "label": "Physical", "bind": "physical_monitor", "cur": "current", "max": "max" },
    { "type": "bar", "label": "Stun",     "bind": "stun_monitor",     "cur": "current", "max": "max" },
    { "type": "bar", "label": "Edge",     "bind": "edge",             "cur": "current", "max": "max", "require_cur": true },
    { "type": "stat_lines", "lines": [
      { "label": "Init",    "bind": "initiative" },
      { "label": "Phys Lim","bind": "physical_limit" },
      { "label": "Ment Lim","bind": "mental_limit" } ] },
    { "type": "tag_list",   "bind": "conditions" },
    { "type": "tag_single", "bind": "sustaining", "prefix": "◈ " },
    { "type": "effects",    "bind": "effects" },
    { "type": "badge_set",  "bind": "milestones" }
  ],
  "sheet": {
    "combat_strip": [
      { "label": "Physical", "bind": "physical_monitor", "format": "ratio" },
      { "label": "Stun",     "bind": "stun_monitor",     "format": "ratio" },
      { "label": "Edge",     "bind": "edge",             "format": "ratio" },
      { "label": "Init",     "bind": "initiative" }
    ],
    "stat_grid": {
      "label": "Attributes",
      "bind": "ability_scores",
      "show_modifier": false,
      "stats": [
        { "key": "BOD", "label": "BOD" }, { "key": "AGI", "label": "AGI" },
        { "key": "REA", "label": "REA" }, { "key": "STR", "label": "STR" },
        { "key": "WIL", "label": "WIL" }, { "key": "LOG", "label": "LOG" },
        { "key": "INT", "label": "INT" }, { "key": "CHA", "label": "CHA" }
      ]
    }
  }
}
```

The SR system module pushes the matching fields (`physical_monitor`, `edge`,
`ability_scores` as raw ratings, etc.) when it sends stats, and declares
`**System Module:** shadowrun5e` in the campaign's `state.md`. Everything else —
the renderer, the feed, dice, turn order — is untouched.

## Reference

`systems/dnd5e/ui.json` is the working reference manifest; it mirrors the renderer's
built-in default exactly and reproduces the original D&D 5e display.
