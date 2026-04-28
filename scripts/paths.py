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
