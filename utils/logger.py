"""
Utils: Logger
=============
Centralized logging configuration for the whole application.

Provides a single ``get_logger(name)`` factory that writes to both the
``logs/`` directory (rotating file) and the console, using a level taken from
the ``LOG_LEVEL`` environment variable (default ``INFO``). Handlers are
attached once per logger to avoid duplicate log lines under Streamlit's
re-run model.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

_LOG_DIR: Final[Path] = Path(__file__).resolve().parents[1] / "logs"
_LOG_FILE: Final[Path] = _LOG_DIR / "forecastiq.log"
_LOG_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES: Final[int] = 1_000_000
_BACKUP_COUNT: Final[int] = 3


def _resolve_level() -> int:
    """Resolve the configured log level from the environment."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger.

    Idempotent: repeated calls for the same ``name`` reuse the existing
    handlers instead of stacking new ones (important under Streamlit re-runs).

    Args:
        name: Logger name, conventionally ``__name__`` of the caller module.

    Returns:
        A ready-to-use :class:`logging.Logger`.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(_resolve_level())
    logger.propagate = False
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler.
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Rotating file handler (best-effort: never break the app over logging).
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("File logging unavailable; continuing with console only.")

    return logger
