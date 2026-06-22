"""
AI: Base Provider
=================
Abstract provider interface and the unified AI response contract.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Final

from utils import column_mapper
from utils.logger import get_logger

logger = get_logger(__name__)

PROVIDER_GROQ: Final[str] = "groq"
PROVIDER_OLLAMA: Final[str] = "ollama"
PROVIDER_RULE_BASED: Final[str] = "rule_based"


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_response(provider: str = PROVIDER_RULE_BASED) -> dict[str, Any]:
    """Return an empty unified AI response contract."""
    return {
        "summary": "",
        "insights": [],
        "recommendations": [],
        "risks": [],
        "opportunities": [],
        "provider": provider,
        "generated_at": utc_now(),
    }


def merge_responses(insights_part: dict[str, Any], recs_part: dict[str, Any]) -> dict[str, Any]:
    """Merge insight-engine and recommendation-engine outputs."""
    provider = insights_part.get("provider") or recs_part.get("provider") or PROVIDER_RULE_BASED
    return {
        "summary": insights_part.get("summary") or recs_part.get("summary") or "",
        "insights": insights_part.get("insights") or [],
        "recommendations": recs_part.get("recommendations") or [],
        "risks": insights_part.get("risks") or [],
        "opportunities": insights_part.get("opportunities") or [],
        "provider": provider,
        "generated_at": insights_part.get("generated_at") or recs_part.get("generated_at") or utc_now(),
    }


def build_context(
    analytics: dict[str, Any] | None,
    health: dict[str, Any] | None,
    forecast: dict[str, Any] | None,
    evaluation: dict[str, Any] | None,
    *,
    dataset_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a serializable context from existing session payloads."""
    analytics = analytics or {}
    health = health or {}
    forecast = forecast or {}
    if evaluation is None:
        evaluation = forecast.get("evaluation") or {}
    profile = dataset_profile or {}

    return {
        "meta": analytics.get("meta", {}),
        "profile": {
            "row_count": profile.get("row_count"),
            "date_range": profile.get("date_range_label"),
            "quality_score": profile.get("data_quality_score"),
            "metrics": profile.get("detected_metrics") or analytics.get("meta", {}).get("metrics", []),
        },
        "revenue": _slim_metric(analytics.get(column_mapper.REVENUE, {})),
        "orders": _slim_metric(analytics.get(column_mapper.ORDERS, {})),
        "customers": _slim_metric(analytics.get(column_mapper.CUSTOMERS, {})),
        "expenses": _slim_metric(analytics.get(column_mapper.EXPENSES, {})),
        "profit": analytics.get("profit") or {},
        "health": {
            "score": health.get("score"),
            "category": health.get("category"),
            "breakdown": health.get("breakdown", {}),
        },
        "forecast": {
            "ok": forecast.get("ok", False),
            "metric": forecast.get("metric"),
            "model": forecast.get("model_label") or forecast.get("model"),
            "horizon": forecast.get("horizon"),
            "growth_pct": forecast.get("growth_pct"),
            "peak_month": forecast.get("peak_month"),
            "lowest_month": forecast.get("lowest_month"),
            "annual_projection": forecast.get("annual_projection"),
        },
        "evaluation": {
            "mae": evaluation.get("mae"),
            "rmse": evaluation.get("rmse"),
            "mape": evaluation.get("mape"),
            "confidence_score": evaluation.get("confidence_score"),
            "confidence_rating": evaluation.get("confidence_rating"),
            "method": evaluation.get("method"),
            "notes": evaluation.get("notes"),
        },
    }


class BaseAIProvider(ABC):
    """Abstract AI provider."""

    name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider can be invoked."""

    @abstractmethod
    def generate_insights(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return partial contract: summary, insights, risks, opportunities."""

    @abstractmethod
    def generate_recommendations(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return partial contract: recommendations."""


def parse_llm_json(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from an LLM response."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("Could not parse JSON from model response.")


def _slim_metric(block: dict[str, Any]) -> dict[str, Any]:
    if not block:
        return {}
    return {
        "total": block.get("total"),
        "average": block.get("average"),
        "growth_pct": block.get("growth_pct"),
        "monthly_growth_pct": block.get("monthly_growth_pct"),
        "trend": block.get("trend"),
        "trend_strength": block.get("trend_strength"),
        "highest_month": block.get("highest_month"),
        "lowest_month": block.get("lowest_month"),
    }
