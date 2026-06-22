"""
Page: Upload Data
=================
Premium upload experience wired to the Step 3 ingestion pipeline.

Flow (orchestration only — all logic lives in utils/analytics modules):
    read_uploaded_file → detect_columns → validate_dataframe →
    clean_and_prepare → profile_dataset → compute_metrics → compute_health,
    then persist everything through ``session_manager``.

Displays: dataset summary, validation results, data-quality score, detected
metrics, the column-mapping table, and a data preview.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from analytics import dataset_profiler, health_score, metrics, processor
from components import error_states, theme
from components.sidebar import render_sidebar
from utils import column_mapper, session_manager, validators
from utils.logger import get_logger

logger = get_logger(__name__)


def _bootstrap() -> None:
    theme.configure_page("Upload Data")
    session_manager.init_session_state()
    theme.inject_premium_css()
    render_sidebar(active_page="upload")


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def _run_pipeline(data: bytes, file_name: str, size_bytes: int) -> dict[str, Any] | None:
    """Run the full ingestion pipeline and persist results.

    Returns a dict of display artifacts on success, or ``None`` after rendering
    a user-friendly error/validation message.
    """
    # 1) File-level validation.
    file_check = validators.validate_file(file_name, size_bytes)
    if not file_check.ok:
        for message in file_check.errors:
            error_states.show_error(message, title="Upload rejected")
        return None

    # 2) Read into a dataframe.
    try:
        raw_df = processor.read_uploaded_file(data, file_name)
    except processor.IngestionError as exc:
        error_states.show_error(str(exc), title="Couldn't read file")
        return None

    # 3) Column mapping.
    mapping = column_mapper.detect_columns(raw_df.columns)

    # 4) Content validation.
    validation = validators.validate_dataframe(raw_df, mapping)
    if not validation.ok:
        for message in validation.errors:
            error_states.show_error(message, title="Dataset not usable")
        # Still surface the mapping so the user understands what was detected.
        _render_mapping_table(mapping)
        return None

    # 5) Clean + canonicalize.
    clean_df = processor.clean_and_prepare(raw_df, mapping)
    if clean_df.empty:
        error_states.show_error(
            "After cleaning, no usable rows remained. Please check your dates and values.",
            title="No usable data",
        )
        return None

    # 6) Profile + analytics + health.
    profile = dataset_profiler.profile_dataset(raw_df, clean_df, mapping, validation)
    analytics_payload = metrics.compute_metrics(clean_df)
    health_payload = health_score.compute_health(analytics_payload)

    # 7) Persist — through session_manager only.
    session_manager.update_state(
        {
            session_manager.RAW_DATA: raw_df,
            session_manager.CLEANED_DATA: clean_df,
            session_manager.DATASET_PROFILE: profile.to_dict(),
            session_manager.ANALYTICS: analytics_payload,
            session_manager.HEALTH_METRICS: health_payload,
            session_manager.UPLOADED_FILE: {
                "name": file_name,
                "size_bytes": size_bytes,
                "rows": profile.row_count,
                "columns": profile.column_count,
            },
            # Clear downstream artifacts when a new dataset is loaded.
            session_manager.FORECASTS: None,
            session_manager.FORECAST_METADATA: None,
            session_manager.EVALUATION_RESULTS: None,
            session_manager.AI_INSIGHTS: None,
            session_manager.AI_RECOMMENDATIONS: None,
            session_manager.AI_PROVIDER: None,
            session_manager.AI_METADATA: None,
            session_manager.INSIGHTS: None,
            session_manager.RECOMMENDATIONS: None,
            session_manager.REPORT_DATA: None,
            session_manager.REPORT_HISTORY: None,
            session_manager.GENERATED_REPORTS: None,
        }
    )
    logger.info("Ingestion pipeline complete for '%s'.", file_name)
    return {
        "raw_df": raw_df,
        "clean_df": clean_df,
        "mapping": mapping,
        "validation": validation,
        "profile": profile,
    }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _render_summary_cards(profile: dataset_profiler.DatasetProfile) -> None:
    theme.section_header("Dataset summary")
    cols = st.columns(4)
    cards = [
        ("Rows", f"{profile.row_count:,}", "📋", f"{profile.original_row_count:,} uploaded"),
        ("Columns", f"{profile.column_count:,}", "🧩", f"{len(profile.detected_metrics)} mapped metrics"),
        ("Date range", profile.date_range_label, "🗓️", "Detected automatically"),
        ("Detected metrics", f"{len(profile.detected_metrics)}", "🎯",
         ", ".join(m.title() for m in profile.detected_metrics) or "None"),
    ]
    for col, (label, value, icon, caption) in zip(cols, cards):
        with col:
            theme.metric_card(label, value, icon=icon, caption=caption)


def _render_quality(profile: dataset_profiler.DatasetProfile) -> None:
    theme.section_header("Data quality")
    left, right = st.columns([1, 1.6])
    with left:
        score = profile.data_quality_score
        tone = "up" if score >= 80 else ("neutral" if score >= 50 else "down")
        st.markdown(
            f"""
            <div class="glass-panel fade-in" style="text-align:center;">
                <div class="metric-label">Data Quality Score</div>
                <div style="font-size:3rem; font-weight:800; margin:0.3rem 0;">{score:.0f}<span style="font-size:1.2rem; color:var(--fiq-muted);">/100</span></div>
                <div class="metric-delta {tone}" style="margin:0 auto;">
                    {profile.completeness_pct:.0f}% complete
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        cols = st.columns(2)
        with cols[0]:
            theme.metric_card("Missing values", f"{profile.missing_value_count:,}", icon="🕳️")
            theme.metric_card("Empty columns",
                              f"{int(_metric(profile, 'empty_columns'))}", icon="📭")
        with cols[1]:
            theme.metric_card("Duplicate rows", f"{profile.duplicate_count:,}", icon="🧬")
            theme.metric_card("Invalid dates",
                              f"{int(_metric(profile, 'invalid_dates'))}", icon="📅")


