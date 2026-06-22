"""
AI: Recommendation Engine
=========================
Provider-agnostic recommendation generation with deterministic fallback.

Provider chain: Groq → Ollama → rule-based. Recommendations include
High / Medium / Low priority levels.
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


def generate_recommendations(
    analytics: dict[str, Any] | None,
    health: dict[str, Any] | None,
    forecast: dict[str, Any] | None,
    evaluation: dict[str, Any] | None = None,
    *,
    dataset_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate recommendations via the provider chain."""
    context = build_context(analytics, health, forecast, evaluation, dataset_profile=dataset_profile)
    for provider in _resolve_providers():
        if not provider.is_available() and provider.name != PROVIDER_RULE_BASED:
            logger.info("Recommendations: skipping unavailable provider '%s'.", provider.name)
            continue
        try:
            if provider.name == PROVIDER_RULE_BASED:
                result = generate_rule_based_recommendations(context)
            else:
                result = provider.generate_recommendations(context)
            if result.get("recommendations"):
                logger.info("Recommendations generated using '%s'.", result.get("provider", provider.name))
                return result
        except Exception:  # noqa: BLE001
            logger.exception("Recommendations: provider '%s' failed.", provider.name)

    logger.info("Recommendations: falling back to rule-based engine.")
    return generate_rule_based_recommendations(context)


def generate_rule_based_recommendations(
    context: dict[str, Any], *, provider: str = PROVIDER_RULE_BASED
) -> dict[str, Any]:
    """Deterministic recommendations — always produces output."""
    revenue = context.get("revenue") or {}
    customers = context.get("customers") or {}
    expenses = context.get("expenses") or {}
    health = context.get("health") or {}
    forecast = context.get("forecast") or {}
    evaluation = context.get("evaluation") or {}

    recs: list[dict[str, str]] = []
    rev_growth = float(revenue.get("growth_pct") or 0)
    score = health.get("score")
    conf_score = float(evaluation.get("confidence_score") or 0)

    # --- Strategic ---
    if score is not None and score >= 80:
        recs.append(_rec("Strategic", "Scale what works", "Health is strong — invest in growth channels and operational capacity.", "High"))
    elif score is not None and score < 40:
        recs.append(_rec("Strategic", "Stabilize fundamentals", "Focus on cash flow, core retention, and cost control before expansion.", "High"))

    # --- Revenue ---
    if rev_growth > 5:
        recs.append(_rec("Revenue", "Capture growth momentum", f"Revenue up {rev_growth:.1f}% — increase marketing in top-performing segments.", "High"))
    elif rev_growth < 0:
        recs.append(_rec("Revenue", "Reverse revenue decline", f"Revenue down {abs(rev_growth):.1f}% — audit pricing, churn, and sales pipeline.", "High"))
    else:
        recs.append(_rec("Revenue", "Accelerate revenue", "Growth is flat — test pricing, bundles, or upsell campaigns.", "Medium"))

    # --- Customer ---
    if customers:
        cg = float(customers.get("growth_pct") or 0)
        if cg > 0:
            recs.append(_rec("Customer", "Scale acquisition", f"Customer base grew {cg:.1f}% — optimize onboarding and referral programs.", "Medium"))
        else:
            recs.append(_rec("Customer", "Improve retention", "Customer growth is weak — launch win-back and loyalty initiatives.", "High"))

    # --- Expense ---
    profit = context.get("profit") or {}
    if expenses and profit:
        margin = float(profit.get("margin_pct") or 0)
        if margin < 10:
            recs.append(_rec("Expense", "Reduce operating costs", f"Margin at {margin:.1f}% — review vendor contracts and discretionary spend.", "High"))
        else:
            recs.append(_rec("Expense", "Maintain efficiency", f"Margin healthy at {margin:.1f}% — continue monitoring expense ratios monthly.", "Low"))

    # --- Forecast ---
    if forecast.get("ok"):
        fg = float(forecast.get("growth_pct") or 0)
        if fg > 0:
            recs.append(_rec("Forecast", "Plan for projected growth", f"Forecast shows {fg:+.1f}% — align inventory and staffing with peak month {forecast.get('peak_month')}.", "Medium"))
        else:
            recs.append(_rec("Forecast", "Prepare for softening demand", f"Forecast indicates {fg:.1f}% change — tighten budgets and prioritize retention.", "High"))
    else:
        recs.append(_rec("Forecast", "Generate forecasts", "Run forecasting to inform inventory, hiring, and budget decisions.", "Medium"))

    # --- Risk mitigation ---
    if conf_score < 50:
        recs.append(_rec("Risk Mitigation", "Improve data quality", "Low forecast confidence — collect more historical data and reduce missing values.", "High"))

    if rev_growth < -10:
        recs.append(_rec("Risk Mitigation", "Cash-flow guardrails", "Significant revenue drop — establish weekly cash monitoring and scenario plans.", "High"))

    recs.sort(key=lambda r: {"High": 0, "Medium": 1, "Low": 2}.get(r["priority"], 3))
    logger.info("Rule-based recommendations: %d items.", len(recs))
    return {
        "summary": "",
        "insights": [],
        "risks": [],
        "opportunities": [],
        "recommendations": recs,
        "provider": provider,
        "generated_at": utc_now(),
    }


def _rec(category: str, title: str, body: str, priority: str) -> dict[str, str]:
    return {"category": category, "title": title, "body": body, "priority": priority}


def _resolve_providers() -> list[BaseAIProvider]:
    from ai.groq_provider import GroqProvider
    from ai.ollama_provider import OllamaProvider
    from config.settings import get_settings

    registry = {PROVIDER_GROQ: GroqProvider(), PROVIDER_OLLAMA: OllamaProvider()}
    providers: list[BaseAIProvider] = []
    seen: set[str] = set()
    for key in get_settings().ai_provider_order:
        if key in seen or key == PROVIDER_RULE_BASED:
            continue
        seen.add(key)
        if key in registry:
            providers.append(registry[key])
    providers.append(_RuleBasedRecs())
    return providers


class _RuleBasedRecs(BaseAIProvider):
    name = PROVIDER_RULE_BASED

    def is_available(self) -> bool:
        return True

    def generate_insights(self, context: dict[str, Any]) -> dict[str, Any]:
        from ai.insight_engine import generate_rule_based_insights
        return generate_rule_based_insights(context)

    def generate_recommendations(self, context: dict[str, Any]) -> dict[str, Any]:
        return generate_rule_based_recommendations(context)
