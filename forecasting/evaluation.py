"""
Forecasting: Evaluation
=======================
Model-agnostic accuracy metrics and transparent confidence scoring.

Given aligned actual/predicted hold-out values, computes MAE, RMSE, and MAPE,
then derives a 0–100 ``confidence_score`` and a categorical
``confidence_rating``. The payload carries enough methodology metadata
(method, train/test sizes, samples, notes) for the AI layer (Step 5) to
explain *why* a forecast is or isn't trustworthy.

Uses NumPy only (metric math); scikit-learn estimators live in the model
modules, not here.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from config import forecast_config as cfg
from utils.logger import get_logger

logger = get_logger(__name__)


def evaluate(
    y_true: Sequence[float],
    y_pred: Sequence[float],
    *,
    model: str,
    train_size: int,
    test_size: int,
) -> dict[str, Any]:
    """Compute accuracy metrics + confidence from a hold-out backtest.

    Args:
        y_true: Actual values for the hold-out window.
        y_pred: Model predictions aligned with ``y_true``.
        model: Model key (for metadata/explanations).
        train_size: Number of observations used for training.
        test_size: Number of observations in the hold-out window.

    Returns:
        The evaluation payload (see module docstring).
    """
    true = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    n = min(len(true), len(pred))
    if n == 0:
        return insufficient(train_size + test_size, model=model)

    true, pred = true[:n], pred[:n]
    errors = pred - true
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    mape = _mape(true, pred)

    confidence_score = _confidence_from_mape(mape, samples=n)
    payload: dict[str, Any] = {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 2) if mape is not None else None,
        "confidence_score": confidence_score,
        "confidence_rating": rate_confidence(confidence_score),
        "method": "holdout_backtest",
        "model": model,
        "train_size": int(train_size),
        "test_size": int(test_size),
        "samples": int(n),
        "notes": _notes(mape, n),
    }
    logger.info(
        "Evaluation (%s): MAE=%.2f RMSE=%.2f MAPE=%s conf=%.1f (%s).",
        model, mae, rmse, payload["mape"], confidence_score, payload["confidence_rating"],
    )
    return payload


def insufficient(n_history: int, *, model: str = "") -> dict[str, Any]:
    """Return an evaluation payload when a backtest could not be run.

    Confidence is capped and scaled by available history so the UI can still
    show a meaningful (low) score without misleading the user.
    """
    score = round(min(50.0, max(10.0, n_history * 7.0)), 1)
    logger.info("Evaluation skipped (insufficient data, n=%d): conf=%.1f.", n_history, score)
    return {
        "mae": None,
        "rmse": None,
        "mape": None,
        "confidence_score": score,
        "confidence_rating": rate_confidence(score),
        "method": "insufficient_data",
        "model": model,
        "train_size": int(n_history),
        "test_size": 0,
        "samples": 0,
        "notes": (
            f"Only {n_history} monthly point(s) available — not enough for a "
            "reliable hold-out backtest. Treat this forecast as indicative."
        ),
    }


def rate_confidence(score: float) -> str:
    """Map a 0–100 confidence score to a categorical rating."""
    if score >= cfg.CONFIDENCE_EXCELLENT:
        return "Excellent"
    if score >= cfg.CONFIDENCE_GOOD:
        return "Good"
    if score >= cfg.CONFIDENCE_MODERATE:
        return "Moderate"
    return "Low"


def accuracy_display(evaluation: dict[str, Any] | None) -> dict[str, str]:
    """Return consistent UI labels for forecast accuracy across pages.

    When a hold-out backtest ran, the score is ``100 − MAPE`` ("Forecast Accuracy").
    When history is too short for a backtest, the score reflects data sufficiency only.
    """
    evaluation = evaluation or {}
    score = float(evaluation.get("confidence_score") or 0)
    rating = str(evaluation.get("confidence_rating") or "—")
    method = str(evaluation.get("method") or "")
    if method == "insufficient_data":
        return {
            "label": "Data Sufficiency",
            "value": f"{score:.0f}/100",
            "caption": f"Not enough history for backtest · {rating}",
        }
    mape = evaluation.get("mape")
    mape_note = f"MAPE {mape:.1f}%" if mape is not None else "hold-out backtest"
    return {
        "label": "Forecast Accuracy",
        "value": f"{score:.0f}/100",
        "caption": f"{mape_note} · {rating}",
    }


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _mape(true: np.ndarray, pred: np.ndarray) -> float | None:
    """Mean Absolute Percentage Error over non-zero actuals (as a percent).

    Returns ``None`` if every actual is zero (MAPE undefined).
    """
    mask = true != 0
    if not mask.any():
        return None
    return float(np.mean(np.abs((true[mask] - pred[mask]) / true[mask])) * 100.0)


def _confidence_from_mape(mape: float | None, *, samples: int) -> float:
    """Derive a transparent 0–100 confidence score from MAPE.

    Methodology: ``confidence = 100 − MAPE`` (clamped to 0–100). When MAPE is
    undefined (all-zero actuals), fall back to a small sample-based score so
    the rating is conservative rather than absent.
    """
    if mape is None:
        return round(min(50.0, max(10.0, samples * 8.0)), 1)
    return round(max(0.0, min(100.0, 100.0 - mape)), 1)


def _notes(mape: float | None, samples: int) -> str:
    """Human-readable methodology note for explanations."""
    if mape is None:
        return (
            f"MAPE undefined (zero actuals in the {samples}-point hold-out); "
            "confidence estimated from sample size."
        )
    return (
        f"Confidence = 100 − MAPE on a {samples}-point hold-out "
        f"(MAPE = {mape:.1f}%)."
    )
