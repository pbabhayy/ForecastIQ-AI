"""
Forecasting: Scikit-Learn Models
================================
Linear Regression baseline implementing the same forecasting strategy
interface as Prophet.

``predict(history_df, periods)`` fits an ordinary least-squares trend on a
monthly time index and projects ``periods`` months forward. Confidence bands
are derived transparently from the standard deviation of in-sample residuals
scaled by the configured interval width (via the normal quantile), so the
output frame matches Prophet's exactly: ``ds, yhat, yhat_lower, yhat_upper``.

Serves as a fast, dependency-light baseline and the manager's fallback model.
Random Forest / XGBoost can be added here later behind the same interface.
"""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from config import forecast_config as cfg
from utils.logger import get_logger

logger = get_logger(__name__)


class LinearRegressionForecaster:
    """OLS-trend monthly forecaster (revenue / orders / customers)."""

    key: str = cfg.MODEL_LINEAR
    label: str = cfg.MODEL_LABELS[cfg.MODEL_LINEAR]
    has_intervals: bool = True

    def predict(self, history_df: pd.DataFrame, periods: int) -> pd.DataFrame:
        """Fit a linear trend on history and project ``periods`` months ahead.

        Args:
            history_df: Monthly history with ``ds`` (datetime) and ``y`` (numeric).
            periods: Number of future months to forecast.

        Returns:
            A future-only dataframe with ``ds, yhat, yhat_lower, yhat_upper``
            (non-negative), length ``periods``.
        """
        frame = history_df[["ds", "y"]].dropna().copy()
        frame["ds"] = pd.to_datetime(frame["ds"])
        frame["y"] = frame["y"].astype(float)

        n = len(frame)
        x = np.arange(n, dtype=float).reshape(-1, 1)
        y = frame["y"].to_numpy(dtype=float)

        model = LinearRegression()
        model.fit(x, y)

        # In-sample residual std → symmetric confidence band.
        residuals = y - model.predict(x)
        resid_std = float(np.std(residuals, ddof=1)) if n > 2 else float(np.std(residuals))
        z = NormalDist().inv_cdf((1.0 + cfg.INTERVAL_WIDTH) / 2.0)
        margin = z * resid_std

        future_x = np.arange(n, n + periods, dtype=float).reshape(-1, 1)
        yhat = model.predict(future_x)

        last_ds = frame["ds"].iloc[-1]
        future_ds = pd.date_range(
            start=last_ds + pd.offsets.MonthBegin(1), periods=periods, freq=cfg.FREQUENCY
        )

        out = pd.DataFrame(
            {
                "ds": future_ds,
                "yhat": np.clip(yhat, 0.0, None),
                "yhat_lower": np.clip(yhat - margin, 0.0, None),
                "yhat_upper": np.clip(yhat + margin, 0.0, None),
            }
        )
        logger.info("LinearRegression produced %d forecast point(s).", len(out))
        return out
