# Changelog

All notable changes to open-tabletop-gm are documented here. The skill follows [semantic versioning](https://semver.org/) — `MAJOR.MINOR.PATCH` where MAJOR breaks an existing campaign or workflow, MINOR adds significant new capability, and PATCH fixes bugs without changing behavior.

The current installed version is recorded in the `VERSION` file at the repo root. Run `python3 scripts/update_skill.py --check` (or `/gm update --check`) to compare your local copy against `origin/main`.

Versions before **0.7.0** are reconstructed retroactively from git history; the dates reflect the commit each version is anchored on. Going forward, every release lands in the same commit as a `VERSION` bump and a CHANGELOG entry.

This project is the LLM-agnostic, system-flexible fork of [claude-dnd-skill](https://github.com/Bobby-Gray/claude-dnd-skill). It tracks behind on features that need adaptation for non-Claude tooling and for system-agnostic design; the goal is parity on what makes sense to port and an independent track on what doesn't.

---

## [Unreleased]

- **License formalized as AGPL-3.0-or-later.** Added canonical `LICENSE` file with `Copyright (c) 2026 Neural Initiative LLC` and a `CONTRIBUTING.md` documenting the contribution licensing handshake. The README now includes a proper License section. Self-hosting and modification remain explicitly welcome; AGPL protects against closed-source SaaS forks.

## [0.11.0] — 2026-05-28 — Narrator TTS + i18n expansion (sync from claude-dnd-skill v1.10.0)

Two additive features ported from claude-dnd-skill v1.10.0, adapted to open-tabletop-gm conventions (GM terminology, relative paths, `GM_TTS_KEY` / `GM_SFX_LANGUAGES` env vars, key file at `~/.config/open-tabletop-gm/tts.key`).

### Narrator TTS via Gemini Flash TTS (optional)

Per-block speaker buttons on every `.dm-block` and `.npc-block` in the display companion, paired with a 9-voice dropdown (4 male: Charon, Enceladus, Fenrir, Umbriel; 5 female: Aoede, Gacrux, Kore, Vindemiatrix, Zephyr). Click to hear the block read aloud. Synthesis happens server-side via Google's Gemini Flash TTS through your own AI Studio API key — full setup walkthrough at `docs/SKILL-tts.md`, about five minutes with a free Google account.

A per-browser **Auto Narrate** toggle in the top-right audio controls (saved to `localStorage`) auto-plays each new narration block on that browser only. Turn it on for the casting TV, leave it off on player phones.

Voice selection is per-campaign — persisted to `state.md → ## Session Flags → tts_voice: <name>`. Switching voices mid-session updates the active marker across every visible block's dropdown simultaneously.

**Off by default.** With no key configured, the speaker buttons don't render and the display behaves exactly as it did before. Three layered fail-silent gates: no key → 503 and inert button; invalid voice → silent fallback to default; upstream error → button shows a brief diagnostic label, then resets, with text-only narration continuing.

Browser-side playback uses AudioContext with manual Int16 → Float32 PCM conversion rather than HTMLAudioElement, because iOS WebKit's per-call gesture gating on `<audio>` is hard to work around reliably. AudioContext only needs `ctx.resume()` once per session inside a user gesture. The 2000-character input cap matches Gemini Flash TTS's effective response limit; longer GM blocks are naturally chunked at block flush.

Gemini Flash TTS auto-detects the input language from the text — all 24 supported locales work transparently without any explicit language code on the request. A Spanish-language campaign just narrates in Spanish.

### i18n expansion to all 24 Gemini-supported locales

The two-language SFX foundation (English + Chinese) introduced upstream is extended to all 24 locales Gemini Flash TTS supports: `ar`, `bn`, `de`, `en`, `es`, `fr`, `hi`, `id`, `it`, `ja`, `ko`, `mr`, `nl`, `pl`, `pt`, `ro`, `ru`, `ta`, `te`, `th`, `tr`, `uk`, `vi`, `zh`. Same dict-of-dicts language-pack structure — each language contributes trigger phrases per SFX category, Latin scripts use word-boundary regex, unspaced scripts (CJK, Thai, Arabic) use literal substring matching.

The `_PRINTABLE` character allowlist and `_CHAR_NAME_RE` regex in `display/gm-display-app.py` and `display/wrapper.py` widen to accept letters from every script in scope: Latin Extended A/B, Greek, Cyrillic, Hebrew, Arabic, Devanagari, Bengali, Tamil, Telugu, Thai, Vietnamese diacritics, Hiragana, Katakana, Hangul, and the existing CJK ranges. Player and NPC names in any supported script are now first-class.

Default behavior is unchanged. The active language list stays `["en"]` (English-only) until explicitly overridden via the new `GM_SFX_LANGUAGES` environment variable (e.g. `export GM_SFX_LANGUAGES=en,zh,es`) or per-campaign via `state.md → ## Session Flags → sfx_languages: en,zh`.

Translation quality across the new packs is best-effort starter content. Community PRs to refine any pack are welcomed — the structure is designed for additive, language-by-language extension with zero code changes.

### README — Other ways to play

The README gains a short "Other ways to play" section between the Status block and Quick Start. It names the two sibling projects sharing this framework's design DNA: claude-dnd-skill (the Claude Code-specific upstream) and neuralinitiative.ai (a hosted browser version for users who'd rather skip a local install). Same maintainer, same design DNA, different surfaces.

## [0.10.0] — 2026-05-08 — System-versioning infrastructure (sync from claude-dnd-skill v1.8.0)

Many tabletop systems ship more than one set of rules over their lifetime. A campaign should declare the edition it's playing once and have the GM honour it from then on, without re-explaining at the start of every session which book the table is using. This release lays the framework-level groundwork for that — system-agnostic, deliberately small, deliberately opaque. The *infrastructure* lives in core; the *content* of any specific edition stays in the system module.

### What changed

**Per-campaign `**System Version:**` field on state.md**

A campaign records its chosen edition on the header line. The value is an opaque string from the framework's perspective — core never parses or validates it. The system module owns what counts as a valid value and what the default is.

- **`paths.campaign_system_version(name)`** for any script that needs to read the field. CLI passthrough: `paths.py campaign-system-version <campaign> [default]`.
- **`paths.system_data_path(system, version, filename)`** for any module that wants to ship version-keyed data files. Resolves to `systems/<system>/data/<filename>`; the system module composes file names however it prefers.

**`scripts/migrate_system_version.py`**

Backwards-compat migrator for legacy campaigns. `--check` (strictly non-mutating) and `--yes` (idempotent stamp + timestamped backup) modes. Used by `/gm load` against legacy campaigns. Edge cases handled cleanly: missing campaign exits 2; non-standard headers exit 0 "not-applicable" (so `/gm load` doesn't pester GMs of campaigns with hand-rolled metadata blocks).

**`/gm new` step 2 (optional version prompt)**

When the system module advertises a `## System Versions` section in its `system.md`, `/gm new` prompts for a version at creation time. Skipped silently otherwise.

**`/gm load` step 3 (migration check)**

Runs the migrator's `--check` and surfaces a one-time migration prompt for legacy campaigns. Already-stamped campaigns proceed silently. Subsequent steps renumbered.

**Display companion `#system-version-badge`**

Sidebar badge populated automatically from the campaign's recorded value. Empty hides. The server reads `paths.campaign_system_version` on `/stats --set-campaign`; `push_stats.py --system-version` exposes an explicit override.

**`systems/dnd5e/system.md` worked example**

Documents how a system module declares its versions via the `## System Versions` section. Other system modules can follow the same pattern when they need multi-edition support.

### Out of scope (deferred to follow-up PRs scoped to system modules)

- Per-version build and lookup routing scripts. These belong in `systems/<system>/scripts/`, not core.
- Edition-specific mechanics (e.g. weapon mastery in 5e 2024). Those are system content.
- The dnd5e module's per-edition datasets. Will land as a separate PR scoped to `systems/dnd5e/`.

### Backwards compatibility

Legacy campaigns predate the field. The migrator backs `state.md` up before any write, stamps the chosen version, and is idempotent. The migration default is **system-defined**, not core-defined — a system module configures whether legacy campaigns silently inherit "the older edition" or are forced to make an explicit choice. Core has no opinion. Character files don't need their own migration; they inherit the campaign's version at runtime.

### Companion development upstream

The parent project, [`claude-dnd-skill`](https://github.com/Bobby-Gray/claude-dnd-skill), shipped v1.8.0 today using this pattern. The dnd5e module there now carries data for both of its published editions, with provenance preserved per record (CC-BY-4.0). otgm users running the dnd5e module will get those data files in a follow-up PR scoped to `systems/dnd5e/`.

---

## [0.9.1] — 2026-05-01 — Display robustness + arc pre-emption (sync from claude-dnd-skill v1.7.5)

Three reliability bugs land hard fixes here, with regression tests so they don't come back. Synced from claude-dnd-skill v1.7.5 — same root causes affected both repos.

### What changed

**send.py — body-bundling restored, integrity checks added**

Bug: when `--stat-*` flags were combined with a heredoc body, `send.py` dispatched the stat update but silently dropped the narration. Root cause was in the stdin-read decision: `_build_stats_payload(args)` was treated as a "body-less" signal, so reading stdin was skipped even when a heredoc was attached.

- **Stdin decision rewritten.** Three categories distinguished cleanly: content flags require a body; truly body-less flags (`--milestone-award`, `--milestone-spend`) skip stdin; stat flags and `--set-campaign` are body-OPTIONAL — stdin read when piped (heredoc), skipped when an interactive TTY (avoids blocking).
- **Pre-flight `_validate_payload(...)`.** Chunk payloads must have text, an award, or a campaign tag; multiple content tags rejected; stats payloads must carry a list. Validation failures abort `sys.exit(2)` with stderr diagnostic.
- **HTTP-level receipt verification.** `_post(...)` now logs every send to `_SEND_LOG` and inspects response status. Non-2xx surfaces body excerpt to stderr.
- **Post-flight self-check.** Tallies failures from `_SEND_LOG`; display-offline yields one quiet stderr line; other partial failures yield `PARTIAL FAILURE` summary + `sys.exit(3)`.
- **Optional `--verify` round-trip** against the new `/health` endpoint. Use during dev/debug.

**gm-display-app.py — non-destructive tail persistence + atomic writes**

Bug: `session_tail.json` got silently wiped to `[]` between sessions, so `/gm load` had no last-scene replay. Root cause: `_load_tail()` cleared the buffer then re-appended campaign-filtered entries; if every entry filtered out, the buffer ended up zeroed and the next `_persist_tail()` wrote `[]` over the file.

- **`_load_tail` is non-destructive.** Builds a candidate buffer first; only swaps it in if at least one entry survived filtering. Empty/all-filtered/corrupt → buffer left alone.
- **`_persist_tail` skips on empty.** Refuses to overwrite an existing non-empty file with an empty buffer. Stderr warning when it does.
- **Atomic writes.** Tempfile + `os.replace(...)` — readers can never see partial state.
- **Legacy fallback path removed.** Tails only land in the campaign-specific file. If `CAMP_FILE` is missing/empty, persist holds the buffer in memory and skips disk — no shared file that bleeds across campaigns.
- **`/health` endpoint added.** Returns `alive`, `tail_buffer` count, `tail_file_size`, `text_log` count, `campaign`, `clients`. No auth required (no PII).

**`/gm save` tail backstop + `verify_tail.sh` + `write_canonical_tail.py`**

Belt-and-suspenders for the worst case. `verify_tail.sh <campaign>` checks the on-disk tail is healthy (>50 bytes, parses as a non-empty JSON list, entries have recognizable shape). When unhealthy, the GM writes a canonical replacement directly to disk via `write_canonical_tail.py` from session context — bypasses the display entirely so the file is good even after server crashes. Atomic write, campaign-stamped, capped at 30 entries. Both helpers respect `GM_CAMPAIGN_ROOT`.

**Beat 2b structural fix — pre-emption is a revision trigger**

Bug (campaign-level): when players act faster than the world, a beat's `world_pressure` event plays out fully without the `what_changes` consequence landing. Beats go stale.

Root cause: arc beats were generated with `what_changes` written event-shaped (something specific happens) when it should be consequence-shaped (something fundamentally different is true).

- **SKILL.md rule 8 added.** Pre-emption auto-triggers `/gm arc revise` at `/gm save`. Three landing-path templates: **cost** (party paid for moving fast), **secondary consequence** (world responds to being pre-empted), **deferred** (rewrite `world_pressure` toward same consequence on a longer horizon).
- **`/gm new` step 14 strengthened.** Arc-generation prompt explicitly demands `what_changes` be consequence-shaped, with worked event-vs-consequence example.
- **`/gm save` arc-check rewritten.** Performs explicit pre-emption check on each outstanding beat; auto-triggers `/gm arc revise` when needed.
- **`/gm arc revise` enhanced.** Surfaces three landing-path templates as a structured choice; before/after diff shown for review.

### Tests

- New `tests/test_display_robustness.py` (20 tests) covers: stdin-read decision across all flag combinations including the bundled-stat regression, payload validation, tail load (empty/filtered-out/matching/corrupt/missing CAMP_FILE), tail persist (skip-on-empty/atomic/no-camp-no-write), set-campaign body-optional path.

## [0.9.0] — 2026-05-01

The milestone feature is now visually complete. The award block alone wasn't enough for stack-based reward systems where the count is the whole point — Bennies, Fate Points, Hero Points all rely on knowing how many you have at any moment. This release adds the sidebar counter that v0.8.1 promised was coming.

### What's new

- **Milestone counter in the player sidebar.** Each character card now shows a row per active milestone label (`INSPIRATION 1`, `BENNIE 3`, `HERO POINT 2`) with a gold count pill. Empty labels are not rendered, and a label drops out of the sidebar entirely when its count hits zero — the card stays clean rather than accumulating zero-count entries.
- **Server-side mutation ops `_milestone_inc` and `_milestone_dec`** — the same pattern as the existing `_conditions_add` / `_slot_use` family. Increments are floor-clamped at 0 (a spend before any award has no effect; the label simply doesn't exist on the player).
- **`milestone_caps` per-player override** — for binary reward systems like D&D 5e Inspiration, set `milestone_caps: {"Inspiration": 1}` on the player and the count will never exceed 1 regardless of how many awards arrive. System modules can set this at character creation.
- **`send.py` now POSTs to both `/chunk` and `/stats`** for milestone events. The chunk renders the gold-glow feed block (already shipped in v0.8.1); the stats POST drives the sidebar counter (new).

### Test suite (now 63 tests)

`tests/test_milestone_counter.py` (8 new tests):
- Increment from zero creates the label
- Repeated increments accumulate
- Decrement-to-zero removes the label entirely
- Decrement below zero is floor-clamped (no negative counts)
- Multiple labels coexist on the same player
- `milestone_caps` per-label cap is respected
- Decrement without a prior increment is a no-op
- Other stat mutations (conditions, slots) don't clobber milestones

### Demo verification

In-process simulation: 3 award + 1 spend on Aldric → `{Bennie: 2, Hero Point: 1}`. Mira with `milestone_caps: {Inspiration: 1}` correctly capped at 1 despite two award calls.

### What stays deferred

- Phase 3 hybrid extractor mode — still out of scope for this LLM-agnostic fork.

---

## [0.8.1] — 2026-05-01

Two follow-ups from the v0.8.0 deferred list. The first replaces the upstream's D&D-specific `--inspiration-reason` with a system-agnostic equivalent. The second ports forward the future-tense planning verbs that just shipped in claude-dnd-skill v1.7.3.

### What's new

- **Generic milestone-event support** in the display companion. New `send.py` flags:
  - `--milestone-award NAME [--reason "..."] [--label "Inspiration"]`
  - `--milestone-spend NAME [--label "Inspiration"]`

  `--label` is the system-specific name for what was earned: `"Inspiration"` (D&D 5e), `"Bennie"` (Savage Worlds), `"Hero Point"` (Pathfinder 2e), `"Fate Point"`, etc. Default is `"Milestone"`.

  The award fires a gold-glow `.milestone-block` in the feed showing the character name, label, and reason. Spend events are processed but don't render a feed block (future work: sidebar counter for stack-based systems like Bennies). System modules can map their reward mechanic to this generic event without touching display code.

  The award block is also persisted in the session tail and replayed on browser reconnect.

- **Six new future-tense verbs in the seed**: `plans_to`, `intends_to`, `scheduled_to`, `aims_to`, `expected_to`, `targets`. All `lifetime: dispositional`, medium confidence. The deterministic extractor now picks up GM session-prep prose like *"Vedra plans to file the nomination Friday"* — previously silently dropped.

- **`V` wildcard in pattern templates** — represents a variable verb phrase (1–4 lowercase tokens) between a fixed modal phrase and an entity. One template `"X plans to V Y"` matches `"plans to file"`, `"plans to meet"`, `"plans to ambush before dawn"` against the same regex. Implemented with `(?-i:...)` so the wildcard never accidentally consumes a capitalized entity prefix.

### Test suite (55 tests, up from 48)

- Seven new `FutureTenseVerbTests` ported from upstream — V-wildcard capture, capital-letter exclusion, all six new patterns, end-to-end extraction.

### Demo verification

```
$ python3 display/send.py --milestone-award "Aldric" --label "Inspiration" \
    --reason "took the harder path through the Stairs"
→ gold-glow block in feed: "Aldric  INSPIRATION" / "took the harder path..."

$ /gm graph extract  (against synthetic 1-session log)
Captain Renna Voss --[plans_to]--> Mira Solveig
  "Captain Renna Voss plans to ambush Mira Solveig at the docks."
```

### What stays deferred

- Sidebar counter for stack-based milestone systems (Bennies, Fate Points). Fires correctly, just doesn't accumulate visually yet.
- Phase 3 hybrid mode — still out of scope for this LLM-agnostic fork.

---

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
