"""
Component: Sidebar
==================
Branded navigation sidebar with active-page highlighting and global status
pills (dataset / AI engine / database).

The default Streamlit page navigation is hidden via CSS (see ``theme.py``)
and replaced with this premium custom navigation. Routing uses
``st.page_link`` for inactive entries; the active entry renders as a
highlighted, non-interactive block so the current location is always clear.

Presentation only — reads state via ``session_manager``; no business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import streamlit as st

from components.theme import APP_NAME
from utils import session_manager


@dataclass(frozen=True)
class NavItem:
    """A single sidebar navigation entry."""

    key: str           # stable identifier matched against the active page
    label: str         # display label
    icon: str          # Material Symbols Rounded glyph name
    path: str          # script path used by st.page_link


# Navigation model (order defines sidebar order).
_NAV_ITEMS: Final[tuple[NavItem, ...]] = (
    NavItem("home", "Home", "home", "app.py"),
    NavItem("upload", "Upload Data", "upload_file", "pages/1_Upload_Data.py"),
    NavItem("analytics", "Business Analytics", "bar_chart_4_bars", "pages/2_Business_Analytics.py"),
    NavItem("forecasting", "Forecasting", "trending_up", "pages/3_Forecasting.py"),
    NavItem("insights", "AI Insights", "auto_awesome", "pages/4_AI_Insights.py"),
    NavItem("reports", "Reports", "description", "pages/5_Reports.py"),
    NavItem("settings", "Settings", "settings", "pages/6_Settings.py"),
)


def render_sidebar(active_page: str) -> None:
    """Render the full branded sidebar.

    Args:
        active_page: Key of the currently active page (see ``NavItem.key``).
            Used to highlight the active navigation entry.
    """
    session_manager.set_current_page(active_page)

    with st.sidebar:
        _render_brand()
        st.markdown(
            '<div class="sidebar-section-label">Navigation</div>',
            unsafe_allow_html=True,
        )
        for item in _NAV_ITEMS:
            _render_nav_item(item, is_active=item.key == active_page)

        st.markdown(
            '<div class="sidebar-section-label">Status</div>',
            unsafe_allow_html=True,
        )
        _render_status_pills()
        _render_footer()


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _render_brand() -> None:
    """Render the brand mark, name, and subtitle."""
    st.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="sidebar-logo">F</div>
            <div class="sidebar-brand-text">
                <span class="sidebar-brand-name">{APP_NAME.replace(" AI", "")}</span>
                <span class="sidebar-brand-sub">Business Forecasting Intelligence</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_nav_item(item: NavItem, *, is_active: bool) -> None:
    """Render one navigation entry (highlighted block or page link)."""
    if is_active:
        st.markdown(
            f"""
            <div class="nav-item active">
                <span class="material-symbols-rounded">{item.icon}</span>
                <span>{item.label}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.page_link(item.path, label=item.label, icon=f":material/{item.icon}:")


def _render_status_pills() -> None:
    """Render live status pills derived from session state."""
    data_loaded = session_manager.is_data_loaded()
    _status_pill(
        "Dataset",
        on=data_loaded,
        value="Loaded" if data_loaded else "Empty",
    )

    ai_provider = session_manager.get_state(session_manager.AI_PROVIDER)
    ai_ready = session_manager.get_state(session_manager.AI_METADATA) is not None
    ai_label = {
        "groq": "Groq",
        "ollama": "Ollama",
        "rule_based": "Rule-based",
    }.get(str(ai_provider or ""), "Ready")
    _status_pill(
        "AI Engine",
        on=True,
        value=ai_label if ai_ready else "Ready",
        warn=False,
    )

    db_status = session_manager.get_state(session_manager.DATABASE_STATUS) or {}
    db_ok = db_status.get("ok", True)
    _status_pill(
        "Database",
        on=db_ok,
        value="SQLite" if db_ok else "Offline",
        warn=not db_ok,
    )


def _status_pill(label: str, *, on: bool, value: str, warn: bool = False) -> None:
    """Render a single status pill."""
    dot_class = "warn" if warn else ("on" if on else "off")
    st.markdown(
        f"""
        <div class="status-pill">
            <span class="status-dot {dot_class}"></span>
            <span>{label}</span>
            <span class="status-value">{value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_footer() -> None:
    """Render a subtle version footer."""
    st.markdown(
        """
        <div style="margin-top:1.25rem; padding-top:0.75rem;
                    border-top:1px solid var(--fiq-border);
                    font-size:0.72rem; color:var(--fiq-muted);">
            v1.0 · Production
        </div>
        """,
        unsafe_allow_html=True,
    )
