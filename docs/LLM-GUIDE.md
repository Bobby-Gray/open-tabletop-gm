# LLM Model Guide for open-tabletop-gm

> **Work in Progress.** This guide will expand as community members report results across different models and hardware. If you have tested open-tabletop-gm with a model not listed here, please share your findings in the GitHub Discussions tab.

---

## Why model choice matters less than you might expect

open-tabletop-gm offloads every mechanical operation to Python:

- Dice rolls (exact, seeded random)
- HP math and damage tracking
- Initiative and turn order
- Timed effects and condition tracking
- Calendar and time advancement
- SRD data lookups

The LLM's job is **narration and judgment**. It decides what the story means, what NPCs say, how a skill check lands narratively. It does not do arithmetic, does not track numbers across turns, and does not need to remember whether a spell slot was used -- the scripts handle all of that.

This means a model that would struggle with a raw "run D&D 5e in your head" prompt can still run a solid session through this framework, because the parts that break smaller models have been moved out of the model entirely.

---

## Minimum viable model floor

The practical floor is roughly **7B parameters** for a playable session. Below that, instruction-following degrades enough that the model may ignore the system prompt structure or fail to call scripts correctly. At 7B you will get short narration, simple NPC voices, and occasional rule misapplication -- but the mechanical layer will still work correctly.

At **14B** the experience becomes genuinely good. Narration has texture, NPCs have distinct voices, and the model follows the system prompt structure reliably.

---

## Tested models

### MiniMax M2.5 (via OpenCode)

Initial test via the `claude-dnd-skill` version (the Claude Code-specific predecessor to this repo). OpenCode picked up the skill file without additional configuration. The model produced creative NPC responses and recognized deceptive intent layered into a player message -- more than expected for a first pass. Not deeply tested yet; results from longer sessions pending.

**Verdict:** Promising. Worth testing further, especially for players who want a free-tier option without local hardware.

### Qwen3-32B (via LM Studio)

Early testing on open-tabletop-gm is going well -- script calls reliable, narration solid, campaign state persisting correctly across sessions. Still being evaluated; full results pending.

**Verdict:** Looking good so far. More results to come.

### Qwen3-14B (via LM Studio)

Testing in progress on open-tabletop-gm. The Claude-specific version of the skill ran into friction at this parameter count -- the portable build is designed to address that. Results pending.

**Verdict:** To be confirmed.

---

## Recommended local models (LM Studio)

These recommendations are based on the Qwen3 family, which currently offers the best balance of instruction-following, creative output, and local inference speed for tabletop use.

| Model | Best for | Notes |
|-------|----------|-------|
| Qwen3-14B | Laptops, daily use | Best performance-per-watt; solid narration; reliable script calls |
| Qwen3-30B-A3B | Balanced desktop | MoE architecture means lower VRAM for its parameter count; good quality jump from 14B |
| Qwen3-32B | High-end desktop | Best single-GPU storytelling; noticeably richer NPC depth |
| Qwen3-80B | Multi-GPU / server | Near-Claude quality on narration; overkill for most sessions |
| DeepSeek-R1/V3 | Logic-heavy campaigns | Strong on rules adjudication and complex scenario reasoning; weaker on atmospheric prose |

---

## Hardware tiers

### Laptop (Apple M3 Air, 24GB unified memory)

- **Qwen3-14B** -- excellent; 15-25 tok/s; recommended default
- **Qwen3-30B-A3B** -- moderate; 8-15 tok/s; usable for slower-paced sessions
- **Qwen3-80B** -- slow; 2-5 tok/s; impractical for real-time play

### Desktop (RTX 4080 / RTX 4090)

- **Qwen3-30B-A3B** -- excellent; 40-70 tok/s
- **Qwen3-32B** -- excellent; 30-50 tok/s; recommended for single-GPU best quality
- **Qwen3-80B** -- usable; 15-30 tok/s; noticeable pauses between turns

### High-memory workstation (M3 Max 64GB or equivalent)

- **Qwen3-30B-A3B** -- 20-35 tok/s
- **Qwen3-32B** -- 15-25 tok/s
- **Qwen3-80B** -- 8-15 tok/s; viable for non-realtime sessions

### Multi-GPU server

All models run at full speed. The 80B becomes practical here.

*Token speed estimates are approximate and vary with context length and batch size.*

---

## LM Studio configuration

The presets below are tuned for tabletop narrative use. Key reasoning:

