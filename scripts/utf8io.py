"""utf8io.py — text reads that never silently corrupt a campaign.

WHY THIS EXISTS
---------------
Python's `open()` and `Path.read_text()` fall back to the locale encoding when
none is given. That is UTF-8 on most Linux and macOS setups and cp1251 (Russian),
cp936/GBK (Chinese) or cp932 (Japanese) on Windows, so the same file round-trips
cleanly for most contributors and corrupts for others. Pinning
`encoding="utf-8"` at every call site fixes the writing side and the reading of
anything written after the sweep.

It does not fix the file a pre-sweep install already wrote in a legacy codepage.
Reading that file as UTF-8 with `errors="replace"` turns every non-ASCII
character into U+FFFD, and writing the result back makes the loss permanent —
the campaign text is then gone, not mis-displayed. `read_text()` below never
produces that outcome.

WHAT IT DOES
------------
  * valid UTF-8 (everything the tree writes) decodes as-is;
  * otherwise the system's legacy codepage is tried, and accepted only if the
    text re-encodes to the exact original bytes, so a read-modify-write becomes
    a one-time migration to UTF-8 rather than a guess;
  * anything else raises TextDecodeError, so a caller refuses loudly instead of
    flattening someone's campaign.

AN HONEST LIMIT
---------------
The round-trip check is strong evidence for a multi-byte codepage like GBK,
where most byte sequences are simply not decodable. It proves much less for a
single-byte codepage like cp1251, where nearly every byte sequence decodes AND
round-trips by construction. So for those the fallback is a *migration path*,
not *detection*: it recovers a legacy file readably, but it cannot tell you the
file was genuinely cp1251 rather than some other single-byte encoding. UTF-8 is
always tried first precisely because it is the one that can be proven.
"""
import locale
import pathlib


class TextDecodeError(ValueError):
    """Raised when a file is neither valid UTF-8 nor losslessly legacy-decodable."""


def legacy_encoding() -> str:
    """The codepage a pre-sweep install on THIS machine would have written.

    Returns an empty string when the locale is already UTF-8, which is the
    common case and means there is no legacy fallback to try.
    """
    try:
        enc = locale.getpreferredencoding(False) or ""
    except Exception:
        return ""
    return "" if "utf" in enc.lower().replace("-", "") else enc


def read_text(path) -> str:
    """Read `path` as text without ever producing U+FFFD replacement characters.

    Raises TextDecodeError (a ValueError) when the bytes are neither valid
    UTF-8 nor a lossless round-trip through the system's legacy codepage.
    """
    path = pathlib.Path(path)
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass

    legacy = legacy_encoding()
    if not legacy:
        raise TextDecodeError(
            f"{path}: not valid UTF-8, and this machine has no legacy codepage "
            "to fall back to — refusing to read"
        ) from None
    try:
        text = raw.decode(legacy)
    except (UnicodeDecodeError, LookupError):
        raise TextDecodeError(
            f"{path}: not valid UTF-8 or {legacy} — refusing to read"
        ) from None
    try:
        round_trips = text.encode(legacy) == raw
    except UnicodeEncodeError:
        round_trips = False
    if not round_trips:
        raise TextDecodeError(
            f"{path}: bytes decode as {legacy} but do not round-trip — "
            "refusing to read"
        ) from None
    return text
