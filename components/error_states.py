"""
Component: Error States
=======================
Non-intrusive, consistently styled status banners.

These translate validation/forecast/AI outcomes into calm, layout-safe
messages. They never raise, never break layout, and never expose raw stack
traces. Presentation only.
"""

from __future__ import annotations

import streamlit as st


def show_warning(message: str, *, title: str = "Heads up") -> None:
    """Render a warning banner.

    Args:
        message: User-facing warning text.
        title: Short bold lead-in for the banner.
    """
    _banner("warning-banner", "⚠️", title, message)


def show_error(message: str, *, title: str = "Something went wrong") -> None:
    """Render an error banner.

    Args:
        message: User-facing, friendly error text.
        title: Short bold lead-in for the banner.
    """
    _banner("error-banner", "⛔", title, message)


def show_success(message: str, *, title: str = "Success") -> None:
    """Render a success banner.

    Args:
        message: User-facing confirmation text.
        title: Short bold lead-in for the banner.
    """
    _banner("success-banner", "✅", title, message)


def _banner(css_class: str, icon: str, title: str, message: str) -> None:
    """Render a styled banner (internal)."""
    st.markdown(
        f"""
        <div class="{css_class} fade-in">
            <span class="banner-icon">{icon}</span>
            <span><strong>{title}.</strong> {message}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
