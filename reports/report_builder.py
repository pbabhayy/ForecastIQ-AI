"""
Reports: Report Builder
=======================
Assembles a structured, render-agnostic report model from session payloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from analytics import metrics as metrics_fmt
from utils import column_mapper
from utils.logger import get_logger

logger = get_logger(__name__)


def sanitize_for_storage(obj: Any) -> Any:
    """Make nested structures JSON-serializable (DataFrames → records)."""
    if isinstance(obj, pd.DataFrame):
        frame = obj.copy()
        for col in frame.select_dtypes(include=["datetime", "datetimetz"]).columns:
            frame[col] = frame[col].astype(str)
        return frame.to_dict(orient="records")
    if isinstance(obj, dict):
        return {k: sanitize_for_storage(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_storage(v) for v in obj]
    return obj


def build_report(session_data: dict[str, Any]) -> dict[str, Any]:
    """Aggregate session artifacts into the standardized report object contract."""
    profile = session_data.get("dataset_profile") or {}
    analytics = session_data.get("analytics") or {}
    health = session_data.get("health_metrics") or {}
    forecast = session_data.get("forecasts") or {}
    evaluation = session_data.get("evaluation_results") or forecast.get("evaluation") or {}
    ai_meta = session_data.get("ai_metadata") or {}
    uploaded = session_data.get("uploaded_file") or {}

    revenue = analytics.get(column_mapper.REVENUE, {})
    executive = ai_meta.get("summary") or _default_summary(revenue, health, forecast)

    report: dict[str, Any] = {
        "metadata": {
            "title": "ForecastIQ Executive Report",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "ready",
            "dataset_name": uploaded.get("name") or "Uploaded Dataset",
            "ai_provider": session_data.get("ai_provider") or ai_meta.get("provider"),
            "report_id": None,
        },
        "executive_summary": executive,
        "dataset_overview": _dataset_section(profile, uploaded),
        "analytics_summary": _analytics_section(analytics),
        "health_score": _health_section(health),
        "forecast_summary": _forecast_section(forecast, evaluation),
        "forecast_table": _forecast_table(forecast),
        "ai_insights": ai_meta.get("insights") or [],
        "recommendations": ai_meta.get("recommendations") or session_data.get("recommendations") or [],
        "risks": ai_meta.get("risks") or [],
        "opportunities": ai_meta.get("opportunities") or [],
    }
    logger.info("Report object built for '%s'.", report["metadata"]["dataset_name"])
    return report


def _default_summary(revenue: dict, health: dict, forecast: dict) -> str:
    parts: list[str] = []
    if revenue:
        parts.append(
            f"Revenue growth {float(revenue.get('growth_pct') or 0):+.1f}% "
            f"with trend {revenue.get('trend', 'stable')}."
        )
    if health.get("score") is not None:
        parts.append(f"Business health {health.get('score')}/100 ({health.get('category')}).")
    if forecast.get("ok"):
        parts.append(
            f"Forecast projects {float(forecast.get('growth_pct') or 0):+.1f}% "
            f"over {forecast.get('horizon')} month(s)."
        )
    return " ".join(parts) if parts else "Analysis report generated from uploaded business data."


def _dataset_section(profile: dict, uploaded: dict) -> dict[str, Any]:
    return {
        "name": uploaded.get("name") or "—",
        "rows": profile.get("row_count"),
        "columns": profile.get("column_count"),
        "date_range": profile.get("date_range_label"),
        "metrics": profile.get("detected_metrics") or [],
        "quality_score": profile.get("data_quality_score"),
        "completeness_pct": profile.get("completeness_pct"),
    }


def _analytics_section(analytics: dict) -> dict[str, Any]:
    if not analytics.get("meta", {}).get("available"):
        return {"available": False}
    rev = analytics.get(column_mapper.REVENUE, {})
    return {
        "available": True,
        "total_revenue": rev.get("total"),
        "average_revenue": rev.get("average"),
        "revenue_growth_pct": rev.get("growth_pct"),
        "total_orders": (analytics.get(column_mapper.ORDERS) or {}).get("total"),
        "customer_growth_pct": (analytics.get(column_mapper.CUSTOMERS) or {}).get("growth_pct"),
        "profit_estimate": (analytics.get("profit") or {}).get("estimate"),
    }


def _health_section(health: dict) -> dict[str, Any]:
    return {
        "score": health.get("score"),
        "category": health.get("category"),
        "breakdown": health.get("breakdown") or {},
        "formula": health.get("formula"),
    }


def _forecast_section(forecast: dict, evaluation: dict) -> dict[str, Any]:
    if not forecast or not forecast.get("ok"):
        return {"available": False, "message": "No forecast generated."}
    return {
        "available": True,
        "metric": forecast.get("metric"),
        "model": forecast.get("model_label") or forecast.get("model"),
        "horizon": forecast.get("horizon"),
        "growth_pct": forecast.get("growth_pct"),
        "peak_month": forecast.get("peak_month"),
        "lowest_month": forecast.get("lowest_month"),
        "annual_projection": forecast.get("annual_projection"),
        "confidence_score": evaluation.get("confidence_score"),
        "confidence_rating": evaluation.get("confidence_rating"),
        "mae": evaluation.get("mae"),
        "rmse": evaluation.get("rmse"),
        "mape": evaluation.get("mape"),
    }


def _forecast_table(forecast: dict) -> list[dict[str, Any]]:
    frame = forecast.get("forecast_df")
    if frame is None or (isinstance(frame, pd.DataFrame) and frame.empty):
        return []
    if not isinstance(frame, pd.DataFrame):
        return list(frame) if isinstance(frame, list) else []
    fmt = metrics_fmt.format_currency if forecast.get("metric") == column_mapper.REVENUE else metrics_fmt.format_number
    rows = []
    for _, row in frame.iterrows():
        ds = pd.to_datetime(row["ds"])
        rows.append(
            {
                "month": ds.strftime("%b %Y"),
                "forecast": fmt(row.get("yhat")),
                "lower": fmt(row.get("yhat_lower")),
                "upper": fmt(row.get("yhat_upper")),
            }
        )
    return rows
