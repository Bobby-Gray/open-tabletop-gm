#!/usr/bin/env bash
# Run probe sequentially against OpenRouter models.
# Usage:
#   ./run-openrouter.sh <api-key>          # free tier (rate-limited)
#   ./run-openrouter.sh <api-key> --paid   # paid endpoints (no rate limits, ~$0.01-0.12 total)

API_KEY="${1:?Usage: run-openrouter.sh <api-key> [--paid]}"
PAID=0
[[ "$*" == *"--paid"* ]] && PAID=1

OR_URL="https://openrouter.ai/api"
RESULTS="$(dirname "$0")/results"
PROBE="$(dirname "$0")/probe.py"
mkdir -p "$RESULTS"

FREE_MODELS=(
  # Priority 1 — new/high-quality, untested
  "openai/gpt-oss-120b:free"
  "nousresearch/hermes-3-llama-3.1-405b:free"
  "openai/gpt-oss-20b:free"

  # Priority 2 — retry (were rate-limited in first run)
  "qwen/qwen3-next-80b-a3b-instruct:free"
  "meta-llama/llama-3.3-70b-instruct:free"

  # Priority 3 — additional coverage
  "qwen/qwen3-coder:free"
  "nvidia/nemotron-3-nano-30b-a3b:free"
  "minimax/minimax-m2.5:free"
  "google/gemma-3-27b-it:free"
  "google/gemma-4-31b-it:free"
)

# Paid endpoints: same models, :free suffix dropped
if [[ $PAID -eq 1 ]]; then
  echo "[paid mode] Using paid endpoints — rate limits bypassed, ~\$0.01-0.12 total"
  MODELS=()
  for m in "${FREE_MODELS[@]}"; do
    MODELS+=("${m%:free}")
  done
  GAP=5   # minimal gap needed
else
  echo "[free mode] Using free endpoints — 90s gaps to avoid rate limits"
  MODELS=("${FREE_MODELS[@]}")
  GAP=90
fi

for MODEL in "${MODELS[@]}"; do
  SAFE=$(echo "$MODEL" | tr '/:' '--')
  echo ""
  echo "━━━ $MODEL ━━━"
  python3 "$PROBE" \
    --model "$MODEL" \
    --url "$OR_URL" \
    --api-key "$API_KEY" \
    --skip-skill-md \
    --json \
    --timeout 90 \
    --output-file "$RESULTS/${SAFE}.json" \
    2>&1 | tee "$RESULTS/${SAFE}.log"

  echo "Waiting ${GAP}s..."
  sleep "$GAP"
done

echo ""
echo "━━━ SUMMARY ━━━"
for f in "$RESULTS"/*.json; do
  [ -f "$f" ] || continue
  python3 -c "
import json, sys
d = json.load(open('$f'))
s = d.get('summary', {})
t = d.get('token_summary', {})
tok = f\"  avg {t['avg_prompt_tokens']}p/{t['avg_completion_tokens']}c\" if t else ''
print(f\"{d['model']:<55} PASS:{s.get('PASS',0)} FAIL:{s.get('FAIL',0)} WARN:{s.get('WARN',0)} ERROR:{s.get('ERROR',0)}{tok}\")
"
done
