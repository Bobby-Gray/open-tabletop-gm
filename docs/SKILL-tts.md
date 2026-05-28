# Narrator TTS setup (optional)

The display companion can read narrator and NPC blocks aloud via Google's Gemini Flash TTS. Off by default. The rest of open-tabletop-gm works fine without it.

## What you get

- A speaker button at the bottom of every narrator and NPC block. Click to hear that block read aloud.
- A 9-voice dropdown (4 male, 5 female) sitting next to the speaker button. Change voice mid-session.
- An optional **Auto Narrate** toggle in the top-right audio controls. When on, every new narrator/NPC block auto-plays in **your browser only** — perfect for a TV or main-display cast device while player phones stay quiet.
- Multi-language support — Gemini auto-detects the language from the text, so a campaign played in any of the [24 supported locales](https://ai.google.dev/gemini-api/docs/speech-generation) just works.

## What it costs

Gemini Flash TTS bills per character. Typical narration block is ~600 characters; current pricing is ~$0.001 per block. A 3-hour session with ~30 narration blocks costs roughly 3¢. The free tier handles casual use — billing only matters if you hit rate-limit errors or if you're a new AI Studio account (Google requires prepaid billing for new accounts as of 2026).

## Setup — three steps, ~5 minutes

### 1. Get a Gemini API key from Google AI Studio

1. Visit **https://aistudio.google.com/apikey** and sign in with your Google / Gmail account. Accept the terms on first visit.
2. Click **Create API key**. If it asks which project to use, accept the default.
3. Copy the key. It looks like `AIza...` and is roughly 39 characters.

### 2. Save the key locally

```bash
mkdir -p ~/.config/open-tabletop-gm && chmod 700 ~/.config/open-tabletop-gm

cat > ~/.config/open-tabletop-gm/tts.key
# Paste your key, press Return, then Ctrl-D.

chmod 600 ~/.config/open-tabletop-gm/tts.key
```

If you'd rather use an environment variable, export `GM_TTS_KEY` (or `GEMINI_API_KEY`) instead — env vars take precedence over the key file.

### 3. Verify

```bash
python3 display/tts.py --test
```

Expected output:

```
API key source: file:/Users/you/.config/open-tabletop-gm/tts.key
Model: gemini-2.5-flash-preview-tts
Voice: Enceladus
Text:  'Hello, narrator voice test. The torchlit hall awaits.'
Calling Gemini Flash TTS…
  OK — received 76800 bytes of L16 PCM (24 kHz mono).
```

Also hear it (macOS only):

```bash
python3 display/tts.py --test --speak
```

## Using it during a session

- A small speaker icon appears at the bottom-right of every narrator (`.dm-block`) and NPC (`.npc-block`) block. Click to play; click again to stop.
- A **Voices** dropdown next to it switches the narrator voice. Selection persists per-campaign in `state.md → ## Session Flags → tts_voice: <name>`.
- The **Auto Narrate** row in the top-right audio controls is per-browser (saved in `localStorage`). Toggle on for the casting TV, off on player phones.

Player input blocks, dice-roll blocks, and tutor blocks intentionally **don't** get a speaker button — they're metadata, not narrative voice. The 2000-character cap on the synthesis endpoint matches Gemini Flash TTS's effective limit; longer blocks are truncated server-side.

## Voice catalog

| Group | Voice | Notes |
|---|---|---|
| Male | Charon | Low, gravelly — heavies, villains |
| Male | **Enceladus** *(default)* | Deep, measured — classic narrator |
| Male | Fenrir | Rough, growling — feral characters |
| Male | Umbriel | Soft, reflective — sages and elders |
| Female | Aoede | Clear, bright — heroic / informative |
| Female | Gacrux | Mature, warm — innkeepers, mentors |
| Female | Kore | Youthful, energetic |
| Female | Vindemiatrix | Crisp, formal — nobles, scholars |
| Female | Zephyr | Light, airy — fey, sprites |

To expand to Gemini's full 30 voices, edit `_TTS_VOICES_MALE` / `_TTS_VOICES_FEMALE` in `display/templates/index.html` and add the new names to `VALID_VOICES` in `display/tts.py`. The full catalog is at the [Google speech-generation guide](https://ai.google.dev/gemini-api/docs/speech-generation).

## Per-browser cost note

Each player clicking the speaker button on the same narration block produces a separate Gemini call — no server-side caching by content hash. A 4-player table where everyone clicks every block is roughly 4× the per-block cost. Mitigations:

1. **Auto Narrate on the casting TV only** — players hear the audio from the TV speaker and don't click their own phones.
2. Set a daily spend cap on your Google billing project at [console.cloud.google.com/billing](https://console.cloud.google.com/billing).

## Multi-language sessions

Gemini Flash TTS auto-detects the input language from text content. To play a Spanish-language session, just narrate in Spanish — the `/tts` endpoint comes back synthesized correctly. The voice catalog is identical across languages.

To wire up SFX trigger packs for non-English narration, set the active SFX languages either via environment:

```bash
export GM_SFX_LANGUAGES=en,es     # English first, then Spanish
```

…or per-campaign via `state.md → ## Session Flags`:

```
sfx_languages: en,zh
```

Ships with SFX packs for all 24 Gemini-supported languages: `ar`, `bn`, `de`, `en`, `es`, `fr`, `hi`, `id`, `it`, `ja`, `ko`, `mr`, `nl`, `pl`, `pt`, `ro`, `ru`, `ta`, `te`, `th`, `tr`, `uk`, `vi`, `zh`. Community PRs to refine any pack are welcome.

## Path B — `gcloud` restricted key (advanced, optional)

If you already use the `gcloud` CLI and want a key scoped to *only* the TTS API:

```bash
PROJ=my-gm-tts                  # any globally-unique project id
BILLING=YOUR-BILLING-ID         # gcloud billing accounts list

gcloud projects create "$PROJ"
gcloud billing projects link "$PROJ" --billing-account="$BILLING"
gcloud services enable generativelanguage.googleapis.com --project="$PROJ"

mkdir -p ~/.config/open-tabletop-gm && chmod 700 ~/.config/open-tabletop-gm
gcloud alpha services api-keys create \
  --project="$PROJ" \
  --display-name="open-tabletop-gm-tts" \
  --api-target=service=generativelanguage.googleapis.com \
  --format='value(response.keyString)' \
  > ~/.config/open-tabletop-gm/tts.key
chmod 600 ~/.config/open-tabletop-gm/tts.key
```

The `--api-target` restriction means a leaked key can only call `generativelanguage.googleapis.com` on this specific project.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `python3 display/tts.py --test` says "API key: unset" | No env var **and** no key file — save your key to `~/.config/open-tabletop-gm/tts.key`. |
| Speaker button shows "TTS 401" | API key invalid or disabled — re-mint at https://aistudio.google.com/apikey. |
| Speaker button shows "TTS 403" | Key not authorized for `generativelanguage.googleapis.com` (Path B keys), or billing not configured. |
| Speaker button shows "TTS 429" | Free-tier rate limit, or new AI Studio account without billing. |
| Speaker button shows "TTS 503" | Server reports TTS not configured — re-verify the key file and restart the display. |
| Audio doesn't play but no error label | Check device volume; on iOS Safari, click the speaker once to grant the AudioContext gesture. |
| 1-3 second delay before audio | Normal — Gemini Flash TTS synthesis latency. |

## How to disable

```bash
rm ~/.config/open-tabletop-gm/tts.key
```

Speaker buttons disappear on next page load. Nothing else changes.
