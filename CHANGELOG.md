# Changelog

All notable changes to open-tabletop-gm are documented here. The skill follows [semantic versioning](https://semver.org/) — `MAJOR.MINOR.PATCH` where MAJOR breaks an existing campaign or workflow, MINOR adds significant new capability, and PATCH fixes bugs without changing behavior.

The current installed version is recorded in the `VERSION` file at the repo root. Run `python3 scripts/update_skill.py --check` (or `/gm update --check`) to compare your local copy against `origin/main`.

Versions before **0.7.0** are reconstructed retroactively from git history; the dates reflect the commit each version is anchored on. Going forward, every release lands in the same commit as a `VERSION` bump and a CHANGELOG entry.

This project is the LLM-agnostic, system-flexible fork of [claude-dnd-skill](https://github.com/Bobby-Gray/claude-dnd-skill). It tracks behind on features that need adaptation for non-Claude tooling and for system-agnostic design; the goal is parity on what makes sense to port and an independent track on what doesn't.

---

## [Unreleased]

## [0.15.0] — 2026-09-16 — Creature defenses, narration badges, and a working SRD build

Ten fixes in one release, so an existing install updates once and receives all
of them. The SRD dataset builds again from a fresh clone. Creatures carry their
resistances and immunities into play. Narration blocks are marked with a scene
badge. XP awards are recorded and can be reconciled against a character sheet.
A dice result no longer cuts off the sentence you were reading, and the reading
column grows with the text size instead of narrowing. The test suite runs in CI
for the first time.

Several of these existed in the source already and had never reached a player.
Where that is the case the entry says so, and the commit history has the full
account.

### Fixed — the SRD dataset could not be built at all

- **Every SRD source returned 404.** `build_srd.py` fetched from
  `5e-bits/5e-database/main/src/2014/`; upstream added a language directory and
  the files are at `src/2014/en/` now. Because the generated dataset is
  gitignored, an existing checkout kept running on data built before the move
  and nothing degraded — it broke only a fresh clone, which is the case nobody
  runs. Verified against a control (the repo's README returned 200, so the
  404s were the path and not the network). The corrected path builds 1,267
  records: 319 spells, 237 equipment, 362 magic items, 15 conditions, 334
  monsters. (#42)
- **A build that fetched nothing reported success.** A failed fetch printed to
  stderr, became an empty list, and the build carried on and wrote a dataset
  containing nothing over a good one. Fetch failure and "fetched, and it was
  empty" are now different values, and the writer refuses to overwrite when
  every category came back empty. (#42)

### Added

- **Creature defenses.** Damage resistances, immunities, vulnerabilities and
  condition immunities were in the SRD all along and were dropped by the
  normaliser, so nothing could show them and the GM had no record to consult.
  They are now kept and shown in the creature block — immunities on 136 of 334
  creatures, condition immunities on 92, resistances on 70, vulnerabilities on
  15. Nothing applies them to damage automatically; the GM reads and
  adjudicates, as before. (#43)
- **An XP award ledger.** An award left no trace except a number on a sheet, so
  an award that never happened was invisible until a player noticed weeks later
  that their total had not moved. `campaigns/<name>/xp-ledger.jsonl` records
  each one, and `xp.py check --campaign <name>` reconciles it against the
  sheets and exits non-zero when a sheet holds less than the ledger recorded.
  It detects gaps; it does not fill them. (#46)

### Fixed — features that existed and never ran

- **Narration block badges.** A keyword table, a function that built the image,
  and a CSS class — and the function was never called from anywhere while the
  class had no style rule at all. Nobody had ever seen a badge. It is now wired
  and styled, and it no longer depends on English: block KIND (NPC, dice,
  tutor) is badged with no word list, so that path works in every language, and
  the semantic word list moved into the system's `ui.json` where a campaign in
  another language can override it. (#45)
- **A block arriving mid-narration no longer dumps the paragraph.** An NPC
  line, dice result or tutor note used to snap the rest of the prose to its end
  so it could land underneath — the reveal thrown away to deliver the thing
  that usually explains the sentence you were reading. Blocks are now held
  until the typewriter genuinely drains, with a re-arming check so continuing
  narration does not get cut mid-paragraph, and an 8-second valve so a stalled
  reveal can never swallow a dice roll the table is waiting on. (#41)
- **Text Size scaled the type but not the column.** `#text-content` held a
  fixed 820px measure while the control multiplies the font up to 2.0, so the
  largest setting gave roughly half the words per line — a ribbon, chosen by
  the person who found the text hard to read. The measure now scales with the
  same variable, clamped against the viewport.

  Measured across window widths, in characters per line:

  | viewport | 1.0 | 1.4 | 2.0 |
  |---|---|---|---|
  | 1440px | 82 | 62 | 44 |
  | 1920px | 82 | 82 | 67 |
  | 2560px | 82 | 82 | 82 |

  The measure is fully preserved where there is room for it. On a 1440px
  window it is not: the sidebar and settings gutters reserve 570px between
  them, so the column cannot exceed 870px no matter what the setting says, and
  the type keeps growing past the point the line can hold it. Collapsing either
  column gives the space back. Fixing that properly means the gutters shrinking
  with the scale, which is a layout change rather than a one-line one. (#44)

### Fixed — non-English installs

- **93 text-I/O call sites still took the locale encoding.** The 0.14.1 sweep
  fixed bare `open()` and added a guard; the guard measured that one property
  and `read_text`, `write_text` and every `subprocess` call that decodes child
  output were never checked, with `probe/` excluded outright. Run under a
  non-UTF-8 locale the suite went 15 failed / 12 errors before this and passes
  after. Adds `scripts/utf8io.py` for reading a file a pre-sweep install wrote
  in a legacy codepage, which refuses rather than returning replacement
  characters a write-back would make permanent. (#38)

### Fixed — XP

- **An award against a sheet with no XP field was discarded in silence.**
  `re.sub` was written back without checking whether it matched, so a
  mismatched sheet kept its old XP with no error. Worse, the pattern required
  digits before the slash while a fresh template sheet holds `**XP:** / 2700` —
  so the first award against a new character was exactly that case. Now uses
  `re.subn` and warns when the field is genuinely missing. (#40)

### Changed

- **The "not in the dataset" link is no longer a guess.** It slugified a name
  and constructed a URL that nothing checked, so a name that did not match the
  target site's convention dead-ended, and an unknown category degraded to a
  bare slug at the site root. Constructed links now point at an SRD reference
  verified per category against a control, and it is the same SRD content
  without the ads. A supplemental record still links to the page it was fetched
  from, because that is where non-SRD content lives. A category with no
  verified mapping now produces no link at all. (#47)

### Internal

- **CI exists.** There was no `.github/workflows/` directory; 9 test files and
  nothing ran them. Adds a matrix across ubuntu/macos/windows on Python 3.10
  and 3.13, plus a non-UTF-8 locale job — with `PYTHONCOERCECLOCALE=0` and an
  assertion that the locale really is non-UTF-8, because PEP 538 coerces C to
  C.UTF-8 on Linux and would otherwise make that job pass without testing
  anything. Actions pinned by SHA. (#39)
- 146 tests, up from 105, all passing under both a UTF-8 and an ASCII locale.
  Every new guard was break-tested and fails for its own reason.


## [0.14.1] — 2026-08-23 — Non-English display fixes

Two bugs reported from a Russian-language install, both of which only appear outside an English, UTF-8 environment and neither of which fails loudly enough to notice from the developer's side.

### Fixed

- **Campaign text no longer corrupted on a non-English Windows install.** An in-world date was rendering as `18 РЎРµСЂРїР°РЅСЊ, 412 РѕС‚ РџР°РґРµРЅРёСЏ РЎРІРѕРґРѕРІ` instead of `18 Серпань, 412 от Падения Сводов` — UTF-8 bytes decoded as cp1251, the Windows ANSI code page for Russian. Python's `open()` falls back to the locale encoding when none is given, so every bare `open()` was a corruption site: 67 of them across 15 files. All now pin `encoding="utf-8"`, `start-display.sh` exports `PYTHONUTF8=1` so the *default* is UTF-8 rather than only the call sites that exist today, and `scripts/paths.py` reconfigures the standard streams so printing non-ASCII to a cp1251 or GBK console does not raise. The same bug reaches Chinese users as GBK/cp936. (#36)
- **Display icons no longer 404.** This fork carried `display/templates/` without `display/icons/` or the Flask route that serves it, so all ~20 icon references in the UI — class badges, dice and block badges, the corner logo, the app icons — returned 404 and rendered as blank boxes. The 39-icon set and the `/icons/` and `/favicon.ico` routes are now in place. (#37)

### Internal

- `tests/test_encoding_utf8.py` and `tests/test_display_icons.py` are the detectors that were missing for both bugs. The encoding guard works two ways, since neither is sufficient alone: Python's own `-X warn_default_encoding` catches `read_text`/`write_text` as well as `open()` but only on code that runs, and an AST walk covers the paths no test executes. The icon guard reads names out of the template the way the browser does, including the three tables the JS assembles names from at runtime — the ones a search for a literal path never finds. Both were break-tested in each direction.


## [0.14.0] — 2026-07-24 — GM-side discipline sync from claude-dnd-skill v2.4.0

Ports the GM-discipline and quality-of-life work from claude-dnd-skill **v2.4.0**, generalized to OTGM's system-agnostic core where the upstream version was D&D-flavored. What's genuinely 5e-only stays in `systems/dnd5e/`; mechanical rendering is driven by the system's UI manifest, not a hardcoded list.

### GM discipline (core — SKILL.md)

- **New Standard 13 — Never Play the Player's Side.** A hard constraint separating the GM's authority from the player's: never speak a PC's dialogue, narrate their private thoughts, or decide their actions; adjudicate each *declared* action on its own terms and let it resolve rather than skipping it, swapping it, or narrating past it; and treat the party as exactly the named player characters, never inventing a companion or putting words in a real player's mouth. Faster/weaker models drift into acting for the player without an explicit rule — this is that rule. (Numbered 13 in OTGM, which does not carry the upstream "Open Each Scene With a Bang" standard.)
- **Table Dials — optional per-campaign tuning.** Three neutral-by-default settings in `state.md → ## Session Flags`: `difficulty` (stakes/lethality only — Standard 7 still governs rolls), `spotlight` (how much the GM drives vs. follows), and `pacing` (pressure vs. room for character scenes). An unset dial changes nothing; a set dial is honored every turn like `## GM Style Notes`.
- **Narration hygiene.** Standard 4 now states plainly that narration is prose for the table, never a document — no markdown headings or bulleted lists inside the fiction, opening scenes included.
- **Bold-play reward backstop (core hook + 5e binding).** Standard 12's generalized reward hook now says: don't rely on remembering — where the system module defines a hard, table-visible trigger, honor it every time. The concrete 5e binding lives in `systems/dnd5e/system.md → ## Bold Play Reward`: a natural 20 on any d20 test (or a nat-20 death-save stabilize) awards Inspiration on the spot unless the character already holds it.

### Continuity & memory (core)

- **Pinned Facts — the memory the GM always keeps.** A new `## Pinned Facts` section in `state.md`, read at every `/gm load` alongside `## GM Style Notes` and kept hot all session. It holds the small, stable set of soft facts a table never wants forgotten (a promise made, a dead sibling's name, a house rule, an in-joke). New command **`/gm pin`** adds/lists/removes them; unlike Live State Flags they are never rewritten wholesale at save.
- **Keep the world clock honest.** SKILL-scripts.md now states the clock is continuity, not decoration: narrate consistently with the last pushed time, advance it deliberately by how much an action costs, and reconcile a drift with a fresh `--world-time` push — including *backward* to the correct time, which undoes nothing since timed effects run on their own tracker durations.
- **Firmer arc-advance discipline + stale-pointer nudge.** `/gm arc advance` now states advancing the pointer is not optional bookkeeping (clearing the current beat's outstanding items, or the party moving into the next beat/chapter's situation, *is* an advance). `/gm load` now sanity-checks a stale pointer (current beat looks finished but never advanced) and offers to move it instead of opening another scene in a done beat.

### Rules lookup & character creation

- **Rules lookup no longer dead-ends on a typo.** `systems/dnd5e/lookup.py` gains a `suggest()` near-miss pass: when an exact/substring lookup misses, it fuzzy-matches the query against real dataset names and offers the closest ones (`poisonned` → Poisoned, `fireballl` → Fireball). The CLI prints a `Did you mean: …?` line; the display's lookup modal renders the misses as tappable chips that re-run the lookup. Suggestions honor the category when given and search all categories otherwise. Zero model calls — reads only the bundled dataset.
- **Describe-it character creation (core flow, system-deferred legality).** `/gm character new` now opens with a build-path choice: the deliberate `Step by step` flow, or a new `Describe it` path where the player says who the character is in a sentence or two and the GM assembles a legal, level-appropriate sheet from it. The prose→concept flow and the single confirm-or-adjust pass are core; the sheet build and legality validation defer to the active system module (`systems/<system>/system.md`) and its lookup. Both paths converge into the same name-check, calc, and write steps.

### Relationship graph & display

- **Typed party disposition in the relationship graph.** `gm_graph.py` gains `set-disposition --to <npc-or-faction> --level <allied|friendly|neutral|suspicious|hostile>` — the party's stance toward an NPC (a `disposition` edge) or faction (a `standing` edge) on the same five-point scale the display's faction panel uses. Edges run from a shared, auto-created `party` node; setting a new stance closes the prior one at that session (arc stays queryable) and only the current stance surfaces in `scene-context`, rendered inline (`The Party --[disposition:suspicious]--> Aldric`). The `/gm save` sweep proposes these alongside NPC↔NPC edges. Covered by tests.
- **Display: "New ↓" pill when you've scrolled up.** Fresh narration arriving while you're scrolled up now surfaces a small tap-to-jump pill at the bottom of the reading column, instead of landing silently below the fold. It retires itself the moment you catch up.
- **Display: tappable conditions (manifest-driven).** Condition pills are now tappable — tap Poisoned, Prone, etc. to pull the rule text in the lookup modal. The tap is wired by a `srd_lookup` / `lookup_category` flag on the system's `tag_list` widget in `ui.json`, not a hardcoded condition list, so a system without a rules dataset simply omits the flag. A name with a suffix like "Exhaustion (2)" resolves to the base condition.
- **Display: settings column no longer overlaps the narration, and folds away.** The reading column now reserves guaranteed right clearance (`max(340px, 18vw)`), and a new `Hide ▶ / ◀ Settings` toggle collapses the settings column (mirroring the left sidebar toggle) so the narration reclaims the space. The choice persists per browser.

### Cleared remaining Claude-coupling leftovers

- **`wrapper.py` wraps any agent**, not just Claude — set `GM_AGENT_CMD` (default `claude`) to wrap `opencode`, `gemini`, etc. The PTY wrapper is a legacy/optional path anyway (the canonical setup runs the agent directly + `send.py`).
- **The phone `/character` route resolves via `paths.py`** (honors `GM_CAMPAIGN_ROOT`) instead of `DND_CAMPAIGN_ROOT` + a hardcoded `~/.claude/dnd` root; the legacy `~/.claude/dnd/characters/` path is kept as a final fallback for older installs.
- Cosmetic: "the DM (Claude)" → "the GM agent" in a couple of script docstrings.

## [0.13.0] — 2026-06-27 — System-agnostic character UI + model-agnostic GM hint

### System-agnostic character UI (systems can define their own sidebar + sheet)

- **The character sidebar and sheet are now driven by a per-system UI manifest** instead of a hardcoded D&D layout. A system ships `systems/<name>/ui.json` describing its sidebar widgets, sheet combat strip, and attribute grid; the display renders from it. A new system becomes a ~40-line JSON file rather than new front-end code. See `systems/UI-MANIFEST.md` for the widget catalog and a Shadowrun 5e example, and `systems/dnd5e/ui.json` for the reference manifest.
- **Backward compatible.** The renderer carries a built-in default manifest that reproduces the original D&D 5e display exactly, so campaigns with no `ui.json` (or no system declared) look identical to before. The attribute grid now also supports raw ratings (`show_modifier: false`) for dice-pool systems, not just D&D's score+modifier.
- A campaign selects its system module with a `**System Module:** <name>` line in `state.md` (distinct from the human-readable `**System:**` label); absent ⇒ `dnd5e`. New `paths.campaign_system()` resolves it. Switching systems takes effect on the next display load.

### Model-agnostic GM hint (thanks @eviloverclaude)

- **The ◈ GM Help hint no longer depends on Claude.** `dm_help.py` previously shelled out to a hardcoded `claude -p --model claude-sonnet-4-6`, so the feature silently produced nothing for anyone running OTGM through opencode, gemini, mistral, or any non-Claude tooling. It now resolves a backend portably: set `OTGM_HINT_CMD` to your own model command (prompt on stdin, hint on stdout), or let OTGM auto-detect a known CLI on `PATH` (`claude`, `opencode`, `gemini`, `llm`). `OTGM_HINT_MODEL` pins a model for the auto-detected backend; `OTGM_HINT_TIMEOUT` bounds the call. Claude still works out of the box but is no longer a dependency, and with no backend available the feature no-ops instead of breaking play.
- **Fixed `push_stats.py` reading the display token from a hardcoded `~/.claude/skills/dnd/display/.token`** instead of its own display directory like every sibling script. This broke stat pushes for any install outside the Claude skill path.

### Display input fixes (synced from claude-dnd-skill)

- **The PARTY INPUT box no longer covers the bottom of the narration.** The fixed input panel grows when it expands (or the editorial drawer opens, or the mobile keyboard raises the viewport); a `ResizeObserver` now keeps `#text-scroll`'s bottom padding synced to the panel's live on-screen footprint so the last lines of narration always clear it. No-op in phone input-only mode.
- **A failed player-input submit now says so.** If the browser→server POST fails after retries, the Stage button shows "Send failed — tap to retry" (the typed text and its `localStorage` cache are preserved, so a tap re-sends) instead of silently resetting to "Stage" — which previously read as "submitted but not acknowledged."

### Sync from claude-dnd-skill v2.1.x — backend + GM-side discipline

Ports the system-agnostic portions of the v2.1.0–v2.1.4 upstream lineup. Backend infrastructure and GM-side docs land here; the deeper phone UX bits (on-screen dice drawer for no-phones games, per-PC Rolls toggle in phone Settings, status-strip rewrite for one-tap send) are deferred to a follow-up PR to be adapted properly against OTGM's tab-based phone UX.

- **`roll_mode` session flag** — campaigns now declare in `state.md → ## Session Flags` whether players roll their own PCs (default — GM waits for the result) or the GM rolls everything openly. `/gm new` asks at session 0; `/gm load` prompts once on legacy campaigns missing the field. SKILL.md → Dice convention rewritten with the new semantics, including the per-character override path via the phone Settings → Rolls toggle (surfaced to the GM as a `[[<Char> roll mode: …]]` directive prepended by `check_input.py`).
- **Narration length directive** — display companion now exposes a Narration slider (250–2500 words). Setting it POSTs to `/narration-pref`; `check_input.py` prepends a `[[Narration length for this turn: aim for ~N words…]]` directive to the queued action so the GM honors the table's pacing this turn. SKILL.md documents how to read and obey the directive.
- **TCC-safe autorun** — `display/autorun-wait.sh` replaced by `display/autorun_wait.py`. macOS TCC blocks shell-level file creation under `~/Documents`, which broke autorun mode for anyone running OTGM out of that path. Pure-python rewrite handles session invalidation, countdown broadcast, queue poll, and `/queue/consumed` POST with identical semantics. Old `.sh` deleted.
- **Phone-aware dice routing infrastructure** — `gm-display-app.py` now tracks which character each SSE client is bound to (`_client_chars`) via the new `?character=<name>` stream query param, and exposes `_phone_present()` so `dice_request` payloads include `onscreen_targets` (characters with no live phone). The follow-up UI PR will use this to auto-open the on-screen dice drawer for those characters; the field is benign without UI support.
- **`GM_REQUIRE_APPROVAL` env var** — device approval gate now defaults to **off** (auto-trust any reachable device). The approve/deny friction made every casual home-LAN game feel like a security checkpoint. Set `GM_REQUIRE_APPROVAL=1` to restore the gate on untrusted networks.
- **Reading-text-size stepper** — display companion gains a Text Size control in audio-controls (A− / A+ / click % to reset). Multiplies `--text-scale` on `#text-content`, persisted to `localStorage["gm-text-scale"]`. Anti-FOUC read in the top-of-document inline script. Font-size, not page zoom — keeps layout intact at scale.
- **Display README** — component table updated for `gm-display-app.py` + `autorun_wait.py`, Player input panel section rewritten to document the `GM_REQUIRE_APPROVAL` default and the phone Settings (Text Size + Narration; Rolls toggle pending in the follow-up PR).
- **License formalized as AGPL-3.0-or-later.** Added canonical `LICENSE` file with `Copyright (c) 2026 Neural Initiative LLC` and a `CONTRIBUTING.md` documenting the contribution licensing handshake. The README now includes a proper License section. Self-hosting and modification remain explicitly welcome; AGPL protects against closed-source SaaS forks.

## [0.12.0] — 2026-05-31 — Phone companion + theme picker (sync from claude-dnd-skill v1.10.0..v1.12.1)

Four upstream PRs land in one bundled sync: phone dice companion (#38), mode switcher + dice-pending badge XSS hardening (#39, v1.11.0), light/dark/auto theme picker (#40, v1.12.0), and audio-controls legibility fixes (#41, v1.12.1). All adapted to open-tabletop-gm conventions — GM terminology, relative-path scripts, `gm_*` localStorage keys (the per-browser TTS / phone / theme preferences), `GM_TTS_KEY` env var, key file at `~/.config/open-tabletop-gm/tts.key`. The `dnd-token` meta tag and the `dnd_device_id` localStorage key stay as-is in this sync — those are fossils preserved across all otgm syncs to avoid invalidating existing approved-device bindings on operator machines.

### Phone dice companion (upstream PR #38, contributed by Ethros)

Adds a phone-side player companion to the existing Flask + SSE display:

- `?view=input&char=<Name>` URL bindings (one phone per character).
- Three-tab phone layout: **Move** (action input) / **Roll** (server-side dice) / **Sheet** (read-only character sheet rendered from the campaign's markdown).
- `POST /player-input/dice` rolls server-side with `secrets.randbelow`; slot-machine reveal locks on the authoritative value.
- `POST /dice-request` lets the GM (or LLM tooling) prescribe a roll to one or more named characters — their phones pre-fill (die, modifier, adv/dis, label, optional DC), lock all controls except Roll, pulse the Roll button. Pad stays locked after a prescribed roll resolves to prevent unsolicited follow-ups.
- `send.py --dice-request --wait` blocks the GM until every prescribed character rolls (polls `GET /dice-request/<id>`). Exits 2 on timeout with a clean `DELETE` of the request.
- Main display "Waiting on…" badge driven by a new `dice_pending` SSE event, replayed on `/stream` connect.
- New `scripts/dice_player.py` wrapper takes `dice.py`-style syntax (`d20+5 --player piper --label "Stealth check"`) so the GM has a familiar CLI that routes through `/dice-request`.
- New `GET /character/<name>` endpoint serves the character markdown for the Sheet tab. Token-gated; both `<name>` and the resolved campaign value pass through an allowlist + length cap before `os.path.join`.

Token-gated on every new endpoint. `secrets.randbelow` for all dice. Strict input validation: spec regex `\d{1,2}d\d{1,3}` plus range checks, modifier clamped ±100, character/label strings stripped of shell metacharacters and length-capped. No external resources loaded, no new dependencies.

### Mode switcher + XSS hardening (upstream PR #39 / v1.11.0)

- **Phone-mode switcher.** Base URL now carries a small "📱 Phone Mode" button on the right rail (above the audio-controls cluster). Click drops a character dropdown populated from the campaign's current player roster (read from the existing `/stream` `stats` payload — no new server endpoint). Pick a name and the browser navigates to `?view=input&char=<Name>` automatically.
- **Full-display toggle.** Symmetric "👁 Full Display" button bottom-left in input mode strips the `?view` / `?char` query params and returns to the base view.
- **Defense-in-depth XSS fix on the dice-pending badge.** The "Waiting on…" badge rendered the server's `dice_pending` snapshot via `innerHTML` to support inline `<span class="dpb-label">` styling. Server-side validation strips `` ` $ \ `` from labels + character names but leaves `< > &` intact. A shared `_escHtml()` helper now wraps both `e.label` and every `e.pending[]` member name before they reach the template literal. Server side of `POST /dice-request` is unchanged — the right escape boundary is the innerHTML sink.

### Light / dark / auto theme picker (upstream PR #40 / v1.12.0)

Three-state theme picker. Default behavior unchanged — anyone who doesn't touch the picker continues to see the same dark, atmospheric display.

- **Dark** *(default)* — the existing ornate look.
- **Light** — parchment scroll on dark scenery. Body, vignette, and particle backdrop stay dark for contrast; `#text-content` becomes a cream "page" with deep-ink narration. Block-identity colors preserved at darker shades (GM-tab purple, NPC bronze, player blue, tutor moss, tutor-warning amber).
- **Auto** — follows the operating system's `prefers-color-scheme`. Switches automatically and tracks change live.

Picker lives as a fourth row in `#audio-controls` (top-right cluster) alongside Sound Effects / Type Speed / Auto Narrate. Click to cycle through Dark → Light → Auto → Dark. Per-browser persistence in `localStorage["gm-theme"]`. A small inline `<script>` in `<head>` reads that value and sets `data-theme` on `<html>` *before* the stylesheet parses — prevents the dark→light or light→dark flash on every load. Auto mode leaves the attribute off and lets `@media (prefers-color-scheme: light)` resolve.

Vellum palette carried over from the Neural Initiative implementation: parchment radial gradient `rgba(255, 245, 220, 0.96)` → `rgba(238, 224, 188, 0.82)`, deep-ink narration `rgb(40, 28, 14)` with warm-light shadow, bronze accents `rgb(70, 50, 18)` / `rgba(140, 95, 20, *)`. Action buttons flip to dark plate + cream text. Modal panels get the same parchment treatment with deep-ink text; modal backdrop stays dark to dim the scenery behind it.

Covers all narration block types, input panel + char tabs + staged queue, sheet + SRD modals + content tables, world clock, composing indicator, all v0.11.0 TTS chrome, the new phone-mode + full-mode buttons, and the dice-pending badge.

### Audio-controls legibility fixes (upstream PR #41 / v1.12.1)

Four small fixes surfaced by table-side testing immediately after the theme picker landed:

- `.theme-label` had no CSS rule and was rendering at browser-default `<span>` size (~16px) while every other label in `#audio-controls` was 7.5px Cinzel. Folded into the combined `.speed-label` / `.narrate-label` / `.theme-label` declaration so all three share font, sizing, and the new pill styling.
- The three click-to-cycle labels (Type Speed, Auto Narrate, Theme) now look like pill buttons — subtle dark inset background, bronze 1px border, 4px corner radius. Active-state ("On", "Light", "Auto") gets a stronger pill background.
- Default `#audio-controls` opacity bumped from 0.38 → 0.78. The cluster used to fade to barely-visible at rest; combined with `rgba(*,0.75)` text alpha that gave ~0.28 effective alpha against the dark backdrop. Individual label defaults bumped from `rgba(180,140,60,0.75)` to `rgba(220,185,100,0.85)`.
- Per-row hover affordance — each `.audio-row` now has its own hover state (subtle background pill, brighter label color). The row under the cursor reads as the active click target.
- `.dice-result` text was `#c8a040` with a faint glow — called out as "barely visible." Bumped to `#f0d27a` with a stronger amber glow plus a deep-ink drop shadow, wrapped in a faint dark plate. Light-mode dice-result picks up a matching deep-ink-on-parchment treatment.

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
