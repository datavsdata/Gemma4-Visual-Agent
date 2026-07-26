# n8n Python Code — Fetch OHLC as-of date from tips CSV.
# If as-of date missing for symbol → {_skip: true}. Else last 200 bars as locked csv_text.
# Adds SMA150 (Close SMA) on full history before trim. Peak/swing labels are added later
# by the Peak Analysis node (uses csv_text_full for lookback).
# Parse dates manually (runner may disallow the private _strptime module).

import csv
from datetime import date
from pathlib import Path

CSV_PATH = Path("/data/tips_5years.csv")
MAX_BARS = 200
SMA_PERIOD = 150

_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def parse_iso(s):
    parts = str(s).strip().split("-")
    if len(parts) != 3:
        raise ValueError(s)
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def parse_nse(s):
    parts = str(s).strip().split("-")
    if len(parts) != 3:
        raise ValueError(s)
    mon = _MONTHS.get(parts[1])
    if mon is None:
        raise ValueError(s)
    return date(int(parts[2]), mon, int(parts[0]))


def fmt_nse(d):
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{d.day:02d}-{names[d.month - 1]}-{d.year}"


item = dict(_items[0]["json"])
nse_code = str(item.get("nse_code") or "").strip().upper()
as_of_s = str(item.get("date") or "").strip()


def skip(reason):
    return [{"json": {**item, "nse_code": nse_code, "date": as_of_s, "_skip": True, "_skip_reason": reason}}]


if not nse_code or not as_of_s:
    return skip("missing nse_code or date")

try:
    as_of = parse_iso(as_of_s)
except ValueError:
    return skip("invalid as-of date " + as_of_s)

if not CSV_PATH.is_file():
    raise FileNotFoundError("CSV not found: " + str(CSV_PATH))


def parse_num(raw):
    return float(str(raw).strip().replace(",", "").replace('"', ""))


rows = []
with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    field_map = {(h or "").strip(): h for h in (reader.fieldnames or [])}

    def col(*names):
        for n in names:
            if n in field_map:
                return field_map[n]
        raise KeyError(names)

    c_sym = col("Symbol")
    c_date = col("Date")
    c_series = col("Series")
    c_open = col("Open Price")
    c_high = col("High Price")
    c_low = col("Low Price")
    c_close = col("Close Price")
    c_prev = col("Prev Close")
    c_ltp = col("Last Price")
    c_vwap = col("Average Price")
    c_vol = col("Total Traded Quantity")
    try:
        c_val = col("Turnover ₹", "Turnover")
    except KeyError:
        c_val = None
    c_tr = col("No. of Trades")

    for raw in reader:
        sym = str(raw.get(c_sym) or "").strip().upper()
        if sym != nse_code:
            continue
        try:
            dt = parse_nse(str(raw.get(c_date) or "").strip())
        except ValueError:
            continue
        if dt > as_of:
            continue
        rows.append(
            (
                dt,
                {
                    "DATE": fmt_nse(dt),
                    "SERIES": str(raw.get(c_series) or "EQ").strip() or "EQ",
                    "OPEN": parse_num(raw[c_open]),
                    "HIGH": parse_num(raw[c_high]),
                    "LOW": parse_num(raw[c_low]),
                    "PREV. CLOSE": parse_num(raw[c_prev]),
                    "LTP": parse_num(raw[c_ltp]),
                    "CLOSE": parse_num(raw[c_close]),
                    "VWAP": parse_num(raw[c_vwap]) if str(raw.get(c_vwap) or "").strip() else "",
                    "52W H": "",
                    "52W L": "",
                    "VOLUME": parse_num(raw[c_vol]) if str(raw.get(c_vol) or "").strip() else "",
                    "VALUE": parse_num(raw[c_val]) if c_val and str(raw.get(c_val) or "").strip() else "",
                    "NO. OF  TRADES": parse_num(raw[c_tr]) if str(raw.get(c_tr) or "").strip() else "",
                    "SMA150": "",
                },
            )
        )

if not any(dt == as_of for dt, _ in rows):
    return skip("as-of date not in CSV")

rows.sort(key=lambda t: t[0])
bars = [r for _, r in rows]

closes = [float(r["CLOSE"]) for r in bars]
for i, r in enumerate(bars):
    if i + 1 < SMA_PERIOD:
        r["SMA150"] = ""
    else:
        window = closes[i + 1 - SMA_PERIOD : i + 1]
        r["SMA150"] = round(sum(window) / SMA_PERIOD, 4)

HEADER = (
    "DATE,SERIES,OPEN,HIGH,LOW,PREV. CLOSE,LTP,CLOSE,VWAP,52W H,52W L,"
    "VOLUME,VALUE,NO. OF  TRADES,SMA150"
)
keys = [
    "DATE", "SERIES", "OPEN", "HIGH", "LOW", "PREV. CLOSE", "LTP", "CLOSE",
    "VWAP", "52W H", "52W L", "VOLUME", "VALUE", "NO. OF  TRADES", "SMA150",
]


def cell(v):
    if v is None or v == "":
        return ""
    s = str(v)
    if any(ch in s for ch in '",\n'):
        return '"' + s.replace('"', '""') + '"'
    return s


def bars_to_csv(bar_list):
    lines = [HEADER]
    for r in bar_list:
        lines.append(",".join(cell(r[k]) for k in keys))
    return "\n".join(lines) + "\n"


csv_text_full = bars_to_csv(bars)
chart_bars = bars[-MAX_BARS:] if len(bars) > MAX_BARS else bars
csv_text = bars_to_csv(chart_bars)

return [
    {
        "json": {
            **item,
            "nse_code": nse_code,
            "date": as_of_s,
            "from": item.get("from"),
            "to": item.get("to"),
            "theme": item.get("theme") or "tradingview_light",
            "source_name": item.get("source_name") or nse_code.lower(),
            "csv_text": csv_text,
            "csv_text_full": csv_text_full,
            "bar_count": len(chart_bars),
            "bar_count_full": len(bars),
            "_skip": False,
        }
    }
]
