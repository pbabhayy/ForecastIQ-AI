"""Lightweight RAG layer (SQLite + Ollama embeddings)."""

from rag.retriever import index_ai_insights, index_analytics, index_forecast, index_profile, retrieve_context

__all__ = [
    "index_profile",
    "index_analytics",
    "index_forecast",
    "index_ai_insights",
    "retrieve_context",
]
