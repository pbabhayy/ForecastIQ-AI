"""
Page: Settings
================
Configuration overview: appearance preferences, AI provider connectivity,
forecast defaults, and application information.
"""

from __future__ import annotations

import streamlit as st

from ai.groq_provider import GroqProvider
from ai.ollama_provider import OllamaProvider
from components import error_states, theme
from components.sidebar import render_sidebar
from config.settings import get_settings
from database import sqlite_manager
from utils import session_manager


def _bootstrap() -> None:
    theme.configure_page("Settings")
    session_manager.init_session_state()
    theme.inject_premium_css()
    render_sidebar(active_page="settings")
    session_manager.set_state(session_manager.DATABASE_STATUS, sqlite_manager.check_health())


def _render_appearance() -> None:
    theme.section_header("Appearance", "Visual preferences")
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Theme", ("Dark (default)", "Light"), key="settings_theme")
    with c2:
        st.selectbox("Accent color", ("Blue", "Violet", "Emerald"), key="settings_accent")
    st.caption("Appearance controls are stored for a future release.")


def _render_providers() -> None:
    theme.section_header("AI Providers", "Resolution order: Groq → Ollama → Rule-based")
    settings = get_settings()
    groq = GroqProvider()
    ollama = OllamaProvider()

    c1, c2 = st.columns(2)
    with c1:
        st.text_input(
            "Groq API key",
            type="password",
            value="••••••••" if settings.groq_api_key else "",
            disabled=True,
            help="Set GROQ_API_KEY in your .env file",
        )
        st.caption(f"Model: {settings.groq_model}")
    with c2:
        st.text_input("Ollama base URL", value=settings.ollama_base_url, disabled=True)
        st.caption(f"Model: {settings.ollama_model}")

    cols = st.columns(3)
    statuses = [
        ("Groq", "Connected" if groq.is_available() else "Not configured", "✅" if groq.is_available() else "💤"),
        ("Ollama", "Connected" if ollama.is_available() else "Not running", "✅" if ollama.is_available() else "💤"),
        ("Rule-based", "Always available", "✅"),
    ]
    for col, (label, value, icon) in zip(cols, statuses):
        with col:
            theme.metric_card(label, value, icon=icon)


def _render_forecast_settings() -> None:
    theme.section_header("Forecast defaults")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox(
            "Default model",
            ("Prophet", "Linear Regression"),
            key="settings_model",
        )
    with c2:
        st.selectbox(
            "Default horizon",
            ("1 Month", "3 Months", "6 Months", "12 Months"),
            index=2,
            key="settings_horizon",
        )
    with c3:
        st.slider("Confidence interval", 80, 99, 90, key="settings_ci")
    st.caption("Defaults apply on the Forecasting page in a future preferences release.")


def _render_app_info() -> None:
    theme.section_header("Application")
    db = session_manager.get_state(session_manager.DATABASE_STATUS) or {}
    st.markdown(
        f"""
        <div class="glass-panel fade-in">
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">Product</span><span>{theme.APP_NAME}</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">Version</span><span>1.0 · Production</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">Database</span><span>{db.get('path', '—')}</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">Stack</span>
                <span>Streamlit · Plotly · Prophet · scikit-learn · SQLite</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">AI</span>
                <span>Groq · Ollama · Rule-based fallback</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if db.get("ok"):
        error_states.show_success("Local SQLite database is connected.", title="Database")
    else:
        error_states.show_warning(
            db.get("error", "Database unavailable."),
            title="Database",
        )


def main() -> None:
    _bootstrap()
    theme.page_header(
        "Settings",
        "Configure providers, forecasting defaults, and appearance.",
        eyebrow="Configuration",
    )
    _render_appearance()
    _render_providers()
    _render_forecast_settings()
    _render_app_info()


if __name__ == "__main__":
    main()
