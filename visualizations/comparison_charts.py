"""
Visualization: Comparison Charts
================================
Plotly multi-series comparison figures.

Two comparisons are supported:
    * :func:`forecast_comparison` — overlays the forecasts of multiple models
      (e.g. Prophet vs Linear Regression) against shared history.
    * :func:`metric_comparison`   — overlays two historical metric series
      (e.g. Revenue vs Expenses) from the analytics payload.
"""

from __future__ import annotations

from typing import Any, Sequence

import pandas as pd
import plotly.graph_objects as go

from visualizations import CHART_SEQUENCE, COLOR_HISTORY, MUTED, apply_dark_layout


def forecast_comparison(
    results_by_model: dict[str, dict[str, Any]], *, height: int = 340
) -> go.Figure:
    """Overlay forecasts from multiple models against shared history.

    Args:
        results_by_model: ``{model_key: forecast_result_contract}``.
        height: Figure height in pixels.
    """
    fig = go.Figure()
    ok_results = {k: r for k, r in results_by_model.items() if r.get("ok")}
    if not ok_results:
        fig.add_annotation(text="No comparable forecasts", showarrow=False,
                           font=dict(color=MUTED))
        return apply_dark_layout(fig, title="Model Comparison", height=height,
                                 show_legend=False)

    # Shared history (from the first available result).
    first = next(iter(ok_results.values()))
    history = first.get("history_df")
    metric_label = str(first.get("metric", "")).title()
    if history is not None and not history.empty:
        hist = history.copy()
        hist["ds"] = pd.to_datetime(hist["ds"])
        fig.add_trace(
            go.Scatter(x=hist["ds"], y=hist["y"], mode="lines", name="Actual",
                       line=dict(color=COLOR_HISTORY, width=2.5),
                       hovertemplate="%{x|%b %Y}<br>Actual: %{y:,.0f}<extra></extra>")
        )
        last_ds, last_y = hist["ds"].iloc[-1], hist["y"].iloc[-1]
    else:
        last_ds = last_y = None

    for i, (model_key, result) in enumerate(ok_results.items()):
        forecast = result.get("forecast_df")
        if forecast is None or forecast.empty:
            continue
        fc = forecast.copy()
        fc["ds"] = pd.to_datetime(fc["ds"])
        if last_ds is not None:
            bridge = pd.DataFrame({"ds": [last_ds], "yhat": [last_y]})
            fc = pd.concat([bridge, fc[["ds", "yhat"]]], ignore_index=True)
        color = CHART_SEQUENCE[(i + 1) % len(CHART_SEQUENCE)]
        fig.add_trace(
            go.Scatter(x=fc["ds"], y=fc["yhat"], mode="lines+markers",
                       name=result.get("model_label", model_key),
                       line=dict(color=color, width=2.2, dash="dash"),
                       marker=dict(size=4),
                       hovertemplate=f"{result.get('model_label', model_key)}"
                                     "<br>%{x|%b %Y}: %{y:,.0f}<extra></extra>")
        )
    return apply_dark_layout(fig, title=f"{metric_label} · Model Comparison", height=height)


def metric_comparison(
    primary_series: Sequence[dict[str, Any]],
    secondary_series: Sequence[dict[str, Any]],
    *,
    primary_name: str = "Revenue",
    secondary_name: str = "Expenses",
    height: int = 300,
) -> go.Figure:
    """Overlay two historical metric series (dual y-axes).

    Args:
        primary_series / secondary_series: Monthly analytics records.
        primary_name / secondary_name: Legend labels.
        height: Figure height in pixels.
    """
    fig = go.Figure()
    p = _frame(primary_series)
    s = _frame(secondary_series)
    fig.add_trace(
        go.Scatter(x=p["period"], y=p["value"], mode="lines", name=primary_name,
                   line=dict(color=CHART_SEQUENCE[0], width=2.5),
                   hovertemplate="%{x|%b %Y}<br>%{y:,.0f}<extra></extra>")
    )
    fig.add_trace(
        go.Scatter(x=s["period"], y=s["value"], mode="lines", name=secondary_name,
                   line=dict(color=CHART_SEQUENCE[2], width=2.5), yaxis="y2",
                   hovertemplate="%{x|%b %Y}<br>%{y:,.0f}<extra></extra>")
    )
    fig = apply_dark_layout(fig, title=f"{primary_name} vs {secondary_name}", height=height)
    fig.update_layout(
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickfont=dict(color=MUTED))
    )
    return fig


def _frame(series: Sequence[dict[str, Any]]) -> pd.DataFrame:
    """Convert analytics records to a sorted (period, value) frame."""
    if not series:
        return pd.DataFrame(columns=["period", "value"])
    frame = pd.DataFrame(list(series))
    frame["period"] = pd.to_datetime(frame["period"], format="%Y-%m", errors="coerce")
    return frame.dropna(subset=["period"]).sort_values("period")
