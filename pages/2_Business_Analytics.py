"""
Page: Business Analytics
========================
Premium analytics dashboard wired to the Step 3 analytics + health engines.

Reads the cleaned canonical dataset from session, computes (or reuses) the
analytics payload and business-health score, and renders real KPIs, the
health score with its transparent breakdown, a trend summary, and peak/weak
periods. Charts are deferred to Step 4.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from analytics import health_score, metrics
from components import empty_states, theme
from components.sidebar import render_sidebar
from utils import column_mapper, session_manager
from utils.logger import get_logger
from visualizations import heatmaps, revenue_charts

logger = get_logger(__name__)


def _bootstrap() -> None:
    theme.configure_page("Business Analytics")
    session_manager.init_session_state()
    theme.inject_premium_css()
    render_sidebar(active_page="analytics")


def _ensure_analytics() -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Return ``(analytics, health)`` from session, computing lazily if needed."""
    clean_df = session_manager.get_state(session_manager.CLEANED_DATA)
    if clean_df is None or getattr(clean_df, "empty", True):
        return None

    analytics = session_manager.get_state(session_manager.ANALYTICS)
    if not analytics or not analytics.get("meta", {}).get("available"):
        analytics = metrics.compute_metrics(clean_df)
        session_manager.set_state(session_manager.ANALYTICS, analytics)

    health = session_manager.get_state(session_manager.HEALTH_METRICS)
    if not health:
        health = health_score.compute_health(analytics)
        session_manager.set_state(session_manager.HEALTH_METRICS, health)

    return analytics, health


def _render_revenue_kpis(analytics: dict[str, Any]) -> None:
    revenue = analytics.get(column_mapper.REVENUE)
    if not revenue:
        return
    theme.section_header("Revenue", "Core revenue performance")
    cols = st.columns(4)
    cards = [
        ("Total Revenue", metrics.format_currency(revenue["total"]), "💰"),
        ("Average / Month", metrics.format_currency(revenue["average"]), "📊"),
        ("Median / Month", metrics.format_currency(revenue["median"]), "➗"),
        ("Revenue Growth", metrics.format_percent(revenue["growth_pct"]), "📈"),
    ]
    for col, (label, value, icon) in zip(cols, cards):
        with col:
            theme.metric_card(label, value, icon=icon)


def _render_growth_kpis(analytics: dict[str, Any]) -> None:
    theme.section_header("Growth & volume")
    cols = st.columns(4)
    revenue = analytics.get(column_mapper.REVENUE, {})
    orders = analytics.get(column_mapper.ORDERS)
    customers = analytics.get(column_mapper.CUSTOMERS)
    profit = analytics.get("profit")

    with cols[0]:
        theme.metric_card(
            "Monthly Growth",
            metrics.format_percent(revenue.get("monthly_growth_pct")) if revenue else "—",
            icon="🔁", caption="Avg. month-over-month",
        )
    with cols[1]:
        if orders:
            theme.metric_card("Total Orders", metrics.format_number(orders["total"]),
                              icon="🧾", caption=metrics.format_percent(orders["growth_pct"]) + " growth")
        else:
            theme.metric_card("Total Orders", "—", icon="🧾", caption="No order data")
    with cols[2]:
        if customers:
            theme.metric_card("Customer Growth", metrics.format_percent(customers["growth_pct"]),
                              icon="👥", caption=f"Latest: {metrics.format_number(customers['latest'])}")
        else:
            theme.metric_card("Customer Growth", "—", icon="👥", caption="No customer data")
    with cols[3]:
        if profit:
            theme.metric_card("Profit Estimate", metrics.format_currency(profit["estimate"]),
                              icon="🏦", caption=metrics.format_percent(profit["margin_pct"]) + " margin")
        else:
            theme.metric_card("Profit Estimate", "—", icon="🏦", caption="Needs revenue + expenses")


