"""
Utils: Validators
=================
Input and data validation with user-friendly, layout-safe outcomes.

Two entry points:
    * :func:`validate_file`      — cheap checks on the uploaded file object
                                   (extension, size, emptiness).
    * :func:`validate_dataframe` — content checks against the canonical
                                   mapping (missing values, duplicates,
                                   invalid/future dates, empty columns,
                                   unsupported types, negative revenue, …)
                                   plus a 0–100 data-quality score.

Validators consume the canonical mapping (never raw column semantics) so the
rest of the platform stays schema-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

import pandas as pd

from utils import column_mapper
from utils.column_mapper import ColumnMappingResult
from utils.logger import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
SUPPORTED_EXTENSIONS: Final[tuple[str, ...]] = ("csv", "xlsx")
MAX_FILE_BYTES: Final[int] = 50 * 1024 * 1024  # 50 MB

# Data-quality penalty weights (max points removed for a fully-bad dataset).
_MISSING_WEIGHT: Final[float] = 40.0
_DUPLICATE_WEIGHT: Final[float] = 20.0
_INVALID_DATE_WEIGHT: Final[float] = 25.0
_EMPTY_COLUMN_WEIGHT: Final[float] = 5.0  # per empty column, capped at 15
_EMPTY_COLUMN_CAP: Final[float] = 15.0


# --------------------------------------------------------------------------- #
# Result data structures
# --------------------------------------------------------------------------- #
@dataclass
class FileValidation:
    """Outcome of validating the uploaded file object."""

    ok: bool
    extension: str
    size_bytes: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Outcome of validating dataframe content against the canonical mapping."""

    ok: bool
    quality_score: float
    completeness_pct: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def has_warnings(self) -> bool:
        """Whether any non-blocking warnings were recorded."""
        return bool(self.warnings)


# --------------------------------------------------------------------------- #
# File-level validation
# --------------------------------------------------------------------------- #
def validate_file(file_name: str, size_bytes: int) -> FileValidation:
    """Validate the uploaded file's name/extension and size.

    Args:
        file_name: Original uploaded file name.
        size_bytes: Size of the uploaded file in bytes.

    Returns:
        A :class:`FileValidation` describing acceptability.
    """
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    result = FileValidation(ok=True, extension=extension, size_bytes=size_bytes)

    if extension not in SUPPORTED_EXTENSIONS:
        result.ok = False
        result.errors.append(
            f"Unsupported file type '.{extension or '?'}'. "
            f"Please upload a {' or '.join('.' + e for e in SUPPORTED_EXTENSIONS)} file."
        )
    if size_bytes <= 0:
        result.ok = False
        result.errors.append("The file appears to be empty.")
    if size_bytes > MAX_FILE_BYTES:
        result.ok = False
        result.errors.append(
            f"File is too large ({size_bytes / 1_048_576:.1f} MB). "
            f"The limit is {MAX_FILE_BYTES // 1_048_576} MB."
        )

    logger.info(
        "File validation: name=%s ext=%s size=%dB ok=%s.",
        file_name, extension, size_bytes, result.ok,
    )
    return result


