"""
AI: Insight Engine
==================
Provider-agnostic insight generation with deterministic fallback.

Consumes analytics, health, forecast, and evaluation payloads only.
Provider chain: Groq → Ollama → rule-based (never fully fails).
"""

from __future__ import annotations

from typing import Any

from ai.base_provider import (
    PROVIDER_GROQ,
    PROVIDER_OLLAMA,
    PROVIDER_RULE_BASED,
    BaseAIProvider,
    build_context,
    utc_now,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_insights(
    analytics: dict[str, Any] | None,
    health: dict[str, Any] | None,
    forecast: dict[str, Any] | None,
    evaluation: dict[str, Any] | None = None,
    *,
    dataset_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate insights via the provider chain."""
    context = build_context(analytics, health, forecast, evaluation, dataset_profile=dataset_profile)
    for provider in _resolve_providers():
        if not provider.is_available():
            logger.info("Insights: skipping unavailable provider '%s'.", provider.name)
            continue
        try:
            if provider.name == PROVIDER_RULE_BASED:
                result = generate_rule_based_insights(context)
            else:
                result = provider.generate_insights(context)
            if result.get("summary") or result.get("insights"):
                logger.info("Insights generated using '%s'.", result.get("provider", provider.name))
                return result
        except Exception:  # noqa: BLE001
            logger.exception("Insights: provider '%s' failed.", provider.name)

    logger.info("Insights: falling back to rule-based engine.")
    return generate_rule_based_insights(context)


def generate_rule_based_insights(
    context: dict[str, Any], *, provider: str = PROVIDER_RULE_BASED
) -> dict[str, Any]:
    """Deterministic insight generation — always produces output."""
    revenue = context.get("revenue") or {}
    orders = context.get("orders") or {}
    customers = context.get("customers") or {}
    expenses = context.get("expenses") or {}
    health = context.get("health") or {}
    forecast = context.get("forecast") or {}
    evaluation = context.get("evaluation") or {}
    profile = context.get("profile") or {}

    insights: list[dict[str, str]] = []
    risks: list[dict[str, str]] = []
    opportunities: list[dict[str, str]] = []

    score = health.get("score")
    category = health.get("category") or "Unknown"
    rev_growth = float(revenue.get("growth_pct") or 0)
    rev_trend = revenue.get("trend") or "stable"
    conf_score = float(evaluation.get("confidence_score") or 0)
    conf_rating = evaluation.get("confidence_rating") or "—"

    # --- Business summary insight ---
    period = profile.get("date_range") or "the analyzed period"
    summary = (
        f"Business health is {category} ({score}/100) over {period}. "
        f"Revenue trend is {rev_trend} with {rev_growth:+.1f}% overall growth."
    )
    if forecast.get("ok"):
        summary += (
            f" The {forecast.get('horizon')}-month forecast projects "
            f"{float(forecast.get('growth_pct') or 0):+.1f}% change."
        )

    # --- Revenue ---
    if revenue:
        insights.append(
            {
                "category": "Revenue Insights",
                "title": "Revenue performance",
                "body": (
                    f"Total revenue is {_fmt(revenue.get('total'))} with average "
                    f"{_fmt(revenue.get('average'))}/month and {rev_growth:+.1f}% growth. "
                    f"Trend direction: {rev_trend}."
                ),
            }
        )
        if rev_growth < 0:
            risks.append(
                {
                    "title": "Revenue decline",
                    "body": f"Revenue fell {abs(rev_growth):.1f}% over the period — investigate pricing, churn, or seasonality.",
                }
            )
        elif rev_growth > 5:
            opportunities.append(
                {
                    "title": "Revenue momentum",
                    "body": f"Revenue grew {rev_growth:.1f}% — consider reinvesting in acquisition and capacity.",
                }
            )

    # --- Forecast ---
    if forecast.get("ok"):
        insights.append(
            {
                "category": "Forecast Insights",
                "title": "Forward outlook",
                "body": (
                    f"{str(forecast.get('metric', '')).title()} forecast ({forecast.get('model')}) "
                    f"projects {float(forecast.get('growth_pct') or 0):+.1f}% over "
                    f"{forecast.get('horizon')} month(s). Peak: {forecast.get('peak_month')}; "
                    f"weakest: {forecast.get('lowest_month')}."
                ),
            }
        )
    else:
        insights.append(
            {
                "category": "Forecast Insights",
                "title": "No forecast available",
                "body": "Generate a forecast on the Forecasting page to unlock forward-looking insights.",
            }
        )

    # --- Trend ---
    if revenue:
        insights.append(
            {
                "category": "Trend Analysis",
                "title": "Revenue trajectory",
                "body": (
                    f"Revenue is trending {rev_trend} "
                    f"(strength {float(revenue.get('trend_strength') or 0):.2f}). "
                    f"Monthly MoM average: {float(revenue.get('monthly_growth_pct') or 0):+.1f}%."
                ),
            }
        )

    # --- Health commentary ---
    insights.append(
        {
            "category": "Business Health",
            "title": f"Health score: {category}",
            "body": _health_narrative(health),
        }
    )

    # --- Confidence ---
    insights.append(
        {
            "category": "Confidence Commentary",
            "title": f"Forecast confidence: {conf_rating}",
            "body": (
                f"Model confidence score is {conf_score:.0f}/100. "
                f"{evaluation.get('notes') or 'Generate more history for stronger backtests.'}"
            ),
        }
    )

    if conf_score < 50:
        risks.append(
            {
                "title": "Low forecast confidence",
                "body": "Forecast accuracy is limited — treat projections as indicative and gather more data.",
            }
        )

    # --- Risk detection ---
    if score is not None and score < 40:
        risks.append(
            {
                "title": "Business health needs attention",
                "body": f"Health score {score}/100 ({category}) — prioritize recovery actions across growth and efficiency.",
            }
        )

    if orders and float(orders.get("growth_pct") or 0) < 0:
        risks.append(
            {
                "title": "Order volume declining",
                "body": f"Orders declined {abs(float(orders.get('growth_pct') or 0)):.1f}% — review funnel and retention.",
            }
        )

    # --- Growth opportunities ---
    if customers and float(customers.get("growth_pct") or 0) > 0:
        opportunities.append(
            {
                "title": "Customer base expanding",
                "body": f"Customers grew {float(customers.get('growth_pct') or 0):+.1f}% — scale onboarding and support.",
            }
        )

    if expenses and revenue:
        margin = context.get("profit", {}).get("margin_pct")
        if margin is not None and float(margin) > 20:
            opportunities.append(
                {
                    "title": "Healthy margins",
                    "body": f"Estimated margin {float(margin):.1f}% — room for strategic investment.",
                }
            )

    if not insights:
        insights.append(
            {
                "category": "Business Summary",
                "title": "Awaiting analytics",
                "body": "Upload and process a dataset to unlock detailed insights.",
            }
        )

    logger.info("Rule-based insights: %d insights, %d risks, %d opportunities.",
                len(insights), len(risks), len(opportunities))
    return {
        "summary": summary,
        "insights": insights,
        "risks": risks,
        "opportunities": opportunities,
        "recommendations": [],
        "provider": provider,
        "generated_at": utc_now(),
    }


def _resolve_providers() -> list[BaseAIProvider]:
    from ai.groq_provider import GroqProvider
    from ai.ollama_provider import OllamaProvider
    from config.settings import get_settings

    registry = {
        PROVIDER_GROQ: GroqProvider(),
        PROVIDER_OLLAMA: OllamaProvider(),
    }
    order = get_settings().ai_provider_order
    providers: list[BaseAIProvider] = []
    seen: set[str] = set()
    for key in order:
        if key in seen or key == PROVIDER_RULE_BASED:
            continue
        seen.add(key)
        if key in registry:
            providers.append(registry[key])
    providers.append(_RuleBasedInsights())
    return providers


class _RuleBasedInsights(BaseAIProvider):
    name = PROVIDER_RULE_BASED

    def is_available(self) -> bool:
        return True

    def generate_insights(self, context: dict[str, Any]) -> dict[str, Any]:
        return generate_rule_based_insights(context)

    def generate_recommendations(self, context: dict[str, Any]) -> dict[str, Any]:
        from ai.recommendation_engine import generate_rule_based_recommendations
        return generate_rule_based_recommendations(context)


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
        if abs(v) >= 1_000_000:
            return f"${v/1_000_000:.1f}M"
        if abs(v) >= 1_000:
            return f"${v/1_000:,.0f}K"
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _health_narrative(health: dict[str, Any]) -> str:
    breakdown = health.get("breakdown") or {}
    if not breakdown:
        return "Health breakdown unavailable — upload revenue data to compute a score."
    parts = [comp.get("description", "") for comp in breakdown.values() if comp.get("description")]
    return " ".join(parts[:3])
