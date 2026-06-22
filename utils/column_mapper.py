"""
Utils: Column Mapper
====================
Fuzzy detection of canonical fields from arbitrary uploaded headers.

This module is the **mandatory boundary** between raw uploaded data and the
rest of the platform. Downstream systems (analytics, forecasting, AI, reports)
consume *only* the canonical schema produced here and never touch original
column names.

Canonical schema
----------------
    date · revenue · orders · customers · expenses

Matching is case-insensitive, whitespace-insensitive, and combines exact,
token, substring (regex), and fuzzy (difflib) strategies, returning a
confidence score and the method used for every detected column.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Final, Iterable, Sequence

from utils.logger import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Canonical field names (single source of truth for the whole platform)
# --------------------------------------------------------------------------- #
DATE: Final[str] = "date"
REVENUE: Final[str] = "revenue"
ORDERS: Final[str] = "orders"
CUSTOMERS: Final[str] = "customers"
EXPENSES: Final[str] = "expenses"

CANONICAL_FIELDS: Final[tuple[str, ...]] = (DATE, REVENUE, ORDERS, CUSTOMERS, EXPENSES)
#: Numeric metric fields (everything except the time axis).
METRIC_FIELDS: Final[tuple[str, ...]] = (REVENUE, ORDERS, CUSTOMERS, EXPENSES)

# --------------------------------------------------------------------------- #
# Synonym dictionaries (already normalized: lowercase, single-spaced)
# --------------------------------------------------------------------------- #
_SYNONYMS: Final[dict[str, tuple[str, ...]]] = {
    DATE: (
        "date", "month", "period", "timestamp", "time", "day", "year", "week",
        "datetime", "order date", "transaction date", "reporting period",
        "month year", "date time", "yearmonth", "ds",
    ),
    REVENUE: (
        "revenue", "sales", "sales revenue", "monthly revenue", "total revenue",
        "revenue amount", "income", "turnover", "gross revenue", "net revenue",
        "gmv", "earnings", "total sales", "net sales", "amount",
    ),
    ORDERS: (
        "orders", "transactions", "purchases", "order count", "num orders",
        "number of orders", "sales count", "units sold", "order volume",
        "total orders", "transaction count", "deals",
    ),
    CUSTOMERS: (
        "customers", "clients", "users", "customer count", "num customers",
        "number of customers", "active users", "buyers", "subscribers",
        "accounts", "total customers", "new customers", "client count",
    ),
    EXPENSES: (
        "expenses", "costs", "operating cost", "expenditure", "cost", "spend",
        "expense", "operating expenses", "opex", "total cost", "outgoings",
        "operating costs", "cost of goods", "cogs",
    ),
}

#: Minimum confidence required to accept a fuzzy match.
_ACCEPT_THRESHOLD: Final[float] = 0.62
_NON_ALNUM: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9]+")


# --------------------------------------------------------------------------- #
# Result data structures
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FieldMatch:
    """A single source-column → canonical-field match."""

    source: str
    canonical: str
    confidence: float
    method: str  # "exact" | "token" | "substring" | "fuzzy"


@dataclass
class ColumnMappingResult:
    """Structured outcome of column detection."""

    #: source-header -> {"canonical": str, "confidence": float, "method": str}
    mapping: dict[str, dict[str, object]] = field(default_factory=dict)
    #: canonical-field -> chosen source header
    canonical_to_source: dict[str, str] = field(default_factory=dict)
    #: canonical metric fields that were detected (excludes ``date``)
    detected_metrics: list[str] = field(default_factory=list)
    #: source headers that did not map to any canonical field
    unmapped: list[str] = field(default_factory=list)
    #: human-readable diagnostics
    report: list[str] = field(default_factory=list)

    @property
    def has_date(self) -> bool:
        """Whether a date/time column was detected."""
        return DATE in self.canonical_to_source

    @property
    def has_any_metric(self) -> bool:
        """Whether at least one numeric metric was detected."""
        return len(self.detected_metrics) > 0

    @property
    def is_usable(self) -> bool:
        """Minimum requirement: a date column plus at least one metric."""
        return self.has_date and self.has_any_metric

    def source_for(self, canonical: str) -> str | None:
        """Return the source header chosen for a canonical field, if any."""
        return self.canonical_to_source.get(canonical)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def normalize_header(header: str) -> str:
    """Normalize a raw header for comparison.

    Lowercases, replaces any run of non-alphanumeric characters with a single
    space, and trims. e.g. ``"  Sales_Revenue ($) "`` → ``"sales revenue"``.
    """
    return _NON_ALNUM.sub(" ", str(header).lower()).strip()


def detect_columns(columns: Iterable[str]) -> ColumnMappingResult:
    """Detect canonical fields from an iterable of column headers.

    Args:
        columns: The raw column headers (e.g. ``df.columns``).

    Returns:
        A :class:`ColumnMappingResult` with the mapping, confidence scores,
        detected metrics, unmapped columns, and human-readable diagnostics.
    """
    headers: list[str] = [str(c) for c in columns]
    logger.info("Column detection started for %d columns.", len(headers))

    # 1) Score every header against every canonical field.
    candidates: list[FieldMatch] = []
    for header in headers:
        match = _best_match(header)
        if match is not None:
            candidates.append(match)

    # 2) Resolve conflicts: if multiple headers map to the same canonical
    #    field, keep the highest-confidence one; the rest become unmapped.
    result = ColumnMappingResult()
    best_per_canonical: dict[str, FieldMatch] = {}
    for match in sorted(candidates, key=lambda m: m.confidence, reverse=True):
        existing = best_per_canonical.get(match.canonical)
        if existing is None:
            best_per_canonical[match.canonical] = match
        else:
            result.report.append(
                f"'{match.source}' also resembled '{match.canonical}' "
                f"(conf {match.confidence:.2f}); kept '{existing.source}' "
                f"(conf {existing.confidence:.2f})."
            )

    chosen_sources = {m.source for m in best_per_canonical.values()}

    # 3) Build the mapping payload.
    for match in best_per_canonical.values():
        result.mapping[match.source] = {
            "canonical": match.canonical,
            "confidence": round(match.confidence, 4),
            "method": match.method,
        }
        result.canonical_to_source[match.canonical] = match.source

    result.detected_metrics = [
        m for m in METRIC_FIELDS if m in result.canonical_to_source
    ]
    result.unmapped = [h for h in headers if h not in chosen_sources]

    _append_diagnostics(result)
    logger.info(
        "Column detection complete: date=%s, metrics=%s, unmapped=%d.",
        result.has_date, result.detected_metrics, len(result.unmapped),
    )
    return result


def mapping_table(result: ColumnMappingResult) -> list[dict[str, object]]:
    """Flatten a mapping result into rows suitable for tabular display.

    Returns a list of ``{"Source Column", "Canonical Field", "Confidence",
    "Method"}`` dicts, including unmapped columns (canonical = ``"—"``).
    """
    rows: list[dict[str, object]] = []
    for source, info in result.mapping.items():
        rows.append(
            {
                "Source Column": source,
                "Canonical Field": str(info["canonical"]),
                "Confidence": f"{float(info['confidence']) * 100:.0f}%",
                "Method": str(info["method"]).title(),
            }
        )
    for source in result.unmapped:
        rows.append(
            {
                "Source Column": source,
                "Canonical Field": "—",
                "Confidence": "—",
                "Method": "Unmapped",
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _best_match(header: str) -> FieldMatch | None:
    """Return the best canonical match for one header, or ``None``."""
    normalized = normalize_header(header)
    if not normalized:
        return None

    tokens = set(normalized.split())
    best: FieldMatch | None = None

    for canonical, synonyms in _SYNONYMS.items():
        score, method = _score_against_synonyms(normalized, tokens, synonyms)
        if score >= _ACCEPT_THRESHOLD and (best is None or score > best.confidence):
            best = FieldMatch(header, canonical, score, method)

    return best


def _score_against_synonyms(
    normalized: str, tokens: set[str], synonyms: Sequence[str]
) -> tuple[float, str]:
    """Score a normalized header against one field's synonym set.

    Returns the best ``(confidence, method)`` pair found.
    """
    best_score = 0.0
    best_method = "fuzzy"

    for synonym in synonyms:
        # Exact match — strongest signal.
        if normalized == synonym:
            return 1.0, "exact"

        syn_tokens = set(synonym.split())

        # Whole-token match (e.g. header "monthly sales" contains token "sales").
        if syn_tokens and syn_tokens <= tokens:
            score, method = 0.95, "token"
        # Substring containment in either direction.
        elif synonym in normalized or normalized in synonym:
            score, method = 0.86, "substring"
        # Fuzzy similarity fallback.
        else:
            score, method = SequenceMatcher(None, normalized, synonym).ratio(), "fuzzy"

        if score > best_score:
            best_score, best_method = score, method

    return best_score, best_method


def _append_diagnostics(result: ColumnMappingResult) -> None:
    """Append top-level human-readable diagnostics to the report."""
    if not result.has_date:
        result.report.append("No date/time column detected — required for analysis.")
    if not result.has_any_metric:
        result.report.append(
            "No numeric metric (revenue/orders/customers/expenses) detected."
        )
    for canonical in METRIC_FIELDS:
        if canonical not in result.canonical_to_source:
            result.report.append(f"Optional field '{canonical}' not found.")
