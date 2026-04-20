#!/usr/bin/env python3
"""
open-tabletop-gm narrative quality probe — v2
----------------------------------------------
Tests how well a model applies GM craft standards across 12 targeted scenarios.

Scoring is two-layer:
  1. Automated: pattern matching on measurable signals (sensory density, momentum,
     NPC voice markers, response length, structural discipline)
  2. Judge ensemble: 1–5 scores from N judge models on atmosphere, npc_craft, gm_craft.
     Inter-rater agreement (mean pairwise Pearson r) is reported as a methodological
     validity measure — directly addressing the single-judge circularity criticism.

Multi-run mode (--runs N, default 5):
  Each scenario is run N times. Auto-scores are reported as pass-rates (fraction of
  runs that passed each dimension). Judge scores are averaged across runs. Std dev of
  the overall judge score across runs is reported as a generation stability metric —
  high std dev means the model's output quality is inconsistent across draws.

Usage:
  # Single run (fast, less reliable):
  python3 probe/narrative_probe.py --model google/gemma-3-27b-it \
    --url https://openrouter.ai/api --api-key KEY --runs 1

  # 5-run average, 5-judge ensemble (recommended):
  python3 probe/narrative_probe.py --model google/gemma-3-27b-it \
    --url https://openrouter.ai/api --api-key KEY

  # Full sweep:
  bash probe/run-narrative.sh $OPENROUTER_API_KEY
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

PROBE_DIR = Path(__file__).parent

DEFAULT_JUDGES = [
    "openai/gpt-oss-120b",
    "google/gemma-3-27b-it",
    "meta-llama/llama-3.3-70b-instruct",
    "qwen/qwen3-235b-a22b",
    "nvidia/nemotron-3-super-120b-a12b",
]

# ---------------------------------------------------------------------------
# Campaign context — shared across all 12 scenarios
# ---------------------------------------------------------------------------

CAMPAIGN_CONTEXT = """
## Active Campaign Context

**Campaign:** The Ashen Crown
**System:** D&D 5e
**Setting:** Valdremor — a city built on the ruins of a destroyed empire. Ash still falls from the Cinderpeak volcano to the north. The ruling Merchant Council controls all trade; the Thornwarden thieves' guild controls everything else.

**Player character:** Sable, a half-elf rogue, former Council courier who went rogue after witnessing a Council assassination. Cautious, dry humor, loyal to very few people.

**Recent events:** Three sessions ago, Sable accepted a job from Mira (Thornwarden fixer, sharp-tongued, always smells of cloves) to steal a ledger from a Council warehouse. Sable got the ledger but also let a bound warehouse guard go free — a choice that broke the job's clean exit and left a witness.

**Active NPCs:**
- **Mira** — Thornwarden fixer. Wiry, 40s, missing the tip of her left index finger. Always negotiating. Not quite trustworthy, not quite untrustworthy. Smells of cloves.
- **Aldric** — the warehouse guard Sable freed. Young, nervous. Works for the Council but hates it. Owes Sable a life debt he doesn't know how to repay.
- **Councillor Vael** — the man who ordered the assassination Sable witnessed. Cold, meticulous, believes the city's survival requires ugly choices.

**Current scene:** Sable is moving through the Ashmarket — a covered bazaar in Valdremor's lower district, smoky and loud, vendors selling everything from spiced eel to forged travel papers.
""".strip()

SYSTEM_PROMPT = f"""You are a seasoned, atmospheric Game Master running a persistent tabletop RPG campaign. Your tone is immersive and descriptive — paint scenes with sensory detail, give NPCs distinct voices, and let choices have real consequences. You lean toward "yes, and..." rulings and fun over rigid rule enforcement, but the world is dangerous and stakes are real.

Two or three sharp sensory details beat a paragraph of exposition every time. Drop the detail, then stop — let the player's imagination fill the rest. Economy of language keeps the energy high and the pacing alive.

Even a minor character gets one or two distinct traits: a verbal tic, a visible contradiction, a motivation that makes them a person rather than a prop.

When the player goes sideways, make it work. "Yes, and..." beats "no, but..." in almost every case.

The world must visibly react to what the player does. NPCs remember past conversations. Doors that were kicked in stay broken.

