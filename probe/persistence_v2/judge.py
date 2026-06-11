"""LLM-judge for recall scoring.

For each (response, fact) pair, asks a small judge model whether the
response demonstrates knowledge of the canon fact. Returns a structured
JudgeResult so the runner can aggregate over trials.

Default judge: `google/gemini-2.5-flash` via OpenRouter. Cheap, fast,
semantically sharp. Override with $PROBE_JUDGE_MODEL.

The judge prompt is intentionally biased toward PASS on ambiguous
cases — we'd rather over-credit subtle behavioral manifestation
("Mira's hand twitches" implies the missing fingertip canon) than
penalize correct paraphrasing. Calibration cases in CALIBRATION_CASES
guard this — run `python -m probe.persistence_v2.calibrate` to verify
the judge stays honest after a model swap.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Optional

import httpx


JUDGE_MODEL = os.environ.get("PROBE_JUDGE_MODEL", "google/gemini-2.5-flash")
OPENROUTER_BASE = os.environ.get(
    "PROBE_JUDGE_BASE", "https://openrouter.ai/api/v1",
)


@dataclass(frozen=True)
class JudgeResult:
    passed: bool
    confidence: float          # 0.0..1.0, judge-reported
    reason: str
    raw_text: str


JUDGE_SYSTEM = (
    "You judge whether a tabletop-RPG narrator's response demonstrates "
    "knowledge of a canon fact about the game world.\n\n"
    "PASS rules (return passed=true):\n"
    "- The response carries the fact in any form: literal phrasing, "
    "paraphrase, character voice referring to it, OR visible behavioral "
    "manifestation (e.g., a 'nervous' NPC trembles or stammers, "
    "'missing fingertip' NPC's hand is described).\n"
    "- If the fact has multiple parts (separated by 'and', 'but', "
    "semicolons), PASS if the response substantively demonstrates AT "
    "LEAST ONE part. We're measuring memory of the canon, not perfect "
    "recitation.\n\n"
    "FAIL rules (return passed=false):\n"
    "- The response is silent on the fact AND its behavioral signs.\n"
    "- The response contradicts the fact (e.g., narrator describes a "
    "trait that is the opposite of canon).\n"
    "- The response could be written exactly the same way without the "
    "fact existing in the bible.\n\n"
    "Default to FAIL only when the response is genuinely silent — when "
    "in doubt about whether a subtle signal demonstrates the fact, "
    "lean toward PASS with lower confidence.\n\n"
    "Output JSON only, no prose around it:\n"
    "{\n"
    "  \"passed\": true | false,\n"
    "  \"confidence\": 0.0..1.0,\n"
    "  \"reason\": \"one-sentence justification\"\n"
    "}"
)


async def judge_recall(
    *,
    response: str,
    fact_description: str,
    http: httpx.AsyncClient,
    api_key: str,
    model: Optional[str] = None,
) -> JudgeResult:
    """Ask the judge whether `response` demonstrates the `fact`."""
    used_model = model or JUDGE_MODEL
    user_text = (
        f"FACT (the canon you are checking for):\n{fact_description}\n\n"
        f"NARRATOR RESPONSE (what the model generated):\n{response.strip()}\n\n"
        "Did the response demonstrate the fact? Output JSON only."
    )
    body = {
        "model": used_model,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user_text},
        ],
        # Generous output cap: Gemini Flash has internal "thinking" tokens
        # that count against the budget but aren't returned. A 256-cap
        # routinely got eaten by the thinker, leaving no JSON. 1024 gives
        # headroom.
        "max_tokens": 1024,
        "temperature": 0.0,
    }
    try:
        r = await http.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30.0,
        )
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices", [])
        raw = choices[0].get("message", {}).get("content", "") if choices else ""
        raw = (raw or "").strip()
    except Exception as e:  # noqa: BLE001
        return JudgeResult(passed=False, confidence=0.0,
                           reason=f"judge error: {e}", raw_text="")

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw,
                     flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        passed_match = re.search(r'"passed"\s*:\s*(true|false)',
                                 cleaned, re.IGNORECASE)
        if passed_match:
            return JudgeResult(
                passed=passed_match.group(1).lower() == "true",
                confidence=0.5,
                reason="parsed lenient (JSON malformed)",
                raw_text=raw,
            )
        return JudgeResult(passed=False, confidence=0.0,
                           reason="judge produced unparseable output",
                           raw_text=raw)

    return JudgeResult(
        passed=bool(parsed.get("passed", False)),
        confidence=float(parsed.get("confidence", 0.5) or 0.5),
        reason=str(parsed.get("reason", "")),
        raw_text=raw,
    )


# Calibration cases. Run via `python -m probe.persistence_v2.calibrate`
# any time you change the judge model or prompt. All 5 should match
# expected if the judge is honest.
CALIBRATION_CASES: list[tuple[bool, str, str]] = [
    (True,
     "Aldric jumps when he sees Sable, hand reaching for his sword. Young, nervous.",
     "Aldric is young and nervous; he owes Sable a life debt"),
    (True,
     "The boy yelps. His hand twitches toward his belt knife.",
     "Aldric is young and nervous; he owes Sable a life debt"),
    (False,
     "Aldric whistles a tune and walks off without a word.",
     "Aldric is young and nervous; he owes Sable a life debt"),
    (True,
     "Mira leans in. You smell cloves on her breath.",
     "Mira smells of cloves (the bible anchor scent)"),
    (False,
     "Mira nods. She smells of fresh rain and pine.",
     "Mira smells of cloves (the bible anchor scent)"),
]
