"""
AI: Ollama Provider (Secondary)
===============================
Local/self-hosted Ollama implementation of :class:`BaseAIProvider`.
"""

from __future__ import annotations

import json
from typing import Any

from ai.base_provider import BaseAIProvider, PROVIDER_OLLAMA, parse_llm_json, utc_now
from ai.groq_provider import _insights_prompt, _normalize_insights, _normalize_recommendations
from ai.groq_provider import _recommendations_prompt, _SYSTEM
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


class OllamaProvider(BaseAIProvider):
    """Secondary provider targeting a local Ollama server."""

    name = PROVIDER_OLLAMA

    def is_available(self) -> bool:
        settings = get_settings()
        if not settings.ollama_base_url:
            return False
        try:
            import socket
            from urllib.parse import urlparse

            parsed = urlparse(settings.ollama_base_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 11434
            if host in {"localhost", "127.0.0.1", "::1"}:
                host = "127.0.0.1"
            with socket.create_connection((host, port), timeout=1.0):
                pass

            import httpx

            base = settings.ollama_base_url.rstrip("/")
            with httpx.Client(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
                response = client.get(f"{base}/api/tags")
                response.raise_for_status()
            return True
        except Exception:
            return False

    def generate_insights(self, context: dict[str, Any]) -> dict[str, Any]:
        raw = self._complete(_insights_prompt(context))
        return _normalize_insights(parse_llm_json(raw), self.name)

    def generate_recommendations(self, context: dict[str, Any]) -> dict[str, Any]:
        raw = self._complete(_recommendations_prompt(context))
        return _normalize_recommendations(parse_llm_json(raw), self.name)

    def chat(self, messages: list[dict[str, str]], *, context: str = "") -> str:
        settings = get_settings()
        import ollama

        system = (
            "You are the AI Business Analyst for ForecastIQ. "
            "Answer only using the provided data context. Be specific and cite numbers. "
            "If the context is insufficient, say so clearly.\n\n"
            f"DATA CONTEXT:\n{context}"
        )
        client = ollama.Client(host=settings.ollama_base_url, timeout=120.0)
        response = client.chat(
            model=settings.ollama_model,
            messages=[{"role": "system", "content": system}, *messages],
            options={"temperature": 0.3},
        )
        content = response.get("message", {}).get("content", "")
        if not content.strip():
            raise ValueError("Empty Ollama chat response.")
        return content.strip()

    def _complete(self, prompt: str) -> str:
        settings = get_settings()
        try:
            import ollama
        except ImportError as exc:
            raise RuntimeError("ollama package not installed.") from exc

        try:
            client = ollama.Client(host=settings.ollama_base_url)
            response = client.chat(
                model=settings.ollama_model,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.3},
            )
            content = response.get("message", {}).get("content", "")
            if not content.strip():
                raise ValueError("Empty Ollama response.")
            return content
        except Exception as exc:
            logger.warning("Ollama request failed: %s", exc)
            raise
