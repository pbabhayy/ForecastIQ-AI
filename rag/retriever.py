"""
RAG: Retriever
==============
Chunk business artifacts, embed via Ollama, store in SQLite, retrieve by cosine similarity.
Uses only SQLite, pandas, numpy, and Ollama HTTP — no extra vector DB dependencies.
"""

from __future__ import annotations

import json
import re
from typing import Any

import numpy as np

from config.settings import get_settings
from database import sqlite_manager
from utils.logger import get_logger

logger = get_logger(__name__)

EMBED_MODEL = "nomic-embed-text"
_SOURCE_TYPES = ("profile_summary", "analytics_summary", "forecast_summary", "ai_insight")


def _chunk_text(text: str, *, max_chars: int = 320) -> list[str]:
    """Split text into sentence-ish chunks for embedding."""
    if not text or not str(text).strip():
        return []
    parts = re.split(r"(?<=[.!?])\s+", str(text).strip())
    chunks: list[str] = []
    buf = ""
    for part in parts:
        if len(buf) + len(part) + 1 <= max_chars:
            buf = f"{buf} {part}".strip() if buf else part
        else:
            if buf:
                chunks.append(buf)
            buf = part[:max_chars]
    if buf:
        chunks.append(buf)
    return chunks or [str(text)[:max_chars]]


def embed_text(text: str) -> list[float] | None:
    """Call Ollama ``/api/embeddings`` for a single text chunk."""
    settings = get_settings()
    if not settings.ollama_base_url:
        return None
    try:
        import httpx

        base = settings.ollama_base_url.rstrip("/")
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=2.0)) as client:
            response = client.post(
                f"{base}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            vector = data.get("embedding")
            if not vector:
                return None
            return [float(v) for v in vector]
    except Exception:
        logger.warning("Embedding failed for chunk (Ollama may be offline).")
        return None


def _store_chunks(dataset_id: int | None, source_type: str, chunks: list[str]) -> int:
    """Persist embedded chunks; returns count stored."""
    if dataset_id is None or not chunks:
        return 0
    if source_type not in _SOURCE_TYPES:
        source_type = "ai_insight"
    sqlite_manager.initialize_database()
    stored = 0
    for chunk in chunks:
        vector = embed_text(chunk)
        if vector is None:
            continue
        sqlite_manager.execute(
            """
            INSERT INTO embeddings (dataset_id, source_type, chunk_text, embedding_json)
            VALUES (?, ?, ?, ?)
            """,
            (dataset_id, source_type, chunk, json.dumps(vector)),
        )
        stored += 1
    if stored:
        logger.info("RAG indexed %d chunk(s) [%s] dataset_id=%s.", stored, source_type, dataset_id)
    return stored


def index_profile(dataset_id: int | None, profile: dict[str, Any]) -> None:
    """Index dataset profile summary chunks."""
    text = (
        f"Dataset {profile.get('row_count', 0)} rows, "
        f"{profile.get('column_count', 0)} columns, "
        f"date range {profile.get('date_range_label', 'unknown')}, "
        f"metrics {', '.join(profile.get('detected_metrics') or [])}, "
        f"quality score {profile.get('data_quality_score', 0)}/100."
    )
    _store_chunks(dataset_id, "profile_summary", _chunk_text(text))


def index_analytics(dataset_id: int | None, analytics: dict[str, Any]) -> None:
    """Index analytics KPI summary chunks."""
    if not analytics.get("meta", {}).get("available"):
        return
    rev = analytics.get("revenue") or {}
    parts = [
        f"Revenue total {rev.get('total')}, growth {rev.get('growth_pct')}%, trend {rev.get('trend')}.",
    ]
    orders = analytics.get("orders")
    if orders:
        parts.append(f"Orders total {orders.get('total')}, growth {orders.get('growth_pct')}%.")
    customers = analytics.get("customers")
    if customers:
        parts.append(f"Customers growth {customers.get('growth_pct')}%.")
    profit = analytics.get("profit")
    if profit:
        parts.append(f"Profit estimate {profit.get('estimate')}, margin {profit.get('margin_pct')}%.")
    _store_chunks(dataset_id, "analytics_summary", _chunk_text(" ".join(parts)))


def index_forecast(dataset_id: int | None, forecast: dict[str, Any]) -> None:
    """Index forecast summary chunks."""
    if not forecast or not forecast.get("ok"):
        return
    evaluation = forecast.get("evaluation") or {}
    text = (
        f"Forecast {forecast.get('metric')} using {forecast.get('model_label') or forecast.get('model')} "
        f"over {forecast.get('horizon')} months projects {forecast.get('growth_pct')}% growth. "
        f"Peak month {forecast.get('peak_month')}, weakest {forecast.get('lowest_month')}. "
        f"Accuracy score {evaluation.get('confidence_score')}/100 ({evaluation.get('confidence_rating')})."
    )
    _store_chunks(dataset_id, "forecast_summary", _chunk_text(text))


def index_ai_insights(dataset_id: int | None, ai_meta: dict[str, Any]) -> None:
    """Index AI insight and recommendation chunks."""
    if not ai_meta:
        return
    chunks: list[str] = []
    if ai_meta.get("summary"):
        chunks.extend(_chunk_text(str(ai_meta["summary"])))
    for item in ai_meta.get("insights") or []:
        chunks.extend(_chunk_text(f"{item.get('title', '')}: {item.get('body', '')}"))
    for item in ai_meta.get("recommendations") or []:
        chunks.extend(
            _chunk_text(
                f"[{item.get('priority', 'Medium')}] {item.get('title', '')}: {item.get('body', '')}"
            )
        )
    _store_chunks(dataset_id, "ai_insight", chunks)


def retrieve_context(query: str, dataset_id: int | None, *, top_k: int = 4) -> list[str]:
    """Embed query and return top-k chunk texts by cosine similarity."""
    if dataset_id is None or not query.strip():
        return []
    query_vec = embed_text(query.strip())
    if query_vec is None:
        return []
    try:
        sqlite_manager.initialize_database()
        rows = sqlite_manager.fetch_all(
            "SELECT chunk_text, embedding_json FROM embeddings WHERE dataset_id = ?",
            (dataset_id,),
        )
    except sqlite_manager.DatabaseError:
        logger.exception("RAG retrieval failed.")
        return []
    if not rows:
        return []
    q = np.asarray(query_vec, dtype=float)
    q_norm = np.linalg.norm(q)
    if q_norm == 0:
        return []
    scored: list[tuple[float, str]] = []
    for row in rows:
        try:
            vec = np.asarray(json.loads(row["embedding_json"]), dtype=float)
        except (json.JSONDecodeError, TypeError):
            continue
        denom = np.linalg.norm(vec) * q_norm
        if denom == 0:
            continue
        score = float(np.dot(q, vec) / denom)
        scored.append((score, row["chunk_text"]))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:top_k]]
