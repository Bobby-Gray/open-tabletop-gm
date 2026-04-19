#!/usr/bin/env python3
"""
open-tabletop-gm narrative quality probe
-----------------------------------------
Tests how well a model applies the GM applied standards from SKILL.md across
6 targeted scenarios. Each scenario maps to specific, measurable dimensions:

  scene_entry      → sensory detail density, response length, forward momentum
  npc_meeting      → NPC voice distinctiveness, visible motivation, voice vs. narrator
  yes_and          → honors unexpected action, builds on it rather than redirecting
  consequence      → references prior player choice, world visibly changed
  pacing           → skips routine travel, cuts to the interesting moment
  closing_beat     → ends on revelation/question/open thread, not a flat stop

Scoring is two-layer:
  1. Automated: pattern matching for measurable signals (word lists, length, sentence endings)
  2. Judge: optional LLM judge pass (--judge-model) scoring 1-5 on atmospheric quality,
     NPC distinctiveness, and overall GM craft

Usage:
  python3 probe/narrative_probe.py --model openai/gpt-oss-120b --url https://openrouter.ai/api --api-key KEY
  python3 probe/narrative_probe.py --model openai/gpt-oss-120b --url https://openrouter.ai/api --api-key KEY --judge-model openai/gpt-oss-20b
  bash probe/run-narrative.sh $OPENROUTER_API_KEY          # run all models, judge with gpt-oss-20b
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

# ---------------------------------------------------------------------------
# Mini campaign context — injected into every system prompt
# Gives models something real to narrate against without loading files.
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
    r"\?$", r"\?\"$", r"\?\s*$",                    # ends with question
    r"(what do you do|what will you do)\??",         # explicit action prompt
    r"(waits?|watching|watching you|eyes? on you)",  # NPC hanging, waiting
    r"(something|someone) (catches?|snags?) your",  # world pulls attention
]

FLAT_STOP_PATTERNS = [
    r"(you arrive|you reach|you enter|you find yourself)\.",
    r"(the scene|the area|the room) (is|appears|looks) (quiet|empty|calm)\.",
]


def sensory_density(text: str) -> float:
    """Unique sensory words per 100 words."""
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in ALL_SENSORY)
    return round(hits / len(words) * 100, 1)


def length_score(tokens: int) -> str:
    """IDEAL / TERSE / DUMP based on token count."""
    if tokens is None:
        return "UNKNOWN"
    if tokens < 80:
        return "TERSE"
    if tokens <= 380:
        return "IDEAL"
    return "DUMP"


def has_forward_momentum(text: str) -> bool:
    """Ends with a question, open beat, or invitation to act."""
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
    """Check for NPC distinctiveness signals."""
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
    """Check if consequence scenario references the ledger/guard prior choice."""
    markers = ["guard", "aldric", "ledger", "warehouse", "let", "freed", "witness", "loose end",
               "choice", "decision", "that night", "job", "clean exit"]
    tl = text.lower()
    return sum(1 for m in markers if m in tl) >= 2


def builds_on_action(text: str, action_keywords: list[str]) -> bool:
    """Check if yes-and scenario actually incorporates the player's action."""
    tl = text.lower()
    return sum(1 for kw in action_keywords if kw in tl) >= 1


def highlight_sentence(text: str) -> str:
    """Return the single most sensory-rich sentence — best illustrates the model's voice."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences:
        return text[:200]
    scored = []
    for s in sentences:
        words = re.findall(r"\b\w+\b", s.lower())
        if not words:
            continue
        density = sum(1 for w in words if w in ALL_SENSORY) / len(words)
        # Slight bonus for dialogue lines — they often show NPC voice best
        dialogue_bonus = 0.05 if re.search(r'["""]', s) else 0
        scored.append((density + dialogue_bonus, s))
    scored.sort(reverse=True)
    best = scored[0][1] if scored else sentences[0]
    # Cap at 220 chars so it stays readable in reports
    return best[:220] + ("…" if len(best) > 220 else "")


def skips_travel(text: str) -> bool:
    """Check if pacing scenario skips to the interesting moment rather than narrating every step."""
    step_by_step = ["first you", "then you", "you walk", "you move", "you make your way",
                    "step by step", "eventually you", "after a while", "you continue"]
    skip_markers = ["some time later", "by the time", "an hour", "when you arrive", "as you reach",
                    "the journey", "cutting through", "having made", "already", "before long"]
    tl = text.lower()
    has_steps = sum(1 for p in step_by_step if p in tl)
    has_skip = sum(1 for p in skip_markers if p in tl)
    # skip_markers present and few step-by-step = good pacing
    return has_skip > 0 or has_steps <= 1


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

