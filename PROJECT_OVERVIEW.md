# ForecastIQ AI — Project Overview

A concise overview for judges, stakeholders, and technical reviewers.

---

## Problem Statement

Small and mid-sized businesses store performance data in spreadsheets but lack affordable tools to turn that data into forecasts, health assessments, and actionable recommendations. Manual analysis is slow, error-prone, and requires data-science expertise most teams do not have.

---

## Solution

**ForecastIQ AI** is an AI-powered business forecasting and decision intelligence platform. Users upload a CSV or XLSX file; the platform automatically:

1. Detects and maps columns (no manual setup)
2. Validates and profiles data quality
3. Computes business analytics and a health score
4. Generates multi-model forecasts with confidence metrics
5. Produces AI insights and prioritized recommendations
6. Exports a professional executive PDF report

Everything is dynamic — no hardcoded data, no fake analytics.

---

## Architecture

Enterprise modular design with strict layer boundaries:

- **Presentation** — Streamlit multipage UI + premium design system
- **Analytics** — pandas-based metrics, profiling, health scoring
- **Forecasting** — Prophet + Linear Regression behind a manager pattern
- **AI** — Groq → Ollama → rule-based provider chain
- **Visualization** — isolated Plotly layer
- **Persistence** — SQLite repository pattern
- **Reporting** — render-agnostic report builder + ReportLab PDF

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details.

---

## AI Features

| Capability | Description |
|------------|-------------|
| Provider abstraction | Swappable Groq, Ollama, future OpenAI/Gemini |
| Never fails | Rule-based deterministic fallback always available |
| Insights | Business summary, revenue, forecast, trend, risk, opportunities |
| Recommendations | High/Medium/Low priority actions across 6 categories |
| Transparency | Health score breakdown feeds AI context |

---

## Forecasting Features

| Capability | Description |
|------------|-------------|
| Models | Prophet (primary), Linear Regression (baseline/fallback) |
| Horizons | 1, 3, 6, 12 months |
| Metrics | Revenue, orders, customers |
| Evaluation | MAE, RMSE, MAPE, confidence score 0–100 |
| Visualization | Historical vs forecast, confidence bands, heatmaps, model comparison |

---

## Business Value

- **Speed** — spreadsheet to executive report in minutes
- **Accessibility** — no column mapping, no SQL, no code
- **Trust** — transparent health scoring and forecast evaluation
- **Resilience** — AI and forecasting degrade gracefully
- **Portability** — local SQLite, exportable PDFs, demo-ready assets

---

## Technical Highlights

- Fuzzy column detection with confidence scores
- Canonical data contract (`date`, `revenue`, `orders`, `customers`, `expenses`)
- Unified forecast result contract (AI/report/persistence compatible)
- Session-state architecture for instant multipage navigation
- Premium dark SaaS UI (Stripe/Vercel-inspired design system)
- Production logging with rotating file handler
- SOLID-compliant modules — extensible without refactoring

---

## Demo Path (5 minutes)

1. Upload `assets/sample_dataset_extended.csv`
2. Review Business Analytics (KPIs + health + charts)
3. Forecasting → Revenue → 6 months → Prophet → Generate
4. AI Insights → Generate
5. Reports → Generate PDF → Download

Works fully offline with rule-based AI. Add `GROQ_API_KEY` for cloud LLM insights.

---

## Status

**Version 1.0 · Production Ready**

All core layers implemented (Steps 1–7). Suitable for local deployment, demos, and Streamlit Cloud with documented limitations.
