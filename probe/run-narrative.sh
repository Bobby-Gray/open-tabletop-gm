#!/usr/bin/env bash
# Run narrative quality probe (v2) against open-weight models via OpenRouter.
#
# Usage:
#   ./run-narrative.sh <api-key>                     # full sweep (model_sweep.py generated list)
#   ./run-narrative.sh <api-key> --models-file FILE  # custom model list (one ID per line)
#   ./run-narrative.sh <api-key> --model MODEL       # single model
#   ./run-narrative.sh <api-key> --finetunes-only    # community finetunes from scrape_recommendations.py
#   ./run-narrative.sh <api-key> --no-judge          # skip judge scoring (fast auto-score only)
#
# Judges (5-model ensemble, diverse families):
#   openai/gpt-oss-120b          (OpenAI OSS — anchor)
#   google/gemma-3-27b-it        (Google — top performer in v1)
#   meta-llama/llama-3.3-70b-instruct  (Meta)
#   qwen/qwen3-235b-a22b         (Alibaba/Qwen — largest)
#   nvidia/nemotron-3-super-120b-a12b  (NVIDIA — evaluation-tuned)

set -euo pipefail

API_KEY="${1:?Usage: run-narrative.sh <api-key> [options]}"
OR_URL="https://openrouter.ai/api"
PROBE_DIR="$(dirname "$0")"
RESULTS="${PROBE_DIR}/results/narrative"
PROBE="${PROBE_DIR}/narrative_probe.py"
SWEEP="${PROBE_DIR}/model_sweep.py"
SCRAPE="${PROBE_DIR}/scrape_recommendations.py"

mkdir -p "$RESULTS"

# 5-judge ensemble — diverse model families
JUDGES="openai/gpt-oss-120b,google/gemma-3-27b-it,meta-llama/llama-3.3-70b-instruct,qwen/qwen3-235b-a22b,nvidia/nemotron-3-super-120b-a12b"

# Parse options
MODELS_FILE=""
SINGLE_MODEL=""
FINETUNES_ONLY=0
NO_JUDGE=0
RUNS=5   # runs per scenario — set to 1 for a quick pass, 5 for publishable results
GAP=15   # seconds between models (paid tier — no rate limits, but be polite)

shift
while [[ $# -gt 0 ]]; do
  case "$1" in
    --models-file) MODELS_FILE="$2"; shift 2 ;;
    --model)       SINGLE_MODEL="$2"; shift 2 ;;
    --finetunes-only) FINETUNES_ONLY=1; shift ;;
    --no-judge)    NO_JUDGE=1; shift ;;
    --runs)        RUNS="$2"; shift 2 ;;
    --gap)         GAP="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Build model list
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

if [[ -n "$SINGLE_MODEL" ]]; then
  echo "$SINGLE_MODEL" > "$TMPFILE"
elif [[ -n "$MODELS_FILE" ]]; then
  cp "$MODELS_FILE" "$TMPFILE"
elif [[ $FINETUNES_ONLY -eq 1 ]]; then
  echo "Scraping roleplay finetune recommendations..." >&2
  python3 "$SCRAPE" --output "$TMPFILE"
else
  # Full sweep: open-weight models from OpenRouter
  echo "Building open-weight model list..." >&2
  python3 "$SWEEP" --api-key "$API_KEY" --output "$TMPFILE" --verbose
  echo "" >&2

  # Append community finetunes (scrape for ones not already in sweep)
  FINETUNE_TMP=$(mktemp)
  python3 "$SCRAPE" --output "$FINETUNE_TMP" 2>/dev/null || true
  if [[ -s "$FINETUNE_TMP" ]]; then
    echo "Adding community finetune recommendations..." >&2
    while IFS= read -r model; do
      if ! grep -qx "$model" "$TMPFILE"; then
        echo "$model" >> "$TMPFILE"
        echo "  + $model" >&2
      fi
    done < "$FINETUNE_TMP"
  fi
  rm -f "$FINETUNE_TMP"
fi

TOTAL=$(grep -c . "$TMPFILE" 2>/dev/null || echo 0)
echo "" >&2
echo "━━━ Starting narrative probe v2 ━━━" >&2
echo "Models: $TOTAL" >&2
echo "Runs/scenario: $RUNS" >&2
echo "Judges: $(echo "$JUDGES" | tr ',' '\n' | wc -l | tr -d ' ')" >&2
echo "Results dir: $RESULTS" >&2
echo "" >&2

# Judge flag
JUDGE_ARG="--judge-models $JUDGES"
[[ $NO_JUDGE -eq 1 ]] && JUDGE_ARG="--no-judge"

