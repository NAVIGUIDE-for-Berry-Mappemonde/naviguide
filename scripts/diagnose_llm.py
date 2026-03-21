#!/usr/bin/env python3
"""
NAVIGUIDE — Diagnostic LLM (Gemini + Claude Anthropic API)

Usage: python3 scripts/diagnose_llm.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "naviguide_workspace"
if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

from dotenv import load_dotenv

load_dotenv(WS / ".env")

from llm_utils import CLAUDE_ANTHROPIC_MODEL  # noqa: E402


def check_env():
    has_gemini = bool(os.getenv("GEMINI_API_KEY", "").strip())
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    has_sm = bool(os.getenv("GEMINI_SECRET_RESOURCE", "").strip())
    return {
        "GEMINI_API_KEY": "***" if has_gemini else None,
        "GEMINI_SECRET_RESOURCE": has_sm,
        "ANTHROPIC_API_KEY": "***" if has_anthropic else None,
    }


def test_gemini():
    if not os.getenv("GEMINI_API_KEY", "").strip() and not os.getenv("GEMINI_SECRET_RESOURCE", "").strip():
        return ("SKIP", "GEMINI_API_KEY / GEMINI_SECRET_RESOURCE non définis")
    try:
        from llm_utils import _gemini_json

        out = _gemini_json(
            "Reply with JSON only: {\"ok\": true, \"msg\": string}",
            'Return {"ok": true, "msg": "pong"}',
        )
        if out.get("ok"):
            return ("OK", str(out.get("msg", ""))[:50])
        return ("FAIL", str(out)[:80])
    except Exception as e:
        return ("FAIL", str(e))


def test_anthropic_api():
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return ("SKIP", "ANTHROPIC_API_KEY non défini")
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=CLAUDE_ANTHROPIC_MODEL,
            max_tokens=64,
            messages=[{"role": "user", "content": "Say hi in 3 words"}],
        )
        text = msg.content[0].text if msg.content else ""
        return ("OK", text[:50] if text else "")
    except Exception as e:
        return ("FAIL", str(e))


def main():
    print("=" * 60)
    print("NAVIGUIDE — Diagnostic LLM (Gemini + Claude)")
    print("=" * 60)

    env = check_env()
    print("\n1. Variables d'environnement:")
    for k, v in env.items():
        if v is True:
            print(f"   {k}: ✓")
        elif v:
            print(f"   {k}: {v}")
        else:
            print(f"   {k}: ✗")

    print("\n2. Gemini (analyse /duo/*):")
    g = test_gemini()
    print(f"   {g[0]}: {g[1][:120]}")

    print("\n3. Claude API Anthropic (briefing / agents):")
    a = test_anthropic_api()
    print(f"   {a[0]}: {a[1][:120]}")

    print("\n" + "=" * 60)
    any_ok = g[0] == "OK" or a[0] == "OK"
    if any_ok:
        print("→ Au moins un provider fonctionne.")
    else:
        print("→ Vérifier GEMINI_API_KEY et ANTHROPIC_API_KEY dans naviguide_workspace/.env")
    print("=" * 60)
    sys.exit(0 if any_ok else 1)


if __name__ == "__main__":
    main()
