"""
llm_utils.py — Unified LLM caller (Gemini)
Drop-in replacement for the former AWS Bedrock / Nova implementation.
"""

import os
import logging

log = logging.getLogger("llm_utils")

_gemini_model = None

def _get_model():
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    return _gemini_model


def invoke_llm(prompt: str, fallback_msg: str = "") -> str:
    """
    Send a prompt to Gemini and return the text response.
    Returns fallback_msg on any error.
    """
    try:
        model = _get_model()
        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 1024, "temperature": 0.4},
        )
        text = response.text.strip()
        log.info(f"[llm_utils] Gemini responded ({len(text)} chars)")
        return text
    except Exception as exc:
        log.error(f"[llm_utils] Gemini call failed: {exc}")
        return fallback_msg