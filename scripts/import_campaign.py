#!/usr/bin/env python3
"""
import_campaign.py — extract raw text from a campaign source file for /gm import.

Supported input formats:
  .pdf      — pdftotext (requires poppler) or PyMuPDF fallback
  .md       — read directly (plain markdown)
  .txt      — read directly
  .docx     — python-docx extraction

Usage:
  python3 import_campaign.py <filepath>            # print full extracted text
  python3 import_campaign.py <filepath> --info     # print file info + page/word count only
  python3 import_campaign.py <filepath> --chunk N  # print chunk N of ~24,000 characters (for large sources)
  python3 import_campaign.py <filepath> --chunks   # print total number of chunks

Output is UTF-8 plain text, written to stdout. The GM reads this and maps it to campaign files.
"""

import sys
import os
import argparse
import subprocess

# The extracted text goes to stdout, and a module in any non-Latin script
# raised UnicodeEncodeError on the first character under a non-UTF-8 console
# (a Windows code page, or LC_ALL=C). Same guard as scripts/paths.py; this
# script does not import it.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Chunks are measured in characters, not words, and cut on line boundaries.
# Splitting on whitespace and re-joining with single spaces did two kinds of
# damage: every newline in the source was lost, so headings, tables and stat
# blocks arrived as one run-on line; and a script written without spaces
# (Chinese, Japanese, Thai) is one "word" per paragraph, so a whole module
# came out as a single chunk. 24,000 characters is about the 4,000 English
# words the old chunk held.
CHUNK_CHARS = 24000


def extract_pdf(path: str) -> str:
    """Extract text from PDF using pdftotext (poppler). Falls back to PyMuPDF."""
    # Try pdftotext first (best quality)
    result = subprocess.run(
        ["pdftotext", "-layout", path, "-"],
        capture_output=True, text=True, timeout=60
    , encoding="utf-8")
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout

    # Fallback: try PyMuPDF if installed
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path, encoding="utf-8")
        return "\n\n".join(page.get_text() for page in doc)
    except ImportError:
        pass

    raise RuntimeError(
        "PDF extraction failed. Ensure poppler is installed: brew install poppler"
    )


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block (common in markdown files)."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].lstrip()
    return text


def extract_docx(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise RuntimeError(
            "python-docx not installed. Run: pip3 install python-docx"
        )


def extract(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        return extract_pdf(path)
    elif ext in (".md", ".txt", ".markdown"):
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        return strip_frontmatter(text)
    elif ext == ".docx":
        return extract_docx(path)
    else:
        # Unknown extension — try reading as plain text
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Cannot read {path}: {e}")


def word_count(text: str) -> int:
    return len(text.split())


def split_chunks(text: str, size: int = CHUNK_CHARS) -> list:
    """Split `text` into chunks of at most `size` characters, verbatim.

    Cuts fall on line ends, so headings and table rows stay whole and
    "".join(chunks) == text. Only a very long line (a paragraph in a script
    with no spaces, or a PDF that extracted without line breaks) is cut inside,
    after its last space before the limit, or at the limit when it has none.
    """
    chunks, cur = [], ""
    for line in text.splitlines(keepends=True):
        while len(cur) + len(line) > size and len(line) > size // 2:
            # An oversized line: fill the current chunk with as much of it as
            # fits, preferring to cut after a space.
            room = size - len(cur)
            cut = line.rfind(" ", 0, room)
            cut = room if cut < room // 2 else cut + 1
            chunks.append(cur + line[:cut])
            cur, line = "", line[cut:]
        if cur and len(cur) + len(line) > size:
            chunks.append(cur)
            cur = ""
        cur += line
    if cur:
        chunks.append(cur)
    return chunks or [""]


def chunk_text(text: str, chunk_index: int) -> str:
    """Return chunk N (0-indexed) of at most CHUNK_CHARS characters."""
    chunks = split_chunks(text)
    if chunk_index < 0 or chunk_index >= len(chunks):
        return ""
    return chunks[chunk_index]


def total_chunks(text: str) -> int:
    return max(1, len(split_chunks(text)))


def file_info(path: str, text: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    wc = word_count(text)
    chunks = total_chunks(text)
    lines = [
        f"File:   {os.path.basename(path)}",
        f"Type:   {ext or 'unknown'}",
        f"Words:  {wc:,}",
        f"Chars:  {len(text):,}",
        f"Chunks: {chunks}  (--chunk 0 through --chunk {chunks - 1})",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extract text from a campaign source file.")
    parser.add_argument("filepath", help="Path to the source file")
    parser.add_argument("--info", action="store_true", help="Print file info only")
    parser.add_argument("--chunks", action="store_true", help="Print total chunk count")
    parser.add_argument("--chunk", type=int, default=None, metavar="N",
                        help="Print chunk N (0-indexed, up to 24,000 characters each)")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"Error: file not found: {args.filepath}", file=sys.stderr)
        sys.exit(1)

    try:
        text = extract(args.filepath)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not text.strip():
        print("Warning: extracted text is empty. File may be image-only PDF.", file=sys.stderr)
        sys.exit(1)

    if args.info:
        print(file_info(args.filepath, text))
    elif args.chunks:
        print(total_chunks(text))
    elif args.chunk is not None:
        chunk = chunk_text(text, args.chunk)
        if not chunk.strip():
            print(f"Error: chunk {args.chunk} out of range (max: {total_chunks(text) - 1})",
                  file=sys.stderr)
            sys.exit(1)
        print(chunk, end="" if chunk.endswith("\n") else "\n")
    else:
        # Print full text
        print(text)


if __name__ == "__main__":
    main()
