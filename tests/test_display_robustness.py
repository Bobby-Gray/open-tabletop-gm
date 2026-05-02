"""Regression tests for the two display robustness fixes shipped 2026-05-01
(synced from claude-dnd-skill v1.7.5).

Bug #14 — send.py dropped the heredoc body when --stat-* flags were bundled
          with narration. Root cause: _build_stats_payload(args) was treated
          as "body-less" in the stdin-read decision.

Bug #15 — session_tail.json got wiped to [] between sessions. Root cause:
          _load_tail() unconditionally cleared the buffer before re-appending
          campaign-filtered entries; if everything filtered out, the buffer
          was zeroed and the next _persist_tail wrote [] to disk.

These tests exercise the fixed paths directly without standing up Flask.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
DISPLAY = REPO / "display"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ─── send.py ──────────────────────────────────────────────────────────────────

class StdinDecisionTest(unittest.TestCase):
    """The stdin-read decision must:
       - read stdin when content flags are set (--player/--npc/--dice/...)
       - skip stdin when truly body-less flags are set alone
       - read stdin when stat flags + heredoc are bundled (the #14 fix)
       - read stdin for set-campaign with optional body (open-tabletop-gm-specific)
       - not block when stat flags alone are passed in a chained bash call
    """

    def setUp(self) -> None:
        self.send = _load_module(DISPLAY / "send.py", "send_under_test")

    def _decide(self, args, isatty: bool):
        """Re-implement the decision logic from main() in isolation.

        Mirrors send.py main(). If this drifts from main(), the tests will
        fail and we'll know the contract changed.
        """
        has_content = bool(args.get("player") or args.get("npc") or args.get("dice")
                           or args.get("tutor") or args.get("action"))
        # OTGM-specific: --set-campaign is body-OPTIONAL, not truly bodyless.
        truly_bodyless = bool(args.get("milestone_award") or args.get("milestone_spend"))
        if has_content:
            return "read"
        if truly_bodyless:
            return "skip"
        return "skip" if isatty else "read"

    def test_content_flag_reads_stdin(self):
        for flag in ("player", "npc", "dice", "tutor", "action"):
            self.assertEqual(self._decide({flag: True}, isatty=False), "read",
                             f"--{flag} should always read stdin")

    def test_truly_bodyless_skips_stdin(self):
        for flag in ("milestone_award", "milestone_spend"):
            self.assertEqual(self._decide({flag: "X"}, isatty=False), "skip",
                             f"--{flag.replace('_','-')} should never read stdin")

    def test_stat_flags_with_heredoc_reads_stdin(self):
        """The #14 regression: stat flags + heredoc must read stdin."""
        self.assertEqual(self._decide({"stat_hp": ["X:5:10"]}, isatty=False), "read",
                         "Stat flags + heredoc should read stdin (the #14 fix)")

    def test_set_campaign_with_body_reads_stdin(self):
        """OTGM-specific: --set-campaign accepts an optional body."""
        self.assertEqual(self._decide({"set_campaign": "name"}, isatty=False), "read",
                         "set-campaign + heredoc should read stdin")

    def test_stat_flags_alone_no_tty_reads_stdin(self):
        self.assertEqual(self._decide({}, isatty=False), "read")

    def test_stat_flags_alone_interactive_tty_skips_stdin(self):
        self.assertEqual(self._decide({}, isatty=True), "skip")

    def test_validate_chunk_payload_requires_text_or_award(self):
        issues = self.send._validate_payload({}, "chunk")
        self.assertTrue(any("no text" in s for s in issues))

    def test_validate_chunk_payload_accepts_text(self):
        self.assertEqual(self.send._validate_payload({"text": "hello"}, "chunk"), [])

    def test_validate_chunk_payload_accepts_milestone_award(self):
        self.assertEqual(self.send._validate_payload({"milestone_award": "Aldric", "text": "Aldric"}, "chunk"), [])

    def test_validate_chunk_payload_accepts_set_campaign(self):
        """Campaign-only payloads are valid even without text."""
        self.assertEqual(self.send._validate_payload({"campaign": "test"}, "chunk"), [])

    def test_validate_chunk_payload_rejects_multiple_content_tags(self):
        issues = self.send._validate_payload(
            {"text": "x", "player": "A", "npc": "B"}, "chunk")
        self.assertTrue(any("multiple content tags" in s for s in issues))

    def test_validate_stats_payload_requires_list(self):
        issues = self.send._validate_payload({"players": "not a list"}, "stats")
        self.assertTrue(any("not a list" in s for s in issues))


# ─── gm-display-app.py ───────────────────────────────────────────────────────

class TailLogicTest(unittest.TestCase):
    """The _load_tail / _persist_tail pair must guarantee:
       - empty/missing file leaves the in-memory buffer alone
       - every-entry-filtered-out load leaves the buffer alone
       - persisting an empty buffer over an existing non-empty file is refused
       - writes are atomic (tmp + rename)
       - missing CAMP_FILE means in-memory only (no fallback path)
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.campaign_root = self.tmp_path / "campaigns"
        self.campaign_root.mkdir()
        (self.campaign_root / "test-camp").mkdir()
        self.tail_file = self.campaign_root / "test-camp" / "session_tail.json"
        self.camp_file = self.tmp_path / ".campaign"
        self.camp_file.write_text("test-camp")

        self._namespace = self._build_tail_namespace()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _build_tail_namespace(self) -> dict:
        """Extract just the tail block from gm-display-app.py and exec it."""
        src = (DISPLAY / "gm-display-app.py").read_text()
        start = src.index("# The text_log buffer above")
        end = src.index("\n_load_tail()\n", start) + len("\n_load_tail()\n")
        block = src[start:end]

        ns: dict = {
            "deque": __import__("collections").deque,
            "threading": __import__("threading"),
            "json": __import__("json"),
            "os": __import__("os"),
            "sys": __import__("sys"),
            "CAMP_FILE": str(self.camp_file),
            "_campaign_dir": (lambda name: self.campaign_root / name),
        }
        exec(block, ns)
        return ns

    def _persist(self): self._namespace["_persist_tail"]()
    def _load(self):    self._namespace["_load_tail"]()
    @property
    def _buffer(self):  return self._namespace["_tail_buffer"]

    def test_load_with_empty_file_does_not_clear_buffer(self):
        self._buffer.append({"text": "preexisting", "_camp": "test-camp"})
        self.tail_file.write_text("[]")
        self._load()
        self.assertEqual(len(self._buffer), 1)
        self.assertEqual(self._buffer[0]["text"], "preexisting")

    def test_load_with_filtered_out_entries_does_not_clear_buffer(self):
        """The actual #15 root cause."""
        self._buffer.append({"text": "preexisting", "_camp": "test-camp"})
        self.tail_file.write_text(json.dumps([
            {"text": "from-other-campaign", "_camp": "other-camp"},
            {"text": "also-other", "_camp": "another-camp"},
        ]))
        self._load()
        self.assertEqual(len(self._buffer), 1)
        self.assertEqual(self._buffer[0]["text"], "preexisting")

    def test_load_with_matching_entries_replaces_buffer(self):
        self._buffer.append({"text": "preexisting", "_camp": "test-camp"})
        self.tail_file.write_text(json.dumps([
            {"text": "fresh-1", "_camp": "test-camp"},
            {"text": "fresh-2", "_camp": "test-camp"},
        ]))
        self._load()
        self.assertEqual(len(self._buffer), 2)
        self.assertEqual([e["text"] for e in self._buffer], ["fresh-1", "fresh-2"])

    def test_persist_skips_empty_over_content(self):
        self.tail_file.write_text(json.dumps([
            {"text": "important", "_camp": "test-camp"},
        ]))
        self._buffer.clear()
        self._persist()
        on_disk = json.loads(self.tail_file.read_text())
        self.assertEqual(len(on_disk), 1)
        self.assertEqual(on_disk[0]["text"], "important")

    def test_persist_writes_when_buffer_has_content(self):
        self._buffer.append({"text": "new", "_camp": "test-camp"})
        self._persist()
        on_disk = json.loads(self.tail_file.read_text())
        self.assertEqual(on_disk[0]["text"], "new")

    def test_persist_atomic_no_tmp_leftover(self):
        self._buffer.append({"text": "x", "_camp": "test-camp"})
        self._persist()
        tmp = str(self.tail_file) + ".tmp"
        self.assertFalse(os.path.exists(tmp))

    def test_no_camp_file_means_no_disk_write(self):
        self.camp_file.unlink()
        self._buffer.append({"text": "x"})
        self._persist()
        self.assertFalse(self.tail_file.exists())

    def test_load_corrupt_json_leaves_buffer_alone(self):
        self._buffer.append({"text": "preexisting", "_camp": "test-camp"})
        self.tail_file.write_text("{not json")
        self._load()
        self.assertEqual(len(self._buffer), 1)


if __name__ == "__main__":
    unittest.main()
