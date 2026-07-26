"""Classify single-candle patterns from visual OHLC pixel points."""

from __future__ import annotations

from typing import Any


def classify_pattern(color: str, points: dict[str, list[int]]) -> str:
    """
    Heuristic pattern from crop-local points {o,h,l,c} (y grows downward).

    Returns one of: hammer, inverted_hammer, shooting_star, hanging_man,
    doji, spinning_top, marubozu, standard.
    """
    o = points["o"][1]
    h = points["h"][1]
    l = points["l"][1]
    c = points["c"][1]

    body_top = min(o, c)
    body_bot = max(o, c)
    body = max(body_bot - body_top, 1)
    upper = max(body_top - h, 0)
    lower = max(l - body_bot, 0)
    full = max(l - h, 1)

    body_ratio = body / full
    upper_ratio = upper / full
    lower_ratio = lower / full

    # Doji — very small body
    if body_ratio <= 0.12:
        return "doji"

    # Marubozu — almost no wicks
    if upper_ratio <= 0.08 and lower_ratio <= 0.08:
        return "marubozu"

    # Long lower wick, small upper — hammer family
    if lower >= 2.0 * body and upper <= body:
        return "hammer" if color == "green" else "hanging_man"

    # Long upper wick, small lower — inverted hammer / shooting star
    if upper >= 2.0 * body and lower <= body:
        return "inverted_hammer" if color == "green" else "shooting_star"

    # Both wicks meaningful, modest body
    if upper_ratio >= 0.2 and lower_ratio >= 0.2 and body_ratio <= 0.4:
        return "spinning_top"

    return "standard"


def short_points(index: int, points: dict[str, list[int]]) -> dict[str, list[int]]:
    """Convert c{n}_o/h/l/c map → {o,h,l,c}."""
    return {
        "o": list(points[f"c{index}_o"]),
        "h": list(points[f"c{index}_h"]),
        "l": list(points[f"c{index}_l"]),
        "c": list(points[f"c{index}_c"]),
    }


def enrich_candle(candle: dict[str, Any]) -> dict[str, Any]:
    """Build the public candle record: index, color, pattern, points."""
    idx = int(candle["index"])
    color = candle["color"]
    raw_points = candle["points"]
    # Accept either c{n}_* or already-short keys
    if "o" in raw_points:
        pts = {k: list(raw_points[k]) for k in ("o", "h", "l", "c")}
    else:
        pts = short_points(idx, raw_points)
    return {
        "index": idx,
        "color": color,
        "pattern": classify_pattern(color, pts),
        "points": pts,
        **({"swing": candle["swing"]} if candle.get("swing") else {}),
    }
