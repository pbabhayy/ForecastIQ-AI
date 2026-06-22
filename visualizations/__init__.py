"""
Isolated Plotly visualization layer
===================================
ALL chart code lives in this package — nowhere else.

This package init exposes the shared chart-theming primitives so every chart
module renders with one consistent, premium dark style (transparent
background, ``plotly_dark`` template, token-driven fonts/grid). Chart modules
import :func:`apply_dark_layout` and the color tokens from here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import theme_tokens as tokens

if TYPE_CHECKING:  # pragma: no cover - typing only
    import plotly.graph_objects as go

# Re-export commonly used color tokens for chart modules.
ACCENT = tokens.ACCENT
MUTED = tokens.MUTED
TEXT = tokens.TEXT
SUCCESS = tokens.SUCCESS
WARNING = tokens.WARNING
DANGER = tokens.DANGER
COLOR_HISTORY = tokens.COLOR_HISTORY
COLOR_FORECAST = tokens.COLOR_FORECAST
COLOR_CONFIDENCE_FILL = tokens.COLOR_CONFIDENCE_FILL
CHART_SEQUENCE = tokens.CHART_SEQUENCE
HEATMAP_COLORSCALE = tokens.HEATMAP_COLORSCALE


def apply_dark_layout(
    fig: "go.Figure",
    *,
    title: str | None = None,
    height: int = 320,
    show_legend: bool = True,
) -> "go.Figure":
    """Apply the shared premium dark styling to a Plotly figure.

    Transparent paper/plot backgrounds let charts blend into the surrounding
    ``.chart-container`` cards. Hover, zoom, pan, and export are enabled by
    Plotly defaults and preserved here.

    Args:
        fig: The figure to style (mutated in place and returned).
        title: Optional chart title.
        height: Figure height in pixels.
        show_legend: Whether to display the legend.

    Returns:
        The same figure, styled.
    """
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=tokens.FONT_FAMILY, size=tokens.FONT_SIZE, color=tokens.TEXT),
        title=dict(text=title or "", font=dict(size=15, color=tokens.TEXT), x=0.01, xanchor="left"),
        margin=dict(l=10, r=10, t=40 if title else 16, b=10),
        height=height,
        hovermode="x unified",
        showlegend=show_legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)", font=dict(color=tokens.MUTED),
        ),
        colorway=list(tokens.CHART_SEQUENCE),
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=tokens.GRID_COLOR, zeroline=False,
        linecolor=tokens.AXIS_COLOR, tickfont=dict(color=tokens.MUTED),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=tokens.GRID_COLOR, zeroline=False,
        linecolor=tokens.AXIS_COLOR, tickfont=dict(color=tokens.MUTED),
    )
    return fig
