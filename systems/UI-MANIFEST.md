# System UI manifest (`ui.json`)

**Status: DRAFT proposal — not yet wired into the renderer.** This describes the
contract that would let the display companion render a character sheet and stat
sidebar for any game system without touching the front-end. It's the UI-layer
companion to [`SYSTEM-PORTING.md`](../SYSTEM-PORTING.md), which covers the rules
layer (`system.md`).

## The design

One renderer, many manifests. The display front-end (`display/templates/index.html`)
stays a single generic renderer. Each system ships a small declarative
`systems/<name>/ui.json` that says *what to show and how* — which stat widgets sit
in the sidebar, what the primary resource looks like, what the character sheet
contains. The renderer reads the manifest for the loaded campaign's system at
startup and draws the sidebar from it.

Why declarative-manifest instead of per-system HTML: shipping HTML/CSS per system
fragments the front-end and forces every contributor to write display code. A
manifest means a new system is a ~40-line JSON file, and the renderer stays one
place to maintain. This is the realization of `SYSTEM-PORTING.md`'s "describe your
primary resource and we map it to the display" instruction — `ui.json` *is* that map.

## Resolution and fallback

1. Server resolves the active campaign's system (it already knows this via
   `paths.campaign_system_version`).
2. If `systems/<system>/ui.json` exists, the renderer uses it.
3. If it doesn't, the renderer uses a built-in **default manifest** (see below), so
   a system with no UI file still renders something sane. Authoring `ui.json` is an
   upgrade, never a prerequisite for a system to work.

**Self-hiding widgets:** every widget renders nothing when its bound data field is
absent or empty. So the manifest is the *superset* of what can appear — a D&D
caster with no spell slots pushed simply shows no slot widget. A system that never
pushes `spell_slots` never shows it. This is what makes one renderer safe across
systems: the manifest declares capacity, the pushed data decides what's drawn.

## Top-level shape

```jsonc
{
  "manifest_version": 1,
  "system": "dnd5e",          // must match the systems/<dir> name
  "label": "D&D 5e",          // human label (sidebar badge, etc.)
  "sidebar": [ <widget>, ... ],   // ordered, top to bottom
  "sheet": {                       // the click-to-open character sheet modal
    "stat_grid": <stat_grid>,
    "sections": [ <section>, ... ]
  },
  "vocab": {                       // optional affordances/validation hints
    "conditions": [ "...", ... ],
    "sustained_term": "Concentration"
  }
}
```

## Widget catalog (the `sidebar` primitives)

Every widget has `type`, `label`, and `bind` (a key in the pushed player object;
dot-paths like `sheet.abilities` are allowed). Type-specific options follow.

| `type` | Renders | Binds to (shape) | Options |
|--------|---------|------------------|---------|
| `bar` | Horizontal fill bar | `{current, max, temp?}` | `color` |
| `counter` | `value / goal` inline numeric | `{current, next}` (keys configurable via `fields`) | `fields` |
| `pip_track` | One row of pips draining from max | `{remaining\|current, max}` **or** a boolean (→ 1 pip, filled when true) | `pip_color`, `boolean` |
| `pip_levels` | Grouped pip rows keyed by level/category | `{ "<level>": {used, max}, ... }` | `pip_color` |
| `tag_list` | List of named tags | `[ "name", ... ]` | — |
| `tag_single` | One highlighted tag (or hidden if empty) | `string \| null` | `color` |
| `badge_set` | Labeled count badges (the generic milestone map) | `{ "<label>": count }` (+ optional `milestone_caps`) | — |

Notes:
- `pip_track` is the generalization of D&D's Second Wind (boolean) and Hit Dice
  (pool), and the home for things like Shadowrun **Edge** or Cyberpunk **Luck**.
- `pip_levels` is the generalization of D&D **spell slots**. Systems without
  level-banded resources just don't use it.
- `badge_set` is already system-agnostic in the backend today — `milestones` is a
  free `{label: count}` map with per-label caps (`milestone_caps`) and generic
  award/spend events. It's the model the rest of this schema follows: Inspiration,
  Bennie, Hero Point, Edge, Fate Point all ride the same widget.

## Sheet: `stat_grid` and `sections`

```jsonc
"stat_grid": {
  "label": "Ability Scores",
  "bind": "sheet.abilities",            // { "STR": 16, "DEX": 14, ... }
  "stats": [
    { "key": "STR", "label": "STR", "show_modifier": true },
    ...
  ]
}
```

`show_modifier: true` renders the score plus a derived 5e-style modifier
(`(score-10)/2`). `show_modifier: false` renders the value directly — which is the
right behavior for dice-pool systems where the stat *is* the rating (Shadowrun,
VtM, Wrath & Glory). This is the UI side of `SYSTEM-PORTING.md`'s
"is there a modifier conversion?" question.

