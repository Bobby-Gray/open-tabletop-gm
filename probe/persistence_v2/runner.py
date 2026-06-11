"""Async orchestrator.

Runs (subject × bible × mode × trial) combinations with bounded
concurrency. Each trial is one full 20-turn conversation against the
subject + an LLM-judge call per recall fact.

Modes (calibration backbone):
  naive       — fresh per turn; system prompt + current action only.
                Floor: 'what can this model do with bible from system
                prompt alone?'
  normal      — current production behavior. System + full history.
  scaffolded  — normal + <reminders> block prepended to each player
                action. Tests per-turn re-injection of canon.
  perfect     — normal + full bible re-prepended to each player
                action. Ceiling: 'if attention to canon is solved,
                what's the max?'

Without these baselines a persistence number is a floating dimensionless
quantity. With them, every score becomes a position in a known range.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, pstdev

import httpx

from .bibles import BIBLES, Bible, fact_by_id, seed_turn_for_fact
from .judge import JudgeResult, judge_recall
from .scaffolding import build_recall_reminders
from .subjects import call_subject


Mode = str  # "naive" | "normal" | "scaffolded" | "perfect"


@dataclass
class TurnRecord:
    idx: int
    kind: str
    action: str
    response: str
    latency_ms: int
    judge: dict[str, JudgeResult] = field(default_factory=dict)


@dataclass
class TrialResult:
    subject: str
    bible: str
    mode: Mode
    trial: int
    turns: list[TurnRecord]
    persistence_index: float
    weighted_persistence_index: float
    avg_latency_ms: float
    total_wall_clock_s: float


def _action_with_mode(action: str, *, bible: Bible, mode: Mode) -> str:
    if mode == "naive" or mode == "normal":
        return action
    if mode == "scaffolded":
        reminders = build_recall_reminders(npcs_md=bible.npcs_md)
        if not reminders:
            return action
        return f"{reminders}\n\n{action}"
    if mode == "perfect":
        return f"<bible>\n{bible.system_prompt}\n</bible>\n\n{action}"
    raise ValueError(f"unknown mode {mode}")


async def run_trial(
    *,
    subject_route: str,
    bible: Bible,
    mode: Mode,
    trial: int,
    http: httpx.AsyncClient,
    api_key: str,
    max_tokens: int = 1024,
) -> TrialResult:
    """One full 20-turn conversation for (subject, bible, mode, trial)."""
    conversation: list[dict] = []
    turn_records: list[TurnRecord] = []
    t_start = time.perf_counter()

    for turn in bible.turns:
        action_text = _action_with_mode(turn.action, bible=bible, mode=mode)
        if mode == "naive":
            messages = [{"role": "user", "content": action_text}]
        else:
            conversation.append({"role": "user", "content": action_text})
            messages = conversation

        t0 = time.perf_counter()
        try:
            response = await call_subject(
                route=subject_route,
                system=bible.system_prompt,
                messages=messages,
                api_key=api_key,
                http=http,
                max_tokens=max_tokens,
            )
        except Exception as e:
            response = f"[ERROR: {e}]"
        latency_ms = int((time.perf_counter() - t0) * 1000)

        if mode != "naive":
            conversation.append({"role": "assistant", "content": response})

        rec = TurnRecord(
            idx=turn.idx, kind=turn.kind, action=turn.action,
            response=response, latency_ms=latency_ms,
        )

        if turn.kind == "recall" and turn.targets:
            for fact_id in turn.targets:
                f = fact_by_id(bible, fact_id)
                if not f:
                    continue
                rec.judge[fact_id] = await judge_recall(
                    response=response,
                    fact_description=f.description,
                    http=http,
                    api_key=api_key,
                )

        turn_records.append(rec)

    wall = time.perf_counter() - t_start

    pass_vals: list[float] = []
    weighted_vals: list[tuple[float, float]] = []
    for r in turn_records:
        for fid, j in r.judge.items():
            pass_vals.append(1.0 if j.passed else 0.0)
            seed_turn = seed_turn_for_fact(bible, fid)
            if seed_turn is None:
                distance = float(r.idx)
            else:
                distance = max(1, r.idx - seed_turn)
            weighted_vals.append((1.0 if j.passed else 0.0, distance ** 0.5))

    persistence_index = (mean(pass_vals) * 100) if pass_vals else 0.0
    if weighted_vals:
        num = sum(p * w for p, w in weighted_vals)
        den = sum(w for _, w in weighted_vals)
        weighted_persistence_index = (num / den * 100) if den > 0 else 0.0
    else:
        weighted_persistence_index = 0.0

    avg_latency = mean([r.latency_ms for r in turn_records]) if turn_records else 0.0
    return TrialResult(
        subject=subject_route, bible=bible.name, mode=mode, trial=trial,
        turns=turn_records,
        persistence_index=round(persistence_index, 1),
        weighted_persistence_index=round(weighted_persistence_index, 1),
        avg_latency_ms=round(avg_latency, 0),
        total_wall_clock_s=round(wall, 1),
    )


async def run_battery(
    *,
    subject_routes: list[str],
    bible_names: list[str],
    modes: list[Mode],
    trials: int,
    api_key: str,
    concurrency: int = 4,
    out_dir: Path,
) -> list[TrialResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[TrialResult] = []
    sem = asyncio.Semaphore(concurrency)

    async def _bounded(coro):
        async with sem:
            return await coro

    async with httpx.AsyncClient() as http:
        tasks = []
        for subject_route in subject_routes:
            for bible_name in bible_names:
                bible = BIBLES[bible_name]
                for mode in modes:
                    for trial in range(trials):
                        tasks.append(_bounded(run_trial(
                            subject_route=subject_route, bible=bible,
                            mode=mode, trial=trial, http=http,
                            api_key=api_key,
                        )))

        for done in await asyncio.gather(*tasks, return_exceptions=True):
            if isinstance(done, BaseException):
                print(f"  ⚠ trial failed: {done}")
                continue
            results.append(done)
            slug = f"{done.subject.replace('/', '_')}__{done.bible}__{done.mode}__t{done.trial}"
            (out_dir / f"{slug}.json").write_text(json.dumps(
                {
                    "subject": done.subject,
                    "bible": done.bible,
                    "mode": done.mode,
                    "trial": done.trial,
                    "persistence_index": done.persistence_index,
                    "weighted_persistence_index": done.weighted_persistence_index,
                    "avg_latency_ms": done.avg_latency_ms,
                    "total_wall_clock_s": done.total_wall_clock_s,
                    "turns": [
                        {
                            "idx": r.idx, "kind": r.kind, "action": r.action,
                            "response": r.response, "latency_ms": r.latency_ms,
                            "judge": {
                                fid: {
                                    "passed": j.passed,
                                    "confidence": j.confidence,
                                    "reason": j.reason,
                                }
                                for fid, j in r.judge.items()
                            },
                        }
                        for r in done.turns
                    ],
                },
                indent=2,
            ))
    return results


def aggregate(results: list[TrialResult]) -> dict:
    cells: dict[tuple[str, str, str], list[TrialResult]] = {}
    for r in results:
        cells.setdefault((r.subject, r.bible, r.mode), []).append(r)

    rollup: dict = {"cells": [], "per_subject_mode": {}}
    for (subject, bible, mode), trials_list in cells.items():
        ps = [t.persistence_index for t in trials_list]
        wps = [t.weighted_persistence_index for t in trials_list]
        lats = [t.avg_latency_ms for t in trials_list]
        rollup["cells"].append({
            "subject": subject, "bible": bible, "mode": mode,
            "trials": len(trials_list),
            "persistence_mean": round(mean(ps), 1) if ps else 0.0,
            "persistence_std": round(pstdev(ps), 1) if len(ps) > 1 else 0.0,
            "weighted_persistence_mean": round(mean(wps), 1) if wps else 0.0,
            "avg_latency_ms": round(mean(lats), 0) if lats else 0.0,
        })

    by_sm: dict[str, dict[str, dict]] = {}
    for cell in rollup["cells"]:
        by_sm.setdefault(cell["subject"], {})[cell["mode"]] = cell
    for subject, mode_cells in by_sm.items():
        agg = {}
        for mode, _ in mode_cells.items():
            same = [c for c in rollup["cells"]
                    if c["subject"] == subject and c["mode"] == mode]
            if not same:
                continue
            agg[mode] = {
                "persistence_mean": round(mean([c["persistence_mean"] for c in same]), 1),
                "weighted_persistence_mean": round(mean([c["weighted_persistence_mean"] for c in same]), 1),
                "avg_latency_ms": round(mean([c["avg_latency_ms"] for c in same]), 0),
            }
        rollup["per_subject_mode"][subject] = agg

    return rollup


def write_report_md(rollup: dict, out_path: Path, label: str = "") -> None:
    lines = [f"# persistence_v2 results{f' — {label}' if label else ''}\n"]
    lines.append("## Per-subject persistence (averaged across all bibles)\n")
    lines.append("| Subject | Mode | Persistence | Weighted | Latency |")
    lines.append("|---|---|---|---|---|")
    subjects = sorted(rollup["per_subject_mode"].keys())
    for subject in subjects:
        for mode in ("naive", "normal", "scaffolded", "perfect"):
            d = rollup["per_subject_mode"][subject].get(mode)
            if not d:
                continue
            lines.append(
                f"| {subject} | {mode} | {d['persistence_mean']}% | "
                f"{d['weighted_persistence_mean']}% | {d['avg_latency_ms']}ms |"
            )

    lines.append("\n## Per-cell detail\n")
    lines.append("| Subject | Bible | Mode | Trials | Persistence | ±std | Weighted | Latency |")
    lines.append("|---|---|---|---|---|---|---|---|")
    cells = sorted(rollup["cells"], key=lambda c: (c["subject"], c["bible"], c["mode"]))
    for c in cells:
        lines.append(
            f"| {c['subject']} | {c['bible']} | {c['mode']} | {c['trials']} | "
            f"{c['persistence_mean']}% | {c['persistence_std']} | "
            f"{c['weighted_persistence_mean']}% | {c['avg_latency_ms']}ms |"
        )
    out_path.write_text("\n".join(lines) + "\n")
