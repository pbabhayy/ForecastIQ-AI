"""
Database: History Repository
============================
Repository pattern — the only persistence API the application uses.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from database import sqlite_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def _json_dumps(data: Any) -> str:
    return json.dumps(data, default=str)


def _json_loads(text: str | None) -> Any:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Corrupt JSON in history record — returning empty dict.")
        return {}


def save_dataset(
    name: str,
    profile: dict[str, Any],
    *,
    uploaded: dict[str, Any] | None = None,
) -> int:
    """Persist dataset metadata. Returns the new row id."""
    sqlite_manager.initialize_database()
    metrics = profile.get("detected_metrics") or []
    row_id = sqlite_manager.execute(
        """
        INSERT INTO datasets (name, row_count, column_count, date_range,
                              metrics_json, quality_score, payload_json, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            profile.get("row_count"),
            profile.get("column_count"),
            profile.get("date_range_label"),
            _json_dumps(metrics),
            profile.get("data_quality_score"),
            _json_dumps({"profile": profile, "uploaded": uploaded or {}}),
            "saved",
        ),
    )
    logger.info("Saved dataset history id=%d name=%s.", row_id, name)
    return row_id


def save_analytics(dataset_id: int | None, analytics: dict[str, Any]) -> int:
    """Persist an analytics snapshot."""
    sqlite_manager.initialize_database()
    row_id = sqlite_manager.execute(
        "INSERT INTO analytics (dataset_id, payload_json, status) VALUES (?, ?, ?)",
        (dataset_id, _json_dumps(analytics), "saved"),
    )
    logger.info("Saved analytics history id=%d.", row_id)
    return row_id


def save_forecast(dataset_id: int | None, forecast: dict[str, Any]) -> int:
    """Persist a forecast snapshot (DataFrames serialized as records)."""
    sqlite_manager.initialize_database()
    from reports.report_builder import sanitize_for_storage

    payload = sanitize_for_storage(forecast)
    row_id = sqlite_manager.execute(
        """
        INSERT INTO forecasts (dataset_id, metric, model, horizon, payload_json, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            dataset_id,
            forecast.get("metric"),
            forecast.get("model"),
            forecast.get("horizon"),
            _json_dumps(payload),
            "saved" if forecast.get("ok", True) else "failed",
        ),
    )
    logger.info("Saved forecast history id=%d.", row_id)
    return row_id


def save_ai_insights(
    dataset_id: int | None, ai_metadata: dict[str, Any], *, provider: str | None = None
) -> int:
    """Persist AI insight/recommendation snapshot."""
    sqlite_manager.initialize_database()
    row_id = sqlite_manager.execute(
        "INSERT INTO ai_insights (dataset_id, provider, payload_json, status) VALUES (?, ?, ?, ?)",
        (dataset_id, provider or ai_metadata.get("provider"), _json_dumps(ai_metadata), "saved"),
    )
    logger.info("Saved AI insights history id=%d.", row_id)
    return row_id


def save_report(
    dataset_id: int | None,
    title: str,
    report_object: dict[str, Any],
    *,
    file_path: str | None = None,
    status: str = "generated",
) -> int:
    """Persist a generated report record."""
    sqlite_manager.initialize_database()
    row_id = sqlite_manager.execute(
        """
        INSERT INTO reports (dataset_id, title, file_path, payload_json, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (dataset_id, title, file_path, _json_dumps(report_object), status),
    )
    logger.info("Saved report history id=%d title=%s.", row_id, title)
    return row_id


def list_reports(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent report history entries."""
    try:
        sqlite_manager.initialize_database()
        rows = sqlite_manager.fetch_all(
            """
            SELECT id, dataset_id, title, file_path, status, created_at
            FROM reports ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in rows]
    except sqlite_manager.DatabaseError:
        logger.exception("Failed to list reports.")
        return []


def list_datasets(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent dataset history entries."""
    try:
        sqlite_manager.initialize_database()
        rows = sqlite_manager.fetch_all(
            """
            SELECT id, name, row_count, column_count, date_range, quality_score,
                   status, created_at
            FROM datasets ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in rows]
    except sqlite_manager.DatabaseError:
        logger.exception("Failed to list datasets.")
        return []


def list_forecasts(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent forecast history entries."""
    try:
        sqlite_manager.initialize_database()
        rows = sqlite_manager.fetch_all(
            """
            SELECT id, dataset_id, metric, model, horizon, status, created_at
            FROM forecasts ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in rows]
    except sqlite_manager.DatabaseError:
        logger.exception("Failed to list forecasts.")
        return []


def get_report(report_id: int) -> dict[str, Any] | None:
    """Load a single report record by id."""
    try:
        sqlite_manager.initialize_database()
        row = sqlite_manager.fetch_one("SELECT * FROM reports WHERE id = ?", (report_id,))
        if row is None:
            return None
        data = dict(row)
        data["payload"] = _json_loads(data.get("payload_json"))
        return data
    except sqlite_manager.DatabaseError:
        logger.exception("Failed to load report id=%d.", report_id)
        return None


def persist_session_snapshot(session_data: dict[str, Any]) -> dict[str, Any]:
    """Save current session artifacts and return ids/metadata."""
    uploaded = session_data.get("uploaded_file") or {}
    profile = session_data.get("dataset_profile") or {}
    name = uploaded.get("name") or "dataset"

    try:
        dataset_id = save_dataset(name, profile, uploaded=uploaded)
        analytics_id = None
        forecast_id = None
        ai_id = None

        if session_data.get("analytics"):
            analytics_id = save_analytics(dataset_id, session_data["analytics"])
        if session_data.get("forecasts"):
            forecast_id = save_forecast(dataset_id, session_data["forecasts"])
        ai_meta = session_data.get("ai_metadata")
        if ai_meta:
            ai_id = save_ai_insights(dataset_id, ai_meta, provider=session_data.get("ai_provider"))

        return {
            "ok": True,
            "dataset_id": dataset_id,
            "analytics_id": analytics_id,
            "forecast_id": forecast_id,
            "ai_id": ai_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    except sqlite_manager.DatabaseError as exc:
        logger.exception("Session snapshot persistence failed.")
        return {"ok": False, "error": str(exc)}
