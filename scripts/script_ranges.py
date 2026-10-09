r"""Whole-word matching that works in the scripts a campaign is actually played in.

WHY THIS EXISTS
---------------
`\b` and `(?<!\w)` / `(?!\w)` are the right guard for a Latin name: they stop
"Sera" matching inside "Seraphim". They are an IMPOSSIBLE condition for a
Chinese, Japanese, Korean or Thai one.

Python's `\w` counts Han, Kana, Hangul and Thai as word characters, and those
scripts put no space or punctuation between a word and the text around it, so
the character before the name is always a word character and the lookbehind can
never be satisfied. Measured against the anchored pattern this module replaces,
which matched in en, fr, ru and uk and in NONE of zh, ja, ko, th:

    你看到哥布林首領走過來。      哥 is preceded by 到      -> no match
    あなたは田中さんを見る。      田 is preceded by は      -> no match
    당신은 문지기를 봅니다.       문지기 is followed by 를   -> no match
    คุณเห็นผู้เฝ้าประตูเดินมา    no delimiters at all      -> no match

Korean is the case that shows this is not merely about spacing. Korean DOES
space its words, so its LEADING anchor holds; its particles agglutinate onto
the noun with no space, so the TRAILING one fails. Each edge is therefore
decided independently rather than both-or-neither.

WHY THERE IS A LENGTH GATE
--------------------------
Dropping the anchor is not safe at any length. A single Han character is a
morpheme, not a name -- 王 occurs inside ordinary words like 王國 ("kingdom") --
so a one-character match keeps both anchors. Two or more characters is where a
run stops being something ordinary prose reuses.

The asymmetry is deliberate: under-matching leaves a stale name, which is
visible and recoverable, while over-matching rewrites the player's transcript,
which is not.

Latin, Cyrillic and Greek are bit-for-bit unaffected -- they always keep both
anchors.
"""
from __future__ import annotations

import re

#: Scripts written WITHOUT word delimiters.
#:
#: Ranges: CJK Unified Ideographs + Extension A, Hiragana, Katakana, Hangul
#: (Jamo, Compatibility Jamo, Syllables), Thai.
NO_DELIMITER_SCRIPT = re.compile(
    r"[㐀-䶿一-鿿぀-ゟ゠-ヿ"
    r"ᄀ-ᇿ㄰-㆏가-힯฀-๿]"
)

#: Below this many characters, a no-delimiter match keeps its anchors. See
#: "WHY THERE IS A LENGTH GATE" above.
MIN_UNANCHORED_LEN = 2


def needs_anchors(text: str) -> bool:
    """Whether a whole-word pattern for `text` should carry word-boundary anchors.

    False only for a run of two or more characters in a script that has no word
    delimiters, where the anchors could never match anyway.
    """
    if len(text.strip()) < MIN_UNANCHORED_LEN:
        return True
    return not NO_DELIMITER_SCRIPT.search(text)


def whole_word_pattern(text: str, *, flags: int = 0) -> re.Pattern[str]:
    """Compile a whole-word pattern for `text`, anchored where anchoring works.

    Multi-word input is joined with a flexible whitespace pattern, so
    'Aldric  Voss' (double space) still matches 'Aldric Voss'.
    """
    parts = [re.escape(p) for p in text.strip().split()]
    if not parts:
        raise ValueError("whole_word_pattern() needs a non-empty string")
    body = r"\s+".join(parts)
    if needs_anchors(text):
        body = rf"(?<!\w){body}(?!\w)"
    return re.compile(body, flags)
