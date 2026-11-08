"""Synthesized narration is cached on disk, keyed so it can never serve a stale clip.

WHY
===
Every press of a speaker button was a new Gemini call, including a replay of
the same block and a second device playing the block the first device had just
played — paying again for audio the server had already received. The docs
said as much ("no server-side caching by content hash").

The cache key covers the model, the voice and the exact text, so changing any
of them is a miss; the directory is bounded and evicts least-recently-used
clips; GM_TTS_CACHE_MB=0 turns it off.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DISPLAY = ROOT / "display"


def _load_tts():
    spec = importlib.util.spec_from_file_location("tts_under_test", DISPLAY / "tts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CacheEnv(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self._saved = {k: os.environ.get(k) for k in ("GM_TTS_CACHE_DIR", "GM_TTS_CACHE_MB")}
        os.environ["GM_TTS_CACHE_DIR"] = self._d.name
        os.environ.pop("GM_TTS_CACHE_MB", None)
        self.tts = _load_tts()
        self.calls = []

        def fake(text, voice="Enceladus", timeout=30.0):
            self.calls.append((text, voice))
            return f"pcm:{voice}:{text}".encode("utf-8")
        self.tts.synthesize_strict = fake

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._d.cleanup()


class CacheTests(CacheEnv):

    def test_a_repeat_is_served_from_disk(self):
        a, hit_a = self.tts.synthesize_cached("The door creaks.", "Kore")
        b, hit_b = self.tts.synthesize_cached("The door creaks.", "Kore")
        self.assertEqual(a, b)
        self.assertEqual((hit_a, hit_b), (False, True))
        self.assertEqual(len(self.calls), 1)

    def test_voice_text_and_model_are_all_in_the_key(self):
        k = self.tts.cache_key
        self.assertNotEqual(k("x", "Kore"), k("x", "Charon"))
        self.assertNotEqual(k("x", "Kore"), k("y", "Kore"))
        self.assertNotEqual(k("x", "Kore", "model-a"), k("x", "Kore", "model-b"))
        self.tts.synthesize_cached("x", "Kore")
        self.tts.synthesize_cached("x", "Charon")
        self.assertEqual(len(self.calls), 2, "a different voice was served the cached clip")

    def test_the_cache_is_bounded_and_evicts_the_oldest(self):
        os.environ["GM_TTS_CACHE_MB"] = str(2500 / (1024 * 1024))   # ~2,500 bytes
        big = "x" * 1000
        self.tts.synthesize_cached(big + "1", "Kore")
        old = next(pathlib.Path(self._d.name).glob("*.pcm"))
        past = time.time() - 100
        os.utime(old, (past, past))
        self.tts.synthesize_cached(big + "2", "Kore")
        self.tts.synthesize_cached(big + "3", "Kore")
        clips = list(pathlib.Path(self._d.name).glob("*.pcm"))
        total = sum(p.stat().st_size for p in clips)
        self.assertLessEqual(total, 2500)
        self.assertFalse(old.exists(), "the least recently used clip should go first")

    def test_zero_disables_the_cache(self):
        os.environ["GM_TTS_CACHE_MB"] = "0"
        self.tts.synthesize_cached("again", "Kore")
        self.tts.synthesize_cached("again", "Kore")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(list(pathlib.Path(self._d.name).glob("*")), [])

    def test_no_partial_files_are_left(self):
        self.tts.synthesize_cached("clip", "Kore")
        names = [p.name for p in pathlib.Path(self._d.name).iterdir()]
        self.assertTrue(all(n.endswith(".pcm") for n in names), names)


class RouteTests(CacheEnv):
    """Drive POST /tts through Flask with the synthesis call stubbed."""

    def setUp(self):
        super().setUp()
        spec = importlib.util.spec_from_file_location("gmapp_tts", DISPLAY / "gm-display-app.py")
        self.app = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(self.app)
        except Exception as exc:
            raise unittest.SkipTest(f"display app not importable: {exc}")
        self.app._tts = self.tts
        self.app._token_ok = lambda: True
        self.tts.key_source = lambda: "env:TEST"
        self.client = self.app.app.test_client()

    def test_second_request_is_a_hit(self):
        body = {"text": "The torch gutters.", "voice": "Kore"}
        r1 = self.client.post("/tts", json=body)
        r2 = self.client.post("/tts", json=body)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.headers["X-Audio-Cache"], "miss")
        self.assertEqual(r2.headers["X-Audio-Cache"], "hit")
        self.assertEqual(r1.data, r2.data)
        self.assertEqual(len(self.calls), 1)

    def test_no_key_is_still_503(self):
        """The browser fallback keys off 503; a cache must not mask it."""
        self.tts.key_source = lambda: "unset"
        r = self.client.post("/tts", json={"text": "x"})
        self.assertEqual(r.status_code, 503)


if __name__ == "__main__":
    unittest.main()
