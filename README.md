A fast, minimal stock dashboard that fetches **live prices and historical data** (1D–5Y+) from Yahoo Finance, renders interactive charts with **Chart.js**, and logs market snapshots to **MySQL/DuckDB** for analysis. Built for clarity and reproducibility—ideal for coursework and portfolio demos.

---

## Features
- Live price banner for tickers: `AAPL, NVDA, MSFT, META, TSLA, AMZN, AMD, GOOG, PLTR` (configurable)
- Multi-timeframe charts: **1D, 1W, 1M, 3M, 6M, 1Y, 3Y, 5Y, All**
- Company name → ticker resolution (\"Apple\" → `AAPL`)
- Server-side caching with sensible TTLs to avoid rate-limits
- Persistent logging to **MySQL** (prod) and **DuckDB** (local/offline)
- Clean API: `/api/price`, `/api/history`, `/api/resolve`
- One-click deploy to **Railway**; local dev via **Docker Compose** or plain `venv`
