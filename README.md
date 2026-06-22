# ForecastIQ AI

**AI-Powered Business Forecasting & Decision Intelligence Platform**

ForecastIQ AI is a production-grade Streamlit SaaS application that transforms uploaded business spreadsheets into analytics, forecasts, AI insights, and executive PDF reports — with zero manual column mapping.

![Dashboard placeholder — add screenshot of Business Analytics page](assets/screenshots/analytics.png)

---

## Features

- **Smart ingestion** — CSV/XLSX upload with fuzzy column detection (no manual mapping)
- **Business analytics** — revenue, orders, customers, expenses, growth, trends, profit
- **Business health score** — transparent 0–100 composite with component breakdown
- **Multi-model forecasting** — Prophet + Linear Regression with confidence intervals
- **Model evaluation** — MAE, RMSE, MAPE, confidence rating
- **Interactive charts** — Plotly dark-theme visualizations (trends, heatmaps, forecasts)
- **AI intelligence** — Groq → Ollama → rule-based fallback (never fully fails)
- **PDF reports** — executive summaries via ReportLab
- **SQLite history** — local persistence for datasets, forecasts, insights, and reports

---

## Architecture

Layered, modular design:

```
pages/          → orchestration (UI only)
components/     → premium design system
visualizations/ → Plotly charts (isolated)
analytics/      → metrics, health, profiling
forecasting/    → Prophet, sklearn, evaluation
ai/             → provider abstraction + engines
database/       → SQLite repository
reports/        → report builder + PDF export
utils/          → session, validation, column mapping
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

---

## Installation

**Requires Python 3.11 or 3.12** (Prophet/scientific wheels are not reliable on 3.14+).

```bash
git clone <repository-url>
cd ai-forecasting-platform
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

---

## Usage

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

### Quick demo flow

1. **Upload** — use `assets/sample_dataset_extended.csv` (24 months recommended for forecasting)
2. **Business Analytics** — review KPIs, health score, charts
3. **Forecasting** — select metric, horizon, model → Generate forecast
4. **AI Insights** — Generate AI insights
5. **Reports** — Generate PDF → Download

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| UI | Streamlit |
| Charts | Plotly |
| Data | pandas, NumPy |
| ML | scikit-learn, Prophet |
| AI | Groq, Ollama, rule-based |
| Reports | ReportLab |
| Database | SQLite |

---

## Folder Structure

```
app.py                 # Home / entry point
pages/                 # Multipage dashboard
components/            # UI design system
visualizations/        # Plotly charts
analytics/             # Metrics & health
forecasting/           # Forecast manager
ai/                    # Insight & recommendation engines
database/              # SQLite layer
reports/               # PDF generation
config/                # Settings & tokens
utils/                 # Cross-cutting utilities
assets/                # Demo datasets
exports/reports/       # Generated PDFs
```

---

## Configuration

Copy `.env.example` to `.env`:

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Primary AI provider (optional) |
| `OLLAMA_BASE_URL` | Local Ollama server |
| `FORECASTIQ_DB_PATH` | SQLite database path |
| `AI_PROVIDER_ORDER` | Provider chain order |

Without API keys, the **rule-based AI engine** runs automatically.

---

## Documentation

- [DATASET_FORMAT_GUIDE.md](DATASET_FORMAT_GUIDE.md) — file format & column mapping
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) — local, Docker, Streamlit Cloud
- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) — judge-friendly summary
- [development_log.md](development_log.md) — build history

---

## Future Roadmap

- User authentication & multi-tenant SQLite/Postgres
- Random Forest / XGBoost forecast models
- OpenAI / Gemini AI providers
- HTML/PPTX report formats
- Cloud deployment templates (AWS/GCP)
- Scheduled forecast refresh & email reports

---

## License

Proprietary — ForecastIQ AI. All rights reserved.
