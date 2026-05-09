#!/usr/bin/env python3
"""
migrate_system_version.py — backwards-compat migrator for the System Version field.

Legacy campaigns (created before the system-version field existed) have a
state.md header like:

    # Campaign: <name>
    **Created:** 2026-04-10  **Last session:** 2026-05-05  **Session count:** 26

This script detects that form and offers to inject a `**System Version:**`
field. It backs up state.md to
`state.md.backup-pre-system-version-YYYYMMDD-HHMMSS` before any write.
Idempotent: running on an already-migrated campaign exits cleanly.

The field is system-agnostic. The `--version` value is opaque to this script
— pass whatever your game system uses to distinguish editions or rulesets
(e.g. `2014` vs `2024` for D&D 5e, `1e` vs `2e` for other systems).

Usage:
    # Interactive — prompts the GM
    python3 migrate_system_version.py <campaign-name> --version 2014

    # Non-interactive — used by /gm load and CI
    python3 migrate_system_version.py <campaign-name> --version 2014 --yes
    python3 migrate_system_version.py <campaign-name> --check
        # exit 0 = already migrated
        # exit 1 = needs migration
        # exit 2 = missing campaign / state.md
        # exit 3 = user cancelled

The `--check` mode is what the procedural /gm load step calls first to decide
whether to surface the migration prompt to the GM.
"""

from __future__ import annotations

import argparse
import datetime
import shutil
import sys
from pathlib import Path

# Allow running directly from the scripts dir
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import (  # noqa: E402
    campaign_system_version,
    find_campaign,
)


HEADER_LINE_PREFIX = "**Created:**"
FIELD_TOKEN = "**System Version:**"
BACKUP_PREFIX = "state.md.backup-pre-system-version-"


def _state_path(campaign: str) -> Path:
    return find_campaign(campaign) / "state.md"


def _has_field(text: str) -> bool:
    """True if the header line already carries the System Version field."""
    for line in text.splitlines():
        if HEADER_LINE_PREFIX in line:
            return FIELD_TOKEN in line
    return False


def _has_header_line(text: str) -> bool:
    """True if state.md uses the standard `**Created:**` header line."""
    for line in text.splitlines():
        if HEADER_LINE_PREFIX in line:
            return True
    return False


def _inject_field(text: str, version: str) -> str:
    """Append `**System Version:** <version>` to the header line."""
    out = []
    injected = False
    for line in text.splitlines():
        if not injected and HEADER_LINE_PREFIX in line and FIELD_TOKEN not in line:
            stripped = line.rstrip()
            line = f"{stripped}  {FIELD_TOKEN} {version}"
            injected = True
        out.append(line)
    if not injected:
        raise RuntimeError(
            "Could not find header line (no '**Created:**' marker). "
            "Is this a valid state.md?"
        )
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _backup(state: Path) -> Path:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = state.with_name(f"{BACKUP_PREFIX}{stamp}")
    shutil.copy2(state, bak)
    return bak


def cmd_check(campaign: str) -> int:
    state = _state_path(campaign)
    if not state.exists():
        print(f"[migrate_system_version] No state.md at {state}", file=sys.stderr)
        return 2
    text = state.read_text(errors="replace")
    if not _has_header_line(text):
        # state.md uses a non-standard header — not eligible for this migrator.
        # Treat as already-migrated to avoid blocking /gm load.
        print("not-applicable")
        return 0
    if _has_field(text):
        print("migrated")
        return 0
    print("needs-migration")
    return 1


def cmd_migrate(campaign: str, version: str, assume_yes: bool) -> int:
    if not version.strip():
        print(
            "[migrate_system_version] --version is required (e.g. 2014, 2024, 1e).",
            file=sys.stderr,
        )
        return 2

    state = _state_path(campaign)
    if not state.exists():
        print(f"[migrate_system_version] No state.md at {state}", file=sys.stderr)
        return 2

    text = state.read_text(errors="replace")
    if not _has_header_line(text):
        print(
            "[migrate_system_version] state.md uses a non-standard header "
            "(no '**Created:**' marker). Not eligible for this migrator — "
            "edit the file by hand if a System Version field is required.",
            file=sys.stderr,
        )
        return 0
    if _has_field(text):
        declared = campaign_system_version(campaign)
        print(
            f"[migrate_system_version] Already migrated. Declared version: {declared}"
        )
        return 0

    if not assume_yes:
        print(
            f"\nCampaign '{campaign}' predates the system-version field.\n"
            f"  Path:   {state}\n"
            f"  Action: stamp '{FIELD_TOKEN} {version}' on the header line.\n"
            f"  Backup: {BACKUP_PREFIX}<timestamp>\n"
        )
        try:
            ans = input("Proceed? [Y/n] ").strip().lower()
        except EOFError:
            ans = ""
        if ans and ans not in ("y", "yes"):
            print("[migrate_system_version] Cancelled.")
            return 3

    bak = _backup(state)
    new_text = _inject_field(text, version.strip())
    state.write_text(new_text)
    print(
        f"[migrate_system_version] OK — '{campaign}' stamped as version "
        f"{version.strip()}.\n"
        f"  Backup: {bak}\n"
        f"  Revert: cp '{bak}' '{state}'"
    )
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "campaign", help="Campaign name (directory under campaigns root)"
    )
    p.add_argument(
        "--version",
        default="",
        help="System version string to stamp when migrating (opaque to core; "
             "e.g. '2014', '2024', '1e'). Required unless --check.",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt (used by /gm load when GM has answered).",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 0=already migrated, 1=needs migration, 2=missing. No write.",
    )
    args = p.parse_args(argv)

    if args.check:
        return cmd_check(args.campaign)
    return cmd_migrate(args.campaign, args.version, args.yes)


if __name__ == "__main__":
    sys.exit(main())
