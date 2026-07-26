"""Load OHLC+volume from NSE-style equity CSV (locked schema going forward).

Expected columns (header, UTF-8 with optional BOM):

  DATE,SERIES,OPEN,HIGH,LOW,PREV. CLOSE,LTP,CLOSE,VWAP,52W H,52W L,VOLUME,VALUE,NO. OF  TRADES

Notes:
  - DATE is DD-Mon-YYYY (e.g. 20-Jul-2026)
  - Numbers may use Indian grouping commas (e.g. 99,57,579)
  - Rows are often newest-first; we sort oldest→newest for charting
  - Mapped fields: date, open, high, low, close, volume
  - NSE code comes from the CSV filename stem (e.g. sagility.csv → SAGILITY)
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from .swing_structure import normalize_swing


# Locked header names (after BOM strip / normalize)
REQUIRED = ("DATE", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME")

DATE_FMT = "%d-%b-%Y"


def nse_code_from_filename(path: str | Path) -> str:
    """NSE symbol from CSV filename: sagility.csv → SAGILITY."""
    return Path(path).stem.strip().upper()


def _norm_header(name: str) -> str:
    return name.replace("\ufeff", "").strip().upper()


def parse_number(raw: str | None) -> float:
    """Parse '41.76' or Indian-grouped '99,57,579' / '41,18,67,355.12'."""
    if raw is None:
        raise ValueError("missing number")
    s = str(raw).strip().replace(",", "").replace('"', "")
    if not s:
        raise ValueError("empty number")
    return float(s)


def parse_date(raw: str) -> str:
    """Normalize DATE to ISO YYYY-MM-DD (stable for JSON)."""
    dt = datetime.strptime(str(raw).strip(), DATE_FMT)
    return dt.strftime("%Y-%m-%d")


def _parse_reader(
    reader: csv.DictReader,
    *,
    source: str,
    max_bars: int | None,
) -> list[dict[str, Any]]:
    if not reader.fieldnames:
        raise ValueError(f"CSV has no header: {source}")

    key_map = {_norm_header(h): h for h in reader.fieldnames}
    missing = [c for c in REQUIRED if c not in key_map]
    if missing:
        raise ValueError(f"CSV missing columns {missing}; got {list(reader.fieldnames)}")

    rows: list[tuple[datetime, dict[str, Any]]] = []
    for i, raw in enumerate(reader):
        try:
            date_s = raw[key_map["DATE"]].strip()
            dt = datetime.strptime(date_s, DATE_FMT)
            o = parse_number(raw[key_map["OPEN"]])
            h = parse_number(raw[key_map["HIGH"]])
            l = parse_number(raw[key_map["LOW"]])
            c = parse_number(raw[key_map["CLOSE"]])
            vol = parse_number(raw[key_map["VOLUME"]])
        except (KeyError, ValueError) as e:
            raise ValueError(f"{source} row {i + 2}: {e}") from e
        row: dict[str, Any] = {
            "date": dt.strftime("%Y-%m-%d"),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": vol,
        }
        if "SMA150" in key_map:
            raw_sma = str(raw.get(key_map["SMA150"]) or "").strip()
            if raw_sma:
                try:
                    row["sma150"] = parse_number(raw_sma)
                except ValueError:
                    pass
        if "SWING" in key_map:
            swing = normalize_swing(raw.get(key_map["SWING"]))
            if swing:
                row["swing"] = swing
        rows.append((dt, row))

    if not rows:
        raise ValueError(f"CSV has no data rows: {source}")

    rows.sort(key=lambda t: t[0])
    candles = [r for _, r in rows]
    if max_bars is not None and len(candles) > max_bars:
        candles = candles[-max_bars:]
    return candles


def load_ohlc_text(
    text: str,
    *,
    source: str = "csv_text",
    max_bars: int | None = None,
) -> list[dict[str, Any]]:
    """Parse NSE equity CSV from a string (webhook / Code node body)."""
    f: TextIO = io.StringIO(text.lstrip("\ufeff"))
    return _parse_reader(csv.DictReader(f), source=source, max_bars=max_bars)


def load_ohlc_csv(path: str | Path, max_bars: int | None = None) -> list[dict[str, Any]]:
    """
    Read NSE equity CSV → list of {date, open, high, low, close, volume},
    chronological (oldest first). If max_bars is set, keep the last N sessions.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV not found: {path}")

    with path.open(newline="", encoding="utf-8-sig") as f:
        return _parse_reader(csv.DictReader(f), source=path.name, max_bars=max_bars)
