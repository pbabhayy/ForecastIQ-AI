"""
Config: Settings
================
Runtime configuration loaded from environment (.env).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Environment-driven application settings."""

    groq_api_key: str
    groq_model: str
    ollama_base_url: str
    ollama_model: str
    ai_provider_order: tuple[str, ...]
    log_level: str
    db_path: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings (reload only on process restart)."""
    order = os.getenv("AI_PROVIDER_ORDER", "groq,ollama,rule_based")
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip(),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        ai_provider_order=tuple(p.strip() for p in order.split(",") if p.strip()),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        db_path=os.getenv("FORECASTIQ_DB_PATH", "database/forecastiq.db"),
    )
