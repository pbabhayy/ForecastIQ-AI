"""
Analytics: Metrics
==================
Business KPI computation over the canonical dataframe.

Consumes the cleaned canonical dataframe (columns are canonical names only)
and produces a structured, serializable analytics payload keyed by metric:

    {
        "revenue":   {... stats, growth, periods, trend, monthly series ...},
        "orders":    {...},
        "customers": {...},
        "expenses":  {...},
        "profit":    {... if revenue & expenses present ...},
        "meta":      {... period count, frequency, range ...}
    }

Only NumPy/pandas are used (no scikit-learn/Prophet). The payload schema is
stable so the forecasting, AI, and report layers can consume it unchanged.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from utils import column_mapper
from utils.logger import get_logger

logger = get_logger(__name__)

# Metrics treated as point-in-time counts use "last" monthly aggregation;
# all others are summed (flows).
_POINT_IN_TIME = {column_mapper.CUSTOMERS}


def compute_metrics(clean_df: pd.DataFrame) -> dict[str, Any]:
    """Compute the full analytics payload from a canonical dataframe.

    Args:
        clean_df: Cleaned dataframe with a ``date`` column and one or more
            canonical metric columns.

    Returns:
        A structured analytics payload (see module docstring). Returns a
        payload with ``meta.available = False`` if the dataframe is unusable.
    """
    if clean_df is None or clean_df.empty or column_mapper.DATE not in clean_df.columns:
        logger.warning("compute_metrics received an empty/invalid dataframe.")
        return {"meta": {"available": False}}

    present_metrics = [m for m in column_mapper.METRIC_FIELDS if m in clean_df.columns]
    payload: dict[str, Any] = {}

    for metric in present_metrics:
        how = "last" if metric in _POINT_IN_TIME else "sum"
        monthly = _monthly_series(clean_df, metric, how)
        payload[metric] = _metric_block(monthly, is_count=metric in _POINT_IN_TIME)

    # Derived profit block when both revenue and expenses exist.
    if column_mapper.REVENUE in payload and column_mapper.EXPENSES in payload:
        payload["profit"] = _profit_block(
            payload[column_mapper.REVENUE], payload[column_mapper.EXPENSES]
        )

    payload["meta"] = _meta_block(clean_df, present_metrics)
    logger.info("Computed analytics for metrics=%s.", present_metrics)
    return payload


# --------------------------------------------------------------------------- #
# Per-metric computation
# --------------------------------------------------------------------------- #
def _metric_block(monthly: pd.Series, *, is_count: bool) -> dict[str, Any]:
    """Compute the stat/growth/period/trend block for one metric series.

    Args:
        monthly: Month-indexed series for the metric.
        is_count: Whether the metric is a point-in-time count (affects which
            aggregates are emphasized).
    """
    values = monthly.to_numpy(dtype=float)
    n = len(values)
    total = float(np.nansum(values))
    average = float(np.nanmean(values)) if n else 0.0
    median = float(np.nanmedian(values)) if n else 0.0
    latest = float(values[-1]) if n else 0.0

    growth_pct = _overall_growth(values)
    monthly_growth_pct = _avg_period_growth(values)
    quarterly = _quarterly_series(monthly)

    block: dict[str, Any] = {
        "total": round(total, 2),
        "average": round(average, 2),
        "median": round(median, 2),
        "latest": round(latest, 2),
        "growth_pct": growth_pct,
        "monthly_growth_pct": monthly_growth_pct,
        "highest_month": _extreme(monthly, highest=True),
        "lowest_month": _extreme(monthly, highest=False),
        "best_quarter": _extreme(quarterly, highest=True, quarter=True),
        "worst_quarter": _extreme(quarterly, highest=False, quarter=True),
        "series": _series_records(monthly),
    }
    trend_dir, trend_strength = _trend(values)
    block["trend"] = trend_dir
    block["trend_strength"] = trend_strength
    block["is_count"] = is_count
    return block


def _profit_block(revenue: dict[str, Any], expenses: dict[str, Any]) -> dict[str, Any]:
    """Compute a profit/margin block from revenue and expense blocks."""
    total_rev = float(revenue.get("total", 0.0))
    total_exp = float(expenses.get("total", 0.0))
    estimate = total_rev - total_exp
    margin = (estimate / total_rev * 100.0) if total_rev else 0.0
    return {
        "estimate": round(estimate, 2),
        "margin_pct": round(margin, 2),
        "total_revenue": round(total_rev, 2),
        "total_expenses": round(total_exp, 2),
    }


def _meta_block(clean_df: pd.DataFrame, metrics: list[str]) -> dict[str, Any]:
    """Compute the dataset-level meta block."""
    dates = clean_df[column_mapper.DATE]
    monthly_periods = dates.dt.to_period("M").nunique()
    return {
        "available": True,
        "metrics": list(metrics),
        "row_count": int(len(clean_df)),
        "period_count": int(monthly_periods),
        "frequency": "monthly",
        "start": dates.min().date().isoformat() if len(dates) else None,
        "end": dates.max().date().isoformat() if len(dates) else None,
    }


# --------------------------------------------------------------------------- #
# Series helpers
# --------------------------------------------------------------------------- #
def _monthly_series(clean_df: pd.DataFrame, metric: str, how: str) -> pd.Series:
    """Resample a metric to a month-start indexed series."""
    series = (
        clean_df[[column_mapper.DATE, metric]]
        .dropna(subset=[metric])
        .set_index(column_mapper.DATE)[metric]
        .astype(float)
    )
    if series.empty:
        return series
    resampled = series.resample("MS")
    monthly = resampled.last() if how == "last" else resampled.sum()
    return monthly.dropna()


def _quarterly_series(monthly: pd.Series) -> pd.Series:
    """Aggregate a monthly series to quarter-start (summed)."""
    if monthly.empty:
        return monthly
    return monthly.resample("QS").sum()


def _series_records(monthly: pd.Series) -> list[dict[str, Any]]:
    """Convert a month-indexed series to ``[{"period","value"}]`` records."""
    return [
        {"period": idx.strftime("%Y-%m"), "value": round(float(val), 2)}
        for idx, val in monthly.items()
    ]


def _extreme(
    series: pd.Series, *, highest: bool, quarter: bool = False
) -> dict[str, Any] | None:
    """Return the highest/lowest period of a series as a labeled record."""
    if series is None or series.empty:
        return None
    idx = series.idxmax() if highest else series.idxmin()
    label = _quarter_label(idx) if quarter else idx.strftime("%b %Y")
    return {"period": label, "value": round(float(series.loc[idx]), 2)}


# --------------------------------------------------------------------------- #
# Growth / trend helpers
# --------------------------------------------------------------------------- #
def _overall_growth(values: np.ndarray) -> float:
    """Percentage growth from the first to the last period."""
    if len(values) < 2:
        return 0.0
    first, last = float(values[0]), float(values[-1])
    if first == 0:
        return 0.0 if last == 0 else 100.0
    return round((last - first) / abs(first) * 100.0, 2)


def _avg_period_growth(values: np.ndarray) -> float:
    """Average period-over-period percentage change (mean of pct changes)."""
    if len(values) < 2:
        return 0.0
    series = pd.Series(values, dtype=float)
    pct = series.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    return round(float(pct.mean() * 100.0), 2) if not pct.empty else 0.0


def _trend(values: np.ndarray) -> tuple[str, float]:
    """Classify trend direction and strength via least-squares slope + corr.

    Returns ``(direction, strength)`` where direction ∈
    {"upward","downward","stable"} and strength ∈ [0, 1] (|correlation|).
    """
    n = len(values)
    if n < 2:
        return "stable", 0.0
    x = np.arange(n, dtype=float)
    y = values.astype(float)
    if np.allclose(y, y[0]):
        return "stable", 0.0

    slope = float(np.polyfit(x, y, 1)[0])
    mean_y = float(np.mean(y))
    relative_slope = slope / abs(mean_y) if mean_y else 0.0
    corr_matrix = np.corrcoef(x, y)
    strength = abs(float(corr_matrix[0, 1])) if not np.isnan(corr_matrix[0, 1]) else 0.0

    if relative_slope > 0.01:
        direction = "upward"
    elif relative_slope < -0.01:
        direction = "downward"
    else:
        direction = "stable"
    return direction, round(strength, 3)


def _quarter_label(timestamp: pd.Timestamp) -> str:
    """Return a ``"YYYY Qn"`` label for a timestamp."""
    return f"{timestamp.year} Q{(timestamp.month - 1) // 3 + 1}"


# --------------------------------------------------------------------------- #
# Display helpers (used by the analytics page)
# --------------------------------------------------------------------------- #
def format_currency(value: float | int | None) -> str:
    """Format a number as a compact currency string (e.g. ``$1.2M``)."""
    if value is None:
        return "—"
    value = float(value)
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    for threshold, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if magnitude >= threshold:
            return f"{sign}${magnitude / threshold:.1f}{suffix}"
    return f"{sign}${magnitude:,.0f}"


def format_number(value: float | int | None) -> str:
    """Format a number compactly (e.g. ``1.2M``), no currency symbol."""
    if value is None:
        return "—"
    value = float(value)
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    for threshold, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if magnitude >= threshold:
            return f"{sign}{magnitude / threshold:.1f}{suffix}"
    return f"{sign}{magnitude:,.0f}"


def format_percent(value: float | int | None) -> str:
    """Format a percentage with a sign (e.g. ``+12.4%``)."""
    if value is None:
        return "—"
    return f"{value:+.1f}%"