def _render_health(health: dict[str, Any]) -> None:
    left, right = st.columns([1, 1.6])
    with left:
        theme.section_header("Business health")
        score = health.get("score", 0)
        category = health.get("category", "—")
        tone = {"Excellent": "up", "Good": "up", "Moderate": "neutral"}.get(category, "down")
        st.markdown(
            f"""
            <div class="glass-panel fade-in" style="text-align:center;">
                <div class="metric-label">Business Health Score</div>
                <div style="font-size:3rem; font-weight:800; margin:0.3rem 0;">{score}
                    <span style="font-size:1.2rem; color:var(--fiq-muted);">/100</span></div>
                <div class="metric-delta {tone}" style="margin:0 auto;">{category}</div>
                <div class="text-muted" style="font-size:0.8rem; margin-top:0.6rem;">
                    Weighted across growth, stability, trend, customers &amp; expenses.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        theme.section_header("Score breakdown", "Transparent components & weights")
        breakdown = health.get("breakdown", {})
        if not breakdown:
            st.caption("Not enough data to compute component scores.")
            return
        for name, comp in breakdown.items():
            label = name.replace("_", " ").title()
            pct = comp["score"]
            weight = comp.get("weight", 0.0) * 100
            st.markdown(
                f"""
                <div class="insight-card fade-in">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="insight-title">{label}</span>
                        <span style="font-weight:700;">{pct:.0f}/100
                            <span class="text-muted" style="font-weight:500;">· {weight:.0f}% weight</span>
                        </span>
                    </div>
                    <div class="insight-body">{comp['description']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_trend_and_periods(analytics: dict[str, Any]) -> None:
    revenue = analytics.get(column_mapper.REVENUE)
    if not revenue:
        return
    theme.section_header("Trend & key periods")
    cols = st.columns(4)
    trend = revenue.get("trend", "stable").title()
    trend_icon = {"Upward": "📈", "Downward": "📉", "Stable": "➡️"}.get(trend, "➡️")
    highest = revenue.get("highest_month") or {}
    lowest = revenue.get("lowest_month") or {}
    best_q = revenue.get("best_quarter") or {}

    with cols[0]:
        theme.metric_card("Revenue Trend", trend, icon=trend_icon,
                          caption=f"Strength {revenue.get('trend_strength', 0):.2f}")
    with cols[1]:
        theme.metric_card("Peak Month", highest.get("period", "—"), icon="🚀",
                          caption=metrics.format_currency(highest.get("value")))
    with cols[2]:
        theme.metric_card("Weakest Month", lowest.get("period", "—"), icon="📉",
                          caption=metrics.format_currency(lowest.get("value")))
    with cols[3]:
        theme.metric_card("Best Quarter", best_q.get("period", "—"), icon="🏆",
                          caption=metrics.format_currency(best_q.get("value")))


def _render_charts(analytics: dict[str, Any]) -> None:
    """Render interactive Plotly charts for revenue and seasonality."""
    revenue = analytics.get(column_mapper.REVENUE)
    if not revenue:
        return
    theme.section_header("Visual analytics", "Interactive trends & seasonality")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            revenue_charts.revenue_trend(analytics, height=280),
            use_container_width=True,
            config={"displaylogo": False},
        )
    with right:
        st.plotly_chart(
            revenue_charts.growth_trend(revenue.get("series", []), height=280),
            use_container_width=True,
            config={"displaylogo": False},
        )
    clean_df = session_manager.get_state(session_manager.CLEANED_DATA)
    if clean_df is not None and column_mapper.REVENUE in getattr(clean_df, "columns", []):
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(
                heatmaps.monthly_heatmap(clean_df, column_mapper.REVENUE, height=260),
                use_container_width=True,
                config={"displaylogo": False},
            )
        with c2:
            st.plotly_chart(
                heatmaps.quarterly_heatmap(clean_df, column_mapper.REVENUE, height=260),
                use_container_width=True,
                config={"displaylogo": False},
            )


def main() -> None:
    _bootstrap()
    theme.page_header(
        "Business Analytics",
        "A premium overview of your performance, growth, and health.",
        eyebrow="Analytics",
    )

    result = _ensure_analytics()
    if result is None:
        empty_states.show_no_data()
        return

    analytics, health = result
    _render_revenue_kpis(analytics)
    _render_growth_kpis(analytics)
    _render_health(health)
    _render_trend_and_periods(analytics)
    _render_charts(analytics)


if __name__ == "__main__":
    main()
