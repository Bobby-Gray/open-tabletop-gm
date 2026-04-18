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

### Mistral Small 3.1 24B (via LM Studio / OpenCode)

**Tool-call depth limit:** Mistral Small 3.1 24B reliably loses its instruction anchor after approximately 4–5 sequential tool calls. The `/gm load` procedure requires a pid check + 3 file reads before it can deliver the opening narration — 4 tool calls minimum, more with characters and system files. After the last read, the model resets its attention to the top of the instruction set and re-triggers Step 1, loops, or confuses content from the files it just read with new commands (e.g., treating an NPC name as a campaign name to load).

This is an architectural limit of the 24B parameter count under multi-step agentic workloads, not a system prompt wording problem. Extensive instruction iteration did not resolve it. The routing architecture in SKILL-branches.md reduced the failure surface significantly but could not eliminate it.

**RLHF refusal on non-standard signatures:** Passing extra positional args (e.g., `/gm load test-campaign dnd5e`) causes Mistral to refuse with "I don't have the tools needed." Always use exact command signatures.

**System prompt size:** Load with at least 24,576 context. The SKILL-branches.md architecture brings the system prompt to ~2,300 tokens (down from ~18,000), which comfortably fits.

**LM Studio settings:**
```json
{
  "context_length": 24576,
  "eval_batch_size": 4096,
  "flash_attention": true,
  "temperature": 0.75,
  "top_p": 0.9,
  "repeat_penalty": 1.1
}
```

**Hardware verdict:** On a MacBook Air (24GB unified memory), Mistral Small 3.1 24B is at the practical ceiling for local inference, and the tool-call depth limit makes it unreliable for session load. **OpenRouter is the recommended path for 24GB machines** — it delivers better instruction following at no hardware cost (see OpenRouter section below).

On a 64GB+ machine (M3 Max, M4 Max, or equivalent) running a 70B model, the tool-call depth issue does not appear at the same thresholds. If local inference matters to you, the minimum recommended configuration is 64GB RAM with a Qwen3-70B or equivalent.

---

### MiniMax M2.5 (via OpenCode)

Initial test via the `claude-dnd-skill` version (the Claude Code-specific predecessor to this repo). OpenCode picked up the skill file without additional configuration. The model produced creative NPC responses and recognized deceptive intent layered into a player message -- more than expected for a first pass. Not deeply tested yet; results from longer sessions pending.

**Verdict:** Promising. Worth testing further, especially for players who want a free-tier option without local hardware.

### Qwen3-32B (via LM Studio)

Not directly tested. The original entry here was speculative and has been removed.

At 32B parameters, Qwen3-32B sits below the ~70B threshold where local agentic tool-call depth becomes reliable — the same class of issue documented in the Mistral Small 3.1 24B section. On 24GB hardware it would face the same session-load reliability problems. On 64GB+ hardware (M3 Max, M4 Max, or equivalent) it should perform well given Qwen3's generally strong instruction-following.

If you test it and want to share results, open a GitHub Discussion with your hardware, LM Studio settings, and whether `/gm load` completes reliably.

**Verdict:** Untested. Likely viable on 64GB+ hardware; not recommended for 24GB machines.

### Qwen3-14B — gguf (via LM Studio)

Two critical issues found during testing that affect all gguf Qwen3 variants with this skill.

**Issue 1 — System prompt too large for default context:** The full instruction set is approximately 18,000 tokens. Loading the model at the default or recommended 16,384 context window will produce an immediate error: `n_keep >= n_ctx`. Load at 24,576 minimum, or remove `SKILL.md` from your OpenCode instructions file to bring the prompt under 14,000 tokens.

**Issue 2 — Silent loop caused by default eval_batch_size:** This is the primary failure mode that makes Qwen3 gguf appear broken with this skill. LM Studio's default `eval_batch_size` of 512 causes the model to process the 18,000-token system prompt in approximately 35 batches at ~20-30 seconds each — totalling 10-16 minutes of silence before generating a single output token. This is indistinguishable from a hang or infinite loop.

**Fix:** Always load with `eval_batch_size: 4096`. This reduces prefill to ~5 batches and 2-3 minutes. The setting is llama.cpp-specific and has no effect on MLX builds.

**LM Studio settings (gguf):**
```json
{
  "context_length": 24576,
  "eval_batch_size": 4096,
  "flash_attention": true,
  "temperature": 0.8,
  "top_p": 0.9,
  "repeat_penalty": 1.1
}
```

**Thinking mode:** Qwen3 enables chain-of-thought reasoning by default. The `/no_think` token in `no_think.md` suppresses this when injected via the OpenCode instructions array. Confirmed working — `reasoning_tokens` drops to effectively zero in non-streaming inference. Streaming behavior should be verified via LM Studio debug logs on first use.

**Verdict:** Functional once both issues above are addressed, but the 2-3 minute prefill on every new session is a real usability cost. Worth testing if you have the patience; otherwise Mistral Small 24B is a more comfortable default for gguf local inference with this skill.

