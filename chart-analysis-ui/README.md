# Chart Analysis UI

React + Express app for browsing stored candle-draw analyses from DuckDB (`chart_analysis` table).

## Prerequisites

- Node.js 18+
- DuckDB file written by the n8n candle-draw workflow (default: `../pgwhy/data/candle_draw_results.duckdb`)

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHART_ANALYSIS_DB` | `../pgwhy/data/candle_draw_results.duckdb` | Path to analysis DuckDB |
| `API_PORT` | `3001` (dev API), `3002` (production script) | Express port |
| `SERVE_STATIC` | unset | Set to `1` to serve production React build |

## Development

```bash
cd chart-analysis-ui
npm install
export CHART_ANALYSIS_DB=/path/to/pgwhy/data/candle_draw_results.duckdb
npm start
```

- API: http://127.0.0.1:3001
- UI: http://localhost:3000 (CRA proxies `/api` to the API)

## Production (single port)

```bash
export CHART_ANALYSIS_DB=/path/to/candle_draw_results.duckdb
./start-chart-analysis-ui.sh
# → http://127.0.0.1:3002
```

## Features

- **Filters:** symbol, `execution_id`, signal (BUY/SELL/HOLD), date range, min confidence
- **Trend charts:** stacked signals by date, confidence line chart
- **Detail pane:** annotated chart JPEG, stage summary, validation review

Filter by execution id from the n8n webhook:

```sql
SELECT * FROM chart_analysis WHERE execution_id = 'req-ping-20260722-001';
```

## API

| Route | Description |
|-------|-------------|
| `GET /api/health` | DB stats |
| `GET /api/facets` | Distinct symbols and execution ids |
| `GET /api/summary?...` | KPI + trend data for filters |
| `GET /api/analyses?...` | Paginated list (no image blob) |
| `GET /api/analyses/:id` | Single analysis metadata |
| `GET /api/analyses/:id/image` | JPEG chart |

## DuckDB concurrency (n8n backtest + UI)

n8n **writes** during the candle-draw pipeline; the UI **reads**. DuckDB allows one writer and multiple **read-only** readers.

- **UI / API:** opens the DB read-only per request (with retries on lock).
- **CLI / DBeaver:** open read-only only while backtest runs:

```bash
duckdb -readonly ../pgwhy/data/candle_draw_results.duckdb
```

If you see `Conflicting lock`, wait a few seconds and retry — n8n releases the lock after each insert.


```bash
npm test
```

Uses `test-db/chart_analysis.duckdb` fixture created by `npm run fixture`.
