"""
Analytics: Processor
====================
File reading and canonical data preparation.

Two responsibilities:
    * :func:`read_uploaded_file` — turn an uploaded CSV/XLSX into a raw
      dataframe (with friendly errors for unsupported/corrupt/empty files).
    * :func:`clean_and_prepare`  — apply the canonical mapping, normalize
      dates, coerce numerics, impute, de-duplicate, sort chronologically, and
      return an analytics-ready dataframe whose columns are *only* canonical
      field names.

No forecasting/analytics logic — pure ingestion + transformation. The output
contract (canonical columns, sorted by ``date``) is what every downstream
layer depends on.
"""

from __future__ import annotations

import io
from typing import BinaryIO

import pandas as pd

from utils import column_mapper
from utils.column_mapper import ColumnMappingResult
from utils.logger import get_logger

logger = get_logger(__name__)


class IngestionError(Exception):
    """Raised when an uploaded file cannot be read into a dataframe.

    The message is safe to display directly to end users.
    """


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #
def read_uploaded_file(data: bytes, file_name: str) -> pd.DataFrame:
    """Read raw bytes from an upload into a dataframe.

    Args:
        data: Raw file bytes (e.g. ``uploaded_file.getvalue()``).
        file_name: Original file name, used to determine the parser.

    Returns:
        The raw, un-mapped dataframe.

    Raises:
        IngestionError: For unsupported types, empty content, or parse errors.
    """
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if not data:
        raise IngestionError("The uploaded file is empty.")

    buffer: BinaryIO = io.BytesIO(data)
    try:
        if extension == "csv":
            frame = pd.read_csv(buffer)
        elif extension == "xlsx":
            frame = pd.read_excel(buffer, engine="openpyxl")
        else:
            raise IngestionError(
                f"Unsupported file type '.{extension or '?'}'. Upload a CSV or XLSX file."
            )
    except IngestionError:
        raise
    except pd.errors.EmptyDataError as exc:
        raise IngestionError("The file contains no readable data.") from exc
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        logger.exception("Failed to parse uploaded file '%s'.", file_name)
        raise IngestionError(
            "We couldn't read this file. It may be corrupt or improperly formatted."
        ) from exc

    if frame.empty or frame.shape[1] == 0:
        raise IngestionError("The file has no columns or rows to analyze.")

    frame.columns = [str(c).strip() for c in frame.columns]
    logger.info("Read '%s': %d rows × %d cols.", file_name, frame.shape[0], frame.shape[1])
    return frame


# --------------------------------------------------------------------------- #
# Cleaning / canonical preparation
# --------------------------------------------------------------------------- #
def clean_and_prepare(
    raw_df: pd.DataFrame, mapping: ColumnMappingResult
) -> pd.DataFrame:
    """Produce an analytics-ready, canonical dataframe.

    Steps: select mapped columns → rename to canonical → parse dates → drop
    invalid-date rows → coerce metrics to numeric → forward/backward-fill →
    drop fully-unusable rows → aggregate duplicate dates → sort chronologically.

    Args:
        raw_df: The raw uploaded dataframe.
        mapping: Canonical mapping result.

    Returns:
        A dataframe with a ``date`` column (datetime) plus any detected metric
        columns, sorted ascending by date. Columns are canonical names only.
    """
    if not mapping.has_date:
        logger.warning("clean_and_prepare called without a date mapping.")
        return pd.DataFrame()

    # 1) Select + rename mapped columns to canonical names.
    rename_map: dict[str, str] = {}
    for canonical in column_mapper.CANONICAL_FIELDS:
        source = mapping.source_for(canonical)
        if source is not None and source in raw_df.columns:
            rename_map[source] = canonical
    frame = raw_df[list(rename_map.keys())].rename(columns=rename_map).copy()

    # 2) Parse dates and drop unparseable rows.
    frame[column_mapper.DATE] = pd.to_datetime(
        frame[column_mapper.DATE], errors="coerce"
    )
    before = len(frame)
    frame = frame.dropna(subset=[column_mapper.DATE])
    dropped_dates = before - len(frame)
    if dropped_dates:
        logger.info("Dropped %d row(s) with invalid dates.", dropped_dates)

    # 3) Coerce metrics to numeric.
    metric_cols = [m for m in mapping.detected_metrics if m in frame.columns]
    for col in metric_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    # 4) Drop exact duplicate rows.
    dup_before = len(frame)
    frame = frame.drop_duplicates()
    removed_dups = dup_before - len(frame)
    if removed_dups:
        logger.info("Removed %d duplicate row(s).", removed_dups)

    # 5) Sort chronologically (needed before fill so ffill is time-ordered).
    frame = frame.sort_values(column_mapper.DATE).reset_index(drop=True)

    # 6) Aggregate rows that share the same date (sum flows, keep last count).
    if frame[column_mapper.DATE].duplicated().any():
        frame = _aggregate_by_date(frame, metric_cols)

    # 7) Impute missing numeric values (forward then backward; residual → 0).
    for col in metric_cols:
        frame[col] = frame[col].ffill().bfill()
        if frame[col].isna().any():
            frame[col] = frame[col].fillna(0.0)

    # 8) Drop rows where every metric is still unusable (all-NaN safeguard).
    if metric_cols:
        frame = frame.dropna(how="all", subset=metric_cols)

    frame = frame.reset_index(drop=True)
    logger.info(
        "Cleaned dataframe: %d rows, metrics=%s.", len(frame), metric_cols
    )
    return frame


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _aggregate_by_date(frame: pd.DataFrame, metric_cols: list[str]) -> pd.DataFrame:
    """Collapse duplicate dates into a single row per date.

    Flow-type metrics (revenue, orders, expenses) are summed; ``customers`` is
    treated as a point-in-time count and uses the last (latest) value.
    """
    agg: dict[str, str] = {}
    for col in metric_cols:
        agg[col] = "last" if col == column_mapper.CUSTOMERS else "sum"
    grouped = (
        frame.groupby(column_mapper.DATE, as_index=False)
        .agg(agg)
        .sort_values(column_mapper.DATE)
        .reset_index(drop=True)
    )
    logger.info("Aggregated duplicate dates: %d → %d rows.", len(frame), len(grouped))
    return grouped


def to_metric_frame(clean_df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Return a two-column (``ds``, ``y``) frame for a single canonical metric.

    Provided for the forecasting layer (Step 4); produced here so the
    forecasting contract is owned by the data layer. Returns an empty frame if
    the metric is absent.
    """
    if metric not in clean_df.columns or column_mapper.DATE not in clean_df.columns:
        return pd.DataFrame(columns=["ds", "y"])
    out = clean_df[[column_mapper.DATE, metric]].rename(
        columns={column_mapper.DATE: "ds", metric: "y"}
    )
    out["y"] = out["y"].astype(float)
    return out.reset_index(drop=True)