# --------------------------------------------------------------------------- #
# Dataframe content validation
# --------------------------------------------------------------------------- #
def validate_dataframe(
    df: pd.DataFrame, mapping: ColumnMappingResult
) -> ValidationReport:
    """Validate dataframe content and compute the data-quality score.

    Args:
        df: The *raw* uploaded dataframe (original headers).
        mapping: Canonical mapping result from :mod:`column_mapper`.

    Returns:
        A :class:`ValidationReport` with errors, warnings, quality metrics,
        and a clamped 0–100 quality score.
    """
    report = ValidationReport(ok=True, quality_score=0.0, completeness_pct=0.0)
    n_rows, n_cols = int(df.shape[0]), int(df.shape[1])

    # --- Structural blockers -------------------------------------------------
    if n_rows == 0:
        report.ok = False
        report.errors.append("The dataset has no rows.")
        return report
    if not mapping.has_date:
        report.ok = False
        report.errors.append("No date/period column could be detected.")
    if not mapping.has_any_metric:
        report.ok = False
        report.errors.append(
            "No numeric metric (revenue, orders, customers, or expenses) detected."
        )

    # --- Missing values ------------------------------------------------------
    total_cells = max(n_rows * n_cols, 1)
    missing_cells = int(df.isna().sum().sum())
    missing_ratio = missing_cells / total_cells
    completeness = (1.0 - missing_ratio) * 100.0
    if missing_cells:
        report.warnings.append(
            f"{missing_cells} missing value(s) detected "
            f"({missing_ratio * 100:.1f}% of cells) — they will be imputed."
        )

    # --- Duplicate rows ------------------------------------------------------
    duplicate_rows = int(df.duplicated().sum())
    duplicate_ratio = duplicate_rows / n_rows
    if duplicate_rows:
        report.warnings.append(
            f"{duplicate_rows} duplicate row(s) detected — they will be removed."
        )

    # --- Empty columns -------------------------------------------------------
    empty_columns = [c for c in df.columns if df[c].isna().all()]
    if empty_columns:
        report.warnings.append(
            f"{len(empty_columns)} fully-empty column(s): "
            f"{', '.join(map(str, empty_columns))}."
        )

    # --- Date validity -------------------------------------------------------
    invalid_dates = 0
    future_dates = 0
    date_source = mapping.source_for(column_mapper.DATE)
    if date_source is not None and date_source in df.columns:
        parsed = pd.to_datetime(df[date_source], errors="coerce")
        invalid_dates = int(parsed.isna().sum() - df[date_source].isna().sum())
        invalid_dates = max(invalid_dates, 0)
        if invalid_dates:
            report.warnings.append(
                f"{invalid_dates} unparseable date value(s) — affected rows will be dropped."
            )
        now = pd.Timestamp.now().normalize()
        future_dates = int((parsed > now).sum())
        if future_dates:
            report.warnings.append(
                f"{future_dates} row(s) have future dates — kept, but verify the source."
            )

    # --- Metric type / negativity checks ------------------------------------
    for metric in mapping.detected_metrics:
        source = mapping.source_for(metric)
        if source is None or source not in df.columns:
            continue
        coerced = pd.to_numeric(df[source], errors="coerce")
        non_numeric = int(coerced.isna().sum() - df[source].isna().sum())
        non_numeric = max(non_numeric, 0)
        if non_numeric:
            report.warnings.append(
                f"'{source}' ({metric}) has {non_numeric} non-numeric value(s) "
                "— they will be imputed."
            )
        if metric == column_mapper.REVENUE and (coerced < 0).any():
            report.warnings.append(
                f"'{source}' contains negative revenue value(s) — please verify."
            )

    # --- Quality score -------------------------------------------------------
    missing_penalty = missing_ratio * _MISSING_WEIGHT
    duplicate_penalty = duplicate_ratio * _DUPLICATE_WEIGHT
    invalid_date_penalty = (invalid_dates / n_rows) * _INVALID_DATE_WEIGHT
    empty_column_penalty = min(len(empty_columns) * _EMPTY_COLUMN_WEIGHT, _EMPTY_COLUMN_CAP)

    raw_score = 100.0 - (
        missing_penalty + duplicate_penalty + invalid_date_penalty + empty_column_penalty
    )
    report.quality_score = round(_clamp(raw_score, 0.0, 100.0), 1)
    report.completeness_pct = round(_clamp(completeness, 0.0, 100.0), 1)

    report.metrics = {
        "rows": float(n_rows),
        "columns": float(n_cols),
        "missing_cells": float(missing_cells),
        "duplicate_rows": float(duplicate_rows),
        "empty_columns": float(len(empty_columns)),
        "invalid_dates": float(invalid_dates),
        "future_dates": float(future_dates),
        "missing_penalty": round(missing_penalty, 1),
        "duplicate_penalty": round(duplicate_penalty, 1),
        "invalid_date_penalty": round(invalid_date_penalty, 1),
        "empty_column_penalty": round(empty_column_penalty, 1),
    }

    report.ok = report.ok and not report.errors
    logger.info(
        "Dataframe validation: ok=%s quality=%.1f completeness=%.1f warnings=%d.",
        report.ok, report.quality_score, report.completeness_pct, len(report.warnings),
    )
    return report


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive ``[low, high]`` range."""
    return max(low, min(high, value))
