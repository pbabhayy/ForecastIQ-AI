"""
Analytics: Business Health Score
================================
Composite 0–100 business-health scoring with full transparency.

Consumes the analytics payload (from :mod:`analytics.metrics`) and produces:

    {
        "score": 84,
        "category": "Excellent",
        "breakdown": { <component>: {score, weight, raw, description}, ... },
        "weightings": {"base": {...}, "normalized": {...}},
        "formula": "score = Σ(component_score × normalized_weight)",
    }

Components are normalized to 0–100 and combined with weights that
re-normalize over whichever components are *available* for the dataset, so
the score is always meaningful even when optional metrics are missing. The
breakdown is designed to be consumed verbatim by the AI explanation layer
(Step 5) and the report layer (Step 6).
"""

from __future__ import annotations

from typing import Any, Final

from utils import column_mapper
from utils.logger import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Component identifiers and base weights (sum to 1.0)
# --------------------------------------------------------------------------- #
REVENUE_GROWTH: Final[str] = "revenue_growth"
REVENUE_STABILITY: Final[str] = "revenue_stability"
CUSTOMER_GROWTH: Final[str] = "customer_growth"
EXPENSE_EFFICIENCY: Final[str] = "expense_efficiency"
TREND_STRENGTH: Final[str] = "trend_strength"

_BASE_WEIGHTS: Final[dict[str, float]] = {
    REVENUE_GROWTH: 0.30,
    REVENUE_STABILITY: 0.20,
    CUSTOMER_GROWTH: 0.20,
    EXPENSE_EFFICIENCY: 0.15,
    TREND_STRENGTH: 0.15,
}

_CATEGORY_BANDS: Final[tuple[tuple[float, str], ...]] = (
    (80.0, "Excellent"),
    (60.0, "Good"),
    (40.0, "Moderate"),
    (0.0, "Needs Attention"),
)

_FORMULA: Final[str] = (
    "score = Σ(component_score × normalized_weight); "
    "weights re-normalize over available components."
)


def compute_health(analytics: dict[str, Any]) -> dict[str, Any]:
    """Compute the transparent business-health score.

    Args:
        analytics: The analytics payload from :func:`analytics.metrics.compute_metrics`.

    Returns:
        A structured health payload (see module docstring). When analytics are
        unavailable, returns a neutral, clearly-labeled result.
    """
    if not analytics or not analytics.get("meta", {}).get("available"):
        logger.warning("compute_health received unavailable analytics.")
        return _empty_result()

    revenue = analytics.get(column_mapper.REVENUE)
    customers = analytics.get(column_mapper.CUSTOMERS)
    profit = analytics.get("profit")

    components: dict[str, dict[str, Any]] = {}

    # --- Revenue growth ------------------------------------------------------
    if revenue is not None:
        growth = float(revenue.get("growth_pct", 0.0))
        components[REVENUE_GROWTH] = _component(
            _score_growth(growth), growth,
            f"Revenue grew {growth:+.1f}% over the period.",
        )
        # --- Revenue stability ----------------------------------------------
        stability_raw, stability_score = _stability(revenue)
        components[REVENUE_STABILITY] = _component(
            stability_score, stability_raw,
            f"Revenue volatility (CV) of {stability_raw:.2f}.",
        )
        # --- Trend strength -------------------------------------------------
        trend_score, trend_raw = _score_trend(revenue)
        components[TREND_STRENGTH] = _component(
            trend_score, trend_raw,
            f"Revenue trend is {revenue.get('trend', 'stable')} "
            f"(strength {abs(trend_raw):.2f}).",
        )

    # --- Customer growth -----------------------------------------------------
    if customers is not None:
        cust_growth = float(customers.get("growth_pct", 0.0))
        components[CUSTOMER_GROWTH] = _component(
            _score_growth(cust_growth), cust_growth,
            f"Customer base changed {cust_growth:+.1f}% over the period.",
        )

    # --- Expense efficiency --------------------------------------------------
    if profit is not None:
        margin = float(profit.get("margin_pct", 0.0))
        components[EXPENSE_EFFICIENCY] = _component(
            _score_margin(margin), margin,
            f"Estimated profit margin of {margin:+.1f}%.",
        )

    if not components:
        return _empty_result()

    normalized = _normalize_weights(components.keys())
    score = sum(components[name]["score"] * normalized[name] for name in components)
    score = round(_clamp(score, 0.0, 100.0))

    for name in components:
        components[name]["weight"] = round(normalized[name], 4)

    result = {
        "score": int(score),
        "category": _category(score),
        "breakdown": components,
        "weightings": {
            "base": {k: _BASE_WEIGHTS[k] for k in components},
            "normalized": {k: round(v, 4) for k, v in normalized.items()},
        },
        "formula": _FORMULA,
    }
    logger.info(
        "Health score computed: %d (%s) over %d components.",
        result["score"], result["category"], len(components),
    )
    return result


