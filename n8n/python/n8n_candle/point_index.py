"""Candle label → pixel lookup for the Pillow geometry drawer.

Refs use locked syntax: c{index}_{o|h|l|c}  e.g. c12_l
"""

from __future__ import annotations

import re
from typing import Any

REF_RE = re.compile(r"^c(\d+)_(o|h|l|c)$", re.IGNORECASE)
POINT_KEYS = ("o", "h", "l", "c")


def build_point_index(candles: list[dict[str, Any]]) -> dict[str, list[int]]:
    """Build flat map c{n}_o/h/l/c → [x, y] from Phase 1 candle records."""
    index: dict[str, list[int]] = {}
    for c in candles:
        idx = int(c["index"])
        pts = c.get("points") or {}
        for key in POINT_KEYS:
            if key not in pts:
                continue
            xy = pts[key]
            if not isinstance(xy, (list, tuple)) or len(xy) < 2:
                continue
            index[f"c{idx}_{key}"] = [int(xy[0]), int(xy[1])]
    return index


def parse_ref(ref: str) -> tuple[int, str]:
    """Parse 'c12_l' → (12, 'l'). Raises ValueError if invalid."""
    m = REF_RE.match(str(ref).strip())
    if not m:
        raise ValueError(f"invalid candle ref: {ref!r} (expected c{{n}}_o|h|l|c)")
    return int(m.group(1)), m.group(2).lower()


def resolve_ref(ref: str, point_index: dict[str, list[int]]) -> list[int]:
    """Resolve candle ref to [x, y]. Raises ValueError if missing/invalid."""
    idx, key = parse_ref(ref)
    name = f"c{idx}_{key}"
    if name not in point_index:
        # try exact key as given
        alt = str(ref).strip()
        if alt in point_index:
            pt = point_index[alt]
            return [int(pt[0]), int(pt[1])]
        raise ValueError(f"unknown candle ref: {ref!r}")
    pt = point_index[name]
    return [int(pt[0]), int(pt[1])]


def agent_context(candles: list[dict[str, Any]]) -> str:
    """
    Compact label table for the chat agent (IDs only — no pixels).

    Example line: c12 green hammer o,h,l,c
    """
    lines: list[str] = []
    for c in candles:
        idx = int(c["index"])
        color = c.get("color") or "?"
        pattern = c.get("pattern") or "?"
        pts = c.get("points") or {}
        keys = ",".join(k for k in POINT_KEYS if k in pts)
        swing = c.get("swing")
        suffix = f" {swing}" if swing else ""
        lines.append(f"c{idx} {color} {pattern} {keys}{suffix}")
    return "\n".join(lines)
