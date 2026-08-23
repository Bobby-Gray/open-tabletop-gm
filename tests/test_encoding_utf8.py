"""Campaign text must survive a non-UTF-8 default encoding.

WHY (#36)
=========

A Russian-language user reported their in-world date rendering as

    18 РЎРµСЂРїР°РЅСЊ, 412 РѕС‚ РџР°РґРµРЅРёСЏ РЎРІРѕРґРѕРІ

instead of

    18 Серпань, 412 от Падения Сводов

That is the signature of UTF-8 bytes decoded as cp1251, the Windows ANSI code
page for Russian. Python's `open()` uses the locale encoding when none is
given, so on any non-English Windows install every bare `open()` in the tree
was a corruption site. The same bug arrives as GBK/cp936 for Chinese users,
which is what two separate contributors reported against the sibling repo.

It never fails on the developer's machine, because macOS and Linux default to
UTF-8 and the bug is invisible there. So it needs a detector that does not
depend on the platform the tests happen to run on.

TWO DETECTORS, BECAUSE NEITHER IS ENOUGH ALONE
==============================================

1. `-X warn_default_encoding` is Python's own mechanism for this. It fires an
   EncodingWarning on any text-mode open that relied on the default, and it
   catches `read_text`/`write_text` too, which a regex over the source does
   not. But it only sees code that actually RUNS.
2. A static sweep of the tree catches the paths a test never executes, which is
   most of them.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: The reporter's own text (#36), so a regression reproduces their bug and not
#: a synthetic stand-in.
RU_MONTHS = "Стужень,Лютень,Березень,Цветень,Травень,Червень,Серпань,Вересень"
RU_DATE = "18 Серпань 412"          # parser wants "<day> <month> <year>"

def _bare_open_sites() -> list[str]:
    """Real `open(...)` call nodes with no `encoding=` and a text-mode.

    Parsed, not grepped. A regex over the source matches the word open( inside
    docstrings and comments — including this file's own — and a guard that
    fails on its own prose is a guard nobody keeps.
    """
    out: list[str] = []
    for p in sorted(ROOT.rglob("*.py")):
        if ".git" in p.parts or "probe" in p.parts:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:                     # not ours to police
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not (isinstance(fn, ast.Name) and fn.id == "open"):
                continue
            if any(k.arg == "encoding" for k in node.keywords):
                continue
            mode = ""
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = str(node.args[1].value)
            for k in node.keywords:
                if k.arg == "mode" and isinstance(k.value, ast.Constant):
                    mode = str(k.value.value)
            if "b" in mode:                     # binary has no encoding
                continue
            out.append(f"{p.relative_to(ROOT)}:{node.lineno}")
    return out


def test_no_bare_text_mode_open_anywhere():
    """The static half. 67 of these existed before #36 was fixed."""
    sites = _bare_open_sites()
    assert not sites, (
        "text-mode open() without encoding='utf-8' — these corrupt campaign "
        "text on a non-English Windows install:\n  " + "\n  ".join(sites)
    )


def test_a_russian_calendar_round_trips_with_the_default_encoding_armed():
    """The live half.

    Drives calendar.py the way the skill does, with Python's default-encoding
    warning promoted to an error. Any bare open() left on this path raises
    rather than quietly returning mojibake.
    """
    root = Path(tempfile.mkdtemp())
    env = {
        "GM_CAMPAIGN_ROOT": str(root),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(root),
    }
    cal = ROOT / "scripts" / "calendar.py"
    base = [sys.executable, "-X", "warn_default_encoding",
            "-W", "error::EncodingWarning", str(cal), "-c", "russian-test"]

    init = subprocess.run(
        base + ["init", "--date", RU_DATE, "--time", "morning",
                "--months", RU_MONTHS, "--month-length", "30"],
        capture_output=True, text=True, env=env,
    )
    assert init.returncode == 0, f"init failed:\n{init.stdout}\n{init.stderr}"
    assert "EncodingWarning" not in init.stderr, init.stderr

    now = subprocess.run(base + ["now"], capture_output=True, text=True, env=env)
    assert now.returncode == 0, f"now failed:\n{now.stdout}\n{now.stderr}"
    assert "EncodingWarning" not in now.stderr, now.stderr

    # The month name comes back intact, not as cp1251 mojibake.
    assert "Серпань" in now.stdout, f"expected Cyrillic, got: {now.stdout!r}"
    assert "Р" * 2 not in now.stdout, f"mojibake signature present: {now.stdout!r}"

    # And it is stored as UTF-8 on disk, readable as UTF-8.
    written = json.loads(
        (root / "campaigns" / "russian-test" / "calendar.json").read_text(encoding="utf-8")
    )
    assert any("Серпань" in str(v) for v in written.values()), written


def test_the_launcher_forces_utf8_mode():
    """encoding= on every call site fixes the calls that exist today.
    PYTHONUTF8 fixes open()'s DEFAULT, so it also covers the next one somebody
    writes, plus any dependency doing its own IO."""
    sh = (ROOT / "display" / "start-display.sh").read_text(encoding="utf-8")
    assert "PYTHONUTF8=1" in sh
    assert "PYTHONIOENCODING=utf-8" in sh


def test_shared_paths_module_forces_utf8_streams():
    """Reading files correctly is half of it. Printing them to a cp1251 or GBK
    console raises UnicodeEncodeError on the first non-ASCII character."""
    src = (ROOT / "scripts" / "paths.py").read_text(encoding="utf-8")
    assert "reconfigure" in src and 'encoding="utf-8"' in src
