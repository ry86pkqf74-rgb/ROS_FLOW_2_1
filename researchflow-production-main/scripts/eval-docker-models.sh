#!/usr/bin/env bash
# ============================================
# ResearchFlow – Docker/Ollama model evaluation
# ============================================
# Evaluates availability and latency of Docker stack models (Ollama front-end).
# Run from terminal anytime; can be triggered by cron or n8n.
#
# Usage:
#   ./scripts/eval-docker-models.sh           # use OLLAMA_BASE_URL or default
#   OLLAMA_BASE_URL=http://ollama:11434 ./scripts/eval-docker-models.sh
#   LOG_DIR=/var/log/researchflow ./scripts/eval-docker-models.sh  # persist log
# ============================================

set -e

BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
# OpenAI-compatible endpoint
API_URL="${BASE_URL%/}/v1/chat/completions"
LOG_DIR="${LOG_DIR:-.}"
LOG_FILE="${LOG_DIR}/docker-models-eval.log"
MODELS="${EVAL_MODELS:-qwen3-coder,devstral-small-2}"   # comma-separated; add kimi-k2-vllm if available

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════════════"
echo "  Docker/Ollama model evaluation"
echo "  API: $API_URL"
echo "═══════════════════════════════════════════════════════════"

# Check base connectivity
if ! curl -sf "${BASE_URL%/}/api/tags" > /dev/null 2>&1; then
  echo -e "${RED}✗${NC} Ollama not reachable at $BASE_URL. Start the stack or set OLLAMA_BASE_URL."
  exit 1
fi
echo -e "${GREEN}✓${NC} Ollama reachable"

SUCCESS=0
FAIL=0

for model in $(echo "$MODELS" | tr ',' ' '); do
  start=$(date +%s.%N)
  http_code=$(curl -sf -o /dev/null -w "%{http_code}" \
    -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"Say OK in one word.\"}],\"max_tokens\":5}" \
    2>/dev/null || echo "000")
  end=$(date +%s.%N)
  if command -v python3 &>/dev/null; then
    latency_ms=$(python3 -c "print(round(($end - $start) * 1000))" 2>/dev/null || echo "?")
  else
    latency_ms="?"
  fi
  if [ "$http_code" = "200" ]; then
    echo -e "  ${GREEN}✓${NC} $model (${latency_ms}ms)"
    SUCCESS=$((SUCCESS + 1))
    line="$(date -u +%Y-%m-%dT%H:%M:%SZ) ok $model ${latency_ms}ms"
  else
    echo -e "  ${RED}✗${NC} $model (HTTP $http_code)"
    FAIL=$((FAIL + 1))
    line="$(date -u +%Y-%m-%dT%H:%M:%SZ) fail $model HTTP $http_code"
  fi
  [ -n "$LOG_DIR" ] && [ -d "$LOG_DIR" ] && echo "$line" >> "$LOG_FILE"
done

echo "───────────────────────────────────────────────────────────"
echo "  Pass: $SUCCESS  Fail: $FAIL"
if [ -f "$LOG_FILE" ]; then
  echo "  Log: $LOG_FILE"
fi
echo "═══════════════════════════════════════════════════════════"
[ "$FAIL" -gt 0 ] && exit 1
exit 0
