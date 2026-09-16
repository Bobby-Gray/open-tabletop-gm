"""Recall scaffolding parser — builds <reminders> block from a bible.

Parses the bible's `### NPC Name` markdown sections and extracts the
most sensory-anchored 1-2 trait lines per NPC. The resulting block
gets prepended to a player's action message when the runner is in
scaffolded mode.

Pure regex, no external deps. The tabletop-RPG bible format here is
the same one [claude-dnd-skill](https://github.com/Bobby-Gray/claude-dnd-skill)
ships in `templates/npcs.md`.
"""
from __future__ import annotations

import re

MAX_REMINDED_NPCS = 6

_NPC_HEADER_RE = re.compile(r"^###\s+(?P<name>[^\n]+?)\s*$", re.MULTILINE)
_LABELED_TRAIT_RE = re.compile(
    # Accept both `**Label:**` (label+colon inside bold) and `**Label**:`
    # (colon outside bold). Bible authors waver between the two; the
    # probe shouldn't care.
    r"^\*\*(Role|Demeanor|Speech quirk|Motivation|Secret):?\*\*:?\s*(?P<value>[^\n]+)",
    re.MULTILINE | re.IGNORECASE,
)


def _condense(text: str, *, max_chars: int = 110) -> str:
    """Keep first sentence + char cap so reminder blocks stay lean."""
    text = text.strip()
    cut = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    if len(cut) > max_chars:
        return cut[: max_chars - 1].rstrip() + "…"
    return cut


def _extract_npcs(npcs_md: str) -> list[tuple[str, str]]:
    if not npcs_md:
        return []
    headers = list(_NPC_HEADER_RE.finditer(npcs_md))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(headers):
        name = m.group("name").strip()
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(npcs_md)
        section = npcs_md[start:end]
        traits: list[str] = []
        for tm in _LABELED_TRAIT_RE.finditer(section):
            label = tm.group(1).lower()
            value = _condense(tm.group("value"))
            if not value:
                continue
            # Prefer Demeanor + Speech quirk (sensory anchors); fall back
            # to Role + Motivation only if those didn't land.
            if label in ("demeanor", "speech quirk"):
                traits.append(value)
            elif label in ("role", "motivation") and len(traits) < 2:
                traits.append(value)
            if len(traits) >= 2:
                break
        condensed = "; ".join(traits) if traits else ""
        out.append((name, condensed))
        if len(out) >= MAX_REMINDED_NPCS:
            break
    return out


def build_recall_reminders(*, npcs_md: str | None) -> str:
    """Return the reminder block; empty string when the bible yields
    no usable NPC data."""
    if not npcs_md:
        return ""
    npcs = _extract_npcs(npcs_md)
    if not npcs:
        return ""
    lines = ["<reminders>", "Active NPCs:"]
    for name, traits in npcs:
        if traits:
            lines.append(f"- {name}: {traits}")
        else:
            lines.append(f"- {name}")
    lines.append("</reminders>")
    return "\n".join(lines)


def append_reminders_to_action(action: str, reminders: str) -> str:
    if not reminders:
        return action
    return f"{reminders}\n\n{action}"
