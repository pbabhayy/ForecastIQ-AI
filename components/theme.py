"""
Component: Theme Engine
=======================
Centralized design system for ForecastIQ AI.

This module owns the *entire* visual language of the product:
    * page configuration (title / favicon / layout)
    * the global premium CSS (``inject_premium_css``)
    * a small set of reusable, styled render helpers (page header, section
      header, metric card) that compose the CSS design tokens.

ALL CSS lives here. No other module declares inline styles. Components and
pages apply the *classes* defined here; they never write raw CSS.
"""

from __future__ import annotations

import html as html_lib
from datetime import datetime
from typing import Final

import streamlit as st

# --------------------------------------------------------------------------- #
# Design tokens (single source of visual truth)
# --------------------------------------------------------------------------- #
COLORS: Final[dict[str, str]] = {
    "background": "#0B0F19",
    "surface": "#111827",
    "surface_alt": "#0F1623",
    "border": "#1F2937",
    "text": "#F9FAFB",
    "muted": "#9CA3AF",
    "accent": "#3B82F6",
    "accent_soft": "rgba(59, 130, 246, 0.12)",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}

APP_NAME: Final[str] = "ForecastIQ AI"
APP_TAGLINE: Final[str] = "AI-Powered Business Forecasting & Decision Intelligence"
PAGE_ICON: Final[str] = "📈"


# --------------------------------------------------------------------------- #
# Page configuration
# --------------------------------------------------------------------------- #
def configure_page(page_title: str, *, page_icon: str = PAGE_ICON) -> None:
    """Configure the Streamlit page.

    Must be the first Streamlit call in any script/page that uses it.

    Args:
        page_title: Browser tab title suffix (prefixed with the brand).
        page_icon: Favicon emoji/character.
    """
    st.set_page_config(
        page_title=f"{page_title} · {APP_NAME}",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )


# --------------------------------------------------------------------------- #
# Global CSS injection
# --------------------------------------------------------------------------- #
def inject_premium_css(theme_mode: str | None = None) -> None:
    """Inject the global premium design system stylesheet.

    Args:
        theme_mode: ``"dark"`` or ``"light"``. When ``None``, reads session state.
    """
    mode = (theme_mode or _current_theme_mode()).lower()
    if mode == "light":
        st.markdown(_LIGHT_CSS, unsafe_allow_html=True)
    else:
        st.markdown(_PREMIUM_CSS, unsafe_allow_html=True)


def _current_theme_mode() -> str:
    """Return active theme from session (defaults to dark)."""
    try:
        from utils import session_manager

        return str(session_manager.get_state(session_manager.THEME_MODE, "dark") or "dark")
    except Exception:
        return "dark"


def _render_html(fragment: str) -> None:
    """Render raw HTML (``st.html`` when available, else ``st.markdown``)."""
    if hasattr(st, "html"):
        st.html(fragment)
    else:
        st.markdown(fragment, unsafe_allow_html=True)


def format_display_timestamp(iso_value: str | None) -> str:
    """Format an ISO-8601 timestamp for UI display."""
    if not iso_value:
        return "—"
    try:
        normalized = iso_value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%b %d, %Y · %H:%M UTC")
    except (TypeError, ValueError):
        return str(iso_value)


