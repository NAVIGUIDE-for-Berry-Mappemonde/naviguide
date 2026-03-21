"""
NAVIGUIDE Simulation Agents — Claude (Anthropic API)

Per-leg SSE agents and LangGraph nodes use Anthropic Claude via naviguide_workspace/llm_utils.
NavSecOps raw analysis uses Gemini on POST /duo/validate and /duo/risk (see naviguide_duo).

Modes:
  - call_llm()   : synchronous (LangGraph agent nodes)
  - stream_llm() : async generator, word-chunk streaming (FastAPI SSE)
"""

import os
import sys
from pathlib import Path
from typing import AsyncIterator, Tuple

from dotenv import load_dotenv

# Add naviguide_workspace to path and load its .env (override API .env for ANTHROPIC_API_KEY)
_WS = Path(__file__).resolve().parents[2] / "naviguide_workspace"
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))
load_dotenv(_WS / ".env", override=True)


def call_llm(prompt: str, system: str = "") -> Tuple[str, str]:
    """
    Send a prompt via Nova + Claude fallback (Bedrock).
    Used internally by LangGraph agent nodes.

    Returns:
        (content, data_freshness) where data_freshness is 'training_only'.
    Falls back to ("", "training_only") when the service is unavailable.
    """
    try:
        from llm_utils import invoke_llm
        content = invoke_llm(prompt, system=system, fallback_msg="")
        return (content or "", "training_only")
    except Exception:
        return "", "training_only"


async def stream_llm(prompt: str, system: str = "") -> AsyncIterator[str]:
    """
    Stream tokens via Nova + Claude fallback (Bedrock).
    Async generator — yields tokens for SSE progressive display.
    """
    try:
        from llm_utils import stream_llm as _stream
        async for token in _stream(prompt, system=system):
            yield token
    except Exception:
        return
