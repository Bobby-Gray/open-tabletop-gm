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
  python3 import_campaign.py <filepath> --chunk N  # print chunk N of ~4000 words (for large sources)
  python3 import_campaign.py <filepath> --chunks   # print total number of chunks

Output is UTF-8 plain text, written to stdout. The GM reads this and maps it to campaign files.
"""

import sys
import os
import argparse
import subprocess

CHUNK_WORDS = 4000  # words per chunk for large sources


def extract_pdf(path: str) -> str:
    """Extract text from PDF using pdftotext (poppler). Falls back to PyMuPDF."""
    # Try pdftotext first (best quality)
    result = subprocess.run(
        ["pdftotext", "-layout", path, "-"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout

    # Fallback: try PyMuPDF if installed
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
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


def chunk_text(text: str, chunk_index: int) -> str:
    """Return chunk N (0-indexed) of ~CHUNK_WORDS words."""
    words = text.split()
    start = chunk_index * CHUNK_WORDS
    end = start + CHUNK_WORDS
    chunk_words = words[start:end]
    if not chunk_words:
        return ""
    return " ".join(chunk_words)


def total_chunks(text: str) -> int:
    wc = word_count(text)
    return max(1, (wc + CHUNK_WORDS - 1) // CHUNK_WORDS)


def file_info(path: str, text: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    wc = word_count(text)
    chunks = total_chunks(text)
    lines = [
        f"File:   {os.path.basename(path)}",
        f"Type:   {ext or 'unknown'}",
        f"Words:  {wc:,}",
        f"Chunks: {chunks}  (--chunk 0 through --chunk {chunks - 1})",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extract text from a campaign source file.")
    parser.add_argument("filepath", help="Path to the source file")
    parser.add_argument("--info", action="store_true", help="Print file info only")
    parser.add_argument("--chunks", action="store_true", help="Print total chunk count")
    parser.add_argument("--chunk", type=int, default=None, metavar="N",
                        help="Print chunk N (0-indexed, ~4000 words each)")
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
        if not chunk:
            print(f"Error: chunk {args.chunk} out of range (max: {total_chunks(text) - 1})",
                  file=sys.stderr)
            sys.exit(1)
        print(chunk)
    else:
        # Print full text
        print(text)


if __name__ == "__main__":
    main()