# --------------------------------------------------------------------------- #
# Reusable render helpers (compose the CSS classes)
# --------------------------------------------------------------------------- #
def page_header(title: str, subtitle: str = "", *, eyebrow: str = "") -> None:
    """Render a consistent page hero header.

    Args:
        title: Main page title.
        subtitle: Supporting one-line description.
        eyebrow: Small uppercase label rendered above the title.
    """
    eyebrow_html = f'<div class="page-eyebrow">{eyebrow}</div>' if eyebrow else ""
    subtitle_html = f'<p class="page-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="page-header fade-in">
            {eyebrow_html}
            <h1 class="page-title">{title}</h1>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "") -> None:
    """Render a section divider/header used to group content on a page."""
    subtitle_html = (
        f'<span class="section-subtitle">{subtitle}</span>' if subtitle else ""
    )
    st.markdown(
        f"""
        <div class="section-header">
            <h3 class="section-title">{title}</h3>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(
    label: str,
    value: str,
    *,
    delta: str | None = None,
    delta_positive: bool | None = None,
    icon: str = "",
    caption: str = "",
) -> None:
    """Render a premium KPI / metric card.

    Presentation only — receives already-formatted strings. During Step 2
    these are populated with placeholder values; later steps pass computed
    metrics.

    Args:
        label: Metric label (e.g. "Total Revenue").
        value: Formatted value string (e.g. "$1.2M" or "—").
        delta: Optional formatted delta string (e.g. "+12.4%").
        delta_positive: Controls delta color (green/red). ``None`` = neutral.
        icon: Optional emoji/glyph rendered in the card corner.
        caption: Optional small caption beneath the value.
    """
    icon_html = f'<div class="metric-icon">{html_lib.escape(icon)}</div>' if icon else ""
    safe_label = html_lib.escape(label)
    safe_value = html_lib.escape(value)
    safe_caption = html_lib.escape(caption) if caption else ""
    caption_html = f'<div class="metric-caption">{safe_caption}</div>' if safe_caption else ""
    delta_html = ""
    if delta is not None:
        tone = (
            "neutral"
            if delta_positive is None
            else ("up" if delta_positive else "down")
        )
        delta_html = f'<div class="metric-delta {tone}">{html_lib.escape(delta)}</div>'

    value_class = "metric-value"
    if label.lower() == "date range":
        value_class = "metric-value metric-value-compact"

    _render_html(
        f"""
        <div class="metric-card fade-in">
            <div class="metric-card-top">
                <span class="metric-label">{safe_label}</span>
                {icon_html}
            </div>
            <div class="{value_class}">{safe_value}</div>
            {delta_html}
            {caption_html}
        </div>
        """
    )


def chart_placeholder(title: str, height: int = 320) -> None:
    """Render a styled chart-container placeholder (no chart logic).

    Used by page shells in Step 2; later steps render real Plotly figures
    inside the same ``.chart-container`` styling.
    """
    st.markdown(
        f"""
        <div class="chart-container fade-in" style="min-height:{height}px;">
            <div class="chart-placeholder-inner">
                <div class="chart-placeholder-icon">📊</div>
                <div class="chart-placeholder-title">{title}</div>
                <div class="chart-placeholder-sub">
                    Visualization renders here once data is processed
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# The stylesheet
# --------------------------------------------------------------------------- #
_PREMIUM_CSS: Final[str] = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0&display=block');

:root {
    --fiq-bg: #0B0F19;
    --fiq-surface: #111827;
    --fiq-surface-alt: #0F1623;
    --fiq-border: #1F2937;
    --fiq-text: #F9FAFB;
    --fiq-muted: #9CA3AF;
    --fiq-accent: #3B82F6;
    --fiq-accent-soft: rgba(59, 130, 246, 0.12);
    --fiq-success: #22C55E;
    --fiq-warning: #F59E0B;
    --fiq-danger: #EF4444;

    --fiq-radius: 12px;
    --fiq-radius-sm: 8px;
    --fiq-shadow: 0 1px 2px rgba(0,0,0,0.30), 0 8px 24px rgba(0,0,0,0.20);
    --fiq-shadow-hover: 0 2px 4px rgba(0,0,0,0.35), 0 16px 40px rgba(0,0,0,0.30);
    --fiq-transition: 0.2s ease;
}

/* ---------- Base ---------- */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', system-ui, 'Segoe UI', -apple-system,
                 BlinkMacSystemFont, 'San Francisco', sans-serif;
}
.stApp {
    background:
        radial-gradient(1200px 600px at 80% -10%, rgba(59,130,246,0.08), transparent 60%),
        radial-gradient(900px 500px at -10% 10%, rgba(59,130,246,0.05), transparent 55%),
        var(--fiq-bg);
    color: var(--fiq-text);
}

/* ---------- Hide default Streamlit chrome ---------- */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stStatusWidget"] { display: none; }

/* ---------- Reduce default spacing ---------- */
.block-container {
    padding-top: 2.4rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}
[data-testid="stVerticalBlock"] { gap: 1rem; }

/* ---------- Typography ---------- */
h1, h2, h3, h4 { color: var(--fiq-text); font-weight: 700; letter-spacing: -0.02em; }
p, span, label, li { color: var(--fiq-text); }
.text-muted, .metric-caption, .page-subtitle { color: var(--fiq-muted) !important; }