{CAMPAIGN_CONTEXT}"""

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

SENSORY_WORDS = {
    "sight": ["dark", "light", "shadow", "glow", "flicker", "dim", "bright", "colour", "color",
              "grey", "gray", "red", "gold", "amber", "pale", "smoke", "ash", "gleam", "glint",
              "silhouette", "shape", "face", "eye", "eyes", "stare", "glance", "flash"],
    "sound": ["noise", "sound", "voice", "voices", "shout", "murmur", "hiss", "clatter", "creak",
              "rumble", "crack", "silence", "quiet", "loud", "echo", "ring", "scrape", "hum", "buzz"],
    "smell": ["smell", "scent", "odour", "odor", "reek", "stench", "aroma", "clove", "smoke",
              "sweat", "salt", "rot", "sweet", "sour", "acrid", "burning"],
    "touch": ["cold", "warm", "hot", "rough", "smooth", "sharp", "soft", "hard", "damp", "wet",
              "dry", "weight", "heavy", "light", "press", "grip", "sting", "ache"],
    "taste": ["taste", "bitter", "sweet", "salt", "sour", "spice", "acid", "bland"],
}
ALL_SENSORY = {w for words in SENSORY_WORDS.values() for w in words}

REFUSAL_PATTERNS = [
    r"you can't", r"you cannot", r"that's not possible", r"I'm unable", r"I cannot",
    r"that would be", r"it's not possible", r"I don't think", r"as an AI",
    r"I'm sorry", r"I apologize",
]

CLOSING_BEAT_PATTERNS = [
    r"\?$", r"\?\"$", r"\?\s*$",
    r"(what do you do|what will you do)\??",
    r"(waits?|watching|watching you|eyes? on you)",
    r"(something|someone) (catches?|snags?) your",
]

FLAT_STOP_PATTERNS = [
    r"(you arrive|you reach|you enter|you find yourself)\.",
    r"(the scene|the area|the room) (is|appears|looks) (quiet|empty|calm)\.",
]


def sensory_density(text: str) -> float:
    if not text:
        return 0.0
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in ALL_SENSORY)
    return round(hits / len(words) * 100, 1)


def length_score(tokens: int | None) -> str:
    if tokens is None:
        return "UNKNOWN"
    if tokens < 80:
        return "TERSE"
    if tokens <= 380:
        return "IDEAL"
    return "DUMP"


def has_forward_momentum(text: str) -> bool:
    last = text.strip().split("\n")[-1].strip()
    for pat in CLOSING_BEAT_PATTERNS:
        if re.search(pat, last, re.IGNORECASE):
            return True
    return False


def has_refusal(text: str) -> bool:
    for pat in REFUSAL_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def has_flat_stop(text: str) -> bool:
    last_two = " ".join(text.strip().split("\n")[-2:])
    for pat in FLAT_STOP_PATTERNS:
        if re.search(pat, last_two, re.IGNORECASE):
            return True
    return False


def npc_voice_markers(text: str) -> list[str]:
    found = []
    if re.search(r'["""].+["""]', text):
        found.append("has_dialogue")
    if re.search(r"(always|never|every time|habit|used to|still)", text, re.IGNORECASE):
        found.append("has_trait_marker")
    if re.search(r"(smells?|reeks?|stinks?|scent of)", text, re.IGNORECASE):
        found.append("sensory_npc_detail")
    if re.search(r"(laughs?|grins?|snorts?|sighs?|shrugs?|winces?|narrows?|raises?|leans?)",
                 text, re.IGNORECASE):
        found.append("physical_gesture")
    if re.search(r"(want|need|looking for|after|trying to|plan|deal)", text, re.IGNORECASE):
        found.append("visible_motivation")
    return found


def references_prior_choice(text: str) -> bool:
    markers = ["guard", "aldric", "ledger", "warehouse", "let", "freed", "witness", "loose end",
               "choice", "decision", "that night", "job", "clean exit"]
    tl = text.lower()
    return sum(1 for m in markers if m in tl) >= 2


def builds_on_action(text: str, action_keywords: list[str]) -> bool:
    tl = text.lower()
    return sum(1 for kw in action_keywords if kw in tl) >= 1


def skips_travel(text: str) -> bool:
    step_by_step = ["first you", "then you", "you walk", "you move", "you make your way",
                    "step by step", "eventually you", "after a while", "you continue"]
    skip_markers = ["some time later", "by the time", "an hour", "when you arrive", "as you reach",
                    "the journey", "cutting through", "having made", "already", "before long"]
    tl = text.lower()
    has_steps = sum(1 for p in step_by_step if p in tl)
    has_skip = sum(1 for p in skip_markers if p in tl)
    return has_skip > 0 or has_steps <= 1


# --- New helpers for v2 test cases ---

def has_mechanical_language(text: str) -> bool:
    """Raw game mechanics leak into narration — fails the immersion test."""
    patterns = [
        r"\b\d+\s*(hit points|hp)\b",
        r"\broll\b.{0,20}\b\d+\b",
        r"\bmodifier\b",
        r"\barmou?r class\b",
        r"\b(d4|d6|d8|d10|d12|d20)\b",
        r"\bsaving throw\b",
        r"\battack roll\b",
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def fail_forward(text: str) -> bool:
    """Failure moves the world — world reacts, story continues, not a dead stop."""
    dead_stops = [
        r"\byou fail\b(?! to notice| to see| forward)",
        r"\bnothing happens\b",
        r"\byou don'?t succeed\b",
        r"\bthe attempt fails\b",
        r"\byou are unable\b",
        r"\bunsuccessful\b",
    ]
    forward_markers = ["but", "however", "instead", "as you stumble", "the guard",
                       "catches", "notices", "hears you", "sees you", "turns",
                       "snaps", "commotion", "sound of", "your cover"]
    tl = text.lower()
    has_dead_stop = any(re.search(p, tl) for p in dead_stops)
    has_forward = sum(1 for m in forward_markers if m in tl) >= 1
    return has_forward and not has_dead_stop


def has_subtle_deception_tell(text: str) -> bool:
    """Behavioral tells without explicitly saying 'he's lying'."""
    subtle = ["pause", "almost", "smooth", "carefully", "precise", "exactly",
              "adjusted", "settle", "inhale", "exhale", "finger", "still",
              "composed", "measured", "deliberate", "practiced", "too"]
    explicit_tells = ["lying", "you can tell", "you sense he", "clearly false",
                      "obviously", "detect a lie", "deception check"]
    tl = text.lower()
    has_subtle = sum(1 for w in subtle if w in tl) >= 2
    has_explicit = any(w in tl for w in explicit_tells)
    return has_subtle and not has_explicit


def immediate_pivot(text: str) -> bool:
    """Tone shift lands immediately — no slow 'you notice' framing."""
    slow_framing = ["you notice", "you realize", "you become aware", "suddenly you",
                    "all of a sudden", "you hear that ", "you see that "]
    tl = text.lower()
    first_sentence = tl[:120]
    return not any(p in first_sentence for p in slow_framing)


def preserves_mystery(text: str) -> bool:
    """World reveal leaves questions open — doesn't dump all lore."""
    dump_markers = ["this means that", "you understand now", "it all makes sense",
                    "the truth is", "you realize that this is", "clearly this is",
                    "this explains everything", "now you know"]
    hook_markers = ["why", "who sealed", "when", "how long", "?", "wonder",
                    "perhaps", "might have", "could be", "suggests", "hints at"]
    tl = text.lower()
    has_dump = sum(1 for m in dump_markers if m in tl) >= 2
    has_hook = sum(1 for h in hook_markers if h in tl) >= 2
    return has_hook and not has_dump


def player_agency_preserved(text: str) -> bool:
    """Moral dilemma doesn't tell the player what to do or feel."""
    railroading = ["you must", "you have to", "you need to decide", "the only choice",
                   "you should", "you decide to", "you realize you have no choice",
                   "what do you choose", "what is your decision", "choose wisely"]
    tl = text.lower()
    return not any(r in tl for r in railroading)


def highlight_sentence(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences:
        return text[:220]
    scored = []
    for s in sentences:
        words = re.findall(r"\b\w+\b", s.lower())
        if not words:
            continue
        density = sum(1 for w in words if w in ALL_SENSORY) / len(words)
        dialogue_bonus = 0.05 if re.search(r'["""]', s) else 0
        scored.append((density + dialogue_bonus, s))
    scored.sort(reverse=True)
    best = scored[0][1] if scored else sentences[0]
    return best[:220] + ("…" if len(best) > 220 else "")


# ---------------------------------------------------------------------------
# Test cases — 12 scenarios
# ---------------------------------------------------------------------------

TEST_CASES = [
    # --- Original 6 ---
    {
        "id": "scene_entry",
        "label": "Scene entry — sensory economy",
        "standard": "S4: Describe vividly but efficiently",
        "messages": [
            {"role": "user",
             "content": "I move deeper into the Ashmarket, keeping my hood up, scanning for tails."}
        ],
        "score_fn": lambda text, tokens, _: {
            "sensory_density": sensory_density(text),
            "length": length_score(tokens),
            "forward_momentum": has_forward_momentum(text),
            "no_refusal": not has_refusal(text),
        },
        "pass_thresholds": {
            "sensory_density": lambda v: v >= 2.0,
            "length": lambda v: v == "IDEAL",
            "forward_momentum": lambda v: v,
            "no_refusal": lambda v: v,
        },
    },
    {
        "id": "npc_meeting",
        "label": "NPC encounter — memorable character",
        "standard": "S5: Make every NPC memorable",
        "messages": [
            {"role": "user", "content": "I spot Mira across the market and head her way."}
        ],
        "score_fn": lambda text, tokens, _: {
            "npc_voice_markers": npc_voice_markers(text),
            "has_dialogue": "has_dialogue" in npc_voice_markers(text),
            "visible_motivation": "visible_motivation" in npc_voice_markers(text),
            "has_physical_gesture": "physical_gesture" in npc_voice_markers(text),
            "length": length_score(tokens),
        },
        "pass_thresholds": {
            "has_dialogue": lambda v: v,
            "visible_motivation": lambda v: v,
            "has_physical_gesture": lambda v: v,
            "length": lambda v: v in ("IDEAL", "TERSE"),
        },
    },
    {
        "id": "yes_and",
        "label": "Off-rails action — yes, and...",
        "standard": "S1: Improvise, don't script",
        "messages": [
            {"role": "user",
             "content": "I grab a handful of ash from a vendor's brazier and throw it in the face of the nearest Council patrol guard, then duck into the crowd."}
        ],
        "score_fn": lambda text, tokens, _: {
            "no_refusal": not has_refusal(text),
            "builds_on_action": builds_on_action(text, ["ash", "guard", "crowd", "patrol", "dust",
                                                         "scatter", "blind", "stumble", "shout",
                                                         "commotion", "smoke"]),
            "forward_momentum": has_forward_momentum(text),
            "length": length_score(tokens),
        },
        "pass_thresholds": {
            "no_refusal": lambda v: v,
            "builds_on_action": lambda v: v,
            "forward_momentum": lambda v: v,
            "length": lambda v: v == "IDEAL",
        },
    },
    {
        "id": "consequence",
        "label": "Consequence delivery — player feels consequential",
        "standard": "S3: Make the player feel consequential",
        "messages": [
            {"role": "assistant",
             "content": "You're moving through the Ashmarket. The usual crowd — eel vendors, forgers, people who don't want to be found. Nothing out of the ordinary."},
            {"role": "user",
             "content": "I stop at a spice stall and wait. Something feels off."},
        ],
        "injected_context": "Aldric, the guard Sable freed three sessions ago, is in the Ashmarket today. He spotted Sable two minutes ago and has been following at a distance, working up the nerve to approach.",
        "score_fn": lambda text, tokens, ctx: {
            "references_prior_choice": references_prior_choice(text),
            "world_reacts": any(w in text.lower() for w in
                                ["aldric", "guard", "familiar", "recognize", "recognise",
                                 "warehouse", "before", "that night", "follow"]),
            "forward_momentum": has_forward_momentum(text),
            "no_flat_stop": not has_flat_stop(text),
        },
        "pass_thresholds": {
            "references_prior_choice": lambda v: v,
            "world_reacts": lambda v: v,
            "forward_momentum": lambda v: v,
            "no_flat_stop": lambda v: v,
        },
    },
    {
        "id": "pacing",
        "label": "Pacing — skip uneventful travel",
        "standard": "S6: Control the pace deliberately",
        "messages": [
            {"role": "user",
             "content": "I need to get from the Ashmarket to the Thornwarden safehouse in the Oldwall district. It's about a 20 minute walk through back streets."}
        ],
        "score_fn": lambda text, tokens, _: {
            "skips_travel": skips_travel(text),
            "length": length_score(tokens),
            "forward_momentum": has_forward_momentum(text),
            "no_step_by_step": not any(p in text.lower() for p in
                                        ["first you", "then you walk", "you make your way",
                                         "you continue through", "after several streets"]),
        },
        "pass_thresholds": {
            "skips_travel": lambda v: v,
            "length": lambda v: v in ("TERSE", "IDEAL"),
            "forward_momentum": lambda v: v,
            "no_step_by_step": lambda v: v,
        },
    },
    {
        "id": "closing_beat",
        "label": "Closing beat — session shape",
        "standard": "S6: Every session has a shape",
        "messages": [
            {"role": "assistant",
             "content": "Mira takes the coin, pockets it, and gives you that flat look that means she's already thinking three steps ahead. \"Job's done. You're clear.\" She starts to turn away."},
            {"role": "user", "content": "I grab her arm. \"The guard I let go. Is that going to be a problem?\""},
        ],
        "score_fn": lambda text, tokens, _: {
            "has_closing_beat": has_forward_momentum(text) or re.search(
                r"(silence|pause|beat|moment|something|question hangs|left unsaid)", text, re.IGNORECASE) is not None,
            "mira_has_reaction": any(w in text.lower() for w in
                                     ["mira", "she", "her", "pause", "stops", "turns", "looks",
                                      "says", "laughs", "sighs", "expression"]),
            "no_flat_stop": not has_flat_stop(text),
            "length": length_score(tokens),
        },
        "pass_thresholds": {
            "has_closing_beat": lambda v: v,
            "mira_has_reaction": lambda v: v,
            "no_flat_stop": lambda v: v,
            "length": lambda v: v == "IDEAL",
        },
    },

    # --- New v2 test cases ---
    {
        "id": "combat_hit",
        "label": "Combat — critical hit without mechanics leak",
        "standard": "S4: Describe vividly but efficiently",
        "messages": [
            {"role": "assistant",
             "content": "The Thornwarden enforcer steps into the alley, blocking your exit. He's big — not someone who got where he is by being slow."},
            {"role": "user", "content": "Natural 20. I drive my blade up under his guard."},
        ],
        "score_fn": lambda text, tokens, _: {
            "no_mechanics_leak": not has_mechanical_language(text),
            "sensory_density": sensory_density(text),
            "forward_momentum": has_forward_momentum(text),
            "no_refusal": not has_refusal(text),
            "length": length_score(tokens),
        },
        "pass_thresholds": {
            "no_mechanics_leak": lambda v: v,
            "sensory_density": lambda v: v >= 1.5,
            "forward_momentum": lambda v: v,
            "no_refusal": lambda v: v,
            "length": lambda v: v == "IDEAL",
        },
    },
    {
        "id": "player_failure",
        "label": "Player failure — fail forward narration",
        "standard": "S1: Improvise, don't script",
        "messages": [
            {"role": "assistant",
             "content": "A Council patrol has set up a checkpoint at the Ashmarket's north gate. Four guards, two with crossbows on the roof. You need to get through unseen."},
            {"role": "user", "content": "I try to slip through with the crowd. I rolled a 3 on stealth."},
        ],
        "score_fn": lambda text, tokens, _: {
            "fail_forward": fail_forward(text),
            "no_refusal": not has_refusal(text),
            "forward_momentum": has_forward_momentum(text),
            "no_flat_stop": not has_flat_stop(text),
            "length": length_score(tokens),
        },
        "pass_thresholds": {
            "fail_forward": lambda v: v,
            "no_refusal": lambda v: v,
            "forward_momentum": lambda v: v,
            "no_flat_stop": lambda v: v,
            "length": lambda v: v in ("TERSE", "IDEAL"),
        },
    },
    {
        "id": "npc_deception",
        "label": "NPC deception — Vael lying, subtle tells only",
        "standard": "S5: Make every NPC memorable",
        "messages": [
            {"role": "user",
             "content": "I look Councillor Vael directly in the eye. \"The merchant who died in the Ashmarket last winter — Harlen Doss. Was that your order?\""},
        ],
        "injected_context": "Vael ordered the killing. He is lying. He is very good at it — calm, plausible, a little truth mixed with the lie. He does not panic, he does not overexplain. He has done this before.",
        "score_fn": lambda text, tokens, _: {
            "vael_speaks": any(w in text.lower() for w in ["vael", "councillor", "he says", "he replies", "his voice", '"']),
            "subtle_tell": has_subtle_deception_tell(text),
            "no_refusal": not has_refusal(text),
            "length": length_score(tokens),
        },
        "pass_thresholds": {
            "vael_speaks": lambda v: v,
            "subtle_tell": lambda v: v,
            "no_refusal": lambda v: v,
            "length": lambda v: v in ("TERSE", "IDEAL"),
        },
    },
    {
        "id": "tone_shift",
        "label": "Tone shift — banter to sudden threat",
        "standard": "S6: Control the pace deliberately",
        "messages": [
            {"role": "assistant",
             "content": "Mira's laughing at something you said — genuinely, which is rare. The market is loud and warm around you."},
            {"role": "user", "content": "A crossbow bolt cracks into the stall post six inches from my head."},
        ],
        "score_fn": lambda text, tokens, _: {
            "immediate_pivot": immediate_pivot(text),
            "sensory_density": sensory_density(text),
            "mira_reacts": any(w in text.lower() for w in
                               ["mira", "she", "her", "drops", "grabs", "pulls", "moves", "low"]),
            "forward_momentum": has_forward_momentum(text),
            "length": length_score(tokens),
        },
        "pass_thresholds": {
            "immediate_pivot": lambda v: v,
            "sensory_density": lambda v: v >= 2.0,
            "mira_reacts": lambda v: v,
            "forward_momentum": lambda v: v,
            "length": lambda v: v in ("TERSE", "IDEAL"),
        },
    },
    {
        "id": "world_reveal",
        "label": "World reveal — artifact, mystery preserved",
        "standard": "S4: Describe vividly but efficiently",
        "messages": [
            {"role": "user",
             "content": "I pull the object from behind the ash-brick panel — it's been sealed in there a long time. What is it?"},
        ],
        "injected_context": "The object is a sealed brass cylinder, etched with the administrative seal of the old empire — the one destroyed a century ago when the ash first fell. Inside are census records. Someone sealed this deliberately, expecting to return. They never did.",
        "score_fn": lambda text, tokens, _: {
            "mystery_preserved": preserves_mystery(text),
            "sensory_grounding": sensory_density(text) >= 1.5,
            "hooks_curiosity": has_forward_momentum(text) or "?" in text,
            "length": length_score(tokens),
            "no_refusal": not has_refusal(text),
        },
        "pass_thresholds": {
            "mystery_preserved": lambda v: v,
            "sensory_grounding": lambda v: v,
            "hooks_curiosity": lambda v: v,
            "length": lambda v: v in ("TERSE", "IDEAL"),
            "no_refusal": lambda v: v,
        },
    },
    {
        "id": "moral_weight",
        "label": "Moral weight — genuine dilemma, agency preserved",
        "standard": "S3: Make the player feel consequential",
        "messages": [
            {"role": "assistant",
             "content": "Mira slides a piece of paper across the table. A name. An address. \"Loose end from the warehouse job. Thornwarden policy.\""},
            {"role": "user", "content": "I look at the paper. \"Is this what I think it is?\""},
        ],
        "injected_context": "The name on the paper is Aldric — the guard Sable freed. Mira is not ordering Sable to do anything directly. She's presenting it as information. But everyone in this room knows what Thornwarden policy means.",
        "score_fn": lambda text, tokens, _: {
            "aldric_named_or_implied": any(w in text.lower() for w in
                                           ["aldric", "guard", "warehouse", "name", "paper", "the man"]),
            "player_agency_preserved": player_agency_preserved(text),
            "mira_in_character": not re.search(r"(mira (says|tells|explains) (you|that) (you must|you have to|the only))", text, re.IGNORECASE),
            "forward_momentum": has_forward_momentum(text),
            "length": length_score(tokens),
        },
        "pass_thresholds": {
            "aldric_named_or_implied": lambda v: v,
            "player_agency_preserved": lambda v: v,
            "mira_in_character": lambda v: v,
            "forward_momentum": lambda v: v,
            "length": lambda v: v == "IDEAL",
        },
    },
]

# ---------------------------------------------------------------------------
# Judge rubric
# ---------------------------------------------------------------------------

JUDGE_RUBRIC = """You are evaluating a Game Master's response in a tabletop RPG session. Score it on three dimensions, each 1-5. Reply with ONLY a JSON object — no explanation.

Dimensions:
- "atmosphere": How vivid and immersive is the narration? (1=flat description, 5=rich sensory scene)
- "npc_craft": How distinct, memorable, and human does any NPC feel? (1=generic prop, 5=feels like a real person with wants)
- "gm_craft": Does this feel like a skilled GM, not a chatbot? (1=robotic/formulaic, 5=exactly what you'd want from a great GM)

If no NPC appears, score npc_craft based on how well the world itself is characterized.

Response to evaluate:
---
{response}
---

Reply with only: {{"atmosphere": N, "npc_craft": N, "gm_craft": N}}"""

# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def chat(model: str, messages: list, url: str, timeout: int, api_key: str,
         max_tokens: int = 500, temperature: float = 0.8) -> dict:
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers=headers,
    )
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 429:
                wait = 20 * (attempt + 1)
                print(f" [429 rate-limited, retrying in {wait}s]", end="", flush=True)
                time.sleep(wait)
                continue
            return {"error": body}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "rate-limited after 3 retries"}


