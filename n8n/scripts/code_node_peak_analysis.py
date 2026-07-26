"""n8n Code node — Peak Analysis (before Label Candles).

Detects significant peaks/valleys (ben-arnao), classifies H/L/HH/HL/LH/LL
vs prior same-type swings on full history, then annotates the chart window.

Input:  csv_text (chart window), optional csv_text_full (full lookback)
Output: csv_text with SWING column, swings[] for Label Candles placement
"""

from n8n_candle.ohlc_csv import load_ohlc_text
from n8n_candle.swing_annotate import (
    DEFAULT_BETA,
    DEFAULT_COM,
    DEFAULT_MAX_BARS,
    DEFAULT_MIN_PERIODS,
    DEFAULT_PIVOT_K,
    build_swings_for_chart,
    swings_to_csv_column,
)

item = dict(_items[0]["json"])
if isinstance(item.get("body"), dict):
    item = {**item, **item["body"]}

csv_full = item.get("csv_text_full") or item.get("csv_text")
csv_chart = item.get("csv_text") or csv_full
if not isinstance(csv_full, str) or not csv_full.strip():
    raise ValueError("csv_text_full or csv_text is required for Peak Analysis")

com = float(item.get("pv_com") or DEFAULT_COM)
beta = float(item.get("pv_beta") or DEFAULT_BETA)
min_periods = int(item.get("pv_min_periods") or DEFAULT_MIN_PERIODS)
pivot_k = int(item.get("pv_pivot_k") if item.get("pv_pivot_k") is not None else DEFAULT_PIVOT_K)
max_bars = int(item.get("max_bars") or DEFAULT_MAX_BARS)

full_candles = load_ohlc_text(csv_full, source="peak_full")
_chart_candles, swings = build_swings_for_chart(
    full_candles,
    max_bars=max_bars,
    com=com,
    beta=beta,
    min_periods=min_periods,
    pivot_k=pivot_k,
)

# Annotate the chart-window CSV (last max_bars) with SWING for Label Candles
chart_lines = csv_chart.strip().splitlines()
if len(chart_lines) > max_bars + 1:
    # Safety: keep header + last max_bars if someone passed full as csv_text
    csv_chart = "\n".join([chart_lines[0], *chart_lines[-(max_bars):]]) + "\n"

annotated_csv = swings_to_csv_column(csv_chart, swings)

out = {
    **item,
    "csv_text": annotated_csv,
    "swings": swings,
    "swing_count": len(swings),
    "peak_analysis": {
        "com": com,
        "beta": beta,
        "min_periods": min_periods,
        "pivot_k": pivot_k,
        "full_bars": len(full_candles),
        "chart_bars": len(_chart_candles),
        "labels": sorted({s["label"] for s in swings}),
    },
}
return [{"json": out}]
