"""
Forecasting: Forecast Manager
=============================
The single entry point for forecasting (Manager / Strategy pattern).

Responsibilities
----------------
* Build a clean monthly ``(ds, y)`` history for a canonical metric.
* Select a forecasting strategy (Prophet, Linear Regression; Random Forest /
  XGBoost reserved) from a registry — adding a model means registering a new
  strategy here, with no changes to callers (Open/Closed).
* Run a hold-out backtest via :mod:`forecasting.evaluation`.
* Assemble the **unified forecast result contract** consumed unchanged by the
  AI, report, and persistence layers:

    {
        "metric": str, "model": str, "horizon": int,
        "forecast_df": pd.DataFrame,     # future: ds,yhat,yhat_lower,yhat_upper
        "growth_pct": float,
        "peak_month": str, "lowest_month": str,
        "evaluation": dict,
        # extras (additive, never breaking): model_label, history_df,
        # annual_projection, is_count, generated_at, ok, message
    }

Every path is fault-tolerant: invalid inputs and model failures yield an
``ok=False`` contract with a friendly message — the app never crashes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

import pandas as pd

from analytics import processor
from config import forecast_config as cfg
from forecasting import evaluation
from forecasting.prophet_forecast import ProphetForecaster
from forecasting.sklearn_forecast import LinearRegressionForecaster
from utils import column_mapper
from utils.logger import get_logger

logger = get_logger(__name__)

#: Metrics the forecasting engine supports (expenses excluded by default).
FORECASTABLE_METRICS: tuple[str, ...] = (
    column_mapper.REVENUE,
    column_mapper.ORDERS,
    column_mapper.CUSTOMERS,
)
_POINT_IN_TIME = {column_mapper.CUSTOMERS}


class Forecaster(Protocol):
    """Structural interface every forecasting strategy satisfies."""

    key: str
    label: str
    has_intervals: bool

    def predict(self, history_df: pd.DataFrame, periods: int) -> pd.DataFrame:
        """Return a future-only forecast frame (ds, yhat, yhat_lower, yhat_upper)."""
        ...


def _registry() -> dict[str, Forecaster]:
    """Build the model registry (fresh instances per call are cheap)."""
    return {
        cfg.MODEL_PROPHET: ProphetForecaster(),
        cfg.MODEL_LINEAR: LinearRegressionForecaster(),
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def generate_forecast(
    clean_df: pd.DataFrame,
    metric: str,
    horizon: int,
    model: str = cfg.DEFAULT_MODEL,
) -> dict[str, Any]:
    """Generate a single forecast with automatic fallback on model failure.

    Args:
        clean_df: Cleaned canonical dataframe.
        metric: Canonical metric to forecast (revenue/orders/customers).
        horizon: Forecast horizon in months (1/3/6/12).
        model: Preferred model key.

    Returns:
        The unified forecast result contract (``ok`` indicates success).
    """
    validation_error = _validate_request(clean_df, metric, horizon)
    history = _build_monthly_history(clean_df, metric) if validation_error is None else pd.DataFrame()
    if validation_error is None and len(history) < cfg.MIN_FORECAST_POINTS:
        validation_error = (
            f"Need at least {cfg.MIN_FORECAST_POINTS} monthly data points to "
            f"forecast (found {len(history)})."
        )
    if validation_error is not None:
        logger.warning("Forecast request rejected: %s", validation_error)
        return _failure_result(metric, model, horizon, validation_error)

    registry = _registry()
    attempts = [model] + [m for m in cfg.FALLBACK_ORDER if m != model]
    last_error = "Forecasting failed."
    for index, model_key in enumerate(attempts):
        forecaster = registry.get(model_key)
        if forecaster is None:
            continue
        try:
            result = _run_single(forecaster, history, metric, horizon)
            if index > 0:
                result["message"] = (
                    f"{registry[model].label} was unavailable; used "
                    f"{forecaster.label} instead."
                )
                logger.info("Fell back to %s for metric '%s'.", forecaster.label, metric)
            return result
        except Exception as exc:  # noqa: BLE001 — fault tolerance is the goal
            last_error = str(exc)
            logger.exception("Model '%s' failed for metric '%s'.", model_key, metric)

    return _failure_result(
        metric, model, horizon,
        "We couldn't generate this forecast. Try the Linear Regression model "
        "or a larger dataset.",
        detail=last_error,
    )


def compare_models(
    clean_df: pd.DataFrame, metric: str, horizon: int
) -> dict[str, dict[str, Any]]:
    """Run every available model for side-by-side comparison.

    Returns a mapping ``{model_key: result_contract}`` for all
    :data:`config.forecast_config.AVAILABLE_MODELS`. Failing models yield an
    ``ok=False`` contract rather than raising.
    """
    validation_error = _validate_request(clean_df, metric, horizon)
    history = _build_monthly_history(clean_df, metric) if validation_error is None else pd.DataFrame()
    if validation_error is None and len(history) < cfg.MIN_FORECAST_POINTS:
        validation_error = (
            f"Need at least {cfg.MIN_FORECAST_POINTS} monthly data points to "
            f"forecast (found {len(history)})."
        )

    registry = _registry()
    results: dict[str, dict[str, Any]] = {}
    for model_key in cfg.AVAILABLE_MODELS:
        if validation_error is not None:
            results[model_key] = _failure_result(metric, model_key, horizon, validation_error)
            continue
        forecaster = registry[model_key]
        try:
            results[model_key] = _run_single(forecaster, history, metric, horizon)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Comparison: model '%s' failed.", model_key)
            results[model_key] = _failure_result(
                metric, model_key, horizon,
                f"{forecaster.label} failed: {exc}", detail=str(exc),
            )
    return results


# --------------------------------------------------------------------------- #
# Core execution
# --------------------------------------------------------------------------- #
def _run_single(
    forecaster: Forecaster, history: pd.DataFrame, metric: str, horizon: int
) -> dict[str, Any]:
    """Execute one model end-to-end and assemble the result contract."""
    is_count = metric in _POINT_IN_TIME
    forecast_df = forecaster.predict(history, horizon)
    eval_payload = _backtest(forecaster, history)

    last_actual = float(history["y"].iloc[-1]) if not history.empty else 0.0
    future_end = float(forecast_df["yhat"].iloc[-1]) if not forecast_df.empty else 0.0
    growth_pct = _growth(last_actual, future_end)

    peak_month = _label_extreme(forecast_df, highest=True)
    lowest_month = _label_extreme(forecast_df, highest=False)
    annual_projection = _annual_projection(forecast_df, is_count=is_count)

    logger.info(
        "Forecast OK: metric=%s model=%s horizon=%d growth=%.1f%% conf=%.1f.",
        metric, forecaster.key, horizon, growth_pct,
        eval_payload.get("confidence_score", 0.0),
    )
    return {
        "metric": metric,
        "model": forecaster.key,
        "model_label": forecaster.label,
        "horizon": int(horizon),
        "forecast_df": forecast_df,
        "history_df": history.reset_index(drop=True),
        "growth_pct": growth_pct,
        "peak_month": peak_month,
        "lowest_month": lowest_month,
        "annual_projection": round(annual_projection, 2),
        "evaluation": eval_payload,
        "is_count": is_count,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok": True,
        "message": "",
    }


def _backtest(forecaster: Forecaster, history: pd.DataFrame) -> dict[str, Any]:
    """Hold-out backtest the last window of history with the given model."""
    n = len(history)
    if n < cfg.MIN_EVAL_POINTS:
        return evaluation.insufficient(n, model=forecaster.key)

    test_size = max(1, round(n * cfg.TEST_RATIO))
    if n - test_size < 2:
        test_size = n - 2
    if test_size < 1:
        return evaluation.insufficient(n, model=forecaster.key)

    train = history.iloc[: n - test_size]
    test = history.iloc[n - test_size :]
    try:
        pred = forecaster.predict(train, test_size)
        y_pred = pred["yhat"].to_numpy(dtype=float)[:test_size]
        y_true = test["y"].to_numpy(dtype=float)
        return evaluation.evaluate(
            y_true, y_pred, model=forecaster.key,
            train_size=len(train), test_size=test_size,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Backtest failed for model '%s'.", forecaster.key)
        return evaluation.insufficient(n, model=forecaster.key)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _validate_request(clean_df: pd.DataFrame, metric: str, horizon: int) -> str | None:
    """Return a user-friendly error string, or ``None`` if the request is valid."""
    if clean_df is None or getattr(clean_df, "empty", True):
        return "No dataset is loaded. Upload data before forecasting."
    if metric not in clean_df.columns:
        return f"The '{metric}' metric is not present in this dataset."
    if metric not in FORECASTABLE_METRICS:
        return f"Forecasting is not supported for '{metric}'."
    if horizon not in cfg.SUPPORTED_HORIZONS:
        return f"Unsupported horizon '{horizon}'. Choose one of {cfg.SUPPORTED_HORIZONS}."
    return None


def _build_monthly_history(clean_df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Build a monthly ``(ds, y)`` history for a metric.

    Flow metrics are summed per month; ``customers`` uses the last value.
    """
    frame = processor.to_metric_frame(clean_df, metric)
    if frame.empty:
        return frame
    series = frame.dropna(subset=["y"]).set_index("ds")["y"].astype(float)
    if series.empty:
        return pd.DataFrame(columns=["ds", "y"])
    resampled = series.resample(cfg.FREQUENCY)
    monthly = resampled.last() if metric in _POINT_IN_TIME else resampled.sum()
    monthly = monthly.dropna()
    out = monthly.reset_index()
    out.columns = ["ds", "y"]
    return out


