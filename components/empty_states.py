"""
Component: Empty States
=======================
Elegant, centered empty-state panels with a clear call-to-action.

Each function renders a ``.placeholder-panel`` and, where relevant, a
navigation link guiding the user to the next logical action. Presentation
only — these are the guards pages use when a prerequisite is missing.
"""

from __future__ import annotations

import streamlit as st


def _render_panel(
    icon: str,
    title: str,
    message: str,
    *,
    cta_label: str | None = None,
    cta_path: str | None = None,
) -> None:
    """Render a centered empty-state panel with an optional CTA link.

    Args:
        icon: Emoji/glyph displayed in the panel badge.
        title: Panel title.
        message: Supporting muted message.
        cta_label: Optional call-to-action label.
        cta_path: Optional page path the CTA links to.
    """
    st.markdown(
        f"""
        <div class="placeholder-panel fade-in">
            <div class="placeholder-icon">{icon}</div>
            <div class="placeholder-title">{title}</div>
            <div class="placeholder-message">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if cta_label and cta_path:
        # Center the navigation link beneath the panel.
        _, mid, _ = st.columns([1, 1, 1])
        with mid:
            st.page_link(cta_path, label=cta_label, icon=":material/arrow_forward:")


def show_no_data() -> None:
    """Empty state shown when no dataset has been uploaded yet."""
    _render_panel(
        "📂",
        "No dataset yet",
        "Upload a CSV or XLSX file to unlock analytics, forecasting, and "
        "AI-generated insights for your business.",
        cta_label="Upload a dataset",
        cta_path="pages/1_Upload_Data.py",
    )


def show_no_forecast() -> None:
    """Empty state shown when no forecast has been generated yet."""
    _render_panel(
        "📈",
        "No forecasts generated",
        "Once a dataset is loaded, generate revenue, order, and customer "
        "forecasts with confidence intervals and accuracy metrics.",
        cta_label="Go to Forecasting",
        cta_path="pages/3_Forecasting.py",
    )


def show_no_insights() -> None:
    """Empty state shown when no insights are available yet."""
    _render_panel(
        "✨",
        "No insights available",
        "AI-generated growth, risk, and trend insights will appear here after "
        "your analytics and forecasts are ready.",
        cta_label="Open AI Insights",
        cta_path="pages/4_AI_Insights.py",
    )


def show_no_reports() -> None:
    """Empty state shown when no reports have been generated yet."""
    _render_panel(
        "📄",
        "No reports yet",
        "Generate a professional PDF report summarizing analytics, forecasts, "
        "insights, and recommendations once your analysis is complete.",
        cta_label="Go to Reports",
        cta_path="pages/5_Reports.py",
    )