# --------------------------------------------------------------------------- #
# Component scorers (each returns a 0–100 score)
# --------------------------------------------------------------------------- #
def _score_growth(growth_pct: float) -> float:
    """Map a growth percentage to 0–100 (0% growth → 50, ±33% → 0/100)."""
    return _clamp(50.0 + growth_pct * 1.5, 0.0, 100.0)


def _score_margin(margin_pct: float) -> float:
    """Map a profit margin percentage to 0–100 (0% → 50, +50% → 100)."""
    return _clamp(50.0 + margin_pct, 0.0, 100.0)


def _stability(revenue: dict[str, Any]) -> tuple[float, float]:
    """Compute revenue stability from the coefficient of variation.

    Returns ``(cv, score)`` where a lower CV yields a higher score.
    """
    series = [r["value"] for r in revenue.get("series", []) if r.get("value") is not None]
    if len(series) < 2:
        return 0.0, 60.0  # not enough data — neutral-positive default
    mean = sum(series) / len(series)
    if mean == 0:
        return 0.0, 50.0
    variance = sum((v - mean) ** 2 for v in series) / len(series)
    cv = (variance ** 0.5) / abs(mean)
    score = _clamp(100.0 - cv * 100.0, 0.0, 100.0)
    return round(cv, 3), score


def _score_trend(revenue: dict[str, Any]) -> tuple[float, float]:
    """Score the revenue trend direction × strength.

    Returns ``(score, signed_strength)``.
    """
    direction = revenue.get("trend", "stable")
    strength = float(revenue.get("trend_strength", 0.0))
    sign = {"upward": 1.0, "downward": -1.0}.get(direction, 0.0)
    signed = sign * strength
    score = _clamp(50.0 + signed * 50.0, 0.0, 100.0)
    return score, signed


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _component(score: float, raw: float, description: str) -> dict[str, Any]:
    """Assemble a single component breakdown entry (weight added later)."""
    return {
        "score": round(_clamp(score, 0.0, 100.0), 1),
        "raw": round(raw, 3),
        "weight": 0.0,
        "description": description,
    }


def _normalize_weights(available: Any) -> dict[str, float]:
    """Re-normalize base weights over the available components."""
    names = list(available)
    total = sum(_BASE_WEIGHTS[name] for name in names)
    if total == 0:
        equal = 1.0 / len(names)
        return {name: equal for name in names}
    return {name: _BASE_WEIGHTS[name] / total for name in names}


def _category(score: float) -> str:
    """Map a 0–100 score to its categorical band."""
    for threshold, label in _CATEGORY_BANDS:
        if score >= threshold:
            return label
    return "Needs Attention"


def _empty_result() -> dict[str, Any]:
    """Return a neutral result when scoring is not possible."""
    return {
        "score": 0,
        "category": "Needs Attention",
        "breakdown": {},
        "weightings": {"base": {}, "normalized": {}},
        "formula": _FORMULA,
        "available": False,
    }


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive ``[low, high]`` range."""
    return max(low, min(high, value))
