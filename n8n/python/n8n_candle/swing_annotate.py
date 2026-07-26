"""Annotate chart bars with structure swing labels from full-history detection."""

from __future__ import annotations

from typing import Any

from .pv_detect import (
    condense_events_hl,
    get_event_indexes,
    local_peaks,
    local_valleys,
)
from .swing_structure import classify_swings, normalize_swing

# Defaults aligned with Fetch / Peak Analysis nodes
DEFAULT_COM = 10.0
DEFAULT_BETA = 0.02
DEFAULT_MIN_PERIODS = 10
DEFAULT_MAX_BARS = 200
DEFAULT_PIVOT_K = 3


def detect_and_classify(
    candles: list[dict[str, Any]],
    *,
    com: float = DEFAULT_COM,
    beta: float = DEFAULT_BETA,
    min_periods: int = DEFAULT_MIN_PERIODS,
    pivot_k: int = DEFAULT_PIVOT_K,
) -> dict[int, str]:
    """
    Run peak/valley detection, then structure-classify vs prior swings.

    Combines Close EWM events with confirmed local High/Low pivots so shallow
    pullbacks in strong trends (e.g. late-rally HLs) are not missed.
    """
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]

    peaks_e, valleys_e = get_event_indexes(
        closes,
        com=com,
        beta=beta,
        min_periods=min_periods,
        condense_events=True,
        backwards=True,
    )
    peaks_f = local_peaks(highs, pivot_k) if pivot_k > 0 else []
    valleys_f = local_valleys(lows, pivot_k) if pivot_k > 0 else []

    peaks, valleys = condense_events_hl(
        highs,
        lows,
        sorted(set(peaks_e) | set(peaks_f)),
        sorted(set(valleys_e) | set(valleys_f)),
    )
    return classify_swings(candles, peaks, valleys)


def build_swings_for_chart(
    full_candles: list[dict[str, Any]],
    *,
    max_bars: int = DEFAULT_MAX_BARS,
    com: float = DEFAULT_COM,
    beta: float = DEFAULT_BETA,
    min_periods: int = DEFAULT_MIN_PERIODS,
    pivot_k: int = DEFAULT_PIVOT_K,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Detect on full history, return (chart_candles, swings).

    chart_candles = last max_bars with swing set.
    swings = [{index, label, price, kind}] with chart-local index (0 = leftmost).
    """
    labels = detect_and_classify(
        full_candles,
        com=com,
        beta=beta,
        min_periods=min_periods,
        pivot_k=pivot_k,
    )
    offset = max(0, len(full_candles) - max_bars)
    chart = []
    swings: list[dict[str, Any]] = []
    for full_idx in range(offset, len(full_candles)):
        row = dict(full_candles[full_idx])
        chart_idx = full_idx - offset
        label = labels.get(full_idx)
        if label:
            row["swing"] = label
            kind = "peak" if label in {"H", "HH", "LH"} else "valley"
            price = float(row["high"] if kind == "peak" else row["low"])
            swings.append(
                {
                    "index": chart_idx,
                    "label": label,
                    "price": price,
                    "kind": kind,
                    "date": row.get("date"),
                }
            )
        else:
            row.pop("swing", None)
        chart.append(row)
    return chart, swings


def apply_swings_to_candles(
    candles: list[dict[str, Any]],
    swings: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge Peak Analysis swings[] onto candle rows by chart index."""
    if not swings:
        return candles
    by_idx = {}
    for s in swings:
        label = normalize_swing(s.get("label"))
        if not label:
            continue
        try:
            idx = int(s["index"])
        except (KeyError, TypeError, ValueError):
            continue
        by_idx[idx] = label
    out = []
    for i, c in enumerate(candles):
        row = dict(c)
        if i in by_idx:
            row["swing"] = by_idx[i]
        out.append(row)
    return out


def swings_to_csv_column(csv_text: str, swings: list[dict[str, Any]]) -> str:
    """Rewrite csv_text adding/replacing SWING column from swings[]."""
    import csv
    import io

    f = io.StringIO(csv_text.lstrip("\ufeff"))
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        return csv_text
    fieldnames = list(reader.fieldnames)
    # normalize header presence
    swing_key = None
    for h in fieldnames:
        if h.replace("\ufeff", "").strip().upper() == "SWING":
            swing_key = h
            break
    if swing_key is None:
        swing_key = "SWING"
        fieldnames = fieldnames + [swing_key]

    by_idx = {int(s["index"]): normalize_swing(s.get("label")) for s in swings}
    rows = list(reader)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for i, row in enumerate(rows):
        label = by_idx.get(i)
        row[swing_key] = label or ""
        writer.writerow(row)
    return out.getvalue()