- **temperature** is kept moderate (0.7-0.8) rather than high. Very high temperature produces vivid but inconsistent narration -- NPCs start contradicting themselves within a scene. The scripts handle determinism; you want the model slightly creative, not chaotic.
- **repeat_penalty** at 1.1 prevents the model from looping on phrases, which is a common failure mode for local models during long combat turns.
- **context_length** is set conservatively. A longer context means slower inference and higher VRAM pressure. The campaign file structure is designed to keep active context lean (state.md is a summary, not a full log), so you rarely need the maximum.
- **batch_size** scales down with model size to stay within VRAM limits. Reducing it on larger models trades throughput for stability.

### Qwen3-14B

```json
{
  "context_length": 16384,
  "temperature": 0.8,
  "top_p": 0.9,
  "repeat_penalty": 1.1,
  "batch_size": 32
}
```

### Qwen3-30B-A3B

```json
{
  "context_length": 24576,
  "temperature": 0.75,
  "top_p": 0.9,
  "repeat_penalty": 1.1,
  "batch_size": 24
}
```

### Qwen3-32B

```json
{
  "context_length": 32768,
  "temperature": 0.75,
  "top_p": 0.9,
  "repeat_penalty": 1.1,
  "batch_size": 16
}
```

### Qwen3-80B

```json
{
  "context_length": 16384,
  "temperature": 0.7,
  "top_p": 0.9,
  "repeat_penalty": 1.05,
  "batch_size": 8
}
```

---

## Qwen3 thinking mode

Qwen3 models support an explicit thinking mode (extended chain-of-thought before responding). For tabletop use, **thinking mode is generally not recommended** during active play. It adds latency before every response -- acceptable for a one-off rules adjudication, but disruptive when narrating a combat turn or NPC dialogue.

Consider enabling it for:
- One-shot rulings on unusual interactions
- World-building questions at session start
- Any situation where you want the model to reason through a complex scenario before committing

Disable it for:
- Narration turns
- NPC dialogue
- Any real-time play context

In LM Studio this is toggled via the `thinking` parameter in the chat request, or through the UI inference settings.

---

## What degrades at smaller model sizes

These are the specific failure modes observed at 7B-14B range:

**Narration:** Shorter, less atmospheric. The model describes what happens rather than painting the scene. Sensory detail drops first.

**NPC distinctiveness:** Voices blur together. Minor NPCs sound like the DM rather than themselves. Major NPCs with strong system.md descriptions hold up better.

**Long-term consistency:** The model may drift on established world facts across a long session. The campaign files (state.md, world.md, npcs.md) compensate for this -- the model re-reads facts from files rather than remembering them. Keep state.md lean and accurate.

**Script call reliability:** At 7B, the model occasionally omits a script call or formats one incorrectly. At 14B this is rare. The scripts fail silently rather than crashing, so a missed call shows up as a missing stat update rather than an error.

**What does not degrade:** Dice math (Python handles it). HP tracking (Python handles it). Turn order (Python handles it). Condition tracking (Python handles it). The mechanical layer is model-independent.

---

## Gameplay tuning by scene type

| Scene type | Recommended temperature | Notes |
|------------|------------------------|-------|
| Exploration / narration | 0.8 | Higher creativity, richer description |
| NPC dialogue | 0.75-0.8 | Distinct voices without incoherence |
| Combat resolution | 0.5-0.7 | Lower temp for consistent tactical narration |
| Rules adjudication | 0.4-0.6 | Precise, less creative |

---

## Context window management in long sessions

The session-log.md file grows unboundedly. The display companion and campaign files keep active context lean, but during a long campaign the accumulated log can push context limits on smaller models.

Strategies:
- Use `/gm save` regularly -- this writes a session summary rather than the full log to the active context
- The archive file (session-log-archive.md) keeps history outside the active window
- For 14B models, keep context_length at 16384 or below and rely on the summary system rather than full-log injection
- For 32B+ models, you can increase context_length if VRAM allows; the quality of long-range consistency improves noticeably above 32k tokens

---

## Cloud API models (non-local)

open-tabletop-gm works with any OpenAI-compatible API endpoint through OpenCode. This includes:

- OpenAI GPT-4o / GPT-4.1
- Google Gemini (via OpenAI-compatible endpoint)
- Mistral API
- DeepSeek API
- Any provider OpenCode supports

For cloud API use, the LM Studio presets do not apply. Use your provider's default settings and adjust temperature if narration quality is off. The system prompt structure and script calls work identically regardless of provider.

---

## Contributing results

This guide will expand with community testing data. If you run a session and want to share what you found, open a GitHub Discussion with:

- Model name and parameter count
- Hardware / API provider
- Token speed if local
- What worked well
- What broke or degraded
- Any LM Studio settings that improved things

The more data points the guide has, the more useful it becomes for everyone choosing a model.
