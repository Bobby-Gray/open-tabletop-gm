# Changelog

All notable changes to open-tabletop-gm are documented here. The skill follows [semantic versioning](https://semver.org/) — `MAJOR.MINOR.PATCH` where MAJOR breaks an existing campaign or workflow, MINOR adds significant new capability, and PATCH fixes bugs without changing behavior.

The current installed version is recorded in the `VERSION` file at the repo root. Run `python3 scripts/update_skill.py --check` (or `/gm update --check`) to compare your local copy against `origin/main`.

Versions before **0.7.0** are reconstructed retroactively from git history; the dates reflect the commit each version is anchored on. Going forward, every release lands in the same commit as a `VERSION` bump and a CHANGELOG entry.

This project is the LLM-agnostic, system-flexible fork of [claude-dnd-skill](https://github.com/Bobby-Gray/claude-dnd-skill). It tracks behind on features that need adaptation for non-Claude tooling and for system-agnostic design; the goal is parity on what makes sense to port and an independent track on what doesn't.

---

## [Unreleased]

## [0.8.0] — 2026-05-01

This sync ports forward the deterministic extractor + Phase 2.5 graph features that landed in claude-dnd-skill v1.7.1 and v1.7.2 today. The deterministic extractor is the centerpiece — it's exactly the LLM-free path the v0.7.0 release said was deferred, and it's why this fork exists.

Existing campaigns and `graph.json` files keep working unchanged. Everything new is opt-in.

### What's new

- **`/gm graph extract`** — pattern-matches the campaign's session logs against `data/graph/verb_table_seed.yaml`. Zero LLM calls. Estimated recall ~50%, precision ~95% on clean SVO and SVO-with-prep relationships. Output format matches the upstream Haiku extractor exactly so proposals are interchangeable.
- **`/gm graph extract --last-session-only`** — narrow extraction to the most recent `## Session N` block (skip the archive). Useful for end-of-session sweeps.
- **`/gm graph extract-apply --review`** — interactive proposal-by-proposal walkthrough with `y / n / q` prompts. Shows the verbatim source anchor and confidence for each proposal. Mutually exclusive with `--pick`.
- **`/gm graph close-edge --anchor "..."`** — record the verbatim phrase that justifies the closure as a new optional `closed_anchor` field on the edge.
- **`/gm graph supersede-edge`** — mark an edge as superseded (hard retcon). Use when canon explicitly contradicts a prior extraction. Optional `--by <correct-edge-id>` links the replacement; `--reason "..."` records why. Distinct from `close-edge`: closing ends a real relationship; superseding says the original was wrong.
- **Category-node edges**. State-verbs flagged `category_object_ok: true` in the verb seed (`possessed_by`, `worships`, `cleric_of`, `cursed_by`, `fears`, `flagged_offlimits`) now match patterns where the object is a categorical noun phrase ("a ghost", "the silver veil"). `extract-apply` auto-creates a node with `category_node: true`, `type: category`, `id: cat_*`. `scene-context` renders these with an `(unnamed)` marker so the GM remembers canon hasn't named them yet.

### Schema additions

- **`Edge.superseded_by`** — `<edge-id>` or `true`. `_edge_active_at()` excludes any edge with this set, so superseded edges never surface in `scene-context` but stay in the graph for audit trail.
- **`Edge.supersede_reason`** — optional human explanation of the retcon.
- **`Edge.closed_anchor`** — optional verbatim closure phrase.
- **`Node.category_node: true`** — flag on auto-created category nodes.
- **`verb_table_seed.yaml`** v0.5 ports forward with `lifetime: event | state | dispositional` annotated on every inclusion + borderline entry (119 total).

### Test suite (new)

`python3 -m unittest discover tests` → **48 tests in ~2s**, all green.

- `tests/test_verb_table.py` (12) — seed sanity, every entry has `lifetime`, lifetime values valid.
- `tests/test_deterministic_extract.py` (25) — entity recognizer, alias index (first-word / surname / middle-subsequence, stop-word rejection, ambiguity skipping), pattern regex, sentence splitter, session-number resolution, end-to-end synthetic campaign, dedup, last-session-only.
- `tests/test_gm_graph.py` (11) — actual `gm_graph.py` CLI: `add-node`, `add-edge`, `close-edge` with and without `--anchor`, `scene-context` filtering by `--at-session` (closed and superseded edges hidden), uninitialized-graph notice, `extract` writes JSON, `extract-apply --pick`, `supersede-edge` marks correctly, category-node creation from a possession scene.

### Demo verification

A synthetic 2-session "Winterhold" campaign extracted cleanly:

```
Aldric Brandt --[met]--> Mira Solveig             s1  (high)
Renna Voss --[attacked]--> Aldric Brandt          s2  (high)
wraith --[possessed_by]--> Aldric Brandt          s2  (low)  [X is category]
Mira Solveig --[swore_oath_to]--> Aldric Brandt   s1  (high)
```

`extract-apply` created 4 edges + 1 category node (`cat_wraith`). `supersede-edge --id e1` correctly hid the met-edge from later `scene-context` queries.

### What's still deferred

- **Hybrid mode** (Phase 3) — pattern-first then LLM-fallback on unmatched sentences. The LLM-agnostic constraint of this fork makes it less compelling here than upstream, but worth revisiting if a deterministic-only model can be plugged in via the same interface.
- **Future-tense planning verbs** (`plans_to`, `intends_to`, `scheduled_to`) — corpus mismatch (Reddit narrative is past-tense). Needs a separate corpus pass on DM session-prep documents.
- **`--inspiration-reason`** — D&D-specific Inspiration mechanic; needs design as a generic milestone event before porting.

---

## [0.7.0] — 2026-05-01

This release ports forward the campaign relationship graph that just shipped in claude-dnd-skill v1.7.0 — adapted for the LLM-agnostic constraints of this project — alongside the version-tracking infrastructure that's been overdue and a couple of important bug fixes.

The graph in this fork is **manual + query-only**. The Haiku-backed `extract` / `extract-apply` subcommands from the upstream version are not ported (they assume Claude API access). The high-value parts — `init`, `add-edge`, `close-edge`, and the `scene-context` query that auto-pulls at `/gm load` — work exactly the same way and don't require any LLM. When a deterministic verb-table extractor is built (it's designed in the upstream `docs/research/graph/phase-2-3-plan.md`), it will land here too.

### What's new

- **Campaign relationship graph.** `scripts/gm_graph.py` ships with subcommands `init`, `add-node`, `add-edge`, `close-edge`, `list`, `show`, `subgraph`, and `scene-context`. Local-only, time-stamped (`since_session` / `until_session`), with verbatim source-anchors on every edge. Stored at `<campaign-root>/<name>/graph.json`.
- **Auto-pull at `/gm load`.** Scene-context runs as part of the load flow, before the recap, so the GM has the active subgraph in scope before they speak. If the graph isn't initialized yet, the load flow offers an auto-init with a backup-first prompt — see below.
- **Backwards-compatible auto-init.** Existing campaigns don't have a graph. When `/gm load` notices `graph.json` is missing, it offers:

  > *"This campaign doesn't have a relationship graph yet. I can initialize one now — it improves long-session continuity recall when full NPC files fall out of context. As a safety precaution, I'll back up the campaign first to `<campaign-root>/<name>.backup-YYYYMMDD-HHMMSS/`. Proceed? [y/n]"*

  `y` runs a `cp -R` snapshot before anything touches the campaign, then proposes seed nodes and edges from the existing markdown for GM approval. `n` continues without the graph for that session and doesn't re-prompt. No silent extraction, no auto-write.
- **Sweep at `/gm save`.** The save flow scans the session for relationship shifts that weren't recorded live and presents them to the GM as a numbered list (`y / pick / skip`) before writing.
- **`/gm graph` command suite** documented end-to-end in `SKILL-commands.md`.

### Versioning is now tracked

- New `VERSION` file at the repo root (semver, `0.7.0`).
- New `CHANGELOG.md` (this file) with the full retroactive history.
- `python3 scripts/update_skill.py --check` (and `/gm update --check`) now shows local vs. remote version side by side, so it's obvious at a glance whether you've fallen behind.

### Bug fixes

- **`send.py` no longer hangs on chained-bash invocations.** Body-less calls (e.g. `--set-campaign` alone, or any `--stat-*` flag without text) were waiting on stdin that never came. Body-less detection now skips `sys.stdin.read()` entirely when the call has no content flag and only carries state-update flags.
- **Spell slots no longer 500 on long rest.** `display/gm-display-app.py` now accepts both `{used, max}` and legacy `{remaining, max}` slot schemas via a new `_normalize_slot()` helper. Affects systems that use spell slots and send them through the display.

### What's deferred (not in this release)

- **Phase 1 Haiku extractor** (`extract`, `extract-apply` subcommands) — Claude API-specific; doesn't fit OTGM's LLM-agnostic constraint. Ports forward when the deterministic Phase 2 extractor is implemented.
- **Verb-table seed and corpus tooling** — research artifacts from upstream; useful when Phase 2 lands but not user-facing in this release.
- **`/gm graph extract` documentation** — added back when an LLM-agnostic extractor exists.

---

## [0.6.0] — 2026-04-28

Two new commands that close the longest-standing usability gap: figuring out which copy of the skill you're running and where your campaign data lives.

### What's new

- **`/gm update`** — pull skill changes from `origin/main`. Refuses on a dirty tree, fast-forward only, so it never silently merges divergent history.
- **`/gm path`** — view or relocate campaign storage via the `GM_CAMPAIGN_ROOT` environment variable. Useful if you keep your campaigns in iCloud, on a network drive, or anywhere other than the default location. Existing campaigns aren't auto-migrated; the path resolver handles legacy fallback + copy-on-access.
- **`scripts/paths.py`** — central path resolution module. All campaign reads/writes route through `find_campaign()`, which honours `GM_CAMPAIGN_ROOT`, falls back to the legacy default, and copies on access if the campaign was found in the legacy location. Decouples the skill from any one install location.

---

## [0.5.0] — 2026-04-23

Display companion polish + arc-aware GM hints. The `app.py` rename to `gm-display-app.py` was overdue — having a generic-named file in the project root made it harder to find when grepping.

### What's new

- **`display/app.py` renamed to `display/gm-display-app.py`** — distinct, greppable name. `start-display.sh` updated to launch by the new name and `pkill` by it cleanly on restart.
- **Arc-aware GM hints.** The DM Help button (◈) now reads `## Campaign Arc` from `state.md` and tailors hints to the current beat — telegraphing what's in scope without spoiling the beat itself.
- **Reliability improvements** — display force-restart at `/gm load` (no more stale processes lingering), per-campaign log routing, `set-campaign` flow tightening, `check_input.py` for queued player input retrieval.

---

## [0.4.0] — 2026-04-20

The narrative-arc release. Every campaign now has a committed three-act narrative shape, and the GM is aware of it during play.

### What's new

- **Dynamic arc system.** Auto-generated at campaign creation from world threat + factions + setting. Six beats (1a/1b setup, 2a/2b confrontation, 3a/3b resolution) defined by *consequence* (`what_changes`) not by event. The arc commits to a thematic resolution. The shape bends; it doesn't break.
- **`/gm arc advance <beat>`** — mark a beat complete at session end.
- **`/gm arc revise`** — when a player choice significantly redirects the story, revise outstanding beats to fit the new direction without retconning what already happened.
- **`/gm arc new`** — generate a new arc from the consequences of a completed one. Same world, new story question.
- **Arc-aware GM steering.** The skill reads `## Campaign Arc` at every session load. World pressure for the next beat lands as a visible event before the beat itself. No beats delivered cold.
- **Campaign import** — `/gm import` accepts PDF, markdown, DOCX, or plain text. Extracts structure type, acts, chapters, key beats, telegraph scenes, NPCs, factions, and quest hooks. Builds all campaign files automatically.
- **Live State Flags** in `state.md` — compaction-resistant key-value block holding cover, faction stances, and NPC dispositions. Read first on any recap or status claim before falling back to fuller files.
- **`state.md` template** updated to include the arc + Live State Flags structure by default.

---

## [0.3.0] — 2026-04-18

Routing architecture + model evaluation. This release made open-tabletop-gm actually portable across LLMs, not just nominally.

### What's new

- **Model routing policy** — explicit Script / Tier-1 / Tier-2 / Tier-3 tiers per task class. Mechanics offload to scripts; narration uses the strongest available model; lookup uses the cheapest.
- **Lazy script loading** — `SKILL-scripts.md` and `SKILL-commands.md` load once at session start instead of being inlined in the system prompt. Smaller context footprint per turn.
- **`probe/` directory** — narrative-quality probe with 5-judge ensemble. 37-model sweep across OpenRouter providers; results in `probe/results/`. `--runs N` for averaged scores.
- **`SYSTEM-PORTING.md`** — first draft of the guide for porting non-D&D systems. Establishes the `systems/<system>/` module convention.
- **LLM guide expansion** — model-routing examples, OpenCode and LM Studio integration notes, narration vs. mechanics split documented.

---

## [0.2.0] — 2026-04-18

The first sync from claude-dnd-skill into this project. Display fixes + GM discipline mechanisms (`## DM Style Notes` → `## GM Style Notes`) ported across, with terminology adapted and Claude-specific paths replaced with relative ones.

### What's new

- **GM discipline mechanisms** — calibration block in `state.md → ## GM Style Notes`, read at every load, accumulates table-specific patterns across sessions. Compounds the skill's "read this specific player" standard rather than resetting each session.
- **NPC full-entry split convention** — `npcs.md` index + `npcs-full.md` per-NPC entries with personality axes, relationships, hidden goals. GM reads the full entry proactively before voicing dialogue.
- **Display fixes** — faction validation, device approval persistence, deadlock fix, sheet modal `console.warn` + `/gm load` hint.
- **Autorun mid-wait queue check** — when a GM message interrupts the autorun wait, check `.input_queue` once before processing the message.

---

## [0.1.0] — 2026-04-16

Initial release. The shape of the project was already there at first commit.

- Persistent campaigns at `<campaign-root>/<name>/` with `state.md`, `world.md`, `npcs.md`, `session-log.md`, `characters/`.
- `/gm` command suite: `new`, `load`, `save`, `end`, `list`, `recap`, `world`, `quests`, `character new/sheet/import/level-up`, `roll`, `combat start`, `rest`.
- Twelve applied GM behavioral standards in `SKILL.md` enforced as hard constraints in every session.
- Helper scripts: `dice.py`, `combat.py`, `character.py`, `tracker.py`, `calendar.py`, `lookup.py`, `xp.py`, `ability-scores.py`, `campaign_search.py`.
- Cinematic display companion (Flask SSE): typewriter narration, scene-reactive backgrounds, dynamic sky canvas, live party sidebar, LAN mode with TLS, player input form, autorun mode.
- Bundled SRD dataset (D&D 5e for the default `systems/dnd5e/` module); `systems/<system>/` convention for porting other rulesets.

---

## Versioning policy

- **PATCH** (0.7.x) — bug fixes, doc updates, no behavior change.
- **MINOR** (0.x.0) — new commands, new scripts, new opt-in features. Existing workflows continue to work without modification.
- **MAJOR** (x.0.0) — breaking change to campaign data format, command rename/removal, or workflow that requires migration.

Tag releases with `git tag v<version>` and update both `VERSION` and `CHANGELOG.md` in the same commit. Tags follow `vX.Y.Z` format.
