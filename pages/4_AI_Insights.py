"""
Page: AI Insights
=================
Premium AI dashboard wired to the Step 5 insight + recommendation engines.

Orchestration only: reads analytics, health, forecast, and evaluation from
session, delegates to the Groq → Ollama → rule-based provider chain, and
persists results via ``session_manager``.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from ai.base_provider import merge_responses
from ai.insight_engine import generate_insights
from ai.recommendation_engine import generate_recommendations
from components import empty_states, error_states, theme
from components.sidebar import render_sidebar
from rag import index_ai_insights
from utils import session_manager
from utils.logger import get_logger

logger = get_logger(__name__)

_PROVIDER_LABELS = {
    "groq": "Groq",
    "ollama": "Ollama",
    "rule_based": "Rule-Based Engine",
}


def _bootstrap() -> None:
    theme.configure_page("AI Insights")
    session_manager.init_session_state()
    theme.inject_premium_css()
    render_sidebar(active_page="insights")


def _load_payloads() -> tuple[dict, dict, dict, dict, dict]:
    forecast = session_manager.get_state(session_manager.FORECASTS) or {}
    evaluation = (
        forecast.get("evaluation")
        or session_manager.get_state(session_manager.EVALUATION_RESULTS)
        or {}
    )
    return (
        session_manager.get_state(session_manager.ANALYTICS) or {},
        session_manager.get_state(session_manager.HEALTH_METRICS) or {},
        forecast,
        evaluation,
        session_manager.get_state(session_manager.DATASET_PROFILE) or {},
    )


def _generate_and_persist() -> dict[str, Any]:
    analytics, health, forecast, evaluation, profile = _load_payloads()
    insights_part = generate_insights(analytics, health, forecast, evaluation, dataset_profile=profile)
    recs_part = generate_recommendations(analytics, health, forecast, evaluation, dataset_profile=profile)
    combined = merge_responses(insights_part, recs_part)

    session_manager.update_state(
        {
            session_manager.AI_INSIGHTS: insights_part,
            session_manager.AI_RECOMMENDATIONS: recs_part,
            session_manager.AI_PROVIDER: combined.get("provider"),
            session_manager.AI_METADATA: combined,
            session_manager.INSIGHTS: combined.get("insights"),
            session_manager.RECOMMENDATIONS: combined.get("recommendations"),
        }
    )
    logger.info("AI intelligence persisted (provider=%s).", combined.get("provider"))
    dataset_id = session_manager.get_state(session_manager.DATASET_ID)
    try:
        index_ai_insights(dataset_id, combined)
    except Exception:
        logger.exception("RAG AI indexing skipped.")
    return combined


def _render_analyst_panel(combined: dict[str, Any] | None) -> None:
    provider = (combined or {}).get("provider", "—")
    label = _PROVIDER_LABELS.get(provider, provider.title() if provider != "—" else "—")
    generated = (combined or {}).get("generated_at", "Not generated yet")
    st.markdown(
        f"""
        <div class="glass-panel fade-in" style="display:flex; align-items:center;
             justify-content:space-between; gap:1rem; flex-wrap:wrap;">
            <div style="display:flex; align-items:center; gap:1rem;">
                <div class="feature-icon" style="margin:0;">🤖</div>
                <div>
                    <div style="font-weight:700; font-size:1.05rem;">AI Business Analyst</div>
                    <div class="text-muted" style="font-size:0.88rem;">
                        Groq → Ollama → rule-based fallback — always returns intelligence.
                    </div>
                </div>
            </div>
            <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                <div class="step-chip"><span class="step-num">⚡</span>Provider: {label}</div>
                <div class="step-chip"><span class="step-num">🕒</span>{generated}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary(combined: dict[str, Any]) -> None:
    theme.section_header("Executive summary")
    summary = combined.get("summary") or "No summary available."
    st.markdown(
        f'<div class="glass-panel fade-in"><p style="margin:0; line-height:1.6;">{summary}</p></div>',
        unsafe_allow_html=True,
    )


def _render_insights(combined: dict[str, Any]) -> None:
    theme.section_header("Key insights")
    for item in combined.get("insights") or []:
        st.markdown(
            f"""
            <div class="insight-card fade-in">
                <div class="insight-title">{item.get('category', 'Insight')} · {item.get('title', '')}</div>
                <div class="insight-body">{item.get('body', '')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_risks(combined: dict[str, Any]) -> None:
    risks = combined.get("risks") or []
    if not risks:
        return
    theme.section_header("Risks", "Signals requiring attention")
    for item in risks:
        error_states.show_warning(item.get("body", ""), title=item.get("title", "Risk"))


def _render_opportunities(combined: dict[str, Any]) -> None:
    opps = combined.get("opportunities") or []
    if not opps:
        return
    theme.section_header("Opportunities")
    for item in opps:
        error_states.show_success(item.get("body", ""), title=item.get("title", "Opportunity"))


def _render_recommendations(combined: dict[str, Any]) -> None:
    theme.section_header("Recommendations", "Prioritized actions")
    recs = combined.get("recommendations") or []
    if not recs:
        st.caption("No recommendations generated.")
        return
    rows = [recs[i : i + 2] for i in range(0, len(recs), 2)]
    for row in rows:
        cols = st.columns(2)
        for col, rec in zip(cols, row):
            priority = rec.get("priority", "Medium")
            icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "⚪")
            with col:
                theme.metric_card(
                    rec.get("title", "Recommendation"),
                    priority,
                    icon=icon,
                    caption=f"{rec.get('category', '')} — {rec.get('body', '')}",
                )


def _render_commentary(combined: dict[str, Any]) -> None:
    theme.section_header("Commentary", "Forecast & health context")
    insights = combined.get("insights") or []
    forecast_items = [i for i in insights if "Forecast" in i.get("category", "") or "Confidence" in i.get("category", "")]
    health_items = [i for i in insights if "Health" in i.get("category", "")]
    left, right = st.columns(2)
    with left:
        st.markdown("**Forecast commentary**")
        for item in forecast_items[:2]:
            st.markdown(f"- {item.get('body', '')}")
        if not forecast_items:
            st.caption("Generate a forecast to unlock commentary.")
    with right:
        st.markdown("**Business health commentary**")
        for item in health_items[:2]:
            st.markdown(f"- {item.get('body', '')}")
        if not health_items:
            st.caption("Health score appears after analytics run.")


def main() -> None:
    _bootstrap()
    theme.page_header(
        "AI Insights",
        "Narrative intelligence and recommendations for your business.",
        eyebrow="Intelligence",
    )

    analytics, _, _, _, _ = _load_payloads()
    if not analytics.get("meta", {}).get("available"):
        empty_states.show_no_data()
        return

    if st.button("Generate AI insights", type="primary"):
        with st.spinner("Synthesizing business intelligence…"):
            combined = _generate_and_persist()
        error_states.show_success("Insights and recommendations updated.", title="Complete")
    else:
        combined = session_manager.get_state(session_manager.AI_METADATA)

    _render_analyst_panel(combined)

    if not combined:
        empty_states.show_no_insights()
        st.caption("Click **Generate AI insights** to analyze your data.")
        return

    _render_summary(combined)
    _render_insights(combined)
    _render_risks(combined)
    _render_opportunities(combined)
    _render_recommendations(combined)
    _render_commentary(combined)


if __name__ == "__main__":
    main()