def judge_single(response_text: str, judge_model: str, url: str, api_key: str,
                 timeout: int):
    prompt = JUDGE_RUBRIC.format(response=response_text[:1500])
    result = chat(judge_model,
                  [{"role": "user", "content": prompt}],
                  url, timeout, api_key,
                  max_tokens=300, temperature=0.0)
    if "error" in result:
        return None
    content = (result.get("choices", [{}])[0].get("message") or {}).get("content", "")
    try:
        match = re.search(r"\{[^}]+\}", content)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


def judge_ensemble(response_text: str, judge_models: list[str], url: str, api_key: str,
                   timeout: int) -> dict:
    """Run all judge models, return per-judge scores and aggregate."""
    per_judge: dict[str, dict] = {}
    for judge in judge_models:
        scores = judge_single(response_text, judge, url, api_key, timeout)
        if scores:
            per_judge[judge] = scores

    if not per_judge:
        return {"per_judge": {}, "aggregate": None}

    # Average across judges
    dims = ["atmosphere", "npc_craft", "gm_craft"]
    agg = {}
    for dim in dims:
        vals = [s[dim] for s in per_judge.values() if dim in s]
        agg[dim] = round(sum(vals) / len(vals), 2) if vals else None

    return {"per_judge": per_judge, "aggregate": agg}

