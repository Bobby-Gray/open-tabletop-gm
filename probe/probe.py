#!/usr/bin/env python3
"""
open-tabletop-gm model probe
-----------------------------
Runs a fixed sequence of test prompts against a locally loaded LM Studio model
and scores each response against expected behavior patterns.

Usage:
  python3 probe/probe.py --model <lmstudio-model-id> [--url http://localhost:1234]

Before running:
  - Load the target model in LM Studio
  - Populate probe/tools.json with tool definitions captured from an OpenCode
    debug log (see tools.json for instructions)

Output:
  Prints a scored report to stdout. PASS/FAIL/WARN per test case.
  Append --json to get machine-readable output for logging.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

SKILL_BASE = Path(__file__).parent.parent
PROBE_DIR  = Path(__file__).parent

# ---------------------------------------------------------------------------
# System prompt assembly — mirrors opencode.json instructions order
# ---------------------------------------------------------------------------

def build_system_prompt(include_skill_md: bool = True) -> str:
    files = [
        SKILL_BASE / "no_think.md",
        SKILL_BASE / "paths.md",
    ]
    if include_skill_md:
        files.append(SKILL_BASE / "SKILL.md")
    files.append(SKILL_BASE / "SKILL-commands.md")

    parts = []
    for f in files:
        if f.exists():
            parts.append(f.read_text())
        else:
            print(f"[WARN] Missing system prompt file: {f}", file=sys.stderr)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "id": "list_campaigns",
        "label": "/gm list",
        "messages": [
            {"role": "user", "content": "/gm list"}
        ],
        "pass_if": [
            # Model should either: issue a Glob/Read tool call, OR describe that it would
            # It should NOT hallucinate specific campaign names
            "glob",          # tool call issued
        ],
        "fail_if": [
            "Campaign 1",    # hallucinated data
            "Campaign 2",
        ],
        "warn_if": [
            # If no tool call and no hallucination — model described the procedure but didn't act
        ],
        "notes": "Requires tools.json populated. Without tools, model will hallucinate — mark as SKIP if tools empty."
    },
    {
        "id": "load_campaign",
        "label": "/gm load test-campaign",
        "messages": [
            {"role": "user", "content": "/gm load test-campaign"}
        ],
        "pass_if": [
            # Should read state.md, ask about display companion, NOT run list
            "test-campaign",
            "display",
        ],
        "fail_if": [
            # Regression: fell back to listing campaigns
            "no campaigns available",
            "create a new campaign",
            # RLHF refusal
            "don't have the tools",
            "I'm sorry, but I currently don't have the tools",
        ],
        "warn_if": [
            # Hallucinated a campaign list instead of reading files
            "Campaign 1",
        ],
        "notes": "Key regression test. Should follow procedure from SKILL-commands.md guard."
    },
    {
        "id": "load_extra_args",
        "label": "/gm load test-campaign dnd5e (extra arg)",
        "messages": [
            {"role": "user", "content": "/gm load test-campaign dnd5e"}
        ],
        "pass_if": [
            # Should ignore the extra arg and load normally, OR note the signature mismatch politely
            "test-campaign",
        ],
        "fail_if": [
            "don't have the tools",
            "I'm sorry, but I currently don't have the tools",
            "I cannot",
        ],
        "notes": "Known Mistral failure mode. Extra positional args trigger RLHF refusal."
    },
    {
        "id": "roll_dice",
        "label": "/gm roll d20",
        "messages": [
            {"role": "user", "content": "/gm roll d20"}
        ],
        "pass_if": [
            # Should issue a Bash tool call to dice.py, OR echo a result between 1-20
            "dice.py",
        ],
        "fail_if": [
            "I cannot roll",
            "don't have the ability",
        ],
        "notes": "Script-call test. Model should run python3 <skill-base>/scripts/dice.py d20."
    },
    {
        "id": "no_gm_prefix_after_load",
        "label": "No /gm prefix needed after session active",
        "messages": [
            {
                "role": "user",
                "content": "/gm load test-campaign"
            },
            {
                "role": "assistant",
                "content": "Campaign loaded. The party stands at the edge of Ebonkeep. Start the cinematic display companion? [y/n]"
            },
            {
                "role": "user",
                "content": "n"
            },
            {
                "role": "assistant",
                "content": "Understood. The party stands in the shadow of Ebonkeep's crumbling gate..."
            },
            {
                "role": "user",
                "content": "I look around for guards."
            }
        ],
        "pass_if": [
            # Should respond in-character, not ask for /gm prefix
        ],
        "fail_if": [
            "please use /gm",
            "you need to use a /gm command",
        ],
        "notes": "Once loaded, the model should stay in GM mode without requiring /gm prefix."
    },
]


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def lms_request(method: str, path: str, body: dict, url: str, timeout: int = 60) -> dict:
    """Hit a LM Studio management API endpoint."""
    req = urllib.request.Request(
        f"{url}{path}",
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read().decode())}
    except Exception as e:
        return {"error": str(e)}


def get_loaded_model(url: str):
    """Return the instance_id of the currently loaded model, or None."""
    result = lms_request("GET", "/api/v0/models", {}, url)
    for m in result.get("data", []):
        if m.get("state") == "loaded":
            return m["id"]
    return None


def switch_model(target_id: str, context_length: int, url: str) -> bool:
    """Unload whatever is currently loaded, then load target_id. Returns True on success."""
    current = get_loaded_model(url)
    if current and current != target_id:
        print(f"  [model] Unloading {current} ...", end="", flush=True)
        r = lms_request("POST", "/api/v1/models/unload", {"instance_id": current}, url, timeout=30)
        if "error" in r:
            print(f" FAILED: {r['error']}")
            return False
        print(" done")

    if get_loaded_model(url) != target_id:
        print(f"  [model] Loading {target_id} (context={context_length}) ...", end="", flush=True)
        r = lms_request("POST", "/api/v1/models/load", {
            "model": target_id,
            "context_length": context_length,
            "eval_batch_size": 4096,
            "flash_attention": True,
            "echo_load_config": True,
        }, url, timeout=120)
        if "error" in r:
            print(f" FAILED: {r['error']}")
            return False
        print(f" loaded in {r.get('load_time_seconds', '?')}s")

    return True


def chat(model: str, messages: list, tools: list, url: str, timeout: int = 180,
         api_key: str = "") -> dict:
    payload = {
        "model": model,
        "temperature": 0.7,
        "max_tokens": 500,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers=headers,
    )
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 429:
                wait = 20 * (attempt + 1)
                print(f" [429 rate-limited, retrying in {wait}s]", end="", flush=True)
                time.sleep(wait)
                continue
            return {"error": body}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "rate-limited after 3 retries"}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score(test: dict, response: dict) -> tuple[str, str]:
    """Returns (PASS|FAIL|WARN|SKIP|ERROR, detail)"""
    if "error" in response:
        return "ERROR", response["error"]

    choice = response.get("choices", [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    tool_calls = (choice.get("message") or {}).get("tool_calls") or []

    # Build a combined text surface for matching (content + tool call names/args)
    surface = content.lower()
    for tc in tool_calls:
        surface += " " + json.dumps(tc).lower()

    # SKIP if tools required but not available
    if test.get("notes", "").startswith("Requires tools.json") and not tool_calls and not content:
        return "SKIP", "No tools injected — cannot evaluate tool-call behavior"

    for pattern in test.get("fail_if", []):
        if pattern.lower() in surface:
            return "FAIL", f"Matched fail pattern: '{pattern}'"

    passed = []
    for pattern in test.get("pass_if", []):
        if pattern.lower() in surface:
            passed.append(pattern)

    for pattern in test.get("warn_if", []):
        if pattern.lower() in surface:
            return "WARN", f"Matched warn pattern: '{pattern}'"

    if test.get("pass_if") and not passed:
        return "WARN", "No pass patterns matched — response may be incomplete or unexpected"

    return "PASS", f"Matched: {passed}" if passed else "No disqualifying patterns found"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def run_probe(model: str, url: str, skip_skill_md: bool, output_json: bool, timeout: int,
              context_length: int = 16384, auto_switch: bool = False, api_key: str = ""):
    is_local = "localhost" in url or "127.0.0.1" in url
    if is_local:
        if auto_switch:
            if not switch_model(model, context_length, url):
                print("Aborting — could not switch to target model.")
                return []
        else:
            current = get_loaded_model(url)
            if current != model:
                print(f"[WARN] Target model '{model}' is not loaded (loaded: {current}).")
                print("       Run with --auto-switch to load it automatically, or load it in LM Studio UI.\n")

    system = build_system_prompt(include_skill_md=not skip_skill_md)
    tools_path = PROBE_DIR / "tools.json"
    tools = []
    if tools_path.exists():
        raw = json.loads(tools_path.read_text())
        tools = raw.get("tools", [])
        if not tools:
            print("[INFO] tools.json has no tool definitions — tool-call tests will be limited\n")

    results = []
    for test in TEST_CASES:
        messages = [{"role": "system", "content": system}] + test["messages"]
        print(f"  Running: {test['label']} ...", end="", flush=True)
        t0 = time.time()
        response = chat(model, messages, tools, url, timeout=timeout, api_key=api_key)
        elapsed = time.time() - t0
        status, detail = score(test, response)
        print(f" {status} ({elapsed:.1f}s)", end="")
        if status != "PASS":
            print(f"\n    → {detail}", end="")

        content = ""
        usage = {}
        if "choices" in response:
            content = (response["choices"][0].get("message") or {}).get("content") or ""
        if "usage" in response:
            usage = response["usage"]
            prompt_tok = usage.get("prompt_tokens", 0)
            comp_tok = usage.get("completion_tokens", 0)
            if prompt_tok or comp_tok:
                print(f"    tokens: {prompt_tok}p / {comp_tok}c", end="")
        print()

        results.append({
            "id": test["id"],
            "label": test["label"],
            "status": status,
            "detail": detail,
            "elapsed_s": round(elapsed, 1),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "response_excerpt": content[:300] if content else "(no text content — possible tool call only)",
            "notes": test.get("notes", ""),
        })

    # Summary + token stats
    counts = {s: sum(1 for r in results if r["status"] == s)
              for s in ["PASS", "FAIL", "WARN", "SKIP", "ERROR"]}
    prompt_totals = [r["prompt_tokens"] for r in results if r.get("prompt_tokens")]
    comp_totals   = [r["completion_tokens"] for r in results if r.get("completion_tokens")]
    print(f"\n{'='*60}")
    print(f"Model: {model}")
    print(f"System prompt: {'with' if not skip_skill_md else 'without'} SKILL.md")
    print(f"Tools injected: {'yes' if tools else 'no'}")
    print(f"Results: {counts}")
    if prompt_totals:
        avg_prompt = int(sum(prompt_totals) / len(prompt_totals))
        avg_comp   = int(sum(comp_totals) / len(comp_totals)) if comp_totals else 0
        # Rough session estimate: system_prompt (prompt_totals[0] approx) +
        # 20 turns * avg_comp output + growing history
        sys_toks   = prompt_totals[0] if prompt_totals else 0
        turn_in    = avg_prompt - sys_toks + avg_comp   # incremental tokens per turn
        turn_out   = avg_comp
        session_20 = sys_toks + 20 * (turn_in + turn_out)
        # OpenRouter free tier: ~200 req/day (10 req/min burst) for most models
        req_per_session = 20  # rough turns per session
        sessions_per_200req = 200 // req_per_session
        print(f"Token averages: {avg_prompt}p in / {avg_comp}c out per probe call")
        print(f"  System prompt ~{sys_toks} tokens")
        print(f"  Est. 20-turn session: ~{session_20:,} tokens")
        print(f"  Est. sessions/day (200 req limit): ~{sessions_per_200req}")
    print(f"{'='*60}\n")

    if output_json:
        token_summary = {}
        if prompt_totals:
            token_summary = {
                "avg_prompt_tokens": int(sum(prompt_totals) / len(prompt_totals)),
                "avg_completion_tokens": int(sum(comp_totals) / len(comp_totals)) if comp_totals else 0,
                "system_prompt_tokens_est": prompt_totals[0] if prompt_totals else None,
            }
        out = {
            "model": model,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "skill_md_included": not skip_skill_md,
            "tools_injected": bool(tools),
            "summary": counts,
            "token_summary": token_summary,
            "cases": results,
        }
        print(json.dumps(out, indent=2))

    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="open-tabletop-gm model probe")
    parser.add_argument("--model", required=True, help="LM Studio model identifier")
    parser.add_argument("--url", default="http://localhost:1234", help="LM Studio base URL")
    parser.add_argument("--skip-skill-md", action="store_true",
                        help="Exclude SKILL.md from system prompt (faster; tests command routing only)")
    parser.add_argument("--json", dest="output_json", action="store_true",
                        help="Output full results as JSON after summary")
    parser.add_argument("--timeout", type=int, default=180,
                        help="Per-request timeout in seconds (default: 180)")
    parser.add_argument("--context-length", type=int, default=24576,
                        help="Context length when auto-loading model (default: 24576 — minimum for full system prompt)")
    parser.add_argument("--auto-switch", action="store_true",
                        help="Automatically unload current model and load target model via LM Studio API")
    parser.add_argument("--api-key", default="",
                        help="Bearer token for external APIs (OpenRouter, etc.)")
    parser.add_argument("--output-file", default="",
                        help="Write JSON results to this file instead of stdout")
    args = parser.parse_args()

    print(f"\nopen-tabletop-gm probe — {args.model}\n{'-'*60}")
    results = run_probe(args.model, args.url, args.skip_skill_md, args.output_json,
                        args.timeout, args.context_length, args.auto_switch, args.api_key)

    if args.output_file and results:
        pt = [r["prompt_tokens"] for r in results if r.get("prompt_tokens")]
        ct = [r["completion_tokens"] for r in results if r.get("completion_tokens")]
        token_summary = {}
        if pt:
            token_summary = {
                "avg_prompt_tokens": int(sum(pt) / len(pt)),
                "avg_completion_tokens": int(sum(ct) / len(ct)) if ct else 0,
                "system_prompt_tokens_est": pt[0],
            }
        out = {
            "model": args.model,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "url": args.url,
            "cases": results,
            "summary": {s: sum(1 for r in results if r["status"] == s)
                        for s in ["PASS", "FAIL", "WARN", "SKIP", "ERROR"]},
            "token_summary": token_summary,
        }
        Path(args.output_file).write_text(json.dumps(out, indent=2))
        print(f"Results written to {args.output_file}")