def _render_validation(validation: validators.ValidationReport) -> None:
    if not validation.warnings:
        error_states.show_success(
            "No data-quality issues detected — your dataset looks clean.",
            title="All clear",
        )
        return
    theme.section_header("Validation notes", "Handled automatically during cleaning")
    for warning in validation.warnings:
        error_states.show_warning(warning, title="Note")


def _render_detected_metrics(mapping: column_mapper.ColumnMappingResult) -> None:
    theme.section_header("Detected metrics")
    if not mapping.detected_metrics:
        st.caption("No numeric metrics detected.")
        return
    chips = "".join(
        f'<div class="step-chip"><span class="step-num">✓</span>{m.title()}</div>'
        for m in [column_mapper.DATE, *mapping.detected_metrics]
    )
    st.markdown(
        f'<div style="display:flex; flex-wrap:wrap; gap:0.5rem;">{chips}</div>',
        unsafe_allow_html=True,
    )


def _render_mapping_table(mapping: column_mapper.ColumnMappingResult) -> None:
    theme.section_header("Column mapping", "Source columns → canonical fields")
    rows = column_mapper.mapping_table(mapping)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No columns to map.")


def _render_preview(raw_df: pd.DataFrame) -> None:
    theme.section_header("Data preview", "First rows of your upload")
    st.dataframe(raw_df.head(10), use_container_width=True, hide_index=True)


def _render_artifacts(artifacts: dict[str, Any]) -> None:
    """Render full upload results from pipeline artifacts."""
    _render_summary_cards(artifacts["profile"])
    _render_quality(artifacts["profile"])
    _render_detected_metrics(artifacts["mapping"])
    _render_validation(artifacts["validation"])
    _render_mapping_table(artifacts["mapping"])
    _render_preview(artifacts["raw_df"])
    st.page_link(
        "pages/2_Business_Analytics.py",
        label="View Business Analytics",
        icon=":material/arrow_forward:",
    )


def _render_session_results() -> None:
    """Re-render upload results from session without re-processing."""
    raw_df = session_manager.get_state(session_manager.RAW_DATA)
    profile_dict = session_manager.get_state(session_manager.DATASET_PROFILE) or {}
    if raw_df is None or not profile_dict:
        return
    profile = dataset_profiler.DatasetProfile(**profile_dict)
    mapping = column_mapper.detect_columns(raw_df.columns)
    validation = validators.validate_dataframe(raw_df, mapping)
    _render_artifacts(
        {
            "raw_df": raw_df,
            "profile": profile,
            "mapping": mapping,
            "validation": validation,
        }
    )


def _render_existing_state() -> None:
    """Render a compact summary if a dataset is already loaded this session."""
    profile_dict = session_manager.get_state(session_manager.DATASET_PROFILE)
    if not profile_dict:
        st.caption(
            "Your file stays in this session. Detected columns and a data-quality "
            "report appear here after you upload."
        )
        return
    uploaded = session_manager.get_state(session_manager.UPLOADED_FILE) or {}
    error_states.show_success(
        f"'{uploaded.get('name', 'dataset')}' is loaded "
        f"({profile_dict.get('row_count', 0):,} rows). Upload a new file to replace it.",
        title="Dataset ready",
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _metric(profile: dataset_profiler.DatasetProfile, key: str) -> float:
    """Read a count from the column summary / profile defensively."""
    # invalid_dates / empty_columns are not stored on the profile directly;
    # derive them from the column summary where possible.
    if key == "empty_columns":
        return float(sum(1 for c in profile.column_summary if c["non_null"] == 0))
    if key == "invalid_dates":
        # original rows minus cleaned rows approximates dropped (invalid) rows.
        return float(max(profile.original_row_count - profile.row_count, 0))
    return 0.0


def main() -> None:
    _bootstrap()
    theme.page_header(
        "Upload Data",
        "Bring your business data in — ForecastIQ handles the rest.",
        eyebrow="Ingestion",
    )

    theme.section_header("Upload your dataset", "CSV or XLSX · up to 50 MB")
    st.caption(
        "Demo files: `assets/sample_dataset.csv` (12 months) and "
        "`assets/sample_dataset_extended.csv` (24 months) — upload from your file explorer."
    )
    uploaded = st.file_uploader(
        "Drag and drop your business data",
        type=["csv", "xlsx"],
        accept_multiple_files=False,
        help="Columns are auto-detected — no manual mapping needed.",
        key="upload_widget",
    )

    if uploaded is None:
        _render_existing_state()
        if session_manager.get_state(session_manager.DATASET_PROFILE):
            _render_session_results()
        return

    data = uploaded.getvalue()
    uploaded_meta = session_manager.get_state(session_manager.UPLOADED_FILE) or {}
    already_loaded = (
        uploaded_meta.get("name") == uploaded.name
        and uploaded_meta.get("size_bytes") == len(data)
        and session_manager.get_state(session_manager.DATASET_PROFILE) is not None
    )

    if already_loaded:
        _render_session_results()
        return

    with st.spinner("Reading and analyzing your dataset…"):
        artifacts = _run_pipeline(data, uploaded.name, len(data))

    if artifacts is None:
        return

    error_states.show_success(
        f"'{uploaded.name}' processed successfully.", title="Upload complete"
    )
    _render_artifacts(artifacts)

    st.page_link("pages/2_Business_Analytics.py", label="View Business Analytics",
                 icon=":material/arrow_forward:")


if __name__ == "__main__":
    main()