# ---------------------------------------------------------------------------
# Inter-rater agreement
# ---------------------------------------------------------------------------

def std_dev(values: list) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return round((sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5, 3)


def pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 2:
        return None
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    sy = sum((yi - my) ** 2 for yi in y) ** 0.5
    if sx == 0 or sy == 0:
        return None
    return round(cov / (sx * sy), 3)


def compute_inter_rater_agreement(all_results: list) -> dict:
    """
    Compute mean pairwise Pearson r between judges across all test responses.
    High r (>0.7) across diverse model families = methodological validity.
    """
    from itertools import combinations

    # Collect scores per judge across all responses
    judge_scores: dict[str, list[dict]] = {}
    for result in all_results:
        pj = result.get("multi_judge", {}).get("per_judge", {})
        for judge, scores in pj.items():
            if judge not in judge_scores:
                judge_scores[judge] = []
            judge_scores[judge].append(scores)

    if len(judge_scores) < 2:
        return {}

    dims = ["atmosphere", "npc_craft", "gm_craft"]
    pairwise: dict[str, list] = {d: [] for d in dims}

    judges = list(judge_scores.keys())
    for j1, j2 in combinations(judges, 2):
        s1, s2 = judge_scores[j1], judge_scores[j2]
        n = min(len(s1), len(s2))
        if n < 2:
            continue
        for dim in dims:
            x = [s.get(dim, 3) for s in s1[:n]]
            y = [s.get(dim, 3) for s in s2[:n]]
            r = pearson(x, y)
            if r is not None:
                pairwise[dim].append(r)

    out = {}
    for dim in dims:
        if pairwise[dim]:
            out[dim] = round(sum(pairwise[dim]) / len(pairwise[dim]), 3)
    if out:
        out["mean"] = round(sum(out.values()) / len(out), 3)
    return out

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_narrative_probe(model: str, url: str, api_key: str, timeout: int,
                        judge_models: list[str], output_file: str = "",
                        runs: int = 5) -> list:
    print(f"\nnarrative probe v2 — {model}")
    print(f"judges ({len(judge_models)}): {', '.join(j.split('/')[-1] for j in judge_models)}")
    print(f"runs per scenario: {runs}")
    print("-" * 70)
    results = []
    dims = ["atmosphere", "npc_craft", "gm_craft"]

    for test in TEST_CASES:
        if test.get("injected_context"):
            sys_with_ctx = SYSTEM_PROMPT + f"\n\n**Scene note (GM only):** {test['injected_context']}"
            messages_base = [{"role": "system", "content": sys_with_ctx}]
        else:
            messages_base = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages_base = messages_base + test["messages"]

        print(f"  [{test['standard']}] {test['label']}")
        run_data = []

        for run_idx in range(runs):
            print(f"    run {run_idx + 1}/{runs} ...", end="", flush=True)
            t0 = time.time()
            response = chat(model, messages_base, url, timeout, api_key)
            elapsed = time.time() - t0

            if "error" in response:
                print(f" ERROR ({elapsed:.1f}s)")
                run_data.append({"error": response["error"], "elapsed_s": round(elapsed, 1)})
                continue

            content = (response.get("choices", [{}])[0].get("message") or {}).get("content") or ""
            comp_tokens = (response.get("usage") or {}).get("completion_tokens")

            if not content:
                print(f" ERROR (empty content)")
                run_data.append({"error": "empty_content", "elapsed_s": round(elapsed, 1)})
                continue

            scores = test["score_fn"](content, comp_tokens, test.get("injected_context", ""))
            thresholds = test["pass_thresholds"]
            passed = [k for k, v in scores.items() if k in thresholds and thresholds[k](v)]
            failed = [k for k, v in scores.items() if k in thresholds and not thresholds[k](v)]
            auto_status = "PASS" if not failed else ("WARN" if len(failed) <= 1 else "FAIL")
            print(f" {auto_status} ({elapsed:.1f}s)", end="")

            multi_judge = {"per_judge": {}, "aggregate": None}
            if judge_models:
                print(f"  judging...", end="", flush=True)
                multi_judge = judge_ensemble(content, judge_models, url, api_key, timeout)
                agg = multi_judge.get("aggregate") or {}
                if agg:
                    avg = round(sum(v for v in agg.values() if v is not None) / 3, 2)
                    print(f" avg={avg}")
                else:
                    print(" (judges failed)")
            else:
                print()

            run_data.append({
                "content": content,
                "auto_scores": scores,
                "auto_status": auto_status,
                "passed": passed,
                "failed": failed,
                "multi_judge": multi_judge,
                "completion_tokens": comp_tokens,
                "elapsed_s": round(elapsed, 1),
                "highlight": highlight_sentence(content),
            })

        # --- Aggregate across runs ---
        valid = [r for r in run_data if "error" not in r]
        n_errors = len(run_data) - len(valid)

        if not valid:
            results.append({
                "id": test["id"], "label": test["label"], "standard": test["standard"],
                "runs": runs, "runs_valid": 0, "runs_errors": n_errors,
                "status": "ERROR",
                "multi_judge": {"per_judge": {}, "aggregate": None},
            })
            continue

        # Auto-scores: per-dimension pass rate, threshold at majority (>= 0.5)
        all_dims = set()
        for r in valid:
            all_dims.update(r.get("passed", []) + r.get("failed", []))

        pass_rates = {
            d: round(sum(1 for r in valid if d in r.get("passed", [])) / len(valid), 3)
            for d in all_dims
        }
        passed_dims = [d for d, rate in pass_rates.items() if rate >= 0.5]
        failed_dims = [d for d, rate in pass_rates.items() if rate < 0.5]
        n_failed = len(failed_dims)
        auto_status = "PASS" if n_failed == 0 else ("WARN" if n_failed <= 1 else "FAIL")

        # Judge scores: average per-judge per-dim across runs, then aggregate across judges
        judge_run_scores: dict = {}
        for r in valid:
            for judge, scores in (r.get("multi_judge", {}).get("per_judge") or {}).items():
                if judge not in judge_run_scores:
                    judge_run_scores[judge] = []
                judge_run_scores[judge].append(scores)

        avg_per_judge: dict = {}
        for judge, score_list in judge_run_scores.items():
            avg_per_judge[judge] = {}
            for dim in dims:
                vals = [s[dim] for s in score_list if isinstance(s.get(dim), (int, float))]
                avg_per_judge[judge][dim] = round(sum(vals) / len(vals), 3) if vals else None

        agg: dict = {}
        for dim in dims:
            vals = [s[dim] for s in avg_per_judge.values() if s.get(dim) is not None]
            agg[dim] = round(sum(vals) / len(vals), 3) if vals else None

        multi_judge_agg = {
            "per_judge": avg_per_judge,
            "aggregate": agg if any(v is not None for v in agg.values()) else None,
        }

        # Std dev of overall judge score across runs (generation stability)
        per_run_overall = []
        for r in valid:
            run_agg = (r.get("multi_judge") or {}).get("aggregate") or {}
            vals = [run_agg[d] for d in dims if isinstance(run_agg.get(d), (int, float))]
            if vals:
                per_run_overall.append(sum(vals) / len(vals))
        judge_score_std = std_dev(per_run_overall) if len(per_run_overall) > 1 else None

        # Token stats
        tok_vals = [r["completion_tokens"] for r in valid if isinstance(r.get("completion_tokens"), int)]
        tokens_mean = round(sum(tok_vals) / len(tok_vals)) if tok_vals else None
        tokens_std = round(std_dev(tok_vals), 1) if len(tok_vals) > 1 else None

        # Best highlight by sensory density
        best_hl = max(
            (r["highlight"] for r in valid if r.get("highlight")),
            key=lambda h: sensory_density(h),
            default=""
        )

        overall_this = (round(sum(v for v in agg.values() if v is not None) / 3, 2)
                        if agg else None)
        print(f"    → status={auto_status}  judge_avg={overall_this}  std={judge_score_std}")
        print(f"    → pass_rates: {pass_rates}")
        if best_hl:
            print(f"    ❝ {best_hl}")

        results.append({
            "id": test["id"],
            "label": test["label"],
            "standard": test["standard"],
            "runs": runs,
            "runs_valid": len(valid),
            "runs_errors": n_errors,
            "status": auto_status,
            "pass_rates": pass_rates,
            "passed_dimensions": passed_dims,
            "failed_dimensions": failed_dims,
            "multi_judge": multi_judge_agg,
            "judge_score_std": judge_score_std,
            "completion_tokens_mean": tokens_mean,
            "completion_tokens_std": tokens_std,
            "highlight": best_hl,
            "run_highlights": [r["highlight"] for r in valid if r.get("highlight")],
        })

    # --- Final summary ---
    auto_counts = {s: sum(1 for r in results if r.get("status") == s)
                   for s in ["PASS", "WARN", "FAIL", "ERROR"]}

    all_agg = [r["multi_judge"].get("aggregate") or {} for r in results
               if (r.get("multi_judge") or {}).get("aggregate")]
    judge_avgs: dict = {}
    if all_agg:
        for dim in dims:
            vals = [j[dim] for j in all_agg if j.get(dim) is not None]
            judge_avgs[dim] = round(sum(vals) / len(vals), 2) if vals else None

    ira = compute_inter_rater_agreement(results)
    overall_judge = (round(sum(v for v in judge_avgs.values() if v is not None) / 3, 2)
                     if judge_avgs else None)

    all_stds = [r["judge_score_std"] for r in results if r.get("judge_score_std") is not None]
    mean_judge_std = round(sum(all_stds) / len(all_stds), 3) if all_stds else None

    print(f"\n{'=' * 70}")
    print(f"Model: {model}  (runs/scenario: {runs})")
    print(f"Auto: {auto_counts}")
    if judge_avgs:
        print(f"Judge avg: atm={judge_avgs.get('atmosphere')}  "
              f"npc={judge_avgs.get('npc_craft')}  "
              f"gm={judge_avgs.get('gm_craft')}  "
              f"overall={overall_judge}")
    if mean_judge_std is not None:
        print(f"Mean judge score std: {mean_judge_std}  (lower = more stable outputs)")
    if ira:
        print(f"IRA (mean Pearson r): {ira.get('mean')}  "
              f"[atm={ira.get('atmosphere')} npc={ira.get('npc_craft')} gm={ira.get('gm_craft')}]")
    print(f"{'=' * 70}\n")

    if output_file:
        out = {
            "model": model,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "runs_per_scenario": runs,
            "judge_models": judge_models,
            "auto_summary": auto_counts,
            "judge_averages": judge_avgs,
            "overall_judge_score": overall_judge,
            "mean_judge_score_std": mean_judge_std,
            "inter_rater_agreement": ira,
            "cases": results,
        }
        Path(output_file).write_text(json.dumps(out, indent=2))
        print(f"Results written to {output_file}")

    return results

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="open-tabletop-gm narrative quality probe v2")
    parser.add_argument("--model", required=True)
    parser.add_argument("--url", default="http://localhost:1234")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--judge-models", default=",".join(DEFAULT_JUDGES),
                        help="Comma-separated judge model IDs (default: 5-model ensemble)")
    parser.add_argument("--no-judge", action="store_true", help="Skip judge scoring entirely")
    parser.add_argument("--runs", type=int, default=5,
                        help="Number of times to run each scenario (default: 5)")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output-file", default="")
    args = parser.parse_args()

    judges = [] if args.no_judge else [j.strip() for j in args.judge_models.split(",") if j.strip()]

    run_narrative_probe(
        args.model, args.url, args.api_key, args.timeout,
        judges, args.output_file, runs=args.runs,
    )
