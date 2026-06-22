"""
Reports: PDF Generator
======================
Renders the report-builder model to a professional PDF (ReportLab).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils.logger import get_logger

logger = get_logger(__name__)

EXPORT_DIR = Path("exports/reports")
ACCENT = colors.HexColor("#3B82F6")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#E2E8F0")


class PDFGenerationError(Exception):
    """Raised when PDF export fails. Message is user-safe."""


def generate_pdf(report: dict[str, Any], *, filename: str | None = None) -> str:
    """Render a report object to PDF and return the file path."""
    try:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        meta = report.get("metadata") or {}
        if not filename:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            safe_name = (meta.get("dataset_name") or "report").replace(" ", "_")[:40]
            filename = f"ForecastIQ_{safe_name}_{stamp}.pdf"
        path = EXPORT_DIR / filename

        doc = SimpleDocTemplate(
            str(path),
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=meta.get("title", "ForecastIQ Report"),
        )
        styles = _styles()
        story: list[Any] = []

        # Cover / title block
        story.append(Paragraph("ForecastIQ AI", styles["Brand"]))
        story.append(Paragraph(meta.get("title", "Executive Report"), styles["Title"]))
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(f"Dataset: {meta.get('dataset_name', '—')}", styles["Muted"]))
        story.append(Paragraph(f"Generated: {meta.get('generated_at', '—')}", styles["Muted"]))
        if meta.get("ai_provider"):
            story.append(Paragraph(f"AI Provider: {meta.get('ai_provider')}", styles["Muted"]))
        story.append(Spacer(1, 0.35 * inch))

        # Executive summary
        _section(story, styles, "Executive Summary", report.get("executive_summary", ""))

        # Dataset overview
        ds = report.get("dataset_overview") or {}
        ds_lines = [
            f"File: {ds.get('name', '—')}",
            f"Rows: {ds.get('rows', '—')} · Columns: {ds.get('columns', '—')}",
            f"Date range: {ds.get('date_range', '—')}",
            f"Metrics: {', '.join(ds.get('metrics') or []) or '—'}",
            f"Data quality: {ds.get('quality_score', '—')}/100 "
            f"({ds.get('completeness_pct', '—')}% complete)",
        ]
        _section(story, styles, "Dataset Overview", "<br/>".join(ds_lines))

        # Analytics
        an = report.get("analytics_summary") or {}
        if an.get("available"):
            an_lines = [
                f"Total revenue: {_fmt_money(an.get('total_revenue'))}",
                f"Average revenue: {_fmt_money(an.get('average_revenue'))}",
                f"Revenue growth: {_fmt_pct(an.get('revenue_growth_pct'))}",
                f"Total orders: {an.get('total_orders', '—')}",
                f"Customer growth: {_fmt_pct(an.get('customer_growth_pct'))}",
                f"Profit estimate: {_fmt_money(an.get('profit_estimate'))}",
            ]
            _section(story, styles, "Analytics Summary", "<br/>".join(an_lines))
        else:
            _section(story, styles, "Analytics Summary", "Analytics not available.")

        # Health score
        hs = report.get("health_score") or {}
        hs_text = (
            f"Score: {hs.get('score', '—')}/100 · Category: {hs.get('category', '—')}<br/>"
            f"Formula: {hs.get('formula', '—')}"
        )
        _section(story, styles, "Business Health Score", hs_text)
        for name, comp in (hs.get("breakdown") or {}).items():
            story.append(
                Paragraph(
                    f"• <b>{name.replace('_', ' ').title()}</b>: "
                    f"{comp.get('score', '—')}/100 — {comp.get('description', '')}",
                    styles["Body"],
                )
            )
        story.append(Spacer(1, 0.2 * inch))

        # Forecast
        fc = report.get("forecast_summary") or {}
        if fc.get("available"):
            fc_lines = [
                f"Metric: {str(fc.get('metric', '')).title()} · Model: {fc.get('model', '—')}",
                f"Horizon: {fc.get('horizon', '—')} month(s) · Growth: {_fmt_pct(fc.get('growth_pct'))}",
                f"Peak: {fc.get('peak_month', '—')} · Weakest: {fc.get('lowest_month', '—')}",
                f"Annual projection: {fc.get('annual_projection', '—')}",
                f"Confidence: {fc.get('confidence_score', '—')}/100 ({fc.get('confidence_rating', '—')})",
                f"MAE: {fc.get('mae', '—')} · RMSE: {fc.get('rmse', '—')} · MAPE: {fc.get('mape', '—')}%",
            ]
            _section(story, styles, "Forecast Summary", "<br/>".join(fc_lines))
            table_rows = report.get("forecast_table") or []
            if table_rows:
                story.append(Paragraph("Forecast Table", styles["Heading2"]))
                data = [["Month", "Forecast", "Lower", "Upper"]]
                for row in table_rows:
                    data.append([row.get("month", ""), row.get("forecast", ""),
                                 row.get("lower", ""), row.get("upper", "")])
                tbl = Table(data, colWidths=[1.4 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch])
                tbl.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                            ("PADDING", (0, 0), (-1, -1), 6),
                        ]
                    )
                )
                story.append(tbl)
                story.append(Spacer(1, 0.25 * inch))
        else:
            _section(story, styles, "Forecast Summary", fc.get("message", "No forecast available."))

        # AI insights
        _bullet_section(story, styles, "AI Insights", report.get("ai_insights") or [],
                        title_key="title", body_key="body", category_key="category")
        _bullet_section(story, styles, "Risks", report.get("risks") or [],
                        title_key="title", body_key="body")
        _bullet_section(story, styles, "Opportunities", report.get("opportunities") or [],
                        title_key="title", body_key="body")

        # Recommendations
        recs = report.get("recommendations") or []
        if recs:
            story.append(Paragraph("Recommendations", styles["Heading1"]))
            story.append(Spacer(1, 0.1 * inch))
            for rec in recs:
                story.append(
                    Paragraph(
                        f"• <b>[{rec.get('priority', 'Medium')}] {rec.get('title', '')}</b> "
                        f"({rec.get('category', '')})<br/>{rec.get('body', '')}",
                        styles["Body"],
                    )
                )
            story.append(Spacer(1, 0.2 * inch))

        # Footer
        story.append(Spacer(1, 0.3 * inch))
        story.append(
            Paragraph(
                f"ForecastIQ AI · Status: {meta.get('status', 'generated')} · "
                f"Report generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                styles["Footer"],
            )
        )

        doc.build(story)
        logger.info("PDF generated at %s.", path)
        return str(path)
    except Exception as exc:
        logger.exception("PDF generation failed.")
        raise PDFGenerationError("We couldn't generate the PDF. Please try again.") from exc


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Brand": ParagraphStyle("Brand", parent=base["Normal"], fontSize=11,
                                textColor=ACCENT, spaceAfter=4),
        "Title": ParagraphStyle("Title", parent=base["Title"], fontSize=22,
                                  textColor=colors.HexColor("#0F172A"), spaceAfter=8),
        "Heading1": ParagraphStyle("H1", parent=base["Heading1"], fontSize=14,
                                     textColor=colors.HexColor("#0F172A"), spaceBefore=12, spaceAfter=6),
        "Heading2": ParagraphStyle("H2", parent=base["Heading2"], fontSize=12,
                                   textColor=ACCENT, spaceBefore=8, spaceAfter=4),
        "Body": ParagraphStyle("Body", parent=base["Normal"], fontSize=10,
                               leading=14, textColor=colors.HexColor("#334155"), spaceAfter=6),
        "Muted": ParagraphStyle("Muted", parent=base["Normal"], fontSize=9,
                                textColor=MUTED, spaceAfter=3),
        "Footer": ParagraphStyle("Footer", parent=base["Normal"], fontSize=8,
                                 textColor=MUTED, alignment=TA_CENTER),
    }


def _section(story: list, styles: dict, title: str, body: str) -> None:
    story.append(Paragraph(title, styles["Heading1"]))
    story.append(Paragraph(str(body), styles["Body"]))
    story.append(Spacer(1, 0.15 * inch))


def _bullet_section(
    story: list, styles: dict, title: str, items: list,
    *, title_key: str, body_key: str, category_key: str | None = None,
) -> None:
    if not items:
        return
    story.append(Paragraph(title, styles["Heading1"]))
    for item in items:
        prefix = f"{item.get(category_key, '')} · " if category_key and item.get(category_key) else ""
        story.append(
            Paragraph(
                f"• <b>{prefix}{item.get(title_key, '')}</b><br/>{item.get(body_key, '')}",
                styles["Body"],
            )
        )
    story.append(Spacer(1, 0.15 * inch))


def _fmt_money(value: Any) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):+.1f}%"
    except (TypeError, ValueError):
        return str(value)
