#!/usr/bin/env python3
"""Pure-python autorun wait — TCC-safe replacement for autorun-wait.sh.

macOS TCC blocks shell-level file creation under ~/Documents, but python file
writes are permitted. autorun-wait.sh fails on its `echo > .autorun-wait.pid`
redirect when the OTGM repo lives there; this script does the identical job
(session-invalidation, countdown broadcast, input-queue poll, /queue/consumed
POST) using python I/O only.

Prints the queued player action(s) to stdout, or nothing on timeout (9 min).

Usage (from SKILL.md autorun bash block):
    AUTORUN=$(python3 <skill-base>/display/autorun_wait.py)
"""
import json
import os
import secrets
import ssl
import subprocess
import sys
import time
import urllib.request

DISPLAY_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(DISPLAY_DIR, "..", "scripts"))
PUSH = os.path.join(DISPLAY_DIR, "push_stats.py")

try:
    from paths import find_campaign
except Exception:
    find_campaign = None

QFILE = os.path.join(DISPLAY_DIR, ".input_queue")
SESSION_FILE = os.path.join(DISPLAY_DIR, ".autorun-session")
CAMP_FILE = os.path.join(DISPLAY_DIR, ".campaign")
TOKEN_FILE = os.path.join(DISPLAY_DIR, ".token")
SCHEME_FILE = os.path.join(DISPLAY_DIR, ".scheme")

# Invalidate any previous wait loop by writing a new session id (python write — TCC-ok)
my_session = secrets.token_hex(8)
with open(SESSION_FILE, "w") as f:
    f.write(my_session)

# Resolve autorun interval from the active campaign's state.md (default 60s)
interval = 60
if find_campaign is not None:
    try:
        import re
        camp = open(CAMP_FILE).read().strip()
        txt = (find_campaign(camp) / "state.md").read_text(errors="replace")
        m = re.search(r"autorun_interval:\s*(\d+)", txt)
        if m:
            interval = int(m.group(1))
    except Exception:
        pass

subprocess.run(
    [sys.executable, PUSH, "--autorun-waiting", "true", "--autorun-cycle", str(interval)],
    capture_output=True,
)


def _print_entries(entries):
    out = []
    for entry in entries:
        char = entry.get("character", "Player")
        text = (entry.get("text") or "").strip()
        if text:
            out.append(f"[{char}]: {text}")
    return "\n".join(out)


# Poll loop — exit when queue appears, session changes, or 9 minutes pass
content = ""
for _ in range(1800):  # 0.3s * 1800 = 9 min
    if os.path.exists(QFILE):
        try:
            raw = open(QFILE).read()
            os.unlink(QFILE)
        except Exception:
            raw = ""
        if raw:
            try:
                entries = json.loads(raw)
                content = _print_entries(entries) if isinstance(entries, list) else raw
            except Exception:
                content = raw
        break
    try:
        if open(SESSION_FILE).read().strip() != my_session:
            break
    except Exception:
        break
    time.sleep(0.3)

# Clean up our session file if it's still ours
try:
    if open(SESSION_FILE).read().strip() == my_session:
        os.unlink(SESSION_FILE)
except Exception:
    pass

subprocess.run([sys.executable, PUSH, "--autorun-waiting", "false"], capture_output=True)

# Clear the display queue indicator on success
if content:
    try:
        scheme = open(SCHEME_FILE).read().strip() if os.path.exists(SCHEME_FILE) else "http"
        token = open(TOKEN_FILE).read().strip() if os.path.exists(TOKEN_FILE) else ""
        ctx = None
        if scheme == "https":
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            f"{scheme}://localhost:5001/queue/consumed",
            data=b"", method="POST",
            headers={"X-DND-Token": token},
        )
        urllib.request.urlopen(req, timeout=1, context=ctx)
    except Exception:
        pass

sys.stdout.write(content)
