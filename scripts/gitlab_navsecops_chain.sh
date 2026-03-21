#!/usr/bin/env bash
# Simulate GitLab Duo agent chain: validate (Gemini) → risk (Gemini) → briefing (Claude).
# Usage: ./scripts/gitlab_navsecops_chain.sh [BASE_URL]
set -euo pipefail
BASE="${1:-http://127.0.0.1:8001}"
SAMPLE='{"geojson":{"type":"Feature","properties":{"name":"test-leg"},"geometry":{"type":"LineString","coordinates":[[-1.15,46.15],[-4.5,48.4],[-5.0,36.0]]}}}'

echo "== POST $BASE/duo/validate"
VALIDATION=$(curl -sS -X POST "$BASE/duo/validate" -H "Content-Type: application/json" -d "$SAMPLE")
echo "$VALIDATION" | head -c 2000
echo ""

echo "== POST $BASE/duo/risk"
RISK=$(curl -sS -X POST "$BASE/duo/risk" -H "Content-Type: application/json" -d "$SAMPLE")
echo "$RISK" | head -c 2000
echo ""

ANALYSIS=$(echo "$RISK" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('result',{})))" 2>/dev/null || echo "{}")
VALID_BLOCK=$(echo "$VALIDATION" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('result',{})))" 2>/dev/null || echo "{}")

echo "== POST $BASE/duo/briefing"
curl -sS -X POST "$BASE/duo/briefing" -H "Content-Type: application/json" \
  -d "{\"analysis\":$ANALYSIS,\"validation\":$VALID_BLOCK,\"language\":\"en\"}" | head -c 4000
echo ""
