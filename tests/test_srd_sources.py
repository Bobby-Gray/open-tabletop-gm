"""The SRD dataset builder must fetch from a path that still exists.

WHY
===
`5e-bits/5e-database` added a language directory — `src/2014/en/` rather than
`src/2014/` — and every configured source URL began returning 404. Because the
generated dataset is gitignored, an existing checkout kept working off data it
had built earlier, and the breakage only reached someone cloning fresh.

The failure was also soft: a fetch error printed to stderr and became an empty
list, the build carried on, wrote a dataset containing nothing, and exited 0.
So the two things worth guarding are the path shape and the refusal.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import unittest
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "systems" / "dnd5e" / "build_srd.py"


def _const(name: str):
    """Read a module-level string constant without importing (no network)."""
    tree = ast.parse(BUILD.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    if isinstance(node.value, ast.Constant):
                        return node.value.value
    raise AssertionError(f"{name} not found in {BUILD}")


def _files() -> dict:
    tree = ast.parse(BUILD.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "BITS_FILES":
                    return ast.literal_eval(node.value)
    raise AssertionError("BITS_FILES not found")


class SrdSourceShapeTests(unittest.TestCase):
    """Always run. No network."""

    def test_the_source_base_carries_a_language_segment(self):
        base = _const("RAW_5EBITS")
        tail = base.rstrip("/").rsplit("/", 2)[-2:]
        self.assertEqual(
            len(tail[-1]), 2,
            f"RAW_5EBITS is {base!r} — upstream nests by language "
            "(src/<ruleset>/<lang>/), so a path ending at the ruleset 404s",
        )

    def test_a_failed_fetch_is_not_an_empty_category(self):
        """`SourceUnavailable` must exist and be raised, not swallowed.

        If a fetch failure can turn into `[]`, the build writes an empty
        dataset over a good one and reports success — which is how this broke
        without anyone noticing.
        """
        src = BUILD.read_text(encoding="utf-8")
        self.assertIn("class SourceUnavailable", src)
        self.assertIn("raise SourceUnavailable", src)
        self.assertIn(
            "refusing to overwrite", src,
            "the builder must refuse to write a dataset whose categories all "
            "came back empty",
        )


@unittest.skipUnless(
    os.environ.get("OTGM_NETWORK_TESTS") == "1",
    "network test — set OTGM_NETWORK_TESTS=1 to run",
)
class SrdSourceLiveTests(unittest.TestCase):
    """Opt-in. Proves the configured URLs actually resolve TODAY.

    Kept out of the default run because a green suite should not depend on
    GitHub being reachable. Worth running before a release: it is the only
    check that catches upstream moving the files again.
    """

    def test_every_configured_source_responds(self):
        base = _const("RAW_5EBITS")
        for key, filename in _files().items():
            url = f"{base}/{filename}"
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "otgm-tests/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.assertEqual(resp.status, 200, f"{key}: {url}")


if __name__ == "__main__":
    unittest.main()
