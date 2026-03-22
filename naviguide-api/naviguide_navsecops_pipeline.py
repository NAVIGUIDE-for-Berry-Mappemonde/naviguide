"""
NavSecOps — Single-pass analysis pipeline.

POST /api/v1/navsecops/analyze

Server-side chain: validate (Gemini) -> risk (Gemini) -> briefing (Claude).
Returns a unified JSON response with partial-failure support.

Import strategy: same sys.path pattern as naviguide_duo.py — adds
naviguide_workspace/ to sys.path so that llm_utils is importable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

# -- sys.path for llm_utils (same pattern as naviguide_duo.py) --------
_WS = Path(__file__).resolve().parents[1] / "naviguide_workspace"
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from llm_utils import (  # noqa: E402
    CLAUDE_ANTHROPIC_MODEL,
    GEMINI_MODEL,
    duo_risk_assessment,
    duo_validate_route,
    invoke_claude_briefing_from_analysis,
)

from naviguide_navsecops_auth import verify_navsecops_token  # noqa: E402

log = logging.getLogger("navsecops.pipeline")

router = APIRouter(tags=["navsecops"])


# -- Request / Response models -----------------------------------------


class AnalyzeRequest(BaseModel):
    geojson: Dict[str, Any] = Field(
        ..., description="GeoJSON Feature, FeatureCollection, or Geometry"
    )
    language: str = Field("fr", description="Briefing language: 'en' or 'fr'")


class StageError(BaseModel):
    stage: str
    error: str


class AnalyzeMeta(BaseModel):
    request_id: str
    duration_ms: int
    models: List[str]
    stages_ok: int
    stages_failed: int


class AnalyzeResponse(BaseModel):
    status: str = Field(
        ..., description="'complete' | 'partial' | 'failed'"
    )
    validation: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    briefing: Optional[str] = None
    errors: List[StageError] = []
    meta: AnalyzeMeta


# -- Endpoint ----------------------------------------------------------


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    req: AnalyzeRequest,
    _token: str = Depends(verify_navsecops_token),
):
    """
    Single-pass NavSecOps analysis.

    Chain: validate (Gemini) -> risk (Gemini) -> briefing (Claude).
    Each stage is independent in error handling:
    - validate failure -> status 'failed', skip downstream.
    - risk failure -> briefing skipped, status 'partial'.
    - briefing failure or None -> status 'partial'.
    """
    request_id = str(uuid.uuid4())
    t0 = time.monotonic()
    errors: List[StageError] = []
    validation: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    briefing: Optional[str] = None

    # -- Stage 1: validate (blocking -- if this fails, skip everything) --
    try:
        validation = await asyncio.to_thread(duo_validate_route, req.geojson)
    except Exception as exc:
        log.exception("[navsecops:%s] validate failed", request_id)
        errors.append(StageError(stage="validate", error=str(exc)))
        return AnalyzeResponse(
            status="failed",
            errors=errors,
            meta=_build_meta(request_id, t0, errors),
        )

    # -- Stage 2: risk (continue on failure) -----------------------------
    try:
        risk = await asyncio.to_thread(duo_risk_assessment, req.geojson)
    except Exception as exc:
        log.exception("[navsecops:%s] risk failed", request_id)
        errors.append(StageError(stage="risk", error=str(exc)))

    # -- Stage 3: briefing (needs risk; skip if risk failed) -------------
    if risk is not None:
        try:
            briefing = await asyncio.to_thread(
                invoke_claude_briefing_from_analysis,
                risk,
                validation,
                req.language,
            )
            # invoke_claude_briefing_from_analysis returns None when
            # ANTHROPIC_API_KEY is missing or Claude call fails internally.
            if briefing is None:
                errors.append(
                    StageError(
                        stage="briefing",
                        error="Claude returned None (key missing or upstream error)",
                    )
                )
        except Exception as exc:
            log.exception("[navsecops:%s] briefing failed", request_id)
            errors.append(StageError(stage="briefing", error=str(exc)))
    else:
        errors.append(
            StageError(stage="briefing", error="Skipped: risk stage failed")
        )

    # -- Response --------------------------------------------------------
    status = "complete" if not errors else "partial"
    meta = _build_meta(request_id, t0, errors)

    # Structured log line (one JSON dict per request)
    log.info(
        json.dumps(
            {
                "event": "navsecops_analyze",
                "request_id": request_id,
                "status": status,
                "duration_ms": meta.duration_ms,
                "stages_ok": meta.stages_ok,
                "stages_failed": meta.stages_failed,
                "errors": [e.stage for e in errors],
            }
        )
    )

    return AnalyzeResponse(
        status=status,
        validation=validation,
        risk=risk,
        briefing=briefing,
        errors=errors,
        meta=meta,
    )


# -- Helpers -----------------------------------------------------------


def _build_meta(
    request_id: str, t0: float, errors: List[StageError]
) -> AnalyzeMeta:
    return AnalyzeMeta(
        request_id=request_id,
        duration_ms=round((time.monotonic() - t0) * 1000),
        models=[GEMINI_MODEL, CLAUDE_ANTHROPIC_MODEL],
        stages_ok=3 - len(errors),
        stages_failed=len(errors),
    )
