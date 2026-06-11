# persistence_v2 — multi-turn story-persistence probe

A methodologically rigorous probe that measures whether a model **remembers** what the bible established, across a 20-turn conversation. Differs from the original `narrative_probe.py` (single-turn × 12 scenarios) by holding state across turns the way a real play session does.

This probe was originally built for [Neural Initiative](https://github.com/Bobby-Gray/neuralinitiative) — the SaaS sibling of `open-tabletop-gm` — and ported here in cleaned-up form so the open-source community can run the same evaluation against any OpenRouter-routable model.

## What it actually measures

For each model, the probe runs the same scripted player path through three **distinct** campaign bibles (medieval fantasy, sci-fi, modern horror). Each bible introduces facts at specific turns (NPC traits, scene anchors, player choices) and tests recall of those facts 6-15 turns later.

**Persistence index** is the fraction of recall tests the model passes. A recall test is "did the model demonstrate it remembers this fact" — judged by a separate cheap LLM (not regex matching).

The probe reports:
- **Persistence (unweighted)** — fraction of all recall tests passed
- **Weighted persistence** — same, but each test is weighted by `sqrt(turn distance from seed)` so long-range recall dominates. This is what we actually care about; immediate recall is trivial.

## Why we replaced regex with LLM-judged recall

The original regex approach has two systematic failure modes:

| Failure | Example |
|---|---|
| **False positive** | Pattern `\btense\b` matches the room atmosphere being described as tense, not the NPC the test cares about. Probe credits the model with recall it didn't actually do. |
| **False negative** | Model says "the boy" — character-consistent voice for a young NPC named Aldric — but the regex needed `\baldric\b` literal. Probe penalizes correct paraphrase. |

Asking a small LLM "did this response demonstrate knowledge of fact X?" sidesteps both. Judge calibration cases live in `judge.py` so anyone porting can validate their judge stays honest.

## Calibration modes (the methodological backbone)

Without baselines, a "65% persistence" number floats. The probe runs each (model × bible) combination in **four modes** so every score lands in a known measurement range:

| Mode | What it tests | Use |
|---|---|---|
| **naive** | Fresh request per turn, no conversation history at all. Just `system_prompt + current_action`. | Floor. Tells you what the model can do with bible-only context. |
| **normal** | System prompt + full conversation history. Current production behavior. | The number you actually care about. |
| **scaffolded** | normal + a compact `<reminders>` block prepended to every player action. The reminders list active NPCs with their key traits, parsed from the bible. | Tests whether per-turn re-injection of canon facts closes the gap. |
| **perfect** | normal + the FULL bible re-prepended to every player action. | Ceiling. Tells you what the model can do if attention to canon is forced. |

Reading the modes together:
- If naive ≈ normal, the model isn't using conversation history (bad)
- If normal ≈ perfect, attention to canon is the bottleneck (scaffolding will help)
- If scaffolded > normal substantially, ship scaffolding for that model in production
- If scaffolded < normal, the reminders are distracting (turn scaffolding OFF for that model)

That last case is real — when this probe was first run, adding scaffolding **hurt** Sonnet's persistence by ~10pt because the explicit reminder block competed with Sonnet's already-strong native attention to the bible. The same scaffolding helped Gemini ~+11pt. Per-model decisions matter; one-size-fits-all prompt scaffolding is wrong.

## The three bibles

Bibles are sized identically (5 NPCs, 2 factions, 20 turns, 7 recall tests) so the persistence index is comparable across them. Three genres so we can detect a model whose recall is good only in its training-distribution sweet spot:

- **valdremor** — medieval fantasy (urban ruined-empire setting; rogue protagonist)
- **atrias** — sci-fi (orbiting beanstalk skyport; forensic-accountant fixer)
- **nightshift** — modern horror (Ohio rust-belt town, 2am; crime reporter)

## Running

Requires Python 3.11+ and an OpenRouter API key.

```bash
# Smoke test (1 model, 1 bible, 1 mode, 1 trial — ~3 minutes)
export OPENROUTER_API_KEY=sk-or-v1-...
python -m probe.persistence_v2 \
  --subjects anthropic/claude-sonnet-4-6 \
  --bibles valdremor \
  --modes normal \
  --trials 1 \
  --out-dir results/smoke

# Full battery (4 models × 3 bibles × 4 modes × 2 trials — ~45-60 minutes)
python -m probe.persistence_v2 \
  --subjects anthropic/claude-sonnet-4-6,anthropic/claude-haiku-4-5,openai/gpt-4o,google/gemini-2.5-pro \
  --bibles valdremor,atrias,nightshift \
  --modes naive,normal,scaffolded,perfect \
  --trials 2 \
  --out-dir results/v2_full
```

Outputs:
- `results/.../{subject}__{bible}__{mode}__t{trial}.json` — full turn-by-turn record + every judge call's reasoning
- `results/.../rollup.json` — aggregated cell + per-subject-mode tables
- `results/.../rollup.md` — human-readable summary

## Aggregation

For each (subject, bible, mode) cell, the probe reports `mean ± pstdev` across trials. If `pstdev` is high relative to the gap you care about, run more trials.

The recommended top-line for cross-model comparisons is **weighted persistence in normal mode, averaged across all three bibles**. That number is what production users actually experience.

## Adding a new bible

1. Drop a file in `bibles/` following the shape in `bibles/valdremor.py`:
   - `BIBLE` (str) — setting + recent events + factions + current scene
   - `NPCS` (str) — 5 NPCs in `### Name` markdown with at minimum `**Demeanor:**` and `**Speech quirk:**` lines (the scaffolding parser keys on these)
   - `FACTS` (tuple of `Fact`) — discrete bible-canon items the recall tests probe
   - `TURNS` (tuple of `Turn`) — 20 player actions, annotated with `seed` / `neutral` / `recall` kind + `targets` listing fact ids
2. Register it in `bibles/__init__.py::BIBLES`.

The structural shape — when facts seed, when they're recalled, how many recall tests — should match the existing bibles so the persistence index stays comparable across them.

## Adding a new judge

`judge.py::judge_recall` accepts any OpenRouter route. The default is `google/gemini-2.5-flash` (cheap, fast, semantically sharp). To swap, set `PROBE_JUDGE_MODEL`:

```bash
PROBE_JUDGE_MODEL="anthropic/claude-haiku-4-5" python -m probe.persistence_v2 ...
```

The judge's calibration cases in `judge.py::CALIBRATION_CASES` should pass against any reasonable swap. Run them first:

```bash
python -m probe.persistence_v2.calibrate
```

## Known limitations

- **Scripted player path.** Real chat-level usage is reactive; here actions are pre-written. A `v3` would make actions react to the model's prior turn, closer to actual usage. Larger structural change.
- **Single-judge bias.** One LLM judges all responses. Systematic judge bias affects all subjects equally, but it's still bias. An N-judge ensemble (3-5 models, inter-rater agreement reported) would close this.
- **Quality vs persistence.** This probe measures memory, not prose quality. A model can ace persistence while writing wooden prose, or vice versa. The original `narrative_probe.py` covers atmosphere / npc_craft / gm_craft separately; run both for a complete picture.

## Provenance

Originally built for [Neural Initiative](https://github.com/Bobby-Gray/neuralinitiative); methodology and code refined in [this analysis doc](https://github.com/Bobby-Gray/neuralinitiative/blob/main/docs/probes/sonnet_vs_gemini_2026-06-10.md). Ported here under the AGPL-3.0-or-later license that covers the rest of `open-tabletop-gm`.
