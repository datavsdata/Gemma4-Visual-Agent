"""Classify peak/valley indexes into H/L/HH/HL/LH/LL structure labels."""

from __future__ import annotations

from typing import Any, Iterable

VALID_SWINGS = frozenset({"H", "L", "HH", "HL", "LH", "LL"})


def classify_swings(
    candles: list[dict[str, Any]],
    peaks: Iterable[int],
    valleys: Iterable[int],
) -> dict[int, str]:
    """
    Map bar index → structure label.

    Peaks use candle High vs previous peak High → H / HH / LH.
    Valleys use candle Low vs previous valley Low → L / HL / LL.
    """
    labels: dict[int, str] = {}
    prev_peak_high: float | None = None
    for idx in sorted(set(int(i) for i in peaks)):
        if idx < 0 or idx >= len(candles):
            continue
        high = float(candles[idx]["high"])
        if prev_peak_high is None:
            labels[idx] = "H"
        elif high > prev_peak_high:
            labels[idx] = "HH"
        elif high < prev_peak_high:
            labels[idx] = "LH"
        else:
            labels[idx] = "H"
        prev_peak_high = high

    prev_valley_low: float | None = None
    for idx in sorted(set(int(i) for i in valleys)):
        if idx < 0 or idx >= len(candles):
            continue
        low = float(candles[idx]["low"])
        if prev_valley_low is None:
            labels[idx] = "L"
        elif low > prev_valley_low:
            labels[idx] = "HL"
        elif low < prev_valley_low:
            labels[idx] = "LL"
        else:
            labels[idx] = "L"
        prev_valley_low = low

    return labels


def normalize_swing(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if not s or s not in VALID_SWINGS:
        return None
    return s