def _growth(start: float, end: float) -> float:
    """Percentage change from last actual to forecast end."""
    if start == 0:
        return 0.0 if end == 0 else 100.0
    return round((end - start) / abs(start) * 100.0, 2)


def _label_extreme(forecast_df: pd.DataFrame, *, highest: bool) -> str:
    """Return the ``"%b %Y"`` label of the peak/lowest forecast month."""
    if forecast_df is None or forecast_df.empty:
        return "—"
    idx = forecast_df["yhat"].idxmax() if highest else forecast_df["yhat"].idxmin()
    return pd.to_datetime(forecast_df.loc[idx, "ds"]).strftime("%b %Y")


def _annual_projection(forecast_df: pd.DataFrame, *, is_count: bool) -> float:
    """Estimate an annualized projection from the forecast.

    Flows: average monthly forecast × 12. Counts: the final forecast value.
    """
    if forecast_df is None or forecast_df.empty:
        return 0.0
    if is_count:
        return float(forecast_df["yhat"].iloc[-1])
    return float(forecast_df["yhat"].mean() * 12.0)


def _failure_result(
    metric: str, model: str, horizon: int, message: str, *, detail: str = ""
) -> dict[str, Any]:
    """Build an ``ok=False`` contract with empty forecast data."""
    if detail:
        logger.warning("Forecast failure detail: %s", detail)
    return {
        "metric": metric,
        "model": model,
        "model_label": cfg.MODEL_LABELS.get(model, model),
        "horizon": int(horizon),
        "forecast_df": pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper"]),
        "history_df": pd.DataFrame(columns=["ds", "y"]),
        "growth_pct": 0.0,
        "peak_month": "—",
        "lowest_month": "—",
        "annual_projection": 0.0,
        "evaluation": evaluation.insufficient(0, model=model),
        "is_count": metric in _POINT_IN_TIME,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok": False,
        "message": message,
    }
