"""LLM-judge ensemble for recall scoring.

For each (response, fact) pair, queries N judge models in parallel
(default 5 from distinct model families) and returns an ensemble
verdict. Majority PASS = ensemble PASS. Reports per-judge breakdown
so the runner can compute inter-rater agreement (IRA) for the
methodology validity check.

Why 5 judges, not 1:
  Single-judge LLM scoring has two known failure modes — stylistic
  preferences that don't generalize, and re-run variance. Five judges
  from distinct training families (OpenAI/Google/Meta/Alibaba/NVIDIA)
  with each scoring independently is the same principle as peer review
  or ensemble methods in ML. Inter-rater agreement (Cohen's kappa, mean
  across all judge pairs) becomes a measurable validity signal: when
  IRA > 0.5 the judges substantially agreed and the result is more
  trustworthy; when IRA is low the judges disagreed and the result is
  in the gray zone.

The default judge ensemble matches the validated list from
`narrative_probe.py` so contributors switching between probes hit the
same scoring distribution.

Calibration cases at the bottom of this module — `python -m
probe.persistence_v2.calibrate` runs them against the full ensemble.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from itertools import combinations
from statistics import mean
from typing import Optional

import httpx


# Five judges from distinct model families. Mirrors the validated
# ensemble in narrative_probe.py — same set, same rationale.
DEFAULT_JUDGE_MODELS: list[str] = [
    "openai/gpt-oss-120b",
    "google/gemma-3-27b-it",
    "meta-llama/llama-3.3-70b-instruct",
    "qwen/qwen3-235b-a22b",
    "nvidia/nemotron-3-super-120b-a12b",
]

OPENROUTER_BASE = os.environ.get(
    "PROBE_JUDGE_BASE", "https://openrouter.ai/api/v1",
)


@dataclass(frozen=True)
class JudgeResult:
    """One judge's vote on one (response, fact) pair."""
    judge: str
    passed: bool
    confidence: float
    reason: str
    raw_text: str


@dataclass(frozen=True)
class EnsembleResult:
    """The ensemble's verdict + the underlying per-judge votes."""
    fact_description: str
    per_judge: tuple[JudgeResult, ...]
    # majority_pass = at least ceil(N/2) judges said PASS
    majority_pass: bool
    # pass_rate = fraction of judges that said PASS (0.0..1.0)
    pass_rate: float
    # agreement = 1.0 if all judges agreed; 0.0 if perfectly split
    agreement: float


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


async def _one_judge(
    *,
    judge_model: str,
    response: str,
    fact_description: str,
    http: httpx.AsyncClient,
    api_key: str,
) -> JudgeResult:
    """One judge's call. Failures degrade to FAIL with confidence 0."""
    user_text = (
        f"FACT (the canon you are checking for):\n{fact_description}\n\n"
        f"NARRATOR RESPONSE (what the model generated):\n{response.strip()}\n\n"
        "Did the response demonstrate the fact? Output JSON only."
    )
    body = {
        "model": judge_model,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user_text},
        ],
        # 1024 cap leaves room for reasoning-model thinking tokens.
        # gpt-oss-120b in particular burns tokens internally; 300 caps
        # routinely returned empty content.
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
            timeout=45.0,
        )
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices", [])
        raw = choices[0].get("message", {}).get("content", "") if choices else ""
        raw = (raw or "").strip()
    except Exception as e:  # noqa: BLE001
        return JudgeResult(
            judge=judge_model, passed=False, confidence=0.0,
            reason=f"judge error: {e}", raw_text="",
        )

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw,
                     flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
        return JudgeResult(
            judge=judge_model,
            passed=bool(parsed.get("passed", False)),
            confidence=float(parsed.get("confidence", 0.5) or 0.5),
            reason=str(parsed.get("reason", "")),
            raw_text=raw,
        )
    except json.JSONDecodeError:
        passed_match = re.search(r'"passed"\s*:\s*(true|false)',
                                 cleaned, re.IGNORECASE)
        if passed_match:
            return JudgeResult(
                judge=judge_model,
                passed=passed_match.group(1).lower() == "true",
                confidence=0.5,
                reason="parsed lenient (JSON malformed)",
                raw_text=raw,
            )
        return JudgeResult(
            judge=judge_model, passed=False, confidence=0.0,
            reason="judge produced unparseable output", raw_text=raw,
        )