TEST_CASES = [
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


def judge_response(response_text: str, judge_model: str, url: str, api_key: str,
                   timeout: int) -> dict | None:
    """Ask the judge model to score the response. Returns dict or None on failure."""
    prompt = JUDGE_RUBRIC.format(response=response_text[:1500])
    result = chat(
        judge_model,
        [{"role": "user", "content": prompt}],
        url, timeout, api_key,
        max_tokens=300,
        temperature=0.0,
    )
    if "error" in result:
        return None
    content = (result.get("choices", [{}])[0].get("message") or {}).get("content", "")
    try:
        # Extract JSON even if there's surrounding text
        match = re.search(r"\{[^}]+\}", content)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_narrative_probe(model: str, url: str, api_key: str, timeout: int,
                        judge_model: str = "", output_file: str = "") -> list:
    print(f"\nnarrative probe — {model}\n{'-'*60}")
    results = []

    for test in TEST_CASES:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Inject additional context if present
        if test.get("injected_context"):
            sys_with_ctx = SYSTEM_PROMPT + f"\n\n**Scene note (GM only):** {test['injected_context']}"
            messages = [{"role": "system", "content": sys_with_ctx}]

        messages += test["messages"]

        print(f"  [{test['standard']}] {test['label']} ...", end="", flush=True)
        t0 = time.time()
        response = chat(model, messages, url, timeout, api_key)
        elapsed = time.time() - t0

        if "error" in response:
            print(f" ERROR ({elapsed:.1f}s)\n    → {response['error']}")
            results.append({
                "id": test["id"], "label": test["label"], "standard": test["standard"],
                "status": "ERROR", "error": response["error"], "elapsed_s": round(elapsed, 1),
            })
            continue

        content = (response.get("choices", [{}])[0].get("message") or {}).get("content", "")
        usage = response.get("usage", {})
        comp_tokens = usage.get("completion_tokens")

        # Auto-score
        scores = test["score_fn"](content, comp_tokens, test.get("injected_context", ""))
        thresholds = test["pass_thresholds"]
        passed = [k for k, v in scores.items() if k in thresholds and thresholds[k](v)]
        failed = [k for k, v in scores.items() if k in thresholds and not thresholds[k](v)]

        auto_status = "PASS" if not failed else ("WARN" if len(failed) <= 1 else "FAIL")
        print(f" {auto_status} ({elapsed:.1f}s)")
        if failed:
            print(f"    ✗ failed: {failed}")
        if passed:
            print(f"    ✓ passed: {passed}")

        # Judge score
        judge_scores = None
        if judge_model and content:
            print(f"    judging...", end="", flush=True)
            judge_scores = judge_response(content, judge_model, url, api_key, timeout)
            if judge_scores:
                atm = judge_scores.get("atmosphere", "?")
                npc = judge_scores.get("npc_craft", "?")
                gmc = judge_scores.get("gm_craft", "?")
                avg = round(sum(judge_scores.values()) / 3, 1) if judge_scores else "?"
                print(f" atm={atm} npc={npc} gm={gmc} avg={avg}")
            else:
                print(" (judge failed)")

        hl = highlight_sentence(content)
        print(f"    ❝ {hl}")

        results.append({
            "id": test["id"],
            "label": test["label"],
            "standard": test["standard"],
            "status": auto_status,
            "auto_scores": scores,
            "passed_dimensions": passed,
            "failed_dimensions": failed,
            "judge_scores": judge_scores,
            "completion_tokens": comp_tokens,
            "elapsed_s": round(elapsed, 1),
            "highlight": hl,
            "full_response": content,
        })

    # Summary
    auto_counts = {s: sum(1 for r in results if r.get("status") == s)
                   for s in ["PASS", "WARN", "FAIL", "ERROR"]}

    judge_avgs = {}
    judge_results = [r["judge_scores"] for r in results if r.get("judge_scores")]
    if judge_results:
        for dim in ["atmosphere", "npc_craft", "gm_craft"]:
            vals = [j[dim] for j in judge_results if dim in j]
            judge_avgs[dim] = round(sum(vals) / len(vals), 2) if vals else None

    print(f"\n{'='*60}")
    print(f"Model: {model}")
    print(f"Auto: {auto_counts}")
    if judge_avgs:
        print(f"Judge avg: atmosphere={judge_avgs.get('atmosphere')}  "
              f"npc_craft={judge_avgs.get('npc_craft')}  "
              f"gm_craft={judge_avgs.get('gm_craft')}")
    print(f"{'='*60}\n")

    if output_file:
        out = {
            "model": model,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "auto_summary": auto_counts,
            "judge_averages": judge_avgs,
            "cases": results,
        }
        Path(output_file).write_text(json.dumps(out, indent=2))
        print(f"Results written to {output_file}")

    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="open-tabletop-gm narrative quality probe")
    parser.add_argument("--model", required=True)
    parser.add_argument("--url", default="http://localhost:1234")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--judge-model", default="",
                        help="Model to use as LLM judge (e.g. openai/gpt-oss-20b). "
                             "Omit to skip judge scoring.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output-file", default="")
    args = parser.parse_args()

    run_narrative_probe(
        args.model, args.url, args.api_key, args.timeout,
        args.judge_model, args.output_file,
    )
