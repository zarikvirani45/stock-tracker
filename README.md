A fast, minimal stock dashboard that fetches live and historical data (1D–5Y+) from Yahoo Finance, renders interactive charts with Chart.js, and captures user interaction data (searches, sessions, engagement) in MySQL/DuckDB.

Designed as a data-driven application to enable product analytics, user behavior insights, and system performance monitoring.

---

## Features
- Live price banner for tickers: `AAPL, NVDA, MSFT, META, TSLA, AMZN, AMD, GOOG, PLTR` (configurable)
- Multi-timeframe charts: **1D, 1W, 1M, 3M, 6M, 1Y, 3Y, 5Y, All**
- Company name → ticker resolution ("Apple" → `AAPL`)
- Server-side caching with optimized TTLs to reduce API load and latency
- Persistent logging of user interaction and behavioral data to MySQL (prod) and DuckDB (local/offline)
- Clean API: `/api/price`, `/api/history`, `/api/resolve`
- One-click deployment via **Railway**; local development with **Docker Compose** or `venv`

This application includes backend instrumentation to capture and analyze user interactions for product/UX insights.

### Data Captured
- Stock search queries (symbol, timestamp, selected time range)
- Page visits and session activity
- User interaction events (e.g., searches, page loads)

### Database Design
- `stock_searches`: tracks user search behavior and engagement patterns
- `visits`: logs session-level activity
- `user_logs`: captures granular interaction events

### Analytical Use Cases
- Identify high-frequency search patterns and user preferences
- Analyze engagement trends across time and features
- Detect potential drop-off points in user workflows
- Inform data-driven UX and feature optimization decisions
