"""
Page: Reports
=============
Premium reporting dashboard wired to the Step 6 report builder, PDF export,
and SQLite persistence layers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from components import empty_states, error_states, theme
from components.sidebar import render_sidebar
from database import history_repository, sqlite_manager
from reports import pdf_generator, report_builder
from utils import session_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def _bootstrap() -> None:
    theme.configure_page("Reports")
    session_manager.init_session_state()
    theme.inject_premium_css()
    render_sidebar(active_page="reports")
    status = sqlite_manager.check_health()
    session_manager.set_state(session_manager.DATABASE_STATUS, status)


def _session_snapshot() -> dict[str, Any]:
    """Collect session payloads for report building and persistence."""
    return {
        "uploaded_file": session_manager.get_state(session_manager.UPLOADED_FILE),
        "dataset_profile": session_manager.get_state(session_manager.DATASET_PROFILE),
        "analytics": session_manager.get_state(session_manager.ANALYTICS),
        "health_metrics": session_manager.get_state(session_manager.HEALTH_METRICS),
        "forecasts": session_manager.get_state(session_manager.FORECASTS),
        "evaluation_results": session_manager.get_state(session_manager.EVALUATION_RESULTS),
        "ai_metadata": session_manager.get_state(session_manager.AI_METADATA),
        "ai_provider": session_manager.get_state(session_manager.AI_PROVIDER),
        "recommendations": session_manager.get_state(session_manager.RECOMMENDATIONS),
    }


def _generate_report() -> dict[str, Any] | None:
    """Build report object, export PDF, persist history."""
    snapshot = _session_snapshot()
    report = report_builder.build_report(snapshot)

    try:
        pdf_path = pdf_generator.generate_pdf(report)
    except pdf_generator.PDFGenerationError as exc:
        error_states.show_error(str(exc), title="PDF export failed")
        report["metadata"]["status"] = "failed"
        session_manager.set_state(session_manager.REPORT_DATA, report)
        return None

    report["metadata"]["status"] = "generated"
    report["metadata"]["file_path"] = pdf_path

    db_meta: dict[str, Any] = {"ok": False}
    try:
        db_meta = history_repository.persist_session_snapshot(snapshot)
        if db_meta.get("ok"):
            report_id = history_repository.save_report(
                db_meta.get("dataset_id"),
                report["metadata"]["title"],
                report_builder.sanitize_for_storage(report),
                file_path=pdf_path,
                status="generated",
            )
            report["metadata"]["report_id"] = report_id
        else:
            error_states.show_warning(
                db_meta.get("error", "Could not save to local database."),
                title="Database warning",
            )
    except sqlite_manager.DatabaseError as exc:
        logger.exception("Database write failed during report generation.")
        error_states.show_warning(str(exc), title="Database unavailable")
        session_manager.set_state(session_manager.DATABASE_STATUS, {"ok": False, "error": str(exc)})

    history = history_repository.list_reports(limit=20)
    session_manager.update_state(
        {
            session_manager.REPORT_DATA: report,
            session_manager.REPORT_HISTORY: history,
            session_manager.GENERATED_REPORTS: history,
            session_manager.DATABASE_STATUS: sqlite_manager.check_health(),
        }
    )
    logger.info("Report generated: %s", pdf_path)
    return report


def _render_db_status() -> None:
    status = session_manager.get_state(session_manager.DATABASE_STATUS) or {}
    if status.get("ok"):
        error_states.show_success(
            f"SQLite connected · {status.get('path', 'local')}",
            title="Database",
        )
    else:
        error_states.show_warning(
            status.get("error", "Local database unavailable — PDF export still works."),
            title="Database",
        )


def _render_generation_panel() -> None:
    theme.section_header("Generate report", "Executive PDF summary")
    st.markdown(
        """
        <div class="glass-panel fade-in">
            <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.5rem;">
                <span class="material-symbols-rounded" style="color:var(--fiq-accent);">picture_as_pdf</span>
                <strong>Executive report</strong>
            </div>
            <div class="text-muted" style="font-size:0.9rem;">
                Includes executive summary, dataset overview, analytics, health score,
                forecast results, AI insights, and prioritized recommendations.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_controls() -> bool:
    theme.section_header("Export")
    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        st.selectbox("Format", ("PDF",), key="report_format")
    with c2:
        st.selectbox("Sections", ("Full report",), key="report_sections")
    with c3:
        st.markdown("<div style='height:1.75rem;'></div>", unsafe_allow_html=True)
        return st.button("Generate PDF", type="primary", use_container_width=True)


def _render_preview(report: dict[str, Any]) -> None:
    theme.section_header("Report preview")
    meta = report.get("metadata") or {}
    cols = st.columns(4)
    cards = [
        ("Status", meta.get("status", "—").title(), "📄"),
        ("Dataset", meta.get("dataset_name", "—"), "📂"),
        ("Health", f"{(report.get('health_score') or {}).get('score', '—')}/100", "💚"),
        ("AI Provider", meta.get("ai_provider") or "—", "🤖"),
    ]
    for col, (label, value, icon) in zip(cols, cards):
        with col:
            theme.metric_card(label, str(value), icon=icon)

    st.markdown(
        f"""
        <div class="glass-panel fade-in">
            <strong>Executive summary</strong>
            <p class="text-muted" style="margin:0.5rem 0 0; line-height:1.6;">
                {report.get('executive_summary', '')}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fc = report.get("forecast_table") or []
    if fc:
        theme.section_header("Forecast table preview")
        st.dataframe(pd.DataFrame(fc), use_container_width=True, hide_index=True)


def _render_download(report: dict[str, Any]) -> None:
    path = (report.get("metadata") or {}).get("file_path")
    if not path or not Path(path).is_file():
        return
    theme.section_header("Download")
    with open(path, "rb") as handle:
        st.download_button(
            label="Download PDF",
            data=handle.read(),
            file_name=Path(path).name,
            mime="application/pdf",
            type="primary",
            use_container_width=False,
        )


def _render_history() -> None:
    theme.section_header("Report history", "Saved to local SQLite")
    history = session_manager.get_state(session_manager.REPORT_HISTORY)
    if history is None:
        history = history_repository.list_reports(limit=20)
    if not history:
        empty_states.show_no_reports()
        return
    st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)


def main() -> None:
    _bootstrap()
    theme.page_header(
        "Reports",
        "Board-ready exports of your analysis in one click.",
        eyebrow="Reporting",
    )

    if not session_manager.is_data_loaded():
        empty_states.show_no_data()
        return

    analytics = session_manager.get_state(session_manager.ANALYTICS) or {}
    if not analytics.get("meta", {}).get("available"):
        error_states.show_warning("Analytics not available — upload and process data first.",
                                  title="Missing analytics")
        return

    _render_db_status()
    _render_generation_panel()

    if _render_controls():
        with st.spinner("Building report and exporting PDF…"):
            report = _generate_report()
        if report:
            error_states.show_success("Report generated successfully.", title="Complete")

    report = session_manager.get_state(session_manager.REPORT_DATA)
    if report:
        _render_preview(report)
        _render_download(report)

    _render_history()


if __name__ == "__main__":
    main()