```jsonc
"sections": [
  { "type": "attacks",   "label": "Attacks",   "bind": "sheet.attacks" },
  { "type": "spells",    "label": "Spells",    "bind": "sheet.spells" },
  { "type": "features",  "label": "Features",  "bind": "sheet.features" },
  { "type": "inventory", "label": "Inventory", "bind": "sheet.inventory" },
  { "type": "generic_list", "label": "Qualities", "bind": "sheet.qualities" }
]
```

`generic_list` is the escape hatch for system-specific sheet content that doesn't
map to the built-in section types — renders a labeled list of strings (or
`{name, detail}` objects) so a system can show whatever it needs without a new
renderer.

## The default manifest (no `ui.json` present)

```jsonc
{
  "manifest_version": 1,
  "system": "<resolved>",
  "label": "<resolved>",
  "sidebar": [
    { "type": "bar",       "label": "HP",         "bind": "hp",         "color": "#b5524a" },
    { "type": "counter",   "label": "XP",         "bind": "xp" },
    { "type": "tag_list",  "label": "Conditions", "bind": "conditions" },
    { "type": "tag_single","label": "Sustained",  "bind": "concentration" },
    { "type": "badge_set", "label": "Resources",  "bind": "milestones" }
  ],
  "sheet": {
    "stat_grid": { "label": "Stats", "bind": "sheet.abilities", "stats": [], "show_modifier": false },
    "sections": [
      { "type": "attacks",   "label": "Attacks",   "bind": "sheet.attacks" },
      { "type": "features",  "label": "Features",  "bind": "sheet.features" },
      { "type": "inventory", "label": "Inventory", "bind": "sheet.inventory" }
    ]
  }
}
```

With an empty `stats` array the grid renders whatever keys appear in
`sheet.abilities`, so even an unconfigured system shows its attributes.

## Illustrative target — Shadowrun 5e (not a real file yet)

Shown here so the shape is concrete for the SR port. Edge becomes a `pip_track`,
attributes render as raw ratings (`show_modifier: false`), the SR condition
monitors map to two `pip_track`s, and SR's "sustaining a spell" reuses `tag_single`.

```jsonc
{
  "manifest_version": 1,
  "system": "shadowrun5e",
  "label": "Shadowrun 5e",
  "sidebar": [
    { "type": "pip_track", "label": "Physical",  "bind": "physical_monitor", "pip_color": "#b5524a" },
    { "type": "pip_track", "label": "Stun",      "bind": "stun_monitor",     "pip_color": "#5a7fb5" },
    { "type": "pip_track", "label": "Edge",      "bind": "edge",             "pip_color": "#c9a24b" },
    { "type": "tag_list",   "label": "Status",    "bind": "conditions" },
    { "type": "tag_single", "label": "Sustaining","bind": "sustaining" },
    { "type": "badge_set",  "label": "Resources", "bind": "milestones" }
  ],
  "sheet": {
    "stat_grid": {
      "label": "Attributes",
      "bind": "sheet.attributes",
      "stats": [
        { "key": "BOD", "label": "BOD", "show_modifier": false },
        { "key": "AGI", "label": "AGI", "show_modifier": false },
        { "key": "REA", "label": "REA", "show_modifier": false },
        { "key": "STR", "label": "STR", "show_modifier": false },
        { "key": "WIL", "label": "WIL", "show_modifier": false },
        { "key": "LOG", "label": "LOG", "show_modifier": false },
        { "key": "INT", "label": "INT", "show_modifier": false },
        { "key": "CHA", "label": "CHA", "show_modifier": false }
      ]
    },
    "sections": [
      { "type": "generic_list", "label": "Qualities", "bind": "sheet.qualities" },
      { "type": "generic_list", "label": "Gear",      "bind": "sheet.gear" },
      { "type": "spells",       "label": "Spells",    "bind": "sheet.spells" }
    ]
  }
}
```

## Open questions for the renderer PR

- **`sheet.abilities` binding** — confirm where ability/attribute scores actually
  live in the pushed `sheet` object today; the dnd5e reference assumes
  `sheet.abilities`. (`push_stats.py --sheet` documents `attacks/spells/features/inventory`
  but not the ability block, so this needs a look at the sheet-modal render path.)
- **Faction / quest / turn-order panels** stay global (system-agnostic already) and
  are out of scope for `ui.json`.
- **Colors** are passed through as-is; consider a small named palette so manifests
  don't hardcode hex if we want theme-awareness later.