async def judge_recall(
    *,
    response: str,
    fact_description: str,
    http: httpx.AsyncClient,
    api_key: str,
    judge_models: Optional[list[str]] = None,
) -> EnsembleResult:
    """Run the full ensemble on one (response, fact) pair. Judges fire
    in parallel; one slow judge doesn't serialize the others."""
    models = judge_models or DEFAULT_JUDGE_MODELS
    results = await asyncio.gather(*[
        _one_judge(
            judge_model=m, response=response,
            fact_description=fact_description, http=http, api_key=api_key,
        )
        for m in models
    ])
    passes = [j.passed for j in results]
    pass_rate = sum(passes) / len(passes) if passes else 0.0
    # Majority threshold: PASS if at least ceil(N/2) judges agree.
    # For N=5, that's 3.
    threshold = (len(models) + 1) // 2
    majority_pass = sum(passes) >= threshold
    # Agreement: 1.0 if all judges voted the same way, 0.0 if perfectly
    # split. For N=5 majority case (3-2), agreement = 0.6.
    agreement = max(sum(passes), len(passes) - sum(passes)) / len(passes)
    return EnsembleResult(
        fact_description=fact_description,
        per_judge=tuple(results),
        majority_pass=majority_pass,
        pass_rate=pass_rate,
        agreement=agreement,
    )


def cohen_kappa_binary(votes_a: list[bool], votes_b: list[bool]) -> float:
    """Cohen's kappa for two judges' binary votes across N items.
    kappa = 1.0 → perfect agreement; 0.0 → chance-level; <0 → worse than
    chance. Returns 0.0 when undefined (e.g., one judge passes everything
    so chance agreement is 1.0)."""
    if not votes_a or len(votes_a) != len(votes_b):
        return 0.0
    n = len(votes_a)
    # observed agreement
    p_o = sum(1 for a, b in zip(votes_a, votes_b) if a == b) / n
    # expected agreement by chance, given each judge's marginal pass rate
    p_a_pass = sum(votes_a) / n
    p_b_pass = sum(votes_b) / n
    p_e = (p_a_pass * p_b_pass) + ((1 - p_a_pass) * (1 - p_b_pass))
    if p_e == 1.0:
        return 1.0 if p_o == 1.0 else 0.0
    return (p_o - p_e) / (1 - p_e)


def compute_ira(
    ensemble_results: list[EnsembleResult],
    judge_models: Optional[list[str]] = None,
) -> dict:
    """Inter-rater agreement: mean pairwise Cohen's kappa across all
    items judged by the ensemble. Reports the overall mean + per-pair
    breakdown so reviewers can see whether one judge is the outlier.
    """
    models = judge_models or DEFAULT_JUDGE_MODELS
    # Collect votes per judge across all items.
    per_judge_votes: dict[str, list[bool]] = {m: [] for m in models}
    for er in ensemble_results:
        for j in er.per_judge:
            if j.judge in per_judge_votes:
                per_judge_votes[j.judge].append(j.passed)
    # Compute pairwise kappa.
    pair_kappas: dict[str, float] = {}
    kappas: list[float] = []
    for a, b in combinations(models, 2):
        if len(per_judge_votes[a]) != len(per_judge_votes[b]):
            # shouldn't happen if every ensemble has the same judge set
            continue
        k = cohen_kappa_binary(per_judge_votes[a], per_judge_votes[b])
        key = f"{a.split('/')[-1]} ↔ {b.split('/')[-1]}"
        pair_kappas[key] = round(k, 3)
        kappas.append(k)
    return {
        "mean_kappa": round(mean(kappas), 3) if kappas else 0.0,
        "pair_kappas": pair_kappas,
        "n_items": len(ensemble_results),
        "per_judge_pass_rate": {
            j.split('/')[-1]: round(sum(v) / len(v), 3) if v else 0.0
            for j, v in per_judge_votes.items()
        },
    }


# ─── Calibration cases (binary expected; the ensemble's majority_pass
# should match expected on each of these). Run via:
#   python -m probe.persistence_v2.calibrate

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
