#!/usr/bin/env python3
"""
Scrape roleplay/finetune model recommendations from r/SillyTavernAI and r/LocalLLaMA.

Uses requests + BeautifulSoup on old.reddit.com (server-rendered, no JS needed).
Falls back to selenium for new Reddit if old Reddit returns nothing useful.

Usage:
  python3 probe/scrape_recommendations.py
  python3 probe/scrape_recommendations.py --selenium        # force new Reddit via selenium
  python3 probe/scrape_recommendations.py --output finetunes.txt

Output: ranked list of model name mentions with OpenRouter ID guesses where possible.
"""

import argparse
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False
    print("[WARN] beautifulsoup4 not installed — install with: pip install beautifulsoup4", file=sys.stderr)

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_OK = True
except ImportError:
    SELENIUM_OK = False

# ---------------------------------------------------------------------------
# Known roleplay / narrative finetune families + OpenRouter ID hints
# ---------------------------------------------------------------------------

KNOWN_FINETUNES = {
    # name pattern -> openrouter ID (if available)
    "euryale":       "sao10k/l3.3-euryale-70b",
    "hanami":        "sao10k/l3.1-70b-hanami-x1",
    "lunaris":       "sao10k/l3-lunaris-8b",
    "cydonia":       "thedrummer/cydonia-24b-v4.1",
    "skyfall":       "thedrummer/skyfall-36b-v2",
    "rocinante":     "thedrummer/rocinante-12b",
    "unslopnemo":    "thedrummer/unslopnemo-12b",
    "magnum":        "anthracite-org/magnum-v4-72b",
    "weaver":        "mancer/weaver",
    "mythomax":      "gryphe/mythomax-l2-13b",
    "dolphin":       "cognitivecomputations/dolphin-mistral-24b-venice-edition",
    "remm":          "undi95/remm-slerp-l2-13b",
    "hermes":        "nousresearch/hermes-3-llama-3.1-405b",
    "lumimaid":      None,   # not on OpenRouter, local only
    "noromaid":      None,
    "fimbulvetr":    None,
    "stheno":        None,
    "gutenberg":     None,   # mistral-nemo-gutenberg, local
    "synthia":       None,
    "airoboros":     None,
    "midnight-rose": None,
    "aion-rp":       "aion-labs/aion-rp-llama-3.1-8b",
}

# Regex to extract model-name-like strings from freeform text
MODEL_NAME_RE = re.compile(
    r'\b('
    r'(?:llama|mistral|qwen|gemma|phi|falcon|yi|deepseek|solar|openchat|nous|hermes|'
    r'lumimaid|noromaid|fimbulvetr|stheno|midnight|gutenberg|synthia|euryale|airoboros|'
    r'dolphin|openhermes|wizardlm|mythomist|mythomax|magnum|weaver|remm|hanami|'
    r'cydonia|skyfall|rocinante|unslopnemo|lunaris|aion.rp|nemo|mixtral|mistral.nemo|'
    r'llava|nous.hermes|capybara|vicuna|orca|alpaca|platypus|samantha)'
    r'[A-Za-z0-9._\-]*'
    r'|[A-Za-z][A-Za-z0-9_\-]+-\d+(?:\.\d+)?[Bb](?:-[A-Za-z0-9_\-]+)*'
    r')\b',
    re.IGNORECASE,
)

JUNK_WORDS = {
    "the", "and", "for", "with", "that", "this", "have", "from", "they",
    "not", "are", "but", "its", "was", "you", "all", "can", "use", "get",
    "more", "some", "also", "just", "like", "very", "good", "best", "any",
    "new", "old", "big", "small", "will", "been", "has", "than", "then",
    "well", "one", "two", "way", "out", "how", "may", "much", "great",
    "when", "what", "which", "who", "why", "let", "here", "there",
}

# ---------------------------------------------------------------------------
# Scraping targets
# ---------------------------------------------------------------------------

