"""Run the 5 hand-crafted calibration cases against the configured judge.

If the judge model has been swapped, run this first to verify the new
judge agrees with what we expect on each case. Three are PASS cases,
two are FAIL cases — covers literal/paraphrase/behavioral/silent/
contradicting forms.

  python -m probe.persistence_v2.calibrate
"""
from __future__ import annotations

import asyncio
import os
import sys

import httpx

from .judge import CALIBRATION_CASES, judge_recall


async def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("ERROR: set OPENROUTER_API_KEY in env", file=sys.stderr)
        return 1

    passed = 0
    failed = 0
    async with httpx.AsyncClient() as http:
        for expected, response, fact in CALIBRATION_CASES:
            r = await judge_recall(
                response=response, fact_description=fact,
                http=http, api_key=api_key,
            )
            mark = "✓" if r.majority_pass == expected else "✗"
            per_judge = ", ".join(
                f"{pj.judge.split('/')[-1]}={'P' if pj.passed else 'F'}"
                for pj in r.per_judge
            )
            print(f"{mark} expected={expected!s:<5} ensemble={r.majority_pass!s:<5} "
                  f"pass_rate={r.pass_rate:.2f} ({per_judge})")
            if r.majority_pass == expected:
                passed += 1
            else:
                failed += 1

    total = passed + failed
    print(f"\n{passed}/{total} calibration cases agree with expected.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
