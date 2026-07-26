#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-3001}"
UI_PORT="${UI_PORT:-3002}"
PID_FILE="${PID_FILE:-/tmp/chart-analysis-ui.pids}"
LOG_FILE="${LOG_FILE:-/tmp/chart-analysis-ui.log}"

if [[ -z "${CHART_ANALYSIS_DB:-}" ]]; then
  DEFAULT_DB="$ROOT/../pgwhy/data/candle_draw_results.duckdb"
  if [[ -f "$DEFAULT_DB" ]]; then
    export CHART_ANALYSIS_DB="$DEFAULT_DB"
    echo "CHART_ANALYSIS_DB unset; using $CHART_ANALYSIS_DB"
  else
    echo "CHART_ANALYSIS_DB is required. Example:"
    echo "  export CHART_ANALYSIS_DB=/path/to/candle_draw_results.duckdb"
    exit 1
  fi
fi

if [[ ! -f "$CHART_ANALYSIS_DB" ]]; then
  echo "Database not found: $CHART_ANALYSIS_DB"
  exit 1
fi

if pgrep -f "chart-analysis-ui/server/index.js" >/dev/null 2>&1 || pgrep -f "node server/index.js" >/dev/null 2>&1; then
  echo "Chart analysis API may already be running in this directory"
fi

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  echo "Building React app..."
  npm run build
elif [[ ! -d "$ROOT/build" ]]; then
  npm run build
fi

echo "Starting API + static UI on ${API_HOST:-0.0.0.0}:${UI_PORT}..."
nohup env SERVE_STATIC=1 API_PORT="$UI_PORT" API_HOST="${API_HOST:-0.0.0.0}" CHART_ANALYSIS_DB="$CHART_ANALYSIS_DB" \
  node server/index.js >"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

sleep 1
if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Chart Analysis UI started"
  echo "  URL: http://127.0.0.1:${UI_PORT} (local)"
  HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [[ -n "$HOST_IP" ]]; then
    echo "  LAN: http://${HOST_IP}:${UI_PORT}"
  fi
  echo "  DB:  $CHART_ANALYSIS_DB"
  echo "  PID: $(cat "$PID_FILE")"
  echo "  Log: $LOG_FILE"
else
  echo "Failed to start. See $LOG_FILE"
  exit 1
fi
