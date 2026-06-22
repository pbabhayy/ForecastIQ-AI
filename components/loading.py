"""
Component: Loading States
=========================
Premium loading indicators and skeleton placeholders.

These keep the UI responsive and intentional while later steps perform
ingestion, forecasting, and AI generation. Presentation only.
"""

from __future__ import annotations

import streamlit as st


def show_loading(message: str = "Synthesizing business intelligence...") -> None:
    """Render a generic premium loading container.

    Args:
        message: Status text shown beside the spinner.
    """
    st.markdown(
        f"""
        <div class="loading-card fade-in">
            <div class="loading-spinner"></div>
            <div class="loading-text loading-pulse">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_forecast_loading(
    message: str = "Analyzing revenue trajectories...",
) -> None:
    """Render the forecast-specific loading container."""
    show_loading(message)


def show_ai_loading(message: str = "Generating strategic insights...") -> None:
    """Render the AI-specific loading container."""
    show_loading(message)


def show_skeleton(lines: int = 3, *, height: int = 14) -> None:
    """Render shimmering skeleton lines as a content placeholder.

    Args:
        lines: Number of skeleton bars to render.
        height: Height of each bar in pixels.
    """
    widths = ["100%", "92%", "78%", "85%", "64%"]
    bars = "".join(
        f'<div class="skeleton" style="height:{height}px; width:{widths[i % len(widths)]}; '
        f'margin-bottom:0.55rem;"></div>'
        for i in range(max(1, lines))
    )
    st.markdown(f'<div class="fade-in">{bars}</div>', unsafe_allow_html=True)


def show_skeleton_card() -> None:
    """Render a skeleton shaped like a metric card."""
    st.markdown(
        """
        <div class="metric-card">
            <div class="skeleton" style="height:12px; width:55%; margin-bottom:0.8rem;"></div>
            <div class="skeleton" style="height:24px; width:70%; margin-bottom:0.6rem;"></div>
            <div class="skeleton" style="height:10px; width:40%;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