.page-header { margin-bottom: 1.6rem; }
.page-eyebrow {
    text-transform: uppercase; letter-spacing: 0.14em; font-size: 0.72rem;
    font-weight: 600; color: var(--fiq-accent); margin-bottom: 0.5rem;
}
.page-title { font-size: 2rem; font-weight: 800; margin: 0; line-height: 1.15; }
.page-subtitle { font-size: 1rem; color: var(--fiq-muted); margin: 0.5rem 0 0; max-width: 720px; }

.section-header {
    display: flex; align-items: baseline; gap: 0.75rem;
    margin: 0.5rem 0 0.25rem; padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--fiq-border);
}
.section-title { font-size: 1.1rem; font-weight: 700; margin: 0; }
.section-subtitle { font-size: 0.85rem; color: var(--fiq-muted); }

/* ---------- Material symbols (nav icons / brand) ---------- */
.material-symbols-rounded {
    font-family: 'Material Symbols Rounded';
    font-weight: normal; font-style: normal; line-height: 1;
    vertical-align: middle; -webkit-font-smoothing: antialiased;
}

/* ---------- Metric / KPI cards ---------- */
.metric-card {
    background: linear-gradient(180deg, var(--fiq-surface) 0%, var(--fiq-surface-alt) 100%);
    border: 1px solid var(--fiq-border);
    border-radius: var(--fiq-radius);
    padding: 1.15rem 1.25rem;
    box-shadow: var(--fiq-shadow);
    transition: transform var(--fiq-transition), box-shadow var(--fiq-transition),
                border-color var(--fiq-transition);
    height: 100%;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--fiq-shadow-hover);
    border-color: rgba(59,130,246,0.35);
}
.metric-card-top { display: flex; align-items: center; justify-content: space-between; }
.metric-label { font-size: 0.82rem; font-weight: 500; color: var(--fiq-muted); }
.metric-icon { font-size: 1rem; opacity: 0.85; }
.metric-value { font-size: 1.7rem; font-weight: 800; margin-top: 0.4rem; letter-spacing: -0.02em; }
.metric-value-compact { font-size: 1.05rem; font-weight: 700; line-height: 1.35; white-space: nowrap; }
.metric-caption { font-size: 0.75rem; color: var(--fiq-muted); margin-top: 0.35rem; line-height: 1.35; }
.metric-delta {
    display: inline-flex; align-items: center; gap: 0.25rem;
    font-size: 0.78rem; font-weight: 600; margin-top: 0.5rem;
    padding: 0.15rem 0.5rem; border-radius: 999px; width: fit-content;
}
.metric-delta.up { color: var(--fiq-success); background: rgba(34,197,94,0.12); }
.metric-delta.down { color: var(--fiq-danger); background: rgba(239,68,68,0.12); }
.metric-delta.neutral { color: var(--fiq-muted); background: rgba(156,163,175,0.12); }

/* ---------- Glass panel ---------- */
.glass-panel {
    background: rgba(17, 24, 39, 0.65);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid var(--fiq-border);
    border-radius: var(--fiq-radius);
    padding: 1.4rem 1.5rem;
    box-shadow: var(--fiq-shadow);
}

