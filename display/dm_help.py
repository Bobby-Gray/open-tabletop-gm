#!/usr/bin/env python3
"""
dm_help.py — On-demand DM hint generator.

Called by Flask /help-request endpoint as a subprocess.
Reads recent display log + campaign state.md, calls the Claude API,
sends result to the display via send.py --tutor.

Lock lifecycle:
  Flask creates .help-lock (O_EXCL) before spawning this process.
  This script removes .help-lock in its finally block.
  Multiple browser clicks → Flask returns 409 on all but the first.
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys

BASE      = pathlib.Path(__file__).parent.parent
LOCK_FILE = BASE / "display" / ".help-lock"
LOG_FILE  = BASE / "display" / "text_log.json"
SEND_PY   = BASE / "display" / "send.py"


def release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


def get_recent_context(n: int = 8) -> str:
    """Return the last n display blocks as labelled text, skipping previous tutor blocks."""
    if not LOG_FILE.exists():
        return ""
    try:
        data = json.loads(LOG_FILE.read_text())
    except Exception:
        return ""
    recent = data[-n:] if len(data) >= n else data
    parts = []
    for item in recent:
        if not isinstance(item, dict) or "text" not in item:
            continue
        if item.get("tutor"):
            continue  # skip previous hints — don't feed them back as context
        text = item["text"].strip()
        if item.get("player"):
            parts.append(f"[PLAYER ACTION] {text}")
        elif item.get("npc"):
            parts.append(f"[NPC: {item.get('npc', '')}] {text}")
        elif item.get("dice"):
            parts.append(f"[DICE] {text}")
        else:
            parts.append(f"[DM] {text}")
    return "\n\n".join(parts)


def get_campaign_state(campaign: str) -> str:
    """Read the first ~55 lines of state.md — Current Situation, World State, Open Threads."""
    state_path = pathlib.Path(os.environ.get("OPENTTG_CAMPAIGNS_DIR", str(pathlib.Path.home() / ".local" / "share" / "open-tabletop-gm" / "campaigns"))) / campaign / "state.md"
    if not state_path.exists():
        return ""
    lines = state_path.read_text().splitlines()[:55]
    return "\n".join(lines)


def call_claude(context: str, state: str) -> str:
    """Call claude -p (non-interactive print mode) — uses Claude Code's own auth."""
    system = (
        "You are a D&D 5e Dungeon Master generating a brief in-character DM hint. "
        "Given the current scene and recent events, identify the single most useful thing "
        "the player may not have considered right now: a skill check worth attempting and "
        "what it would reveal; 2-3 visible options at this decision point noting which "
        "close doors permanently; if there is an irreversible risk begin with: ⚠ WARNING:; "
        "or an unused class feature or reaction relevant to this exact moment. "
        "Rules: 2-4 sentences maximum. Write from inside the fiction — no rule names, "
        "no meta-language. Never reveal information the character could not know. "
        "If there is genuinely nothing useful to add, respond with exactly: SKIP"
    )

    prompt = (
        f"Current campaign state:\n{state}\n\n"
        f"Recent scene (last display blocks):\n{context}\n\n"
        "Generate a DM hint for the player's current situation."
    )

    result = subprocess.run(
        [
            "claude", "-p",
            "--model", "claude-sonnet-4-6",
            "--system-prompt", system,
            prompt,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        return "SKIP"

    return result.stdout.strip()


def send_tutor(text: str) -> None:
    subprocess.run(
        [sys.executable, str(SEND_PY), "--tutor"],
        input=text,
        text=True,
        capture_output=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and send an on-demand DM hint.")
    parser.add_argument("--campaign", required=True, help="Campaign directory name")
    args = parser.parse_args()

    try:
        context = get_recent_context(8)
        state   = get_campaign_state(args.campaign)

        if not context and not state:
            return

        hint = call_claude(context, state)
        if hint.strip().upper() == "SKIP":
            return

        send_tutor(hint)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
