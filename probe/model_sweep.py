#!/usr/bin/env python3
"""
open-tabletop-gm model sweep
-----------------------------
Fetches OpenRouter model list, filters to open-weight locally-hostable models,
deduplicates by family, and outputs a clean model list for narrative probe runs.

Usage:
  python3 probe/model_sweep.py --api-key KEY
  python3 probe/model_sweep.py --api-key KEY --include-finetunes  # add community finetunes
  python3 probe/model_sweep.py --api-key KEY --output probe/sweep_models.txt
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Open-weight provider allowlist
# These providers publish model weights — models can be run locally via LM Studio / Ollama
# ---------------------------------------------------------------------------

OPEN_WEIGHT_PREFIXES = [
    "meta-llama/",
    "google/gemma-",
    "mistralai/",
    "microsoft/phi-",
    "microsoft/wizardlm-",
    "qwen/qwen-2.5",
    "qwen/qwen3-14b",
    "qwen/qwen3-32b",
    "qwen/qwen3-8b",
    "qwen/qwen3-30b",
    "qwen/qwen3-235b",
    "qwen/qwen3.5-",
    "qwen/qwq-",
    "qwen/qwen3-next-",
    "deepseek/deepseek-r1-distill-",
    "deepseek/deepseek-v3",
    "deepseek/deepseek-r1",
    "deepseek/deepseek-chat-v3",
    "nvidia/nemotron-",
    "nvidia/llama-",
    "nousresearch/",
    "allenai/olmo-",
    "cognitivecomputations/",
    "thedrummer/",
    "sao10k/",
    "gryphe/",
    "mancer/",
    "undi95/",
    "anthracite-org/",
    "aion-labs/aion-rp-",   # roleplay finetune specifically
    "minimax/minimax-m2",    # m2 series has public weights
    "minimax/minimax-m2.5",
    "minimax/minimax-m2.7",
    "z-ai/glm-4-",           # GLM-4 has open weights
    "z-ai/glm-4.5",
    "cohere/command-r",      # Command-R has public weights
    "alpindale/",
    "microsoft/",
]

# ---------------------------------------------------------------------------
# Definitive closed-source / API-only blocklist
# ---------------------------------------------------------------------------

CLOSED_PREFIXES = [
    "openai/", "anthropic/", "google/gemini", "google/lyria",
    "amazon/", "ai21/", "inflection/", "perplexity/", "writer/", "upstage/",
    "x-ai/", "moonshotai/", "bytedance", "baidu/", "cohere/command-a",
    "inception/", "openrouter/", "switchpoint/", "rekaai/", "relace/",
    "stepfun/", "kwaipilot/", "morph/", "tngtech/", "essentialai/",
    "prime-intellect/", "xiaomi/", "tencent/", "ibm-granite/",
    "deepcogito/", "alfredpros/", "nex-agi/", "arcee-ai/",
    "qwen/qwen-max", "qwen/qwen-plus", "qwen/qwen-turbo",
    "qwen/qwen3-max", "qwen/qwen3-coder-plus", "qwen/qwen3-coder-next",
    "qwen/qwen3-coder-flash", "qwen/qwen3.5-plus", "qwen/qwen3.5-flash",
    "qwen/qwen3.6-", "minimax/minimax-01", "minimax/minimax-m1",
    "minimax/minimax-m2-her", "minimax/minimax-m2.1",
]

# Modality / specialization — not useful for narrative eval
SKIP_TAGS = [
    "vl-", "-vl", "-vision", "vision-", "embed", "tts", "whisper",
    "ocr", "-guard", "guard-", "lyria", "clip", "rerank",
]

# Code-only models
CODE_ONLY = [
    "codestral", "devstral", "/coder-large", "/coder-pro",
    "-solidity", "ui-tars", "relace-apply", "relace-search",
    "maestro-reasoning", "spotlight", "morph-v3",
]

# Thinking-only / pure reasoning variants — poor narrative candidates
THINKING_SUFFIX = [
    "-thinking-", ":thinking", "thinking-2507", "r1t2",
    "-think-2507", "-r1-0528", "olmo-3-32b-think",
    "deepseek-r1-distill",   # reasoning distills, not narrative
    "deepseek/deepseek-r1",  # base reasoning model
    "qwen/qwq-",             # reasoning model
    "allenai/",              # research models, not narrative
    "cohere/",               # not locally hostable in practice
    "microsoft/wizardlm-",   # old generation
    "gryphe/",               # very old L2-based
    "undi95/",               # old L2-based
    "nousresearch/hermes-2-", # old generation
    "meta-llama/llama-3-",   # old Llama 3.0 (not 3.1/3.2/3.3)
    "meta-llama/llama-3.1-", # superseded by 3.3
    "meta-llama/llama-3.2-", # small/multimodal focused
    "qwen/qwen3-8b",         # too small
    "qwen/qwen3.5-9b",       # too small
    "qwen/qwen-2.5-7b",      # too small
    "mistralai/mistral-7b",  # old/small
    "mistralai/mistral-nemo", # 12B, borderline — skip for curation
    "mistralai/ministral-3b", # too small
    "mistralai/mistral-saba", # regional/specialized
    "mistralai/mistral-small-24b-instruct-2501", # superseded
    "mistralai/mistral-small-2603",              # superseded
    "mistralai/mistral-small-3.1-",             # superseded by 3.2
    "mistralai/mistral-large-2407",
    "mistralai/mistral-large-2411",
    "mistralai/mistral-medium-3",    # keep 3.1 only
    "mistralai/mixtral-8x7b",        # old MoE
    "mistralai/pixtral-",            # multimodal focus
    "mistralai/voxtral-",            # audio focus
    "mistralai/ministral-14b",       # keep 8b slot only, 14b not widely tested
    "nvidia/nemotron-nano-9b",       # too small
    "nvidia/llama-3.1-nemotron-70b", # superseded by super-49b
    "deepseek/deepseek-chat-v3-0324", # superseded
    "deepseek/deepseek-chat-v3.1",    # superseded
    "deepseek/deepseek-v3.1-",        # superseded
    "deepseek/deepseek-v3.2-exp",     # experimental
    "deepseek/deepseek-v3.2-speciale",
    "google/gemma-2-",               # old generation
    "google/gemma-3-4b",             # too small
    "google/gemma-3n-",              # nano variants
    "google/gemma-3-12b",            # keep 27b tier
    "qwen/qwen3-30b-a3b-instruct-2507", # dedupe with qwen3-next-80b-a3b
    "qwen/qwen3-235b-a22b-2507",     # dedupe, keep base
    "qwen/qwen3-14b",                # keep 32b+ for curation
    "minimax/minimax-m2-",           # keep m2.5 only
    "minimax/minimax-m2.7",          # too new/untested
    "nousresearch/hermes-3-llama-3.1-70b", # keep 405b tier
    "z-ai/",                         # limited info on local hostability
    "aion-labs/aion-1",              # keep rp variant only
    "aion-labs/aion-2",
    "sao10k/l3-euryale-70b",         # superseded by l3.1 and l3.3
    "sao10k/l3-lunaris-8b",          # too small
    "sao10k/l3.1-70b-hanami",        # keep euryale as canonical
    "thedrummer/rocinante-12b",      # keep larger drummer models
    "thedrummer/unslopnemo-12b",     # too small for curation
    "aion-labs/aion-rp",             # 8B, too small
    "nousresearch/hermes-2-pro",     # old generation
    "google/gemma-3-12b",            # skip in favour of 27b
    "qwen/qwen3-30b-a3b",            # dedupe with next-80b
    "microsoft/phi-4",               # 14B, skip in curated mode
    "qwen/qwen-2.5-coder-32b",       # code-focused
    "deepseek/deepseek-chat",        # API wrapper, not distinct
    "qwen/qwen3-next-80b-a3b-thinking",  # thinking variant — skip in favour of instruct
    "minimax/minimax-m2",            # keep m2.5 only
    "mistralai/mistral-medium-3,",   # comma ensures we don't block 3.1
    "mistralai/mistral-small-creative",  # proprietary creative variant
]

# Models that bypass the skip filters — important roleplay finetunes that may have
# low context windows or only exist as :free tiers
ALWAYS_INCLUDE = [
    "mancer/weaver",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition",
    "mistralai/mistral-medium-3.1",
    "sao10k/l3.1-70b-hanami-x1",
    "nousresearch/hermes-3-llama-3.1-405b",
]

# Too small context for useful narrative quality (bypassed for ALWAYS_INCLUDE)
MIN_CONTEXT = 16384


def fetch_models(api_key: str) -> list:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read()).get("data", [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch models: {e}", file=sys.stderr)
        return []


def is_open_weight(model_id: str) -> bool:
    if not model_id:
        return False
    ml = model_id.lower()
    if any(ml.startswith(c.lower()) for c in CLOSED_PREFIXES):
        return False
    return any(ml.startswith(p.lower()) for p in OPEN_WEIGHT_PREFIXES)


def should_skip(model_id: str) -> bool:
    if not model_id:
        return True
    ml = model_id.lower()
    if any(t in ml for t in SKIP_TAGS):
        return True
    if any(t in ml for t in CODE_ONLY):
        return True
    if any(t in ml for t in THINKING_SUFFIX):
        return True
    # Skip :free duplicates — we keep the paid version for the sweep
    # (free tier rate limits would wreck a 70-model run)
    if ml.endswith(":free"):
        return True
    return False


def filter_models(models: list) -> list:
    kept = []
    seen = set()

    # Build lookup by base ID (strip :free) for ALWAYS_INCLUDE resolution
    model_by_id = {m["id"]: m for m in models}
    model_by_base = {}
    for m in models:
        base = m["id"].replace(":free", "")
        if base not in model_by_base:
            model_by_base[base] = m

    # Add ALWAYS_INCLUDE entries first, bypassing most filters
    for include_id in ALWAYS_INCLUDE:
        m = model_by_id.get(include_id) or model_by_base.get(include_id)
        if not m:
            # Try :free variant
            m = model_by_id.get(include_id + ":free")
        if not m:
            continue
        mid = m["id"]
        base = mid.replace(":free", "")
        if base in seen:
            continue
        seen.add(base)
        # Also mark normalized family_key as seen so the regular loop doesn't re-add
        fk = base.lower()
        for suffix in ["-2512", "-2511", "-2409", "-2407", "-2411", "-2501",
                       "-2603", "-0324", "-0528", "-instruct", "-v0.1",
                       "-v0.2", "-v1", "-v2", "-v3", "-v4", "-v4.1",
                       "-a22b", "-a3b", "-a10b", "-a17b"]:
            fk = fk.replace(suffix, "")
        seen.add(fk)
        # Prefer paid version if available
        paid = model_by_id.get(base)
        kept.append(paid if paid else m)

    # Sort remaining by context_length desc so we keep most capable per family
    models_sorted = sorted(
        models,
        key=lambda m: m.get("context_length", 0),
        reverse=True,
    )

    for m in models_sorted:
        mid = m["id"]
        ml = mid.lower()

        if not is_open_weight(mid):
            continue
        if should_skip(mid):
            continue
        if m.get("context_length", 0) < MIN_CONTEXT:
            continue

        # Skip :free if paid exists (already handled in ALWAYS_INCLUDE above)
        if ml.endswith(":free") and mid.replace(":free", "") in model_by_id:
            continue

        # Family dedup: strip version suffixes to get canonical family key
        family_key = ml.replace(":free", "")
        for suffix in ["-2512", "-2511", "-2409", "-2407", "-2411", "-2501",
                       "-2603", "-0324", "-0528", "-instruct", "-v0.1",
                       "-v0.2", "-v1", "-v2", "-v3", "-v4", "-v4.1",
                       "-a22b", "-a3b", "-a10b", "-a17b"]:
            family_key = family_key.replace(suffix, "")

        if family_key in seen:
            continue
        seen.add(family_key)
        kept.append(m)

    return kept


def format_output(models: list, verbose: bool = False) -> str:
    lines = []
    for m in models:
        if verbose:
            ctx = m.get("context_length", "?")
            pricing = m.get("pricing", {})
            cost_per_m = float(pricing.get("completion", 0)) * 1_000_000
            lines.append(f"{m['id']:<60}  ctx={ctx:<8}  ${cost_per_m:.3f}/Mtok")
        else:
            lines.append(m["id"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="OpenRouter open-weight model sweep")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", default="", help="Write model IDs to file (one per line)")
    parser.add_argument("--verbose", action="store_true", help="Show context length and pricing")
    parser.add_argument("--json", dest="output_json", action="store_true")
    args = parser.parse_args()

    print(f"Fetching OpenRouter model list...", file=sys.stderr)
    all_models = fetch_models(args.api_key)
    print(f"  Total models: {len(all_models)}", file=sys.stderr)

    filtered = filter_models(all_models)
    print(f"  After open-weight + dedup filter: {len(filtered)}", file=sys.stderr)
    print(file=sys.stderr)

    # Sort final list by family then name
    filtered.sort(key=lambda m: m["id"])

    output = format_output(filtered, verbose=args.verbose)

    if args.output:
        Path(args.output).write_text("\n".join(m["id"] for m in filtered) + "\n")
        print(f"Wrote {len(filtered)} model IDs to {args.output}", file=sys.stderr)
    elif args.output_json:
        print(json.dumps([m["id"] for m in filtered], indent=2))
    else:
        print(output)


if __name__ == "__main__":
    main()
