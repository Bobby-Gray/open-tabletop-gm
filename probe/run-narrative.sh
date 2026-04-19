#!/usr/bin/env bash
# Run narrative quality probe against all models.
# Judge model: openai/gpt-oss-20b (cheap, fast, ~$0.001/response)
#
# Usage: ./run-narrative.sh <api-key>

API_KEY="${1:?Usage: run-narrative.sh <api-key>}"
OR_URL="https://openrouter.ai/api"
RESULTS="$(dirname "$0")/results/narrative"
PROBE="$(dirname "$0")/narrative_probe.py"
JUDGE="openai/gpt-oss-20b"
mkdir -p "$RESULTS"

MODELS=(
  "openai/gpt-oss-120b"
  "nousresearch/hermes-3-llama-3.1-405b"
  "google/gemma-3-27b-it"
  "google/gemma-4-31b-it"
  "meta-llama/llama-3.3-70b-instruct"
  "nvidia/nemotron-3-nano-30b-a3b"
  "qwen/qwen3-next-80b-a3b-instruct"
  "qwen/qwen3-coder"
  "minimax/minimax-m2.5"
)

for MODEL in "${MODELS[@]}"; do
  SAFE=$(echo "$MODEL" | tr '/:' '--')
  echo ""
  echo "━━━ $MODEL ━━━"
  python3 "$PROBE" \
    --model "$MODEL" \
    --url "$OR_URL" \
    --api-key "$API_KEY" \
    --judge-model "$JUDGE" \
    --timeout 120 \
    --output-file "$RESULTS/${SAFE}.json" \
    2>&1 | tee "$RESULTS/${SAFE}.log"

  echo "Waiting 10s..."
  sleep 10
done

echo ""
echo "━━━ NARRATIVE SUMMARY ━━━"
printf "%-50s  AUTO        JUDGE: atm  npc  gm\n" "Model"
printf "%-50s  ----------  -------------------------\n" "-----"
for f in "$RESULTS"/*.json; do
  [ -f "$f" ] || continue
  python3 -c "
import json
d = json.load(open('$f'))
a = d.get('auto_summary', {})
j = d.get('judge_averages', {})
auto = f\"P:{a.get('PASS',0)} W:{a.get('WARN',0)} F:{a.get('FAIL',0)}\"
atm = f\"{j.get('atmosphere','?')}\" if j else '-'
npc = f\"{j.get('npc_craft','?')}\" if j else '-'
gmc = f\"{j.get('gm_craft','?')}\" if j else '-'
print(f\"{d['model']:<50}  {auto:<10}  {atm:<6} {npc:<6} {gmc}\")
" 2>/dev/null
done

echo ""
echo "━━━ HIGHLIGHT REEL ━━━"
for f in "$RESULTS"/*.json; do
  [ -f "$f" ] || continue
  python3 -c "
import json
d = json.load(open('$f'))
j = d.get('judge_averages', {})
overall = round(sum(j.values())/len(j), 2) if j else '?'
print(f\"\n--- {d['model']} (judge avg: {overall}) ---\")
for c in d.get('cases', []):
    hl = c.get('highlight', '')
    if hl:
        print(f\"  [{c['id']}] {hl}\")
" 2>/dev/null
done