/* ---------- Insight card ---------- */
.insight-card {
    background: var(--fiq-surface);
    border: 1px solid var(--fiq-border);
    border-left: 3px solid var(--fiq-accent);
    border-radius: var(--fiq-radius-sm);
    padding: 1rem 1.15rem;
    margin-bottom: 0.75rem;
    box-shadow: var(--fiq-shadow);
    transition: transform var(--fiq-transition), border-color var(--fiq-transition);
}
.insight-card:hover { transform: translateY(-2px); border-left-color: #60A5FA; }
.insight-card .insight-title { font-weight: 600; font-size: 0.95rem; margin-bottom: 0.25rem; }
.insight-card .insight-body { font-size: 0.88rem; color: var(--fiq-muted); }

/* ---------- Chart container ---------- */
.chart-container {
    background: var(--fiq-surface);
    border: 1px solid var(--fiq-border);
    border-radius: var(--fiq-radius);
    padding: 1.1rem 1.25rem;
    box-shadow: var(--fiq-shadow);
}
[data-testid="stPlotlyChart"] {
    min-height: 260px;
    background: var(--fiq-surface);
    border: 1px solid var(--fiq-border);
    border-radius: var(--fiq-radius);
    padding: 0.35rem;
}
.chart-placeholder-inner { text-align: center; color: var(--fiq-muted); }
.chart-placeholder-icon { font-size: 2rem; opacity: 0.6; }
.chart-placeholder-title { font-weight: 600; color: var(--fiq-text); margin-top: 0.5rem; }
.chart-placeholder-sub { font-size: 0.82rem; margin-top: 0.2rem; }

/* ---------- Placeholder / empty-state panel ---------- */
.placeholder-panel {
    background: var(--fiq-surface);
    border: 1px dashed var(--fiq-border);
    border-radius: var(--fiq-radius);
    padding: 3rem 2rem;
    text-align: center;
    box-shadow: var(--fiq-shadow);
}
.placeholder-icon {
    font-size: 2.6rem; opacity: 0.75; margin-bottom: 0.6rem;
    display: inline-flex; width: 64px; height: 64px; align-items: center;
    justify-content: center; border-radius: 16px; background: var(--fiq-accent-soft);
}
.placeholder-title { font-size: 1.15rem; font-weight: 700; margin: 0.4rem 0 0.3rem; }
.placeholder-message { color: var(--fiq-muted); font-size: 0.9rem; max-width: 460px; margin: 0 auto; }

/* ---------- Buttons (design-token classes) ---------- */
.primary-button, .secondary-button {
    display: inline-flex; align-items: center; gap: 0.5rem;
    padding: 0.6rem 1.1rem; border-radius: var(--fiq-radius-sm);
    font-weight: 600; font-size: 0.9rem; cursor: pointer;
    transition: all var(--fiq-transition); text-decoration: none;
}
.primary-button {
    background: var(--fiq-accent); color: #fff; border: 1px solid var(--fiq-accent);
    box-shadow: 0 8px 20px rgba(59,130,246,0.30);
}
.primary-button:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(59,130,246,0.42); }
.secondary-button {
    background: transparent; color: var(--fiq-text); border: 1px solid var(--fiq-border);
}
.secondary-button:hover { transform: translateY(-2px); border-color: var(--fiq-accent); color: #fff; }

/* ---------- Native Streamlit buttons restyled ---------- */
.stButton > button {
    border-radius: var(--fiq-radius-sm);
    border: 1px solid var(--fiq-border);
    background: var(--fiq-surface);
    color: var(--fiq-text);
    font-weight: 600;
    padding: 0.55rem 1.1rem;
    transition: all var(--fiq-transition);
}
.stButton > button:hover {
    border-color: var(--fiq-accent);
    transform: translateY(-2px);
    box-shadow: var(--fiq-shadow);
    color: #fff;
}
.stButton > button[kind="primary"] {
    background: var(--fiq-accent);
    border-color: var(--fiq-accent);
    color: #fff;
    box-shadow: 0 8px 20px rgba(59,130,246,0.30);
}
.stButton > button[kind="primary"]:hover { box-shadow: 0 12px 28px rgba(59,130,246,0.42); }

/* ---------- Banners ---------- */
.warning-banner, .error-banner, .success-banner {
    display: flex; align-items: flex-start; gap: 0.6rem;
    border-radius: var(--fiq-radius-sm); padding: 0.8rem 1rem;
    font-size: 0.88rem; margin: 0.4rem 0; border: 1px solid transparent;
}
.warning-banner { background: rgba(245,158,11,0.10); border-color: rgba(245,158,11,0.35); color: #FCD34D; }
.error-banner { background: rgba(239,68,68,0.10); border-color: rgba(239,68,68,0.35); color: #FCA5A5; }
.success-banner { background: rgba(34,197,94,0.10); border-color: rgba(34,197,94,0.35); color: #86EFAC; }
.banner-icon { font-size: 1rem; line-height: 1.3; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: var(--fiq-surface-alt);
    border-right: 1px solid var(--fiq-border);
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] { display: none; }
section[data-testid="stSidebar"] .block-container { padding-top: 1.25rem; }

.sidebar-brand { display: flex; align-items: center; gap: 0.7rem; padding: 0.25rem 0.25rem 0.5rem; }
.sidebar-logo {
    width: 38px; height: 38px; border-radius: 10px;
    background: linear-gradient(135deg, var(--fiq-accent), #1D4ED8);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 800; font-size: 1.05rem;
    box-shadow: 0 6px 16px rgba(59,130,246,0.40);
}
.sidebar-brand-text { display: flex; flex-direction: column; line-height: 1.1; }
.sidebar-brand-name { font-weight: 800; font-size: 1.02rem; letter-spacing: -0.01em; }
.sidebar-brand-sub { font-size: 0.7rem; color: var(--fiq-muted); }

.sidebar-section-label {
    text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.66rem;
    color: var(--fiq-muted); font-weight: 600; margin: 1rem 0.35rem 0.4rem;
}

/* Active nav item (custom block) */
.nav-item {
    display: flex; align-items: center; gap: 0.7rem;
    padding: 0.55rem 0.7rem; border-radius: var(--fiq-radius-sm);
    font-size: 0.9rem; font-weight: 600; margin-bottom: 0.15rem;
}
.nav-item.active {
    background: var(--fiq-accent-soft);
    color: #fff; border: 1px solid rgba(59,130,246,0.35);
}
.nav-item.active .material-symbols-rounded { color: var(--fiq-accent); }

/* Inactive nav items rendered via st.page_link */
section[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    border-radius: var(--fiq-radius-sm);
    padding: 0.5rem 0.7rem !important;
    transition: all var(--fiq-transition);
}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: rgba(255,255,255,0.04);
}
section[data-testid="stSidebar"] [data-testid="stPageLink"] p {
    font-size: 0.9rem; font-weight: 600; color: var(--fiq-muted);
}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover p { color: var(--fiq-text); }

/* Status pills */
.status-pill {
    display: flex; align-items: center; gap: 0.5rem;
    padding: 0.45rem 0.6rem; border-radius: var(--fiq-radius-sm);
    background: var(--fiq-surface); border: 1px solid var(--fiq-border);
    font-size: 0.78rem; margin-bottom: 0.35rem; color: var(--fiq-muted);
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.status-dot.on { background: var(--fiq-success); box-shadow: 0 0 0 3px rgba(34,197,94,0.15); }
.status-dot.off { background: var(--fiq-muted); }
.status-dot.warn { background: var(--fiq-warning); box-shadow: 0 0 0 3px rgba(245,158,11,0.15); }
.status-pill .status-value { margin-left: auto; color: var(--fiq-text); font-weight: 600; }

/* ---------- Landing / hero ---------- */
.hero { padding: 2.5rem 0 1rem; }
.hero-badge {
    display: inline-flex; align-items: center; gap: 0.45rem;
    padding: 0.35rem 0.75rem; border-radius: 999px;
    background: var(--fiq-accent-soft); border: 1px solid rgba(59,130,246,0.35);
    color: #93C5FD; font-size: 0.78rem; font-weight: 600; margin-bottom: 1.1rem;
}
.hero-title {
    font-size: 3rem; font-weight: 800; line-height: 1.08;
    letter-spacing: -0.03em; margin: 0 0 1rem; max-width: 820px;
}
.hero-title .grad {
    background: linear-gradient(90deg, #60A5FA, #3B82F6 60%, #2563EB);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub { font-size: 1.1rem; color: var(--fiq-muted); max-width: 640px; margin: 0 0 1.6rem; }

.feature-card {
    background: var(--fiq-surface);
    border: 1px solid var(--fiq-border);
    border-radius: var(--fiq-radius);
    padding: 1.25rem 1.3rem; height: 100%;
    transition: transform var(--fiq-transition), border-color var(--fiq-transition),
                box-shadow var(--fiq-transition);
    box-shadow: var(--fiq-shadow);
}
.feature-card:hover {
    transform: translateY(-2px); border-color: rgba(59,130,246,0.35);
    box-shadow: var(--fiq-shadow-hover);
}
.feature-icon {
    width: 42px; height: 42px; border-radius: 10px; display: flex;
    align-items: center; justify-content: center; font-size: 1.2rem;
    background: var(--fiq-accent-soft); margin-bottom: 0.7rem;
}
.feature-title { font-weight: 700; font-size: 1rem; margin-bottom: 0.3rem; }
.feature-body { font-size: 0.86rem; color: var(--fiq-muted); }

/* Pipeline step */
.step-chip {
    display: flex; align-items: center; gap: 0.6rem;
    background: var(--fiq-surface); border: 1px solid var(--fiq-border);
    border-radius: 999px; padding: 0.45rem 0.9rem; font-size: 0.82rem;
    color: var(--fiq-muted); font-weight: 600;
}
.step-num {
    width: 22px; height: 22px; border-radius: 50%; background: var(--fiq-accent-soft);
    color: var(--fiq-accent); display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700;
}

/* ---------- Inputs (selectbox / file uploader / radio) ---------- */
[data-testid="stFileUploaderDropzone"] {
    background: var(--fiq-surface);
    border: 1.5px dashed var(--fiq-border);
    border-radius: var(--fiq-radius);
    transition: border-color var(--fiq-transition), background var(--fiq-transition);
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--fiq-accent); background: var(--fiq-accent-soft);
}
div[data-baseweb="select"] > div {
    background: var(--fiq-surface); border-color: var(--fiq-border); border-radius: var(--fiq-radius-sm);
}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 0.4rem; border-bottom: 1px solid var(--fiq-border); }
.stTabs [data-baseweb="tab"] {
    background: transparent; color: var(--fiq-muted); font-weight: 600;
    border-radius: var(--fiq-radius-sm) var(--fiq-radius-sm) 0 0;
}
.stTabs [aria-selected="true"] { color: var(--fiq-text); }

/* ---------- Animations ---------- */
@keyframes fiqFadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fiqFadeIn 0.45s ease both; }

@keyframes fiqPulse {
    0%, 100% { opacity: 0.45; }
    50%      { opacity: 1; }
}
.loading-pulse { animation: fiqPulse 1.4s ease-in-out infinite; }

@keyframes fiqShimmer {
    0%   { background-position: -480px 0; }
    100% { background-position: 480px 0; }
}
.skeleton {
    border-radius: var(--fiq-radius-sm);
    background: linear-gradient(90deg, #131b2b 25%, #1b2435 37%, #131b2b 63%);
    background-size: 960px 100%;
    animation: fiqShimmer 1.6s infinite linear;
}

/* ---------- Loading container ---------- */
.loading-card {
    display: flex; align-items: center; gap: 0.8rem;
    background: var(--fiq-surface); border: 1px solid var(--fiq-border);
    border-radius: var(--fiq-radius); padding: 1rem 1.2rem; box-shadow: var(--fiq-shadow);
}
.loading-spinner {
    width: 18px; height: 18px; border-radius: 50%;
    border: 2px solid var(--fiq-border); border-top-color: var(--fiq-accent);
    animation: fiqSpin 0.8s linear infinite; flex-shrink: 0;
}
@keyframes fiqSpin { to { transform: rotate(360deg); } }
.loading-text { font-weight: 600; font-size: 0.9rem; }

/* ---------- Dividers / misc ---------- */
hr { border-color: var(--fiq-border); }
.stDataFrame { border-radius: var(--fiq-radius); overflow: hidden; }
</style>
"""

# Light theme — same structure, swapped palette (Phase 4).
_LIGHT_CSS: Final[str] = _PREMIUM_CSS.replace(
    "--fiq-bg: #0B0F19", "--fiq-bg: #F8FAFC"
).replace(
    "--fiq-surface: #111827", "--fiq-surface: #FFFFFF"
).replace(
    "--fiq-surface-alt: #0F1623", "--fiq-surface-alt: #F1F5F9"
).replace(
    "--fiq-border: #1F2937", "--fiq-border: #E2E8F0"
).replace(
    "--fiq-text: #F9FAFB", "--fiq-text: #0F172A"
).replace(
    "--fiq-muted: #9CA3AF", "--fiq-muted: #64748B"
).replace(
    "radial-gradient(1200px 600px at 80% -10%, rgba(59,130,246,0.08), transparent 60%),\n        radial-gradient(900px 500px at -10% 10%, rgba(59,130,246,0.05), transparent 55%),\n        var(--fiq-bg);",
    "var(--fiq-bg);",
).replace(
    "background: linear-gradient(90deg, #131b2b 25%, #1b2435 37%, #131b2b 63%);",
    "background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 37%, #e2e8f0 63%);",
)
