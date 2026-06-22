"""
Utils: Session Manager
======================
Typed, centralized access to Streamlit session state.

This is the single source of truth for the persisted working set shared
across all pages. Pages and components MUST go through these helpers and
never touch ``st.session_state`` directly. Initialization is idempotent:
re-running it (on every page load) never overwrites existing values.

No business logic lives here — only state lifecycle and typed accessors.
"""

from __future__ import annotations

from typing import Any, Final

import streamlit as st


# --------------------------------------------------------------------------- #
# Session keys (the canonical state schema)
# --------------------------------------------------------------------------- #
# Centralized so every reader/writer references the same identifiers.
RAW_DATA: Final[str] = "raw_data"
CLEANED_DATA: Final[str] = "cleaned_data"
DATASET_PROFILE: Final[str] = "dataset_profile"
HEALTH_METRICS: Final[str] = "health_metrics"
ANALYTICS: Final[str] = "analytics"
FORECASTS: Final[str] = "forecasts"
FORECAST_METADATA: Final[str] = "forecast_metadata"
EVALUATION_RESULTS: Final[str] = "evaluation_results"
SELECTED_MODEL: Final[str] = "selected_model"
SELECTED_HORIZON: Final[str] = "selected_horizon"
SELECTED_METRIC: Final[str] = "selected_metric"
INSIGHTS: Final[str] = "insights"
RECOMMENDATIONS: Final[str] = "recommendations"
AI_INSIGHTS: Final[str] = "ai_insights"
AI_RECOMMENDATIONS: Final[str] = "ai_recommendations"
AI_PROVIDER: Final[str] = "ai_provider"
AI_METADATA: Final[str] = "ai_metadata"
UPLOADED_FILE: Final[str] = "uploaded_file"
THEME_MODE: Final[str] = "theme_mode"
CURRENT_PAGE: Final[str] = "current_page"
REPORT_DATA: Final[str] = "report_data"
REPORT_HISTORY: Final[str] = "report_history"
GENERATED_REPORTS: Final[str] = "generated_reports"
DATABASE_STATUS: Final[str] = "database_status"
DATASET_ID: Final[str] = "dataset_id"
CHAT_HISTORY: Final[str] = "chat_history"
CHAT_DATASET_KEY: Final[str] = "chat_dataset_key"
ERROR_STATE: Final[str] = "error_state"
LOADING_STATE: Final[str] = "loading_state"


# --------------------------------------------------------------------------- #
# Default values for every key in the schema
# --------------------------------------------------------------------------- #
# NOTE: defaults are immutable primitives / ``None`` so a shallow copy is safe
# and there is no shared-mutable-default footgun.
_DEFAULTS: Final[dict[str, Any]] = {
    RAW_DATA: None,
    CLEANED_DATA: None,
    DATASET_PROFILE: None,
    HEALTH_METRICS: None,
    ANALYTICS: None,
    FORECASTS: None,
    FORECAST_METADATA: None,
    EVALUATION_RESULTS: None,
    SELECTED_MODEL: None,
    SELECTED_HORIZON: None,
    SELECTED_METRIC: None,
    INSIGHTS: None,
    RECOMMENDATIONS: None,
    AI_INSIGHTS: None,
    AI_RECOMMENDATIONS: None,
    AI_PROVIDER: None,
    AI_METADATA: None,
    UPLOADED_FILE: None,
    THEME_MODE: "dark",
    CURRENT_PAGE: "home",
    REPORT_DATA: None,
    REPORT_HISTORY: None,
    GENERATED_REPORTS: None,
    DATABASE_STATUS: None,
    DATASET_ID: None,
    CHAT_HISTORY: None,
    CHAT_DATASET_KEY: None,
    ERROR_STATE: None,
    LOADING_STATE: False,
}


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #
def init_session_state() -> None:
    """Idempotently seed every schema key with its default.

    Safe to call at the top of *every* page render. Existing values are
    preserved; only missing keys are created.
    """
    from database import preferences_repository

    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
    # Restore persisted theme on first load.
    if st.session_state.get(THEME_MODE) == _DEFAULTS[THEME_MODE]:
        saved = preferences_repository.get_preference("theme_mode")
        if saved in ("dark", "light"):
            st.session_state[THEME_MODE] = saved


def reset_session_state(*, keep_theme: bool = True) -> None:
    """Reset the working set back to defaults.

    Args:
        keep_theme: When ``True`` (default) the user's ``theme_mode`` is
            preserved across the reset.
    """
    preserved_theme = st.session_state.get(THEME_MODE, _DEFAULTS[THEME_MODE])
    for key, default in _DEFAULTS.items():
        st.session_state[key] = default
    if keep_theme:
        st.session_state[THEME_MODE] = preserved_theme


# --------------------------------------------------------------------------- #
# Generic typed accessors
# --------------------------------------------------------------------------- #
def get_state(key: str, default: Any = None) -> Any:
    """Return a session value, falling back to ``default`` if unset."""
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """Assign a single session value."""
    st.session_state[key] = value


def update_state(values: dict[str, Any]) -> None:
    """Assign multiple session values in one call."""
    for key, value in values.items():
        st.session_state[key] = value


# --------------------------------------------------------------------------- #
# Navigation helpers
# --------------------------------------------------------------------------- #
def set_current_page(page_key: str) -> None:
    """Record the active page for navigation/highlighting purposes."""
    st.session_state[CURRENT_PAGE] = page_key


def get_current_page() -> str:
    """Return the active page key (defaults to ``"home"``)."""
    return st.session_state.get(CURRENT_PAGE, _DEFAULTS[CURRENT_PAGE])


# --------------------------------------------------------------------------- #
# Convenience predicates (used by sidebar status pills & empty-state guards)
# --------------------------------------------------------------------------- #
def is_data_loaded() -> bool:
    """``True`` once a dataset has been ingested into the session."""
    return st.session_state.get(CLEANED_DATA) is not None or (
        st.session_state.get(RAW_DATA) is not None
    )


def has_forecasts() -> bool:
    """``True`` once forecast results exist in the session."""
    return st.session_state.get(FORECASTS) is not None


def has_insights() -> bool:
    """``True`` once AI/rule-based insights exist in the session."""
    return st.session_state.get(INSIGHTS) is not None


def has_recommendations() -> bool:
    """``True`` once recommendations exist in the session."""
    return st.session_state.get(RECOMMENDATIONS) is not None


def has_reports() -> bool:
    """``True`` once a report artifact has been generated."""
    return st.session_state.get(REPORT_DATA) is not None


# --------------------------------------------------------------------------- #
# Loading / error flag helpers
# --------------------------------------------------------------------------- #
def set_loading(is_loading: bool) -> None:
    """Toggle the global loading flag."""
    st.session_state[LOADING_STATE] = is_loading


def is_loading() -> bool:
    """Return the current global loading flag."""
    return bool(st.session_state.get(LOADING_STATE, False))


def set_error(message: str | None) -> None:
    """Record (or clear, with ``None``) a global error message."""
    st.session_state[ERROR_STATE] = message


def get_error() -> str | None:
    """Return the current global error message, if any."""
    return st.session_state.get(ERROR_STATE)


def clear_error() -> None:
    """Clear any recorded global error message."""
    st.session_state[ERROR_STATE] = None
