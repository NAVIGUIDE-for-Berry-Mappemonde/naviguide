"""
NAVIGUIDE — Dual LLM stack (NavSecOps / hackathon Google + Anthropic).

- Gemini: raw GeoJSON analysis (/duo/validate, /duo/risk) via google-generativeai.
- Claude: skipper synthesis (/duo/briefing, orchestrator executive briefing, SSE agents)
  via Anthropic API (ANTHROPIC_API_KEY).

Optional GCP: set GEMINI_SECRET_RESOURCE to a Secret Manager resource name
(projects/…/secrets/…/versions/latest) to load GEMINI_API_KEY when the env var is unset.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, AsyncIterator, Dict, Optional

log = logging.getLogger("naviguide.llm")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
CLAUDE_ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

_gemini_model = None


def _maybe_secret_manager_key() -> Optional[str]:
    resource = os.getenv("GEMINI_SECRET_RESOURCE", "").strip()
    if not resource:
        return None
    try:
        from google.cloud import secretmanager  # type: ignore

        client = secretmanager.SecretManagerServiceClient()
        resp = client.access_secret_version(request={"name": resource})
        return resp.payload.data.decode("UTF-8").strip()
    except Exception as exc:
        log.warning("[llm] Secret Manager GEMINI key failed: %s", exc)
        return None


def _gemini_api_key() -> str:
    k = os.getenv("GEMINI_API_KEY", "").strip()
    if k:
        return k
    k = _maybe_secret_manager_key()
    if k:
        return k
    raise RuntimeError(
        "GEMINI_API_KEY is not set (or GEMINI_SECRET_RESOURCE could not load a key)"
    )


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai

        genai.configure(api_key=_gemini_api_key())
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    return _gemini_model


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    raise ValueError(f"Gemini did not return valid JSON object: {text[:500]}...")


def _gemini_json(system: str, user: str) -> Dict[str, Any]:
    model = _get_gemini_model()
    prompt = f"{system}\n\n{user}"
    response = model.generate_content(
        prompt,
        generation_config={"max_output_tokens": 4096, "temperature": 0.2},
    )
    raw = (response.text or "").strip()
    if not raw:
        raise RuntimeError("Gemini returned empty response")
    log.info("[llm] Gemini JSON response (%d chars)", len(raw))
    return _extract_json_object(raw)


def duo_validate_route(geojson: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structural / navigational validation of a route GeoJSON (Gemini).
    Returns a dict with keys like valid, issues, waypoint_count, geometry_type.
    """
    system = (
        "You are a maritime GIS validator. Reply with a single JSON object only, no markdown. "
        'Schema: {"valid": bool, "geometry_type": string, "waypoint_count": int, '
        '"issues": [string], "bbox_hint": {"min_lat": number, "max_lat": number, '
        '"min_lon": number, "max_lon": number} or null}.'
    )
    user = f"Validate this GeoJSON for use as a sailing route (coordinates lon, lat order):\n{json.dumps(geojson, ensure_ascii=False)[:120000]}"
    return _gemini_json(system, user)


def duo_risk_assessment(geojson: Dict[str, Any]) -> Dict[str, Any]:
    """
    High-level spatial risk digest (Gemini). Output is consumed by Claude for /duo/briefing.
    """
    system = (
        "You are NAVIGUIDE maritime risk analysis. Output a single JSON object only, no markdown. "
        'Schema: {"overall_risk": "LOW"|"MODERATE"|"HIGH"|"CRITICAL", "risk_score": number 0-1, '
        '"segments": [{"label": string, "risk": string, "notes": string}], '
        '"piracy_notes": string, "weather_notes": string, "anti_shipping_notes": string, '
        '"recommendations": [string]}. Use conservative assumptions if data is missing.'
    )
    user = f"Analyse risks for this expedition route GeoJSON:\n{json.dumps(geojson, ensure_ascii=False)[:120000]}"
    return _gemini_json(system, user)


def invoke_claude_briefing_from_analysis(
    analysis: Dict[str, Any],
    validation: Optional[Dict[str, Any]] = None,
    language: str = "en",
) -> Optional[str]:
    """Synthesis-only: Claude turns structured Gemini output into a skipper report."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        log.warning("[llm] ANTHROPIC_API_KEY not set — skipping Claude briefing")
        return None

    lang = "English" if language.lower().startswith("en") else "French"
    system = (
        f"You are NAVIGUIDE's chief maritime safety officer. Write a concise skipper intelligence "
        f"report in {lang} (max 320 words). Use exactly these section headings in order:\n"
        "1. EXECUTIVE SUMMARY\n2. ROUTE VALIDATION\n3. KEY RISKS\n4. RECOMMENDED ACTIONS\n"
        "Base every claim on the JSON facts provided; if data is missing, say so explicitly."
    )
    payload = {"validation": validation or {}, "risk_analysis": analysis}
    prompt = f"Structured analysis JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)[:100000]}"

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=CLAUDE_ANTHROPIC_MODEL,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text if message.content else ""
        out = (text or "").strip()
        if out:
            log.info("[llm] Claude briefing OK (%d chars)", len(out))
            return out
    except Exception as exc:
        log.warning("[llm] Claude briefing failed: %s", exc)
    return None


def invoke_llm(
    prompt: str,
    system: str = "",
    fallback_msg: str = "",
) -> Optional[str]:
    """
    Default LLM path for orchestrator + legacy callers: Claude (Anthropic API).
    Returns None on failure (callers may use static fallback). Does not call Gemini.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        log.warning("[llm] ANTHROPIC_API_KEY not set")
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        kwargs: Dict[str, Any] = {
            "model": CLAUDE_ANTHROPIC_MODEL,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = client.messages.create(**kwargs)
        text = message.content[0].text if message.content else ""
        if text and text.strip():
            log.info("[llm] Claude OK (%d chars)", len(text))
            return text.strip()
    except Exception as exc:
        log.warning("[llm] Claude invoke failed: %s", exc)
    return None


async def stream_llm(
    prompt: str,
    system: str = "",
) -> AsyncIterator[str]:
    """
    Stream tokens for FastAPI SSE: full Claude response, then word-by-word yield
    (simple progressive display compatible with existing AgentPanel).
    """
    try:
        text = await asyncio.to_thread(invoke_llm, prompt, system, "")
        if text:
            for word in text.split():
                yield word + " "
    except Exception as exc:
        log.warning("[llm] stream_llm failed: %s", exc)
