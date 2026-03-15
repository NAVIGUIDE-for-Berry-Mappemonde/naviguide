#!/usr/bin/env python3
"""
NAVIGUIDE — Smoke test Bedrock (Nova 2 Lite + Claude fallback)

Lance ce script dès que Bedrock est débloqué pour valider l'accès.

Usage:
  cd naviguide_workspace && python3 ../scripts/test_bedrock.py

Ou avec le path correct pour charger .env:
  python3 scripts/test_bedrock.py

Prérequis: naviguide_workspace/.env avec AWS_ACCESS_KEY_ID ou AWS_BEARER_TOKEN_BEDROCK
"""

import os
import sys
from pathlib import Path

# Add naviguide_workspace to path and load .env
ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "naviguide_workspace"
if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

# Load .env before any Bedrock imports
try:
    from dotenv import load_dotenv
    load_dotenv(WS / ".env")
except ImportError:
    pass

# Check credentials
has_iam = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
has_bedrock_key = bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))
if not has_iam and not has_bedrock_key:
    print("❌ No credentials. Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or AWS_BEARER_TOKEN_BEDROCK in naviguide_workspace/.env")
    sys.exit(1)

print("Credentials: IAM" if has_iam else "Credentials: Bedrock API key")
print("Testing invoke_llm...")

from llm_utils import invoke_llm

result = invoke_llm("Say hello in exactly 3 words.", fallback_msg="LLM unavailable")
if result:
    print(f"✅ Bedrock OK: {result[:80]}{'...' if len(result) > 80 else ''}")
    sys.exit(0)
else:
    print("❌ invoke_llm returned None — Bedrock still blocked or misconfigured")
    sys.exit(1)
