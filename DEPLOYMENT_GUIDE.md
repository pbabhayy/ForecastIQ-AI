# Deployment Guide

Production deployment instructions for ForecastIQ AI.

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | **3.11 or 3.12** (required for Prophet wheels) |
| OS | Windows, macOS, or Linux |
| RAM | 4 GB minimum (8 GB recommended) |
| Disk | ~500 MB for dependencies + SQLite/PDF exports |

---

## Local Development

### 1. Clone and create virtual environment

```bash
cd ai-forecasting-platform
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Prophet on Windows:** If `pip install prophet` fails, install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) or use Python 3.11/3.12 with prebuilt wheels.

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_key_here          # optional
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
FORECASTIQ_DB_PATH=database/forecastiq.db
AI_PROVIDER_ORDER=groq,ollama,rule_based
LOG_LEVEL=INFO
```

### 4. Start the application

```bash
streamlit run app.py
```

Browser: `http://localhost:8501`

---

## Groq Configuration

1. Create an API key at [console.groq.com](https://console.groq.com)
2. Set `GROQ_API_KEY` in `.env`
3. Optional: change `GROQ_MODEL` (default: `llama-3.1-8b-instant`)

If Groq is unavailable, the app falls back to Ollama, then the rule-based engine.

---

## Ollama Configuration

1. Install [Ollama](https://ollama.com)
2. Pull a model: `ollama pull llama3.1`
3. Ensure Ollama is running: `ollama serve`
4. Set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `.env`

Verify: Settings page shows **Ollama · Connected**.

---

## SQLite Configuration

Default path: `database/forecastiq.db`

Override with `FORECASTIQ_DB_PATH` in `.env`. The directory is created automatically.

**Persisted data:**
- Dataset uploads
- Analytics snapshots
- Forecast runs
- AI insight runs
- Generated report metadata

**Generated PDFs:** `exports/reports/`

Ensure these directories are writable and backed up if needed.

---

## Streamlit Cloud

1. Push repository to GitHub
2. Connect at [share.streamlit.io](https://share.streamlit.io)
3. Set main file: `app.py`
4. Python version: **3.12**
5. Add secrets (Settings → Secrets):

```toml
GROQ_API_KEY = "your-key"
FORECASTIQ_DB_PATH = "database/forecastiq.db"
```

**Note:** Ollama is not available on Streamlit Cloud. AI chain resolves to Groq → rule-based.

**Note:** Prophet may increase cold-start time; consider `packages.txt` if needed.

---

## Docker (Optional)

Example `Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:

```bash
docker build -t forecastiq-ai .
docker run -p 8501:8501 -v forecastiq-data:/app/database forecastiq-ai
```

Mount volumes for `database/` and `exports/` to persist data.

---

## Manual Test Checklist

After deployment, verify:

- [ ] Home page loads with premium theme
- [ ] Upload `assets/sample_dataset_extended.csv`
- [ ] Column mapping displayed correctly
- [ ] Business Analytics shows KPIs and charts
- [ ] Forecasting generates Prophet + comparison
- [ ] AI Insights generates (rule-based without API keys)
- [ ] Reports generates and downloads PDF
- [ ] SQLite history shows on Reports page
- [ ] Settings shows provider/database status

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `No module named 'prophet'` | Use Python 3.11/3.12; reinstall requirements |
| Prophet install fails on Windows | Install C++ build tools or use WSL/Linux |
| `No module named 'pandas'` | Activate venv; `pip install -r requirements.txt` |
| Forecast fails — insufficient data | Use 6+ monthly rows; try extended sample |
| Groq errors | Check API key; app falls back automatically |
| Ollama not connected | Run `ollama serve`; verify URL in Settings |
| Database warning | Check write permissions on `database/` folder |
| PDF export fails | Ensure `exports/reports/` is writable |
| Upload re-processes every click | Fixed in v1.0 — refresh if on older build |
| Blank charts | Upload data first; check browser console |

---

## Logs

Application logs write to:

```
logs/forecastiq.log
```

Set verbosity with `LOG_LEVEL=DEBUG` in `.env`.

---

## Production Recommendations

- Run behind HTTPS reverse proxy (nginx, Caddy)
- Back up `database/` and `exports/` regularly
- Set `LOG_LEVEL=INFO` in production
- Do not commit `.env` or `*.db` files
- Pin Python version in deployment environment
- Monitor disk usage for PDF exports and SQLite growth