TARGETS = [
    {
        "name": "r/SillyTavernAI — top month",
        "url": "https://old.reddit.com/r/SillyTavernAI/top/?t=month",
    },
    {
        "name": "r/SillyTavernAI — search: model recommendation",
        "url": "https://old.reddit.com/r/SillyTavernAI/search/?q=model+recommendation&restrict_sr=1&sort=top&t=year",
    },
    {
        "name": "r/LocalLLaMA — search: roleplay finetune",
        "url": "https://old.reddit.com/r/LocalLLaMA/search/?q=roleplay+finetune&restrict_sr=1&sort=top&t=year",
    },
    {
        "name": "r/LocalLLaMA — search: best model roleplay",
        "url": "https://old.reddit.com/r/LocalLLaMA/search/?q=best+model+roleplay+writing&restrict_sr=1&sort=top&t=year",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; model-recommender/1.0; research use)",
}


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def fetch_old_reddit(url: str) -> str:
    """Fetch old Reddit page HTML via requests."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return ""


def extract_text_old_reddit(html: str) -> str:
    """Pull post titles and top-level comment text from old Reddit HTML."""
    if not BS4_OK or not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    chunks = []

    # Post titles
    for tag in soup.select("a.title, p.title a"):
        chunks.append(tag.get_text())

    # Comment bodies
    for tag in soup.select("div.md, div.usertext-body"):
        chunks.append(tag.get_text())

    return " ".join(chunks)


def fetch_selenium(url: str) -> str:
    """Fallback: fetch new Reddit page via headless Chrome."""
    if not SELENIUM_OK:
        print("  [WARN] selenium not installed — skipping", file=sys.stderr)
        return ""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"user-agent={HEADERS['User-Agent']}")
    try:
        driver = webdriver.Chrome(options=opts)
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        text = driver.find_element(By.TAG_NAME, "body").text
        driver.quit()
        return text
    except Exception as e:
        print(f"  [WARN] selenium fetch failed: {e}", file=sys.stderr)
        return ""


def extract_model_mentions(text: str) -> list[str]:
    """Extract candidate model names from freeform text."""
    hits = []
    for m in MODEL_NAME_RE.finditer(text):
        name = m.group(0).lower().strip("-_")
        if len(name) < 4:
            continue
        if name in JUNK_WORDS:
            continue
        hits.append(name)
    return hits


def match_known_finetune(name: str) -> tuple:
    """Return (canonical_name, openrouter_id) if name matches a known finetune."""
    nl = name.lower()
    for key, or_id in KNOWN_FINETUNES.items():
        if key in nl:
            return key, or_id
    return None, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(use_selenium: bool = False) -> list:
    """Returns list of (name, mention_count, openrouter_id_or_none)."""
    all_mentions: Counter = Counter()

    for target in TARGETS:
        print(f"Scraping: {target['name']}", file=sys.stderr)
        if use_selenium:
            text = fetch_selenium(target["url"])
        else:
            html = fetch_old_reddit(target["url"])
            text = extract_text_old_reddit(html) if html else ""

        if not text:
            print("  → no content retrieved", file=sys.stderr)
            continue

        mentions = extract_model_mentions(text)
        count = len(mentions)
        counter = Counter(mentions)
        print(f"  → {count} mentions, {len(counter)} unique names", file=sys.stderr)
        all_mentions.update(counter)
        time.sleep(2)

    # Filter: only keep names that appear 2+ times OR match a known finetune
    results = []
    seen_canonical = set()
    for name, count in all_mentions.most_common():
        canonical, or_id = match_known_finetune(name)
        if canonical:
            if canonical in seen_canonical:
                continue
            seen_canonical.add(canonical)
            results.append((canonical, count, or_id))
        elif count >= 2 and len(name) >= 5:
            results.append((name, count, None))

    # Add known finetunes that weren't mentioned but are notable
    mentioned_canonicals = {r[0] for r in results}
    for key, or_id in KNOWN_FINETUNES.items():
        if key not in mentioned_canonicals:
            results.append((key, 0, or_id))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def main():
    parser = argparse.ArgumentParser(description="Scrape roleplay model recommendations")
    parser.add_argument("--selenium", action="store_true", help="Use selenium (new Reddit)")
    parser.add_argument("--output", default="", help="Write results to file")
    args = parser.parse_args()

    if not BS4_OK:
        print("Install beautifulsoup4 first: pip install beautifulsoup4", file=sys.stderr)
        sys.exit(1)

    print("Scraping for roleplay finetune recommendations...\n", file=sys.stderr)
    results = run(use_selenium=args.selenium)

    lines = []
    lines.append(f"{'Model':<30}  {'Mentions':>8}  OpenRouter ID")
    lines.append("-" * 75)
    for name, count, or_id in results:
        or_str = or_id or "(local only / not on OpenRouter)"
        mention_str = str(count) if count > 0 else "—"
        lines.append(f"{name:<30}  {mention_str:>8}  {or_str}")

    output = "\n".join(lines)
    print(output)

    if args.output:
        # Write just the OpenRouter IDs that we know about
        ids = [or_id for _, _, or_id in results if or_id]
        Path(args.output).write_text("\n".join(ids) + "\n")
        print(f"\nWrote {len(ids)} OpenRouter IDs to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
