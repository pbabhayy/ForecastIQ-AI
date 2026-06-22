"""
Visualization: Revenue & Metric Trends
======================================
Plotly figures for historical metric trends and growth.

Functions accept the monthly ``series`` records produced by
:mod:`analytics.metrics` (``[{"period": "YYYY-MM", "value": float}, ...]``)
so the visualization layer stays decoupled from raw dataframes. All figures
adopt the shared premium dark styling.
"""

from __future__ import annotations

from typing import Any, Sequence

import pandas as pd
import plotly.graph_objects as go

from visualizations import COLOR_HISTORY, MUTED, apply_dark_layout


def _records_to_frame(series: Sequence[dict[str, Any]]) -> pd.DataFrame:
    """Convert ``[{"period","value"}]`` records to a (period, value) frame."""
    if not series:
        return pd.DataFrame(columns=["period", "value"])
    frame = pd.DataFrame(list(series))
    frame["period"] = pd.to_datetime(frame["period"], format="%Y-%m", errors="coerce")
    return frame.dropna(subset=["period"]).sort_values("period")


def metric_trend(
    series: Sequence[dict[str, Any]],
    *,
    name: str = "Revenue",
    color: str = COLOR_HISTORY,
    height: int = 300,
) -> go.Figure:
    """Render a historical line trend for a single metric.

    Args:
        series: Monthly records from the analytics payload.
        name: Series/legend label.
        color: Line color.
        height: Figure height.
    """
    frame = _records_to_frame(series)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["period"], y=frame["value"], mode="lines+markers", name=name,
            line=dict(color=color, width=2.5), marker=dict(size=5, color=color),
            fill="tozeroy", fillcolor=_translucent(color),
            hovertemplate="%{x|%b %Y}<br>%{y:,.0f}<extra></extra>",
        )
    )
    return apply_dark_layout(fig, title=f"{name} Trend", height=height, show_legend=False)


def revenue_trend(analytics: dict[str, Any], *, height: int = 300) -> go.Figure:
    """Convenience wrapper rendering the revenue trend from an analytics payload."""
    revenue = (analytics or {}).get("revenue", {})
    return metric_trend(revenue.get("series", []), name="Revenue", height=height)


def growth_trend(
    series: Sequence[dict[str, Any]], *, name: str = "Revenue", height: int = 260
) -> go.Figure:
    """Render period-over-period growth (%) as a diverging bar chart.

    Positive months are accented green, negative months red.
    """
    frame = _records_to_frame(series)
    fig = go.Figure()
    if len(frame) >= 2:
        frame["growth"] = frame["value"].pct_change() * 100.0
        frame = frame.dropna(subset=["growth"])
        colors = ["#22C55E" if g >= 0 else "#EF4444" for g in frame["growth"]]
        fig.add_trace(
            go.Bar(
                x=frame["period"], y=frame["growth"], marker_color=colors,
                hovertemplate="%{x|%b %Y}<br>%{y:.1f}%<extra></extra>", name="Growth",
            )
        )
    else:
        fig.add_annotation(
            text="Not enough history for growth", showarrow=False,
            font=dict(color=MUTED),
        )
    return apply_dark_layout(fig, title=f"{name} Growth (MoM %)", height=height, show_legend=False)


def _translucent(hex_color: str, alpha: float = 0.12) -> str:
    """Return an ``rgba(...)`` translucent fill for a ``#RRGGBB`` color."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"rgba(59,130,246,{alpha})"
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"
