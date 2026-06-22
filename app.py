"""
ForecastIQ AI — Application Entry Point
=======================================
AI-Powered Business Forecasting & Decision Intelligence Platform.

Root entry / shell for the Streamlit multipage app. This module:
    * configures the Streamlit page (title / favicon / layout),
    * initializes session state (idempotent),
    * injects the premium CSS design system,
    * renders the branded sidebar navigation, and
    * renders the landing / home experience.

No business logic — Step 2 establishes the premium presentation foundation
that later steps populate with analytics, forecasting, AI, and reporting.
"""

from __future__ import annotations

import streamlit as st

from components import theme
from components.sidebar import render_sidebar
from database import sqlite_manager
from utils import session_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def _bootstrap() -> None:
    """Run the standard page bootstrap sequence.

    Order matters: ``configure_page`` must be the first Streamlit call.
    """
    theme.configure_page("Home")
    session_manager.init_session_state()
    theme.inject_premium_css()
    session_manager.set_state(session_manager.DATABASE_STATUS, sqlite_manager.check_health())
    render_sidebar(active_page="home")


def _render_hero() -> None:
    """Render the landing hero section."""
    st.markdown(
        f"""
        <div class="hero fade-in">
            <span class="hero-badge">
                <span class="status-dot on"></span> Powered by multi-model AI &amp; forecasting
            </span>
            <h1 class="hero-title">
                Turn raw business data into
                <span class="grad">decisions you can trust.</span>
            </h1>
            <p class="hero-sub">
                {theme.APP_TAGLINE}. Upload a CSV or XLSX file and ForecastIQ
                automatically profiles your data, forecasts revenue, orders, and
                customers, and generates board-ready insights — no manual setup.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b, _ = st.columns([1.1, 1, 2.4])
    with col_a:
        if st.button("Upload your dataset", type="primary", use_container_width=True):
            st.switch_page("pages/1_Upload_Data.py")
    with col_b:
        if st.button("View analytics", use_container_width=True):
            st.switch_page("pages/2_Business_Analytics.py")


def _render_features() -> None:
    """Render the capability feature cards."""
    theme.section_header(
        "Everything you need to forecast with confidence",
        "A complete decision-intelligence workflow",
    )

    features = [
        ("📤", "Smart Ingestion",
         "Drag &amp; drop CSV or XLSX. Columns are auto-detected with fuzzy "
         "matching — no manual mapping required."),
        ("🧮", "Business Analytics",
         "Revenue, orders, customers, and expense metrics with growth, trends, "
         "and a 0–100 business health score."),
        ("📈", "Multi-Model Forecasting",
         "Prophet and scikit-learn models with confidence intervals and "
         "transparent accuracy metrics (MAE / RMSE / MAPE)."),
        ("✨", "AI Insights",
         "Growth, risk, and trend narratives plus recommendations — with a "
         "deterministic fallback so it never fails."),
        ("📊", "Interactive Charts",
         "Premium Plotly visualizations with hover, zoom, pan, and export "
         "across every metric."),
        ("📄", "Professional Reports",
         "Export a polished PDF with summaries, forecasts, charts, and "
         "recommendations in one click."),
    ]

    rows = [features[i : i + 3] for i in range(0, len(features), 3)]
    for row in rows:
        cols = st.columns(3)
        for col, (icon, title, body) in zip(cols, row):
            with col:
                st.markdown(
                    f"""
                    <div class="feature-card fade-in">
                        <div class="feature-icon">{icon}</div>
                        <div class="feature-title">{title}</div>
                        <div class="feature-body">{body}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _render_pipeline() -> None:
    """Render the application flow as a row of step chips."""
    theme.section_header("How it works", "From upload to decision in minutes")
    steps = [
        "Upload dataset",
        "Validate &amp; profile",
        "Business analytics",
        "Generate forecasts",
        "AI insights",
        "Export report",
    ]
    chips = "".join(
        f'<div class="step-chip"><span class="step-num">{i + 1}</span>{label}</div>'
        for i, label in enumerate(steps)
    )
    st.markdown(
        f'<div style="display:flex; flex-wrap:wrap; gap:0.6rem; margin-top:0.4rem;">{chips}</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    """Render the home page."""
    try:
        _bootstrap()
        _render_hero()
        st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)
        _render_features()
        st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)
        _render_pipeline()
    except Exception:  # noqa: BLE001 — prevent raw tracebacks in UI
        logger.exception("Home page error")
        st.error("Something went wrong loading the home page. Please refresh and try again.")


if __name__ == "__main__":
    main()
