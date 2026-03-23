"""
NAVIGUIDE — Dual LLM stack (NavSecOps / hackathon Google + Anthropic).

- Gemini: raw GeoJSON analysis (/duo/validate, /duo/risk) via google-genai.
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

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
CLAUDE_ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

_gemini_client = None


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


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        _gemini_client = genai.Client(api_key=_gemini_api_key())
    return _gemini_client


def _slice_first_balanced_json_object(text: str) -> Optional[str]:
    """Extract substring from first '{' through matching '}' (string-aware)."""
    i = text.find("{")
    if i < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for j in range(i, len(text)):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[i : j + 1]
    return None


def _strip_markdown_code_fence(text: str) -> str:
    """Remove optional ```json / ``` wrappers (handles missing closing fence)."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, count=1, flags=re.IGNORECASE)
    t = re.sub(r"\s*```\s*$", "", t).strip()
    return t


def _extract_json_object(text: str) -> Dict[str, Any]:
    """
    Parse a JSON object from Gemini output: raw JSON, fenced ```json, or prose prefix.
    """
    original = text.strip()
    candidates: list[str] = []

    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", original, flags=re.IGNORECASE)
    if m:
        candidates.append(m.group(1).strip())
    stripped = _strip_markdown_code_fence(original)
    if stripped != original.strip() or not m:
        candidates.append(stripped)
    candidates.append(original)

    for blob in (stripped, original):
        balanced = _slice_first_balanced_json_object(blob)
        if balanced and balanced not in candidates:
            candidates.insert(0, balanced)

    seen: set[str] = set()
    for cand in candidates:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        try:
            data = json.loads(cand)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    tail = stripped[:800] if stripped else original[:800]
    raise ValueError(f"Gemini did not return valid JSON object: {tail}...")


def _gemini_json(
    system: str, user: str, *, max_output_tokens: int = 4096
) -> Dict[str, Any]:
    from google.genai import types

    client = _get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_output_tokens,
            temperature=0.2,
        ),
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
        "You are a maritime GIS validator for offshore sailing routes. "
        "Reply with exactly one JSON object: raw JSON only, "
        "no markdown, no code fences, no preamble or trailing commentary. "
        'Schema: {"valid": bool, "geometry_type": string, "waypoint_count": int, '
        '"issues": [string], "bbox_hint": {"min_lat": number, "max_lat": number, '
        '"min_lon": number, "max_lon": number} or null}. '
        "Checks to perform: "
        "coordinates must be [lon, lat] order (lon -180..180, lat -90..90), "
        "if any lat > 90 flag as likely swapped; "
        "antimeridian crossings may use unwrapped lon beyond \u00b1180 (valid, not an error); "
        "flag segments longer than 3000 nm (missing intermediate waypoints); "
        "flag duplicate consecutive waypoints (< 0.001 deg apart); "
        "geometry must be LineString or MultiLineString; "
        "for FeatureCollection count LineString features as legs, Point features as waypoints."
    )
    user = f"Validate this GeoJSON for use as a sailing route (coordinates lon, lat order):\n{json.dumps(geojson, ensure_ascii=False)[:120000]}"
    return _gemini_json(system, user)


def duo_risk_assessment(geojson: Dict[str, Any]) -> Dict[str, Any]:
    """
    High-level spatial risk digest (Gemini). Output is consumed by Claude for /duo/briefing.
    """
    system = (
        "You are NAVIGUIDE maritime risk analysis for a 13.5 m catamaran "
        "(draft 1.8 m, beam-reach optimised, crew of 2-4). "
        "Output exactly one JSON object: raw JSON only, "
        "no markdown, no code fences (no ```), no preamble or trailing commentary. "
        'Schema: {"overall_risk": "LOW"|"MODERATE"|"HIGH"|"CRITICAL", "risk_score": number 0-1, '
        '"segments": [{"label": string, "risk": string, "notes": string}], '
        '"piracy_notes": string, "weather_notes": string, "anti_shipping_notes": string, '
        '"recommendations": [string]}. '
        "Risk knowledge: "
        "piracy CRITICAL zones \u2014 Gulf of Aden (11-15\u00b0N 43-52\u00b0E), "
        "Gulf of Guinea (0-5\u00b0N 2\u00b0W-8\u00b0E), Malacca Strait (1-4\u00b0N 100-104\u00b0E), "
        "Sulu-Celebes Sea (5-8\u00b0N 118-125\u00b0E); "
        "cyclone seasons \u2014 Atlantic Jun-Nov, S Pacific Nov-Apr, "
        "N Indian Apr-Jun & Oct-Dec, S Indian Oct-May; "
        "HIGH traffic \u2014 Bay of Biscay, English Channel, Gibraltar Strait, "
        "Suez/Panama approaches, Torres Strait, Singapore Strait; "
        "shallow water \u2014 1.8 m draft limits coral reef passages, "
        "flag segments near atolls, barrier reefs, or uncharted shoals; "
        "Southern Ocean below 40\u00b0S \u2014 extreme weather, no rescue infrastructure. "
        "Use conservative assumptions if data is missing. "
        "Keep segments to at most 24 items; keep each notes field under 350 characters to stay concise."
    )
    user = f"Analyse risks for this expedition route GeoJSON:\n{json.dumps(geojson, ensure_ascii=False)[:120000]}"
    return _gemini_json(system, user, max_output_tokens=8192)


def invoke_claude_briefing_from_analysis(
    analysis: Dict[str, Any],
    validation: Optional[Dict[str, Any]] = None,
    language: str = "en",
) -> Optional[str]:
    """Synthesis-only: Claude turns structured Gemini output into a skipper report."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        log.warning("[llm] ANTHROPIC_API_KEY not set \u2014 skipping Claude briefing")
        return None

    lang = "English" if language.lower().startswith("en") else "French"
    system = (
        f"You are NAVIGUIDE's chief maritime safety officer for the "
        f"Berry-Mappemonde circumnavigation (13.5 m catamaran, draft 1.8 m, "
        f"crew 2-4, La Rochelle round-trip, 36 000 nm). "
        f"Write a concise skipper intelligence report in {lang} (max 320 words). "
        f"Use exactly these section headings in order:\n"
        f"1. EXECUTIVE SUMMARY \u2014 overall risk level, go/no-go factors\n"
        f"2. ROUTE VALIDATION \u2014 structural issues, coordinate quality, segment count\n"
        f"3. KEY RISKS \u2014 ranked by severity, include lat/lon zones when available, "
        f"note seasonal timing\n"
        f"4. RECOMMENDED ACTIONS \u2014 numbered, actionable for offshore crew, "
        f"include departure window advice when season data is available\n"
        f"Base every claim on the JSON facts provided. "
        f"If data is missing, state what is unknown rather than guessing. "
        f"This report informs; it does not have authority to block departure."
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
