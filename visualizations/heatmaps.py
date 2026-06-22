"""
Visualization: Heatmaps
=======================
Plotly monthly and quarterly seasonality heatmaps.

Built directly from the cleaned canonical dataframe (a ``date`` column plus a
canonical metric column). Flow metrics are summed per period; ``customers`` is
averaged (point-in-time count). Year is on the y-axis, period on the x-axis.
"""

from __future__ import annotations

import calendar

import pandas as pd
import plotly.graph_objects as go

from visualizations import HEATMAP_COLORSCALE, MUTED, apply_dark_layout

_DATE = "date"
_COUNT_METRIC = "customers"


def monthly_heatmap(clean_df: pd.DataFrame, metric: str, *, height: int = 320) -> go.Figure:
    """Render a Year × Month heatmap for a metric."""
    frame = _prepare(clean_df, metric)
    if frame is None:
        return _empty(f"{metric.title()} · Monthly Heatmap", height)

    frame["month"] = frame[_DATE].dt.month
    frame["year"] = frame[_DATE].dt.year
    pivot = frame.pivot_table(
        index="year", columns="month", values=metric, aggfunc=_aggfunc(metric)
    ).reindex(columns=range(1, 13))
    labels = [calendar.month_abbr[m] for m in range(1, 13)]
    return _heatmap_figure(pivot, labels, f"{metric.title()} · Monthly Heatmap", height)


def quarterly_heatmap(clean_df: pd.DataFrame, metric: str, *, height: int = 280) -> go.Figure:
    """Render a Year × Quarter heatmap for a metric."""
    frame = _prepare(clean_df, metric)
    if frame is None:
        return _empty(f"{metric.title()} · Quarterly Heatmap", height)

    frame["quarter"] = frame[_DATE].dt.quarter
    frame["year"] = frame[_DATE].dt.year
    pivot = frame.pivot_table(
        index="year", columns="quarter", values=metric, aggfunc=_aggfunc(metric)
    ).reindex(columns=range(1, 5))
    labels = [f"Q{q}" for q in range(1, 5)]
    return _heatmap_figure(pivot, labels, f"{metric.title()} · Quarterly Heatmap", height)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _prepare(clean_df: pd.DataFrame, metric: str) -> pd.DataFrame | None:
    """Return a validated (date, metric) frame, or ``None`` if unusable."""
    if clean_df is None or metric not in getattr(clean_df, "columns", []):
        return None
    if _DATE not in clean_df.columns:
        return None
    frame = clean_df[[_DATE, metric]].dropna().copy()
    if frame.empty:
        return None
    frame[_DATE] = pd.to_datetime(frame[_DATE], errors="coerce")
    return frame.dropna(subset=[_DATE])


def _aggfunc(metric: str) -> str:
    """Aggregation per metric type (mean for counts, sum for flows)."""
    return "mean" if metric == _COUNT_METRIC else "sum"


def _heatmap_figure(
    pivot: pd.DataFrame, x_labels: list[str], title: str, height: int
) -> go.Figure:
    """Build a styled heatmap figure from a pivot table."""
    fig = go.Figure(
        go.Heatmap(
            z=pivot.to_numpy(dtype=float),
            x=x_labels,
            y=[str(y) for y in pivot.index],
            colorscale=HEATMAP_COLORSCALE,
            hoverongaps=False,
            hovertemplate="%{y} · %{x}<br>%{z:,.0f}<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=MUTED)),
        )
    )
    fig = apply_dark_layout(fig, title=title, height=height, show_legend=False)
    fig.update_yaxes(showgrid=False, autorange="reversed")
    fig.update_xaxes(showgrid=False)
    return fig


def _empty(title: str, height: int) -> go.Figure:
    """Return a styled empty-state figure."""
    fig = go.Figure()
    fig.add_annotation(text="Not enough data", showarrow=False, font=dict(color=MUTED))
    return apply_dark_layout(fig, title=title, height=height, show_legend=False)
