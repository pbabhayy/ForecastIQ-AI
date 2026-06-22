"""
Forecasting: Prophet Model
==========================
Prophet implementation of the forecasting strategy interface.

Exposes a single ``predict(history_df, periods)`` method that fits Prophet on
a monthly ``(ds, y)`` history and returns a *future-only* forecast frame with
columns ``ds, yhat, yhat_lower, yhat_upper`` — the uniform shape every model
in the platform produces. Higher-level concerns (growth %, peak/lowest month,
evaluation, the result contract) are assembled by the ForecastManager, so
this module stays single-responsibility.

Prophet is imported lazily; if it is unavailable or fails, the exception
propagates and the manager falls back to another model. The app never crashes.
"""

from __future__ import annotations

import logging

import pandas as pd

from config import forecast_config as cfg
from utils.logger import get_logger

logger = get_logger(__name__)

# Quieten Prophet/cmdstanpy's noisy INFO logging.
for _noisy in ("prophet", "cmdstanpy", "fbprophet"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)


class ProphetForecaster:
    """Prophet-based monthly forecaster (revenue / orders / customers)."""

    key: str = cfg.MODEL_PROPHET
    label: str = cfg.MODEL_LABELS[cfg.MODEL_PROPHET]
    has_intervals: bool = True

    def predict(self, history_df: pd.DataFrame, periods: int) -> pd.DataFrame:
        """Fit on history and forecast ``periods`` future months.

        Args:
            history_df: Monthly history with columns ``ds`` (datetime) and
                ``y`` (numeric), sorted ascending.
            periods: Number of future months to forecast.

        Returns:
            A future-only dataframe with ``ds, yhat, yhat_lower, yhat_upper``
            (non-negative), length ``periods``.

        Raises:
            ImportError: If Prophet is not installed.
            Exception: If fitting/prediction fails (handled by the manager).
        """
        from prophet import Prophet  # lazy import — optional heavy dependency

        frame = history_df[["ds", "y"]].dropna().copy()
        frame["ds"] = pd.to_datetime(frame["ds"])
        frame["y"] = frame["y"].astype(float)

        model = Prophet(**cfg.PROPHET_PARAMS)
        model.fit(frame)

        future = model.make_future_dataframe(periods=periods, freq=cfg.FREQUENCY)
        forecast = model.predict(future)

        tail = (
            forecast.tail(periods)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
            .copy()
            .reset_index(drop=True)
        )
        for col in ("yhat", "yhat_lower", "yhat_upper"):
            tail[col] = tail[col].clip(lower=0.0)

        logger.info("Prophet produced %d forecast point(s).", len(tail))
        return tail
