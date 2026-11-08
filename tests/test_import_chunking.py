"""An imported module keeps its line structure, in every script.

WHY
===
import_campaign.py chunked a source with `text.split()` and handed each chunk
back as `" ".join(words)`. Two kinds of damage followed:

  * Every newline was lost. Headings, tables, stat blocks and read-aloud boxes
    arrived as one run-on line, so the GM mapping a module into campaign files
    could not tell a chapter title from the paragraph after it.
  * A script written without spaces has one "word" per paragraph. A Chinese or
    Japanese module came out as a single chunk however long it was, so the
    `--chunk N` paging that exists for large sources did nothing for it.

Chunks are now measured in characters and cut on line ends, verbatim.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "import_campaign.py"
_spec = importlib.util.spec_from_file_location("import_campaign_under_test", SCRIPT)
imp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imp)

MODULE_MD = """# Chapter 1: The Sunken Road

| Roll | Encounter |
|------|-----------|
| 1-2  | 2 wolves  |
| 3-6  | a merchant |

> Read aloud: the road dips beneath black water.

## Area 1 — The Ford
"""


class StructureTests(unittest.TestCase):

    def test_line_structure_survives_chunking(self):
        chunk = imp.chunk_text(MODULE_MD, 0)
        self.assertEqual(chunk, MODULE_MD)
        self.assertIn("\n| 1-2  | 2 wolves  |\n", chunk)

    def test_chunks_reassemble_to_the_source_exactly(self):
        text = (MODULE_MD * 400)
        chunks = imp.split_chunks(text)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)
        for c in chunks:
            self.assertLessEqual(len(c), imp.CHUNK_CHARS)

    def test_cuts_fall_on_line_ends(self):
        text = MODULE_MD * 400
        for c in imp.split_chunks(text)[:-1]:
            self.assertTrue(c.endswith("\n"), "a chunk ended mid-line")


class NoSpaceScriptTests(unittest.TestCase):

    def test_a_cjk_module_is_paged_like_any_other(self):
        para = "洞窟の奥で古い祭壇が青く光った。" * 2500          # ~40,000 chars, no spaces
        text = "# 第一章 沈んだ道\n\n" + para + "\n\n## 第二節\n"
        self.assertGreater(imp.total_chunks(text), 1,
                           "a whole Japanese module came back as one chunk")
        chunks = imp.split_chunks(text)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(chunks[0].startswith("# 第一章 沈んだ道\n\n"))
        for c in chunks:
            self.assertLessEqual(len(c), imp.CHUNK_CHARS)


class CliTests(unittest.TestCase):

    def test_chunk_flag_prints_verbatim(self):
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "mod.md"
            p.write_text(MODULE_MD, encoding="utf-8")
            # No PYTHONIOENCODING: under the non-UTF-8 CI job this is the
            # console a Windows code page gives, and the em-dash in the module
            # used to raise UnicodeEncodeError on the way out.
            env = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
            r = subprocess.run([sys.executable, str(SCRIPT), str(p), "--chunk", "0"],
                               capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, MODULE_MD)
            r = subprocess.run([sys.executable, str(SCRIPT), str(p), "--chunk", "5"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
