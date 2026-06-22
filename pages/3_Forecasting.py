"""
Page: Forecasting
=================
Premium forecasting dashboard wired to the Step 4 forecasting + visualization
layers.

Orchestration only: reads the cleaned canonical dataset from session, delegates
to :mod:`forecasting.forecast_manager` (Prophet / Linear Regression), persists
the unified result contract via ``session_manager``, and renders KPIs,
interactive Plotly charts, a forecast table, evaluation metrics, a model
comparison panel, forecast metadata, and seasonality heatmaps.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from analytics import metrics
from components import empty_states, error_states, theme
from components.sidebar import render_sidebar
from config import forecast_config as cfg
from forecasting import evaluation as eval_mod
from forecasting import forecast_manager as fm
from rag import index_forecast
from utils import column_mapper, session_manager
from utils.logger import get_logger
from visualizations import comparison_charts, forecast_charts, heatmaps

logger = get_logger(__name__)

_HORIZON_LABELS: dict[str, int] = {
    "1 Month": 1, "3 Months": 3, "6 Months": 6, "12 Months": 12,
}


def _bootstrap() -> None:
    theme.configure_page("Forecasting")
    session_manager.init_session_state()
    theme.inject_premium_css()
    render_sidebar(active_page="forecasting")


def _present_metrics(clean_df: pd.DataFrame) -> list[str]:
    """Forecastable canonical metrics actually present in the dataset."""
    return [m for m in fm.FORECASTABLE_METRICS if m in clean_df.columns]


def _value_formatter(metric: str):
    """Pick a display formatter appropriate to the metric."""
    return metrics.format_currency if metric == column_mapper.REVENUE else metrics.format_number


# --------------------------------------------------------------------------- #
# Controls
# --------------------------------------------------------------------------- #
def _render_controls(present: list[str]) -> tuple[str, int, str, bool]:
    """Render metric/horizon/model selectors + generate button."""
    theme.section_header("Forecast settings", "Choose a metric, horizon, and model")
    c1, c2, c3, c4 = st.columns([1.3, 1.3, 1.4, 1])

    with c1:
        metric = st.selectbox(
            "Target metric", present,
            format_func=str.title,
            index=_safe_index(present, session_manager.get_state(session_manager.SELECTED_METRIC)),
            key="forecast_target",
        )
    with c2:
        horizon_label = st.selectbox(
            "Forecast horizon", list(_HORIZON_LABELS.keys()), index=2,
            key="forecast_horizon",
        )
        horizon = _HORIZON_LABELS[horizon_label]
    with c3:
        model = st.selectbox(
            "Model", list(cfg.AVAILABLE_MODELS),
            format_func=lambda k: cfg.MODEL_LABELS.get(k, k),
            key="forecast_model",
        )
    with c4:
        st.markdown("<div style='height:1.75rem;'></div>", unsafe_allow_html=True)
        generate = st.button("Generate forecast", type="primary", use_container_width=True)

    return metric, horizon, model, generate


def _safe_index(options: list[str], value: Any) -> int:
    """Return the index of ``value`` in ``options`` (0 if absent)."""
    try:
        return options.index(value) if value in options else 0
    except (ValueError, TypeError):
        return 0


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def _generate(clean_df: pd.DataFrame, metric: str, horizon: int, model: str) -> None:
    """Run both models, persist the unified contract + comparison, via session."""
    with st.spinner("Generating forecasts and evaluating accuracy…"):
        comparison = fm.compare_models(clean_df, metric, horizon)
    primary = comparison.get(model)
    if not primary or not primary.get("ok"):
        primary = fm.generate_forecast(clean_df, metric, horizon, model)

    session_manager.update_state(
        {
            session_manager.FORECASTS: primary,
            session_manager.FORECAST_METADATA: {
                "comparison": comparison,
                "metric": metric,
                "model": model,
                "horizon": horizon,
                "generated_at": primary.get("generated_at"),
            },
            session_manager.EVALUATION_RESULTS: primary.get("evaluation"),
            session_manager.SELECTED_METRIC: metric,
            session_manager.SELECTED_HORIZON: horizon,
            session_manager.SELECTED_MODEL: model,
        }
    )
    logger.info("Forecast generated & persisted: metric=%s model=%s horizon=%d.",
                metric, model, horizon)
    dataset_id = session_manager.get_state(session_manager.DATASET_ID)
    try:
        index_forecast(dataset_id, primary)
    except Exception:
        logger.exception("RAG forecast indexing skipped.")


# --------------------------------------------------------------------------- #
# Result rendering
# --------------------------------------------------------------------------- #
def _render_kpis(primary: dict[str, Any]) -> None:
    theme.section_header("Forecast summary")
    fmt = _value_formatter(primary["metric"])
    evaluation = primary.get("evaluation", {}) or {}
    cols = st.columns(4)
    with cols[0]:
        theme.metric_card("Projected Growth", metrics.format_percent(primary["growth_pct"]),
                          icon="📈", caption=f"Over {primary['horizon']} month(s)")
    with cols[1]:
        theme.metric_card("Peak Month", primary["peak_month"], icon="🚀")
    with cols[2]:
        theme.metric_card("Weakest Month", primary["lowest_month"], icon="📉")
    with cols[3]:
        acc = eval_mod.accuracy_display(evaluation)
        theme.metric_card(acc["label"], acc["value"],
                          icon="✅", caption=acc["caption"])
    st.caption(f"Annualized projection: {fmt(primary.get('annual_projection'))}")


def _render_charts(primary: dict[str, Any]) -> None:
    theme.section_header("Forecast trajectory", "Historical vs forecast with confidence band")
    st.plotly_chart(forecast_charts.forecast_chart(primary), use_container_width=True,
                    config={"displaylogo": False})

    left, right = st.columns([1, 1.3])
    with left:
        theme.section_header("Forecast confidence")
        st.plotly_chart(forecast_charts.confidence_chart(primary), use_container_width=True,
                        config={"displaylogo": False})
    with right:
        theme.section_header("Forecast table")
        st.dataframe(_forecast_table(primary), use_container_width=True, hide_index=True)


def _forecast_table(primary: dict[str, Any]) -> pd.DataFrame:
    """Build a formatted forecast table from the result contract."""
    forecast = primary.get("forecast_df")
    if forecast is None or forecast.empty:
        return pd.DataFrame(columns=["Month", "Forecast", "Lower", "Upper"])
    fmt = _value_formatter(primary["metric"])
    out = forecast.copy()
    out["ds"] = pd.to_datetime(out["ds"])
    return pd.DataFrame(
        {
            "Month": out["ds"].dt.strftime("%b %Y"),
            "Forecast": out["yhat"].map(fmt),
            "Lower": out["yhat_lower"].map(fmt),
            "Upper": out["yhat_upper"].map(fmt),
        }
    )


def _render_evaluation(primary: dict[str, Any]) -> None:
    theme.section_header("Model evaluation", "Transparent accuracy metrics")
    evaluation = primary.get("evaluation", {}) or {}

    def _fmt(value: Any, suffix: str = "") -> str:
        return "—" if value is None else f"{value:,.2f}{suffix}"

    cols = st.columns(4)
    with cols[0]:
        theme.metric_card("MAE", _fmt(evaluation.get("mae")), icon="📏")
    with cols[1]:
        theme.metric_card("RMSE", _fmt(evaluation.get("rmse")), icon="📐")
    with cols[2]:
        theme.metric_card("MAPE", _fmt(evaluation.get("mape"), "%"), icon="％")
    with cols[3]:
        acc = eval_mod.accuracy_display(evaluation)
        theme.metric_card(acc["label"], acc["value"],
                          icon="🎯", caption=acc["caption"])


def _render_comparison(metadata: dict[str, Any]) -> None:
    comparison = (metadata or {}).get("comparison")
    if not comparison:
        return
    theme.section_header("Model comparison", "Prophet vs Linear Regression")
    st.plotly_chart(comparison_charts.forecast_comparison(comparison),
                    use_container_width=True, config={"displaylogo": False})

    rows = []
    for key, result in comparison.items():
        evaluation = result.get("evaluation", {}) or {}
        rows.append(
            {
                "Model": result.get("model_label", key),
                "Status": "OK" if result.get("ok") else "Failed",
                "Growth %": f"{result.get('growth_pct', 0):.1f}%",
                "MAPE": "—" if evaluation.get("mape") is None else f"{evaluation['mape']:.1f}%",
                "Confidence": f"{evaluation.get('confidence_score', 0):.0f}/100",
                "Rating": evaluation.get("confidence_rating", "—"),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_metadata(metadata: dict[str, Any], primary: dict[str, Any]) -> None:
    theme.section_header("Forecast metadata")
    evaluation = primary.get("evaluation", {}) or {}
    st.markdown(
        f"""
        <div class="glass-panel fade-in">
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">Model</span><span>{primary.get('model_label', '—')}</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">Horizon</span><span>{primary.get('horizon', '—')} month(s)</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">Evaluation method</span><span>{evaluation.get('method', '—')}</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">Train / Test</span>
                <span>{evaluation.get('train_size', 0)} / {evaluation.get('test_size', 0)} months</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span class="text-muted">Generated</span><span>{theme.format_display_timestamp(primary.get('generated_at'))}</span>
            </div>
            <div style="margin-top:0.5rem; color:var(--fiq-muted); font-size:0.82rem;">
                {evaluation.get('notes', '')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_heatmaps(clean_df: pd.DataFrame, metric: str) -> None:
    theme.section_header("Seasonality", "Monthly & quarterly patterns")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(heatmaps.monthly_heatmap(clean_df, metric),
                        use_container_width=True, config={"displaylogo": False})
    with right:
        st.plotly_chart(heatmaps.quarterly_heatmap(clean_df, metric),
                        use_container_width=True, config={"displaylogo": False})


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def main() -> None:
    _bootstrap()
    theme.page_header(
        "Forecasting",
        "Project revenue, orders, and customers with confidence.",
        eyebrow="Predictive",
    )

    clean_df = session_manager.get_state(session_manager.CLEANED_DATA)
    if clean_df is None or getattr(clean_df, "empty", True):
        empty_states.show_no_data()
        return

    present = _present_metrics(clean_df)
    if not present:
        error_states.show_warning(
            "This dataset has no forecastable metric (revenue, orders, or customers).",
            title="Nothing to forecast",
        )
        return

    metric, horizon, model, generate = _render_controls(present)
    if generate:
        with st.spinner("Generating forecasts and evaluating accuracy…"):
            _generate(clean_df, metric, horizon, model)

    primary = session_manager.get_state(session_manager.FORECASTS)
    metadata = session_manager.get_state(session_manager.FORECAST_METADATA) or {}

    if not primary:
        empty_states.show_no_forecast()
        return

    if not primary.get("ok"):
        error_states.show_warning(primary.get("message", "Forecast unavailable."),
                                  title="Couldn't forecast")
        return

    if primary.get("message"):
        error_states.show_warning(primary["message"], title="Note")

    _render_kpis(primary)
    _render_charts(primary)
    _render_evaluation(primary)
    _render_comparison(metadata)
    _render_metadata(metadata, primary)
    _render_heatmaps(clean_df, metadata.get("metric", primary["metric"]))


if __name__ == "__main__":
    main()
