"""Entry point: python -m probe.persistence_v2 ...

Smoke test:
  python -m probe.persistence_v2 \\
    --subjects anthropic/claude-sonnet-4-6 \\
    --bibles valdremor \\
    --modes normal \\
    --trials 1

Full battery (4 models × 3 bibles × 4 modes × 2 trials):
  python -m probe.persistence_v2 \\
    --subjects anthropic/claude-sonnet-4-6,anthropic/claude-haiku-4-5,openai/gpt-4o,google/gemini-2.5-pro \\
    --bibles valdremor,atrias,nightshift \\
    --modes naive,normal,scaffolded,perfect \\
    --trials 2

Requires $OPENROUTER_API_KEY.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .runner import aggregate, run_battery, write_report_md


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--subjects", required=True,
                   help="Comma-separated OpenRouter routes (e.g. anthropic/claude-sonnet-4-6)")
    p.add_argument("--bibles", default="valdremor,atrias,nightshift",
                   help="Comma-separated bible names")
    p.add_argument("--modes", default="normal,scaffolded",
                   help="Comma-separated: naive,normal,scaffolded,perfect")
    p.add_argument("--trials", type=int, default=2)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--out-dir", default="probe/persistence_v2/results")
    args = p.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("ERROR: set OPENROUTER_API_KEY in env", file=sys.stderr)
        return 1

    subjects = [s.strip() for s in args.subjects.split(",") if s.strip()]
    bibles = [b.strip() for b in args.bibles.split(",") if b.strip()]
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(subjects) * len(bibles) * len(modes) * args.trials
    print(f"Planned: {total} trials "
          f"({len(subjects)} subjects × {len(bibles)} bibles × "
          f"{len(modes)} modes × {args.trials} trials)",
          file=sys.stderr)
    print(f"Concurrency cap: {args.concurrency}", file=sys.stderr)
    print(f"Out dir: {out_dir}", file=sys.stderr)

    results = asyncio.run(run_battery(
        subject_routes=subjects, bible_names=bibles, modes=modes,
        trials=args.trials, api_key=api_key,
        concurrency=args.concurrency, out_dir=out_dir,
    ))
    print(f"Completed {len(results)}/{total} trials", file=sys.stderr)

    rollup = aggregate(results)
    (out_dir / "rollup.json").write_text(json.dumps(rollup, indent=2))
    write_report_md(rollup, out_dir / "rollup.md", label="persistence_v2")
    print(f"\nRollup: {out_dir / 'rollup.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