# Run probe against each model
COUNT=0
while IFS= read -r MODEL; do
  [[ -z "$MODEL" || "$MODEL" == \#* ]] && continue
  COUNT=$((COUNT + 1))
  SAFE=$(echo "$MODEL" | tr '/:' '--')
  OUTFILE="${RESULTS}/${SAFE}.json"

  echo ""
  echo "━━━ [$COUNT/$TOTAL] $MODEL ━━━"

  # Skip if already completed (re-run with --force to override)
  if [[ -f "$OUTFILE" ]] && python3 -c "
import json, sys
d = json.load(open('$OUTFILE'))
cases = d.get('cases', [])
# Accept if: 12 cases, all have runs_valid >= 1, none are pure ERROR status
errors = sum(1 for c in cases if c.get('status') == 'ERROR' and c.get('runs_valid', 0) == 0)
expected_runs = $RUNS
actual_runs = d.get('runs_per_scenario', 1)
runs_ok = actual_runs >= expected_runs
sys.exit(0 if len(cases) >= 12 and errors == 0 and runs_ok else 1)
" 2>/dev/null; then
    echo "  [SKIP] Already have clean $RUNS-run result — use --force to re-run"
    continue
  fi

  python3 "$PROBE" \
    --model "$MODEL" \
    --url "$OR_URL" \
    --api-key "$API_KEY" \
    $JUDGE_ARG \
    --runs "$RUNS" \
    --timeout 120 \
    --output-file "$OUTFILE" \
    2>&1 | tee "${RESULTS}/${SAFE}.log"

  echo "Waiting ${GAP}s..."
  sleep "$GAP"
done < "$TMPFILE"

echo ""
echo "━━━ NARRATIVE SUMMARY v2 ━━━"
printf "%-55s  %-14s  atm   npc   gm    overall  std   IRA\n" "Model" "Auto(P/W/F)"
printf "%-55s  %-14s  ----  ----  ----  -------  ---   ---\n" "-----" "----------"
for f in "$RESULTS"/*.json; do
  [ -f "$f" ] || continue
  python3 -c "
import json, sys
d = json.load(open('$f'))
a = d.get('auto_summary', {})
j = d.get('judge_averages', {})
ira = d.get('inter_rater_agreement', {})
overall = d.get('overall_judge_score', '')
mstd = d.get('mean_judge_score_std', '')
runs = d.get('runs_per_scenario', 1)
auto = f\"P:{a.get('PASS',0)} W:{a.get('WARN',0)} F:{a.get('FAIL',0)}\"
atm = f\"{j.get('atmosphere','?')}\" if j else '-'
npc = f\"{j.get('npc_craft','?')}\" if j else '-'
gmc = f\"{j.get('gm_craft','?')}\" if j else '-'
ira_mean = f\"{ira.get('mean','?')}\" if ira else '-'
std_str = f\"{mstd}\" if mstd != '' else '-'
print(f\"{d['model']:<55}  {auto:<14}  {atm:<5} {npc:<5} {gmc:<5} {str(overall):<8} {std_str:<5} {ira_mean}  (n={runs})\")
" 2>/dev/null
done | sort -t'=' -k4 -rn

echo ""
echo "━━━ HIGHLIGHT REEL ━━━"
for f in "$RESULTS"/*.json; do
  [ -f "$f" ] || continue
  python3 -c "
import json
d = json.load(open('$f'))
overall = d.get('overall_judge_score', '?')
n_judges = len(set(
    j for c in d.get('cases', [])
    for j in c.get('multi_judge', {}).get('per_judge', {}).keys()
))
print(f\"\n--- {d['model']} (overall: {overall}, judges: {n_judges}) ---\")
for c in d.get('cases', []):
    hl = c.get('highlight', '')
    if hl:
        print(f\"  [{c['id']}] {hl}\")
" 2>/dev/null
done

echo ""
echo "━━━ INTER-RATER AGREEMENT ━━━"
python3 -c "
import json, os, glob
files = glob.glob('$RESULTS/*.json')
print(f'Models with IRA data: {sum(1 for f in files if json.load(open(f)).get(\"inter_rater_agreement\"))}')
iras = [json.load(open(f)).get('inter_rater_agreement', {}) for f in files]
iras = [i for i in iras if i.get('mean')]
if iras:
    mean_r = round(sum(i['mean'] for i in iras) / len(iras), 3)
    print(f'Mean Pearson r across all models: {mean_r}')
    if mean_r >= 0.7:
        print('✓ Strong inter-judge agreement — scoring methodology is consistent')
    elif mean_r >= 0.5:
        print('~ Moderate agreement — results directionally valid')
    else:
        print('✗ Low agreement — interpret scores with caution')
" 2>/dev/null
