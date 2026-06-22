# ForecastIQ AI — Enterprise Architecture

> **AI-Powered Business Forecasting & Decision Intelligence Platform**

This document is the authoritative architectural contract for ForecastIQ AI.
Every implementation step must conform to the boundaries defined here. The
architecture is **modular, SOLID-compliant, AI-provider agnostic,
forecast-model agnostic, visualization-isolated, and deployment-ready**.

---

## Table of Contents
1. [Design Principles](#1-design-principles)
2. [Folder Structure](#2-folder-structure)
3. [Layer Responsibilities](#3-layer-responsibilities)
4. [Data Flow Diagram](#4-data-flow-diagram)
5. [Session State Flow](#5-session-state-flow)
6. [AI Provider Flow](#6-ai-provider-flow)
7. [Forecasting Flow](#7-forecasting-flow)
8. [Database Responsibilities](#8-database-responsibilities)
9. [Canonical Data Contract](#9-canonical-data-contract)
10. [Business Health Score Architecture](#10-business-health-score-architecture)
11. [Design System Architecture](#11-design-system-architecture)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Future Expansion Strategy](#13-future-expansion-strategy)

---

## 1. Design Principles

| Principle | Application |
|-----------|-------------|
| **Single Responsibility** | Every module owns exactly one concern. Pages orchestrate; they never compute. |
| **Open/Closed** | New AI providers and forecast models are added by creating a class + registering it — no edits to existing logic. |
| **Liskov / Interface Segregation** | All providers implement `BaseAIProvider`; all forecasters implement a common forecast-strategy contract. Consumers depend on the interface. |
| **Dependency Inversion** | High-level engines (`insight_engine`, `forecast_manager`) depend on abstractions, not concrete vendors/models. |
| **Isolation of volatility** | Plotly lives only in `visualizations/`; styling only in `config/theme_tokens.py` + `components/theme.py`; SQL only behind `database/history_repository.py`. |
| **Dynamic, never hardcoded** | Every metric, mapping, insight, and forecast is derived at runtime from the uploaded file. |
| **Never fully fails** | AI degrades Groq → Ollama → rule-based; forecasting degrades to simpler models; bad input yields friendly states, never stack traces. |

---

## 2. Folder Structure

```
ai-forecasting-platform/
├── app.py                       # Entry point / shell (home, theme, routing, init)
├── requirements.txt
├── .env.example
├── .gitignore
├── ARCHITECTURE.md
├── development_log.md
├── README.md                    # (Step 7)
│
├── .streamlit/
│   └── config.toml              # Base theme + server config
│
├── pages/                       # MULTIPAGE LAYER — orchestration only
│   ├── 1_Upload_Data.py
│   ├── 2_Business_Analytics.py
│   ├── 3_Forecasting.py
│   ├── 4_AI_Insights.py
│   ├── 5_Reports.py
│   └── 6_Settings.py
│
├── components/                  # PRESENTATION — reusable UI, no business logic
│   ├── theme.py                 # CSS/theme injection
│   ├── cards.py                 # premium KPI cards, gauges, badges
│   ├── sidebar.py               # branded navigation + status pills
│   ├── tables.py                # styled tables
│   ├── loading.py               # skeletons / spinners
│   ├── empty_states.py          # empty-state panels
│   └── error_states.py          # user-friendly error panels
│
├── visualizations/              # VISUALIZATION — ALL Plotly lives here
│   ├── revenue_charts.py
│   ├── forecast_charts.py
│   ├── heatmaps.py
│   ├── kpi_charts.py
│   └── comparison_charts.py
│
├── config/                      # CONFIGURATION — no magic strings/numbers
│   ├── settings.py              # env-driven runtime config
│   ├── constants.py             # canonical fields, synonyms, session keys
│   ├── theme_tokens.py          # color/typography/spacing/chart tokens
│   └── forecast_config.py       # horizons, splits, model hyperparams
│
├── analytics/                   # DOMAIN — analytics
│   ├── processor.py             # clean & prepare canonical frames
│   ├── metrics.py               # KPI computation
│   ├── dataset_profiler.py      # profiling + data-quality
│   ├── health_score.py          # 0–100 business health score
│   └── trend_analyzer.py        # trend / seasonality detection
│
├── forecasting/                 # DOMAIN — model-agnostic forecasting
│   ├── prophet_forecast.py      # Prophet strategy
│   ├── sklearn_forecast.py      # Linear Regression / Random Forest strategies
│   ├── evaluation.py            # MAE / RMSE / MAPE + confidence
│   └── forecast_manager.py      # Manager/Strategy orchestrator
│
├── ai/                          # DOMAIN — provider-agnostic AI
│   ├── base_provider.py         # abstract provider interface
│   ├── groq_provider.py         # PRIMARY provider
│   ├── ollama_provider.py       # SECONDARY provider
│   ├── insight_engine.py        # insights + rule-based fallback
│   └── recommendation_engine.py # recommendations + rule-based fallback
│
├── database/                    # PERSISTENCE — SQLite
│   ├── sqlite_manager.py        # connections + schema lifecycle
│   ├── models.py                # schema + row dataclasses
│   └── history_repository.py    # repository (only SQL touchpoint)
│
├── reports/                     # OUTPUT — reporting
│   ├── report_builder.py        # render-agnostic report model
│   └── pdf_generator.py         # ReportLab PDF renderer
│
├── utils/                       # CROSS-CUTTING
│   ├── column_mapper.py         # fuzzy canonical detection
│   ├── validators.py            # validation + quality
│   ├── session_manager.py       # typed session-state access
│   ├── file_manager.py          # file I/O + artifact paths
│   └── logger.py                # centralized logging
│
├── auth/                        # PLACEHOLDER — future authn/RBAC/multi-tenant
│   └── __init__.py
│
├── logs/                        # centralized log output (runtime)
├── exports/                     # generated artifacts (runtime)
│   ├── reports/
│   ├── charts/
│   └── forecasts/
└── assets/                      # logos, fonts, static assets
```

---

## 3. Layer Responsibilities

| Layer | Package(s) | Responsibility | Must NOT |
|-------|-----------|----------------|----------|
| **Multipage** | `pages/` | Orchestrate: call domain services, render via components/visualizations, read/write session. | Contain analytics/forecast/AI/SQL/chart logic. |
| **Presentation** | `components/` | Reusable, styled UI primitives & states. | Compute metrics or build charts. |
| **Visualization** | `visualizations/` | Build all Plotly figures from prepared data. | Compute data or fetch state. |
| **Configuration** | `config/` | Single source of constants/tokens/settings. | Contain logic. |
| **Analytics** | `analytics/` | Clean, profile, compute metrics/trends/health. | Render UI or charts. |
| **Forecasting** | `forecasting/` | Pluggable models + evaluation behind a manager. | Render UI or charts. |
| **AI** | `ai/` | Provider-agnostic insights/recommendations with fallback. | Bind to one vendor; render UI. |
| **Persistence** | `database/` | SQLite schema + repository API. | Leak SQL outside the repository. |
| **Output** | `reports/` | Build + render professional reports. | Recompute analytics/forecasts. |
| **Cross-cutting** | `utils/` | Mapping, validation, session, files, logging. | Hold domain business rules. |

---

## 4. Data Flow Diagram

```
                 ┌────────────────────────────────────────────────┐
                 │                   pages/ (UI)                   │
                 │  orchestration only — calls services, renders   │
                 └───────────────┬───────────────────┬────────────┘
                                 │                    │
        Upload (CSV/XLSX)        │                    │ render
                                 ▼                    ▼
   utils.file_manager  ──►  utils.validators  ──►  utils.column_mapper
                                 │                    │ (canonical map + confidence)
                                 ▼                    ▼
                         analytics.processor  (clean / dates / dedupe / sort)
                                 │
              ┌──────────────────┼─────────────────────────┐
              ▼                  ▼                          ▼
   analytics.dataset_profiler  analytics.metrics   analytics.trend_analyzer
              │                  │                          │
              └──────────────────┼──────────────┬───────────┘
                                 ▼              ▼
                       analytics.health_score   forecasting.forecast_manager
                                 │                 │ (Prophet / sklearn) + evaluation
                                 └───────┬─────────┘
                                         ▼
                          ai.insight_engine / ai.recommendation_engine
                                         │ (Groq → Ollama → rule-based)
                                         ▼
                              utils.session_manager  (persist working set)
                                         │
                         ┌───────────────┼───────────────┐
                         ▼               ▼               ▼
            database.history_repository  visualizations.*  reports.report_builder
                  (persist history)      (Plotly figures)   → reports.pdf_generator
```

Every arrow is independently fault-tolerant: a failure produces a typed,
user-friendly state and is logged via `utils.logger`.

---

## 5. Session State Flow

State is owned exclusively by `utils.session_manager` (keys defined in
`config.constants`). Pages never touch `st.session_state` directly.

```
        app.py (startup)
            │  session_manager.initialize()  → seed all keys to defaults
            ▼
   ┌──────────────────────── st.session_state ─────────────────────────┐
   │  navigation_state                                                  │
   │  raw_dataset            (Upload page writes)                       │
   │  dataset_metadata       (profiler writes)                          │
   │  column_mapping         (column_mapper writes)                     │
   │  clean_dataset          (processor writes)                         │
   │  analytics              (metrics + trend write)                    │
   │  health_score           (health_score writes)                     │
   │  forecast_results       (forecast_manager writes)                  │
   │  evaluation             (evaluation writes)                        │
   │  insights               (insight_engine writes)                    │
   │  recommendations        (recommendation_engine writes)             │
   │  generated_reports      (report pipeline writes)                   │
   └────────────────────────────────────────────────────────────────────┘
            ▲                  ▲                  ▲                  ▲
       Upload page      Analytics page     Forecasting page     AI/Reports pages
       (writes data)    (reads data,       (reads data,         (read all,
                         writes analytics)  writes forecasts)    write outputs)
```

**Guarantees**
- Single source of truth; consistent keys across all 6 pages.
- Downstream pages render empty-states when a prerequisite key is unset.
- Navigation never loses computed work within a session.

---

## 6. AI Provider Flow

The AI layer is provider-agnostic. Engines depend on `BaseAIProvider`, and a
resolver walks the configured chain. **The system never fully fails.**

```
        ai.insight_engine / ai.recommendation_engine
                        │  build structured prompt (analytics + forecast context)
                        ▼
              ┌───────────────────────┐
              │   Groq Provider        │  PRIMARY
              │   (base_provider impl) │
              └───────────┬───────────┘
                   success │ failure / unavailable / no key
                           ▼
              ┌───────────────────────┐
              │   Ollama Provider      │  SECONDARY (local/self-hosted)
              └───────────┬───────────┘
                   success │ failure / unreachable
                           ▼
              ┌───────────────────────┐
              │  Rule-Based Engine     │  ALWAYS AVAILABLE (deterministic)
              └───────────┬───────────┘
                          ▼
                  Structured insights / recommendations
                  → session_manager → pages render
```

- Provider order is config-driven (`AI_PROVIDER_ORDER`).
- Each provider failure is logged and transparently falls through.
- Adding OpenAI/Gemini later = new `BaseAIProvider` subclass + registration.

---

## 7. Forecasting Flow

```
        Upload
          ▼
    Data Validation            (utils.validators)
          ▼
    Dataset Profiling          (analytics.dataset_profiler)
          ▼
    Forecast Manager           (forecasting.forecast_manager)
          │  selects strategy via config + data characteristics
          ├──────────────► Prophet Forecast        (prophet_forecast.py)
          ├──────────────► Linear Regression        (sklearn_forecast.py)
          ├──────────────► Random Forest            (sklearn_forecast.py)
          └──────────────► [future] XGBoost
          ▼
    Evaluation Layer           (forecasting.evaluation: MAE / RMSE / MAPE + confidence)
          ▼
    Forecast Results           (unified result contract: values, CI, projections)
          ▼
    Session State              (utils.session_manager)
          ▼
    Pages                      (Forecasting / AI Insights / Reports render)
```

- **Manager pattern**: a single orchestration point chooses and runs models.
- **Unified contract**: every model returns the same result shape, so charts,
  evaluation, and reports are model-independent.
- **Horizons**: 1 / 3 / 6 / 12 months (config-driven).

---

## 8. Database Responsibilities

SQLite via a layered persistence design.

| Module | Responsibility |
|--------|----------------|
| `database/sqlite_manager.py` | Connection lifecycle, transactions, schema creation/migration, safe execute/query primitives. |
| `database/models.py` | Table DDL + typed row dataclasses. |
| `database/history_repository.py` | Repository API — the **only** module the rest of the app uses for persistence. |

**Persisted entities**

| Table | Stores |
|-------|--------|
| `datasets` | Dataset metadata (name, rows, columns, date range, detected metrics, quality score, timestamp). |
| `analyses` | Analysis history (computed metrics snapshot, health score). |
| `forecasts` | Forecast history (model used, horizon, accuracy metrics, projections). |
| `insights` | Insight history (provider used, generated insight payloads). |
| `reports` | Report history (path, sections, timestamp). |

Repository pattern keeps SQL isolated → future swap to Postgres/cloud DB does
not touch domain or UI code.

---

## 9. Canonical Data Contract

Uploaded headers are fuzzy-mapped to a fixed canonical schema (logic in
`utils.column_mapper`, synonyms in `config.constants`).

| Canonical field | Type | Required | Example source headers |
|-----------------|------|----------|------------------------|
| `date` | datetime | ✅ | Date, Month, Period, Timestamp |
| `revenue` | numeric | ⚠️ at least one metric | Revenue, Sales, Sales Revenue, Monthly Revenue, Total Revenue |
| `orders` | numeric | optional | Orders, Transactions, Purchases |
| `customers` | numeric | optional | Customers, Clients, Users |
| `expenses` | numeric | optional | Expenses, Costs, Operating Cost |

**Mapping algorithm (conceptual)**
1. Normalize headers (lowercase, strip punctuation/whitespace).
2. Exact/substring match against per-field synonym sets.
3. Fuzzy similarity scoring for near-misses.
4. Resolve conflicts by highest confidence; emit a mapping report with
   confidence scores for user display.

**Rule:** only `date` + ≥1 numeric metric are required. Each optional field
conditionally unlocks its analytics/forecast section. Nothing is hardcoded.

---

## 10. Business Health Score Architecture

A composite **0–100** score computed in `analytics.health_score` from weighted,
normalized components (weights centralized in `config.constants`).

| Component | Signal |
|-----------|--------|
| Revenue Growth | period-over-period revenue growth |
| Forecast Trend | direction/slope of forecasted revenue |
| Customer Growth | customer acquisition trend (if present) |
| Expense Efficiency | revenue-to-expense ratio / margin (if present) |
| Forecast Stability | inverse of forecast volatility / CI width |

```
   normalized components → weighted sum → 0–100 score → band
```

| Score | Band |
|-------|------|
| 80–100 | **Excellent** |
| 60–79  | **Good** |
| 40–59  | **Moderate** |
| 0–39   | **Needs Attention** |

Components present depend on detected fields; weights re-normalize over
available signals so the score is always meaningful.

---

## 11. Design System Architecture

The premium look is token-driven. `config/theme_tokens.py` is the single source
of visual truth; `components/theme.py` injects it as global CSS; the
visualization layer reads chart tokens so charts match the UI.

**Theme Architecture**
```
config/theme_tokens.py  (tokens)
        │
        ├──► components/theme.py   → global CSS for app + pages + components
        └──► visualizations/*      → Plotly layout/template (fonts, palette, grid)
```

**Typography Scale** — single font family; hierarchical sizes
(display → h1 → h2 → h3 → body-lg → body → caption) with defined weights and
line-heights.

**Spacing Scale** — consistent step scale (e.g. 4 / 8 / 12 / 16 / 24 / 32 / 48)
used for padding, gaps, and section rhythm.

**Color Tokens** — neutral surface palette + restrained primary accent +
semantic colors (success / warning / danger / info). Minimal, not colorful.

**Card Design** — soft shadows, rounded corners, generous padding, subtle
borders; KPI cards expose value, label, delta, and optional sparkline.

**Animation Standards** — short, eased transitions (hover lift, fade-in,
skeleton shimmer); motion is subtle and consistent.

**Chart Styling Standards** — shared Plotly template: token palette,
light gridlines, consistent fonts/margins, hover/zoom/pan/export enabled,
responsive layout.

**Inspiration:** Stripe Dashboard · Vercel Analytics · Linear · Notion · Arc —
premium, minimal, modern, elegant, professional.

---

## 12. Deployment Architecture

### 12.1 Local Development
- **Python 3.11 / 3.12** (Prophet & scientific stack wheels available;
  3.14 not yet supported).
- `python -m venv .venv` → activate → `pip install -r requirements.txt`.
- Copy `.env.example` → `.env`; optionally set `GROQ_API_KEY` / Ollama URL.
- `streamlit run app.py`. Without AI keys, the rule-based engine is used.

### 12.2 Streamlit Cloud
- Push repo; set entry point `app.py`.
- Configure secrets (Groq key, etc.) via the Streamlit secrets manager
  (mirrors `.env` keys).
- `pages/` auto-registers as multipage navigation.
- Note: Ollama (local server) is unavailable on Cloud → chain resolves
  Groq → rule-based.

### 12.3 Docker Deployment
- Base image pinned to Python 3.12-slim; install system deps required by
  Prophet (build toolchain), then `requirements.txt`.
- Expose Streamlit port `8501`; mount/persist `database/` and `exports/`
  volumes; inject env via container secrets.
- Image is the portable unit for any container platform.

### 12.4 Future AWS / GCP Compatibility
- Stateless compute + externalizable persistence enables migration:
  - **DB**: swap SQLite → managed Postgres behind `history_repository`.
  - **Storage**: point `exports/` to S3 / GCS via `file_manager`.
  - **AI**: providers already abstracted (add managed-LLM provider).
  - **Runtime**: container runs on ECS/Fargate/Cloud Run unchanged.

---

## 13. Future Expansion Strategy

| Dimension | How it extends without refactoring |
|-----------|-----------------------------------|
| **New AI provider** (OpenAI, Gemini, …) | Implement `BaseAIProvider`, register in resolver, add to `AI_PROVIDER_ORDER`. Engines untouched. |
| **New forecast model** (XGBoost, …) | Add a strategy module conforming to the forecast contract; register in `forecast_manager`. |
| **New visualization** | Add a function in `visualizations/`; reuse shared theme template. |
| **New report format** (HTML/PPTX) | Add a renderer consuming the existing `report_builder` model. |
| **New database** (Postgres/cloud) | Reimplement behind `history_repository`; callers unchanged. |
| **Authentication / multi-tenant** | Build out the reserved `auth/` package; gate pages + scope repository queries by tenant. |
| **New canonical field** | Add synonyms + handling in `config.constants` / `column_mapper`; feature unlocks conditionally. |

The architecture isolates every axis of change behind an interface or a
configuration boundary — new capabilities are additive, not invasive.
```
