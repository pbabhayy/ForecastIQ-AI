"""
Config: Forecast Configuration
==============================
Tunable parameters for the forecasting layer — the single home for all
forecast-related constants (no magic numbers in the engine code).

Covers supported horizons/frequency, train/test split + minimum data
thresholds, confidence-interval width, per-model hyperparameters (Prophet,
Linear Regression; Random Forest / XGBoost reserved), confidence rating
bands, and the manager's default model-selection strategy.
"""

from __future__ import annotations

from typing import Final

# --------------------------------------------------------------------------- #
# Model identifiers (stable keys used across manager / pages / session)
# --------------------------------------------------------------------------- #
MODEL_PROPHET: Final[str] = "prophet"
MODEL_LINEAR: Final[str] = "linear_regression"
# Reserved for future strategies (registered later without refactoring):
MODEL_RANDOM_FOREST: Final[str] = "random_forest"
MODEL_XGBOOST: Final[str] = "xgboost"

MODEL_LABELS: Final[dict[str, str]] = {
    MODEL_PROPHET: "Prophet",
    MODEL_LINEAR: "Linear Regression",
    MODEL_RANDOM_FOREST: "Random Forest",
    MODEL_XGBOOST: "XGBoost",
}

#: Models exposed to users in this release.
AVAILABLE_MODELS: Final[tuple[str, ...]] = (MODEL_PROPHET, MODEL_LINEAR)
#: Models the manager will attempt as fallbacks, in order.
FALLBACK_ORDER: Final[tuple[str, ...]] = (MODEL_LINEAR,)

DEFAULT_MODEL: Final[str] = MODEL_PROPHET

# --------------------------------------------------------------------------- #
# Horizons & frequency
# --------------------------------------------------------------------------- #
SUPPORTED_HORIZONS: Final[tuple[int, ...]] = (1, 3, 6, 12)
DEFAULT_HORIZON: Final[int] = 6
#: Monthly frequency (month-start) — the platform forecasts monthly.
FREQUENCY: Final[str] = "MS"

# --------------------------------------------------------------------------- #
# Data sufficiency & evaluation
# --------------------------------------------------------------------------- #
#: Minimum monthly observations required to attempt a forecast at all.
MIN_FORECAST_POINTS: Final[int] = 4
#: Minimum monthly observations required to run a hold-out backtest.
MIN_EVAL_POINTS: Final[int] = 6
#: Fraction of history held out for backtesting (clamped to keep train ≥ 2).
TEST_RATIO: Final[float] = 0.2
#: Confidence-interval width for forecast bands (0–1).
INTERVAL_WIDTH: Final[float] = 0.90

# --------------------------------------------------------------------------- #
# Confidence rating bands (applied to a 0–100 confidence_score)
# --------------------------------------------------------------------------- #
CONFIDENCE_EXCELLENT: Final[float] = 85.0
CONFIDENCE_GOOD: Final[float] = 70.0
CONFIDENCE_MODERATE: Final[float] = 50.0

# --------------------------------------------------------------------------- #
# Per-model hyperparameters
# --------------------------------------------------------------------------- #
PROPHET_PARAMS: Final[dict[str, object]] = {
    "interval_width": INTERVAL_WIDTH,
    "yearly_seasonality": "auto",
    "weekly_seasonality": False,
    "daily_seasonality": False,
    "seasonality_mode": "additive",
}

# Linear Regression has no hyperparameters here; confidence bands are derived
# from the standard deviation of in-sample residuals (see sklearn_forecast).
LINEAR_PARAMS: Final[dict[str, object]] = {}
