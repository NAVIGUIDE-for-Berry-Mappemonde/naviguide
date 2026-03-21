"""
NavSecOps / GitLab Duo-style endpoints.

Gemini: /duo/validate, /duo/risk
Claude: /duo/briefing (consumes structured JSON from risk step)
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

log = logging.getLogger("naviguide.duo")

_WS = Path(__file__).resolve().parents[1] / "naviguide_workspace"
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from llm_utils import (  # noqa: E402
    duo_risk_assessment,
    duo_validate_route,
    invoke_claude_briefing_from_analysis,
)

router = APIRouter(prefix="/duo", tags=["duo-navsecops"])


class GeoJSONRequest(BaseModel):
    geojson: Dict[str, Any] = Field(..., description="GeoJSON Feature, FeatureCollection, or Geometry")


class BriefingRequest(BaseModel):
    analysis: Dict[str, Any] = Field(
        ...,
        description="Structured risk output from POST /duo/risk",
    )
    validation: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional structured output from POST /duo/validate",
    )
    language: str = Field("en", description="en or fr")


@router.post("/validate")
async def duo_validate(req: GeoJSONRequest):
    """Gemini — structural validation of route GeoJSON."""
    try:
        result = await asyncio.to_thread(duo_validate_route, req.geojson)
        return {"provider": "google_gemini", "model_env": "GEMINI_MODEL", "result": result}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"error": "gemini_unavailable", "message": str(exc)}) from exc
    except Exception as exc:
        log.exception("duo_validate failed")
        raise HTTPException(
            status_code=502,
            detail={"error": "gemini_failed", "message": str(exc)},
        ) from exc


@router.post("/risk")
async def duo_risk(req: GeoJSONRequest):
    """Gemini — spatial / maritime risk digest (JSON for Claude briefing)."""
    try:
        result = await asyncio.to_thread(duo_risk_assessment, req.geojson)
        return {"provider": "google_gemini", "model_env": "GEMINI_MODEL", "result": result}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"error": "gemini_unavailable", "message": str(exc)}) from exc
    except Exception as exc:
        log.exception("duo_risk failed")
        raise HTTPException(
            status_code=502,
            detail={"error": "gemini_failed", "message": str(exc)},
        ) from exc


@router.post("/briefing")
async def duo_briefing(req: BriefingRequest):
    """
    Claude — skipper report from structured Gemini analysis.
    Does not call Gemini; returns 503 if Anthropic is not configured or fails.
    """
    try:
        text = await asyncio.to_thread(
            invoke_claude_briefing_from_analysis,
            req.analysis,
            req.validation,
            req.language,
        )
    except Exception as exc:
        log.exception("duo_briefing failed")
        raise HTTPException(
            status_code=502,
            detail={"error": "claude_failed", "message": str(exc)},
        ) from exc

    if not text:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "claude_unavailable",
                "message": "ANTHROPIC_API_KEY missing or Claude call returned no text",
            },
        )
    return {"provider": "anthropic_claude", "model_env": "ANTHROPIC_MODEL", "briefing": text}
