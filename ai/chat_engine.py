"""
AI: Chat Engine
===============
RAG-augmented chat via the existing Groq → Ollama provider chain.
No rule-based fallback for chat — providers must be configured.
"""

from __future__ import annotations

import time
from typing import Any, Iterator

from ai.base_provider import PROVIDER_GROQ, PROVIDER_OLLAMA, BaseAIProvider
from ai.groq_provider import GroqProvider
from ai.ollama_provider import OllamaProvider
from config.settings import get_settings
from rag.retriever import retrieve_context
from utils.logger import get_logger

logger = get_logger(__name__)

_CHAT_SYSTEM_HINT = (
    "You are the AI Business Analyst for ForecastIQ. "
    "Answer only using the provided data context. Be specific and reference actual numbers."
)


def chat_available() -> bool:
    """Whether any LLM provider can handle chat."""
    return GroqProvider().is_available() or OllamaProvider().is_available()


def generate_chat_reply(
    question: str,
    history: list[dict[str, str]],
    *,
    dataset_id: int | None,
) -> tuple[str, str]:
    """Return ``(reply_text, provider_name)`` or raise RuntimeError if no provider."""
    chunks = retrieve_context(question, dataset_id, top_k=4)
    context = "\n\n".join(f"- {c}" for c in chunks) if chunks else "(No indexed context yet.)"
    messages = [{"role": m["role"], "content": m["content"]} for m in history[-8:]]
    messages.append({"role": "user", "content": question})

    for provider in _resolve_chat_providers():
        if not provider.is_available():
            continue
        try:
            reply = provider.chat(messages, context=context)
            if reply:
                logger.info("Chat reply via '%s'.", provider.name)
                return reply, provider.name
        except Exception:
            logger.exception("Chat provider '%s' failed.", provider.name)

    raise RuntimeError(
        "No chat provider available. Configure GROQ_API_KEY or start Ollama locally."
    )


def stream_reply_text(text: str, *, delay: float = 0.012) -> Iterator[str]:
    """Yield characters for a typing-effect stream in Streamlit."""
    for char in text:
        yield char
        time.sleep(delay)


def _resolve_chat_providers() -> list[BaseAIProvider]:
    registry = {PROVIDER_GROQ: GroqProvider(), PROVIDER_OLLAMA: OllamaProvider()}
    order = get_settings().ai_provider_order
    providers: list[BaseAIProvider] = []
    seen: set[str] = set()
    for key in order:
        if key in seen:
            continue
        seen.add(key)
        if key in registry:
            providers.append(registry[key])
    return providers