---

### Qwen3-14B — MLX (via LM Studio)

**MLX backend failure — libpython3.11.dylib not found:** On some LM Studio installations, the MLX engine fails to load with a `dlopen` error citing a missing Python 3.11 shared library. The MLX backend ships with a vendored Python runtime that can fail to install correctly. If you see this error, check for a LM Studio update or reinstall the MLX backend extension from the LM Studio settings. There is no workaround short of a clean reinstall.

**If MLX loads successfully:** Expect significantly faster prefill than gguf on Apple Silicon hardware — typically 3-5x — due to hardware-optimised execution via the Neural Engine and GPU cores. The `eval_batch_size` parameter does not apply to MLX; batch handling is managed by the engine internally. Load with `context_length: 24576` only.

**Verdict:** Untested end-to-end due to backend installation failure. Theoretically the best Qwen3-14B option on Apple Silicon if MLX is working correctly on your system.

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

## OpenRouter

OpenRouter exposes models via an OpenAI-compatible `/v1/chat/completions` endpoint. Add your API key as a bearer token. Free-tier models use a `:free` suffix; paid endpoints drop the suffix and have no meaningful rate limits.

### Probe results (April 2026, SKILL-branches.md architecture)

All models tested with `--skip-skill-md` (SKILL.md not in system prompt) and no tool injection. The two consistent WARNs across every model are structural, not model-specific: `/gm list` falls back to described behavior without a Glob tool call, and `/gm roll d20` returns a plausible number rather than invoking `dice.py`. Both are expected without tools.json populated.

| Model | P/W/F | Avg output | ~20-turn session | Notes |
|-------|-------|-----------|-----------------|-------|
| openai/gpt-oss-120b | 3/2/0 | 369 tok | ~16,000 tok | Most verbose; rich narration |
| openai/gpt-oss-20b | 3/2/0 | 370 tok | ~16,000 tok | Same quality profile as 120B at probe scale |
| nousresearch/hermes-3-llama-3.1-405b | 3/2/0 | 141 tok | ~7,000 tok | Best balance; hallucinated on `/gm list` |
| google/gemma-3-27b-it | 3/2/0 | 279 tok | ~12,600 tok | Clean list handling; no hallucination |
| google/gemma-4-31b-it | 3/2/0 | 79 tok | ~4,700 tok | Very terse; fast and cheap |
| meta-llama/llama-3.3-70b-instruct | 3/2/0 | 166 tok | ~8,400 tok | Hallucinated on `/gm list` |
| nvidia/nemotron-3-super-120b-a12b | 3/2/0 | — | — | Free tier only; tested separately |
| nvidia/nemotron-3-nano-30b-a3b | 3/2/0 | 333 tok | ~14,800 tok | Verbose for its size |
| qwen/qwen3-next-80b-a3b-instruct | 3/2/0 | 127 tok | ~6,500 tok | Efficient; good instruction following |
| qwen/qwen3-coder | 3/2/0 | 90 tok | ~5,000 tok | Terse but precise; strong on routing |
| minimax/minimax-m2.5 | 3/2/0 | 154 tok | ~7,500 tok | 196k context; good for long sessions |

**`/gm list` hallucination note:** Hermes-405B and Llama-3.3-70B invented campaign names when asked to list campaigns. GPT-OSS, Gemma, Qwen, and MiniMax responded cleanly with "no campaigns found." For `/gm list` correctness, prefer models from the second group or populate `tools.json` so the model uses Glob instead.

### Free tier vs paid

| | Free (`:free`) | Paid |
|--|----------------|------|
| Rate limit | ~200 req/day, 20 req/min | Effectively unlimited |
| Cost | $0 | ~$0.01–0.12 per full probe run |
| Daily sessions (20 turns) | ~10 sessions | Unlimited |
| Model availability | Subset of paid models | All models |

The free tier is viable for casual play — 10 sessions/day covers most use. For extended campaigns or group play where multiple people are making requests, load a small credit balance (~$5–10) and use paid endpoints.

**Rate limit note:** Free-tier daily caps are account-wide. Running `probe/run-openrouter.sh` against multiple models in one day will exhaust the cap. Use 90s gaps between models, or use `--paid` mode.

### Recommended model IDs

**Best overall (paid):**
```
nousresearch/hermes-3-llama-3.1-405b    # richest narration, 405B
openai/gpt-oss-120b                     # verbose, atmospheric
qwen/qwen3-next-80b-a3b-instruct        # efficient, reliable routing
```

**Best free tier:**
```
nvidia/nemotron-3-super-120b-a12b:free  # only tested free model; PASS:3
meta-llama/llama-3.3-70b-instruct:free # expect rate limits
google/gemma-3-27b-it:free             # expect rate limits
```

**Best for long sessions (196k+ context):**
```
minimax/minimax-m2.5                    # 196k context window
```

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
