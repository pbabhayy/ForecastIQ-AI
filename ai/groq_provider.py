"""
AI: Groq Provider (Primary)
============================
Groq API implementation of :class:`BaseAIProvider`.
"""

from __future__ import annotations

import json
from typing import Any

from ai.base_provider import BaseAIProvider, PROVIDER_GROQ, parse_llm_json, utc_now
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


class GroqProvider(BaseAIProvider):
    """Primary cloud LLM provider via Groq."""

    name = PROVIDER_GROQ

    def is_available(self) -> bool:
        return bool(get_settings().groq_api_key)

    def generate_insights(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = _insights_prompt(context)
        raw = self._complete(prompt)
        data = parse_llm_json(raw)
        return _normalize_insights(data, self.name)

    def generate_recommendations(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = _recommendations_prompt(context)
        raw = self._complete(prompt)
        data = parse_llm_json(raw)
        return _normalize_recommendations(data, self.name)

    def chat(self, messages: list[dict[str, str]], *, context: str = "") -> str:
        settings = get_settings()
        if not settings.groq_api_key:
            raise RuntimeError("Groq API key not configured.")
        from groq import Groq

        system = (
            "You are the AI Business Analyst for ForecastIQ. "
            "Answer only using the provided data context. Be specific and cite numbers. "
            "If the context is insufficient, say so clearly.\n\n"
            f"DATA CONTEXT:\n{context}"
        )
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "system", "content": system}, *messages],
            temperature=0.3,
            max_tokens=1200,
        )
        return (response.choices[0].message.content or "").strip()

    def _complete(self, prompt: str) -> str:
        settings = get_settings()
        if not settings.groq_api_key:
            raise RuntimeError("Groq API key not configured.")

        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("groq package not installed.") from exc

        try:
            client = Groq(api_key=settings.groq_api_key)
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1800,
            )
            content = response.choices[0].message.content or ""
            if not content.strip():
                raise ValueError("Empty Groq response.")
            return content
        except Exception as exc:
            logger.warning("Groq request failed: %s", exc)
            raise


_SYSTEM = (
    "You are a senior business analyst for ForecastIQ AI. "
    "Respond with valid JSON only — no markdown fences, no commentary."
)


def _insights_prompt(context: dict[str, Any]) -> str:
    return (
        "Analyze this business data and return JSON with keys: "
        "summary (string), insights (array of {category, title, body}), "
        "risks (array of {title, body}), "
        "opportunities (array of {title, body}).\n\n"
        f"DATA:\n{json.dumps(context, default=str)}"
    )


def _recommendations_prompt(context: dict[str, Any]) -> str:
    return (
        "Return JSON with key recommendations: array of "
        "{category, title, body, priority} where priority is High, Medium, or Low.\n\n"
        f"DATA:\n{json.dumps(context, default=str)}"
    )


def _normalize_insights(data: dict[str, Any], provider: str) -> dict[str, Any]:
    return {
        "summary": str(data.get("summary", "")),
        "insights": list(data.get("insights") or []),
        "risks": list(data.get("risks") or []),
        "opportunities": list(data.get("opportunities") or []),
        "recommendations": [],
        "provider": provider,
        "generated_at": utc_now(),
    }


def _normalize_recommendations(data: dict[str, Any], provider: str) -> dict[str, Any]:
    return {
        "summary": "",
        "insights": [],
        "risks": [],
        "opportunities": [],
        "recommendations": list(data.get("recommendations") or []),
        "provider": provider,
        "generated_at": utc_now(),
    }
