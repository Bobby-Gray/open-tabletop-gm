"""Every icon the display asks for must exist, and something must serve them.

WHY (#37)
=========

`open-tabletop-gm` was forked from `claude-dnd-skill`, and the fork carried the
templates but not `display/icons/` nor the Flask route that serves it. The
result was a 404 on every icon in the UI:

    127.0.0.1 - - [22/Aug/2026 19:52:47] "GET /icons/logo_primary_fullcolor.png HTTP/1.1" 404 -

Nothing anywhere failed. Flask returns 404 for an unrouted path, the browser
renders a blank box for a broken <img>, and the server keeps serving. The only
detector was a user looking at the screen and saying the icons were missing.

So this file is the detector: it reads the icon names out of the template the
same way the browser does — static `/icons/x.png` hrefs, plus the three tables
the JS builds names from at runtime — and asserts each one is a real file.
A dynamic name is exactly the kind that survives review, because grepping for
its literal path finds nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

DISPLAY = Path(__file__).resolve().parents[1] / "display"
TEMPLATE = DISPLAY / "templates" / "index.html"
ICONS = DISPLAY / "icons"
APP = DISPLAY / "gm-display-app.py"

HTML = TEMPLATE.read_text(encoding="utf-8")


def _static_refs() -> set[str]:
    """`href="/icons/app_icon_32.png"`, `src="/icons/focus.png"`, ..."""
    return set(re.findall(r"/icons/([A-Za-z0-9_\-]+\.(?:png|ico))", HTML))


def _runtime_refs() -> set[str]:
    """Names the JS assembles at runtime, which no grep for a path would find.

    Three tables:
      _CLASS_ICONS   {barbarian: 'class_barbarian', ...} -> '/icons/'+file+'.png'
      _BLOCK_BADGES  [{icon: 'attack', ...}, ...]        -> '/icons/'+icon+'.png'
      _diceRollIcon  return 'dragon' | 'spellbook' | ... -> '/icons/'+name+'.png'
    """
    names: set[str] = set()

    cls = re.search(r"_CLASS_ICONS\s*=\s*\{(.*?)\}", HTML, re.S)
    assert cls, "_CLASS_ICONS table not found — did the template change shape?"
    names |= {f"{m}.png" for m in re.findall(r"'(class_[a-z_]+)'", cls.group(1))}

    badges = re.search(r"_BLOCK_BADGES\s*=\s*\[(.*?)\n\];", HTML, re.S)
    assert badges, "_BLOCK_BADGES table not found"
    names |= {f"{m}.png" for m in re.findall(r"icon:\s*'([a-z_]+)'", badges.group(1))}

    dice = re.search(r"function _diceRollIcon\(.*?\n\}", HTML, re.S)
    assert dice, "_diceRollIcon not found"
    names |= {f"{m}.png" for m in re.findall(r"return\s+'([a-z_]+)';", dice.group(0))}

    return names


def test_the_icons_directory_ships():
    assert ICONS.is_dir(), f"{ICONS} is missing — the fork did not carry it"
    assert list(ICONS.glob("*.png")), "icons directory is empty"


def test_every_icon_the_template_asks_for_exists():
    wanted = _static_refs() | _runtime_refs()
    assert wanted, "extracted no icon names at all — this test has stopped testing"
    missing = sorted(n for n in wanted if not (ICONS / n).is_file())
    assert not missing, f"template references icons that do not exist: {missing}"


def test_the_app_serves_the_icons_prefix():
    """The files existing is half of it. #37 was the other half."""
    src = APP.read_text(encoding="utf-8")
    assert '@app.route("/icons/<path:filename>")' in src, \
        "no /icons route — every icon 404s however many files ship"
    assert "send_from_directory" in src


def test_the_favicon_is_served_too():
    src = APP.read_text(encoding="utf-8")
    assert '@app.route("/favicon.ico")' in src
    assert (ICONS / "favicon.ico").is_file()
