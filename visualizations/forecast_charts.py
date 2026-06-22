"""
Visualization: Forecast Charts
==============================
Plotly figures for forecasts, confidence intervals, and confidence scoring.

These consume the **unified forecast result contract** from
:mod:`forecasting.forecast_manager` (``history_df``, ``forecast_df``,
``evaluation``) and render:
    * historical vs forecast with a shaded confidence band, and
    * a confidence-score gauge.

Generic across metrics, so the same functions power revenue, orders, and
customer forecasts.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from visualizations import (
    COLOR_CONFIDENCE_FILL,
    COLOR_FORECAST,
    COLOR_HISTORY,
    DANGER,
    MUTED,
    SUCCESS,
    WARNING,
    apply_dark_layout,
)


def forecast_chart(result: dict[str, Any], *, height: int = 360) -> go.Figure:
    """Render history, forecast, and the confidence band in one figure.

    Args:
        result: A unified forecast result contract.
        height: Figure height in pixels.
    """
    metric_label = str(result.get("metric", "")).title()
    history = result.get("history_df")
    forecast = result.get("forecast_df")
    fig = go.Figure()

    if history is None or forecast is None or forecast.empty:
        fig.add_annotation(text="No forecast to display", showarrow=False,
                           font=dict(color=MUTED))
        return apply_dark_layout(fig, title=f"{metric_label} Forecast", height=height,
                                 show_legend=False)

    history = history.copy()
    history["ds"] = pd.to_datetime(history["ds"])
    forecast = forecast.copy()
    forecast["ds"] = pd.to_datetime(forecast["ds"])

    # Bridge the last historical point into the forecast for visual continuity.
    bridge = pd.DataFrame(
        {
            "ds": [history["ds"].iloc[-1]],
            "yhat": [history["y"].iloc[-1]],
            "yhat_lower": [history["y"].iloc[-1]],
            "yhat_upper": [history["y"].iloc[-1]],
        }
    )
    fc = pd.concat([bridge, forecast], ignore_index=True)

    # Confidence band (upper then lower with fill between).
    fig.add_trace(
        go.Scatter(x=fc["ds"], y=fc["yhat_upper"], mode="lines",
                   line=dict(width=0), hoverinfo="skip", showlegend=False)
    )
    fig.add_trace(
        go.Scatter(x=fc["ds"], y=fc["yhat_lower"], mode="lines", line=dict(width=0),
                   fill="tonexty", fillcolor=COLOR_CONFIDENCE_FILL,
                   name="Confidence", hoverinfo="skip")
    )
    # Historical line.
    fig.add_trace(
        go.Scatter(x=history["ds"], y=history["y"], mode="lines+markers", name="Actual",
                   line=dict(color=COLOR_HISTORY, width=2.5), marker=dict(size=5),
                   hovertemplate="%{x|%b %Y}<br>Actual: %{y:,.0f}<extra></extra>")
    )
    # Forecast line.
    fig.add_trace(
        go.Scatter(x=fc["ds"], y=fc["yhat"], mode="lines+markers", name="Forecast",
                   line=dict(color=COLOR_FORECAST, width=2.5, dash="dash"),
                   marker=dict(size=5),
                   hovertemplate="%{x|%b %Y}<br>Forecast: %{y:,.0f}<extra></extra>")
    )
    return apply_dark_layout(fig, title=f"{metric_label} · Historical vs Forecast",
                             height=height)


def confidence_chart(result: dict[str, Any], *, height: int = 260) -> go.Figure:
    """Render a gauge for the forecast confidence score (0–100).

    Args:
        result: A unified forecast result contract (uses ``evaluation``).
        height: Figure height in pixels.
    """
    evaluation = result.get("evaluation", {}) or {}
    score = float(evaluation.get("confidence_score", 0.0))
    rating = str(evaluation.get("confidence_rating", "—"))
    bar_color = (
        SUCCESS if score >= 70 else WARNING if score >= 50 else DANGER
    )
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number=dict(suffix=" / 100", font=dict(size=30)),
            title=dict(text=f"Confidence · {rating}", font=dict(size=14)),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor=MUTED),
                bar=dict(color=bar_color, thickness=0.3),
                bgcolor="rgba(0,0,0,0)",
                borderwidth=0,
                steps=[
                    dict(range=[0, 50], color="rgba(239,68,68,0.12)"),
                    dict(range=[50, 70], color="rgba(245,158,11,0.12)"),
                    dict(range=[70, 100], color="rgba(34,197,94,0.12)"),
                ],
            ),
        )
    )
    return apply_dark_layout(fig, title=None, height=height, show_legend=False)
