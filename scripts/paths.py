"""
paths.py — canonical path resolution for open-tabletop-gm campaign and character data.

All scripts that need to locate campaign or character files should import from
here rather than hardcoding ~/open-tabletop-gm/. Set GM_CAMPAIGN_ROOT to move
your data anywhere — iCloud, Dropbox, network share, etc. Defaults to
~/open-tabletop-gm.

Usage:
    from paths import campaigns_dir, characters_dir, campaign_dir, find_campaign

Environment:
    GM_CAMPAIGN_ROOT    Root of campaign data tree. Default: ~/open-tabletop-gm
                        Example: export GM_CAMPAIGN_ROOT=~/Dropbox/gm
"""

import os
import pathlib
import shutil
import sys

_DEFAULT_ROOT = pathlib.Path("~/open-tabletop-gm").expanduser()


def _root() -> pathlib.Path:
    """Return the configured data root, expanded and absolute."""
    raw = os.environ.get("GM_CAMPAIGN_ROOT", "")
    if raw.strip():
        return pathlib.Path(raw.strip()).expanduser().resolve()
    return _DEFAULT_ROOT


def campaigns_dir() -> pathlib.Path:
    """Return the campaigns directory under the configured root."""
    return _root() / "campaigns"


def characters_dir() -> pathlib.Path:
    """Return the global characters directory under the configured root."""
    return _root() / "characters"


def campaign_dir(name: str) -> pathlib.Path:
    """Return the directory for a specific campaign under the configured root."""
    return campaigns_dir() / name


def find_campaign(name: str) -> pathlib.Path:
    """Locate a campaign directory, with legacy fallback and optional migration.

    Resolution order:
    1. $GM_CAMPAIGN_ROOT/campaigns/<name>/  — configured root (or default)
    2. ~/open-tabletop-gm/campaigns/<name>/ — legacy default (only checked when
       GM_CAMPAIGN_ROOT is set to a *different* path)

    When a campaign is found at the legacy path and the configured root is custom,
    the campaign is copied to the configured root so subsequent sessions use the
    new location. The original is left in place (no files are deleted).

    Returns the path to the campaign directory (may not exist if not found anywhere).
    """
    configured = campaign_dir(name)
    if configured.exists():
        return configured

    custom_root = os.environ.get("GM_CAMPAIGN_ROOT", "").strip()
    if not custom_root:
        return configured

    legacy = _DEFAULT_ROOT / "campaigns" / name
    if not legacy.exists():
        return configured

    configured.parent.mkdir(parents=True, exist_ok=True)
    print(
        f"[paths] Campaign '{name}' found at legacy path {legacy}\n"
        f"[paths] Copying to {configured} (original kept in place)",
        file=sys.stderr,
    )
    shutil.copytree(str(legacy), str(configured))
    return configured


# ── System version selection (system-agnostic) ────────────────────────────
# A campaign declares an optional version string for its game system on the
# state.md header line, e.g.:
#
#     **System Version:** 2024
#
# The value is opaque to core — it is whatever the chosen game system uses to
# distinguish edition/ruleset (e.g. "2014" vs "2024" for D&D 5e, "1e" vs "2e"
# for some other system). When unset (legacy campaigns predating the field) a
# system-supplied default is returned. Core knows nothing about valid values;
# the system module owns that.

import re as _re

_SYSTEM_VERSION_PAT = _re.compile(
    r"\*\*System Version:\*\*\s*([^\s|]+)", _re.IGNORECASE
)


def campaign_system_version(name: str, default: str = "") -> str:
    """Return the campaign's declared system version, or `default` if unset.

    Reads the state.md header. Returns the empty string by default — callers
    that need a system-specific fallback should pass it explicitly (e.g.
    `campaign_system_version(name, default="2014")` from the dnd5e module).
    """
    state = find_campaign(name) / "state.md"
    if not state.exists():
        return default
    try:
        text = state.read_text(errors="replace")
    except OSError:
        return default
    m = _SYSTEM_VERSION_PAT.search(text)
    if not m:
        return default
    return m.group(1).strip()


def system_data_path(system: str, version: str = "", filename: str = "") -> pathlib.Path:
    """Return a path under `systems/<system>/data/`.

    Generic helper for system modules that store versioned data files. Core
    does not interpret `version` or `filename` — callers compose the file
    name however the system module prefers (e.g. `dnd5e_srd_2024.json`).

    With `filename` empty, returns the data directory for the system.
    With `version` empty and `filename` empty, same as above.
    """
    skill_base = pathlib.Path(__file__).resolve().parent.parent
    base = skill_base / "systems" / system / "data"
    if filename:
        return base / filename
    return base


# ── CLI passthrough ───────────────────────────────────────────────────────
# Useful from shell for procedural commands (e.g. /gm load migration check).
if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "campaign-system-version":
        default = sys.argv[3] if len(sys.argv) >= 4 else ""
        print(campaign_system_version(sys.argv[2], default=default))
        sys.exit(0)
    if len(sys.argv) >= 3 and sys.argv[1] == "system-data-path":
        system = sys.argv[2]
        version = sys.argv[3] if len(sys.argv) >= 4 else ""
        filename = sys.argv[4] if len(sys.argv) >= 5 else ""
        print(system_data_path(system, version, filename))
        sys.exit(0)
    print(
        "usage:\n"
        "  python3 paths.py campaign-system-version <campaign-name> [default]\n"
        "  python3 paths.py system-data-path <system> [version] [filename]",
        file=sys.stderr,
    )
    sys.exit(2)
