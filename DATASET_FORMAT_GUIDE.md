# Dataset Format Guide

ForecastIQ AI accepts **CSV** and **XLSX** files. Columns are detected automatically — you never map fields manually.

---

## Supported File Types

| Format | Extension | Notes |
|--------|-----------|-------|
| CSV | `.csv` | UTF-8 recommended |
| Excel | `.xlsx` | First sheet is read |

Maximum upload size: **50 MB** (configured in `.streamlit/config.toml`).

---

## Required Data

| Requirement | Details |
|-------------|---------|
| **Date column** | At least one time column (see synonyms below) |
| **One metric** | At least one numeric business metric |

Minimum **4 monthly rows** recommended for forecasting; **6+** for reliable evaluation.

---

## Optional Columns

Additional metrics unlock more analytics and forecasts:

| Canonical field | Unlocks |
|-----------------|---------|
| `revenue` | Revenue KPIs, revenue forecast, profit (with expenses) |
| `orders` | Order analytics & forecasting |
| `customers` | Customer growth & forecasting |
| `expenses` | Expense analysis, profit margin, efficiency scoring |

---

## Canonical Schema

Uploaded headers are fuzzy-mapped to these logical fields:

| Canonical | Example source headers |
|-----------|------------------------|
| `date` | Date, Month, Period, Timestamp |
| `revenue` | Revenue, Sales, Sales Revenue, Monthly Revenue, Total Revenue |
| `orders` | Orders, Transactions, Purchases, Order Count |
| `customers` | Customers, Clients, Users, Customer Count |
| `expenses` | Expenses, Costs, Operating Cost, Expenditure, OPEX |

Mapping confidence is shown on the Upload page after ingestion.

---

## Example Datasets (Included)

### `assets/sample_dataset.csv`
- **12 months** (2024)
- Columns: `Date`, `Sales Revenue`, `Orders`, `Customers`, `Operating Cost`
- Good for: analytics, health score, basic AI insights

### `assets/sample_dataset_extended.csv`
- **24 months** (2022–2023)
- Same column layout with realistic growth and seasonality
- Good for: forecasting, model evaluation, full demo flow

---

## Recommended File Layout

```csv
Date,Sales Revenue,Orders,Customers,Operating Cost
2024-01-01,98500,312,1420,62000
2024-02-01,102400,328,1455,63500
...
```

**Tips:**
- Use consistent date formats (ISO `YYYY-MM-DD` works best)
- One row per period (duplicates on the same date are aggregated)
- Avoid completely empty columns
- Numeric metrics should not contain currency symbols in cells

---

## Common Validation Issues

| Issue | What happens |
|-------|--------------|
| Missing date column | Upload rejected — no time axis detected |
| No numeric metrics | Upload rejected |
| Missing values | Warning shown; values forward/backward-filled |
| Duplicate rows | Warning shown; duplicates removed |
| Unparseable dates | Affected rows dropped |
| Future dates | Warning shown; rows kept |
| Negative revenue | Warning shown; data still processed |
| Fewer than 4 monthly points | Analytics OK; forecasting may fail |
| Fewer than 6 monthly points | Forecast runs; evaluation marked low confidence |

---

## Data Quality Score

Calculated 0–100 from:

- Missing data penalty
- Duplicate penalty
- Invalid date penalty
- Empty column penalty

Shown on the Upload page after processing.

---

## What Gets Computed

After upload, ForecastIQ automatically:

1. Detects and maps columns
2. Validates and cleans data
3. Profiles the dataset
4. Computes analytics & health score
5. Prepares data for forecasting (on demand)
6. Feeds AI insights (on demand)
7. Exports PDF reports (on demand)

No manual configuration required.
