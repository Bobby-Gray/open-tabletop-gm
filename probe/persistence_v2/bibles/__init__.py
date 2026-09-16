"""Bible registry.

Each module in this package defines BIBLE, NPCS, FACTS, TURNS at
module top-level. Re-exported here as a single dict so the runner can
look them up by name.

Adding a new bible:
  1. Drop a file `bibles/<name>.py` following the shape of valdremor.py
  2. Add the import + entry below
  3. The runner picks it up automatically via the BIBLES dict
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from . import atrias, nightshift, valdremor


TurnKind = Literal["seed", "neutral", "recall"]


@dataclass(frozen=True)
class Turn:
    idx: int
    action: str
    kind: TurnKind
    seeds: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()


@dataclass(frozen=True)
class Fact:
    id: str
    description: str


@dataclass(frozen=True)
class Bible:
    name: str
    genre: str
    system_prompt: str
    npcs_md: str
    facts: tuple[Fact, ...]
    turns: tuple[Turn, ...]


def _build(mod, name: str, genre: str) -> Bible:
    return Bible(
        name=name,
        genre=genre,
        system_prompt=mod.BIBLE + "\n\n" + mod.NPCS,
        npcs_md=mod.NPCS,
        facts=tuple(Fact(id=f.id, description=f.description) for f in mod.FACTS),
        turns=tuple(
            Turn(idx=t.idx, action=t.action, kind=t.kind,
                 seeds=t.seeds, targets=t.targets)
            for t in mod.TURNS
        ),
    )


BIBLES: dict[str, Bible] = {
    "valdremor":  _build(valdremor,  "valdremor",  "medieval fantasy"),
    "atrias":     _build(atrias,     "atrias",     "sci-fi"),
    "nightshift": _build(nightshift, "nightshift", "modern horror"),
}


def fact_by_id(bible: Bible, fact_id: str):
    return next((f for f in bible.facts if f.id == fact_id), None)


def seed_turn_for_fact(bible: Bible, fact_id: str) -> int | None:
    for t in bible.turns:
        if fact_id in t.seeds:
            return t.idx
    return None
