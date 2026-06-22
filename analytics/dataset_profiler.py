"""
Analytics: Dataset Profiler
===========================
Automated dataset profiling and quality summary.

Combines the raw dataframe, the cleaned canonical dataframe, the column
mapping, and the validation report into a single structured profile object
that is persisted to session state and reused by the Upload page, the AI
layer (Step 5), and the report layer (Step 6).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from utils import column_mapper
from utils.column_mapper import ColumnMappingResult
from utils.logger import get_logger
from utils.validators import ValidationReport

logger = get_logger(__name__)


@dataclass
class ColumnSummary:
    """Per-column summary used in the profile."""

    name: str
    dtype: str
    non_null: int
    nulls: int
    canonical: str | None


@dataclass
class DatasetProfile:
    """Structured dataset profile (persisted as ``dataset_profile``)."""

    row_count: int
    original_row_count: int
    column_count: int
    missing_value_count: int
    duplicate_count: int
    date_start: str | None
    date_end: str | None
    date_range_label: str
    detected_metrics: list[str]
    data_quality_score: float
    completeness_pct: float
    column_summary: list[dict[str, Any]] = field(default_factory=list)
    mapping_report: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation (JSON/report friendly)."""
        return asdict(self)


def profile_dataset(
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    mapping: ColumnMappingResult,
    validation: ValidationReport,
) -> DatasetProfile:
    """Build a :class:`DatasetProfile` from ingestion artifacts.

    Args:
        raw_df: The raw uploaded dataframe (original headers).
        clean_df: The cleaned canonical dataframe.
        mapping: Canonical column mapping result.
        validation: Validation report (source of the quality score).

    Returns:
        A structured, serializable dataset profile.
    """
    date_start, date_end, date_label = _date_range(clean_df)

    profile = DatasetProfile(
        row_count=int(clean_df.shape[0]),
        original_row_count=int(raw_df.shape[0]),
        column_count=int(raw_df.shape[1]),
        missing_value_count=int(raw_df.isna().sum().sum()),
        duplicate_count=int(raw_df.duplicated().sum()),
        date_start=date_start,
        date_end=date_end,
        date_range_label=date_label,
        detected_metrics=list(mapping.detected_metrics),
        data_quality_score=validation.quality_score,
        completeness_pct=validation.completeness_pct,
        column_summary=_column_summaries(raw_df, mapping),
        mapping_report=list(mapping.report),
    )
    logger.info(
        "Profiled dataset: rows=%d cols=%d metrics=%s quality=%.1f.",
        profile.row_count, profile.column_count,
        profile.detected_metrics, profile.data_quality_score,
    )
    return profile


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _date_range(clean_df: pd.DataFrame) -> tuple[str | None, str | None, str]:
    """Return ``(start_iso, end_iso, human_label)`` for the date column."""
    if column_mapper.DATE not in clean_df.columns or clean_df.empty:
        return None, None, "—"
    series = clean_df[column_mapper.DATE]
    start, end = series.min(), series.max()
    if pd.isna(start) or pd.isna(end):
        return None, None, "—"
    start_str, end_str = start.strftime("%b %Y"), end.strftime("%b %Y")
    label = start_str if start_str == end_str else f"{start_str} – {end_str}"
    return start.date().isoformat(), end.date().isoformat(), label


def _column_summaries(
    raw_df: pd.DataFrame, mapping: ColumnMappingResult
) -> list[dict[str, Any]]:
    """Build per-column summaries with their canonical assignment."""
    summaries: list[dict[str, Any]] = []
    for col in raw_df.columns:
        info = mapping.mapping.get(str(col))
        canonical = str(info["canonical"]) if info else None
        summaries.append(
            ColumnSummary(
                name=str(col),
                dtype=str(raw_df[col].dtype),
                non_null=int(raw_df[col].notna().sum()),
                nulls=int(raw_df[col].isna().sum()),
                canonical=canonical,
            ).__dict__
        )
    return summaries
