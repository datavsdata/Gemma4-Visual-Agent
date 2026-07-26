#!/usr/bin/env python3
"""Smoke test: NSE CSV (sagility) + synthetic OHLC → paired jpg + JSON."""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from n8n_candle.candle_label_node import run, save_paired_outputs  # noqa: E402
from n8n_candle.ohlc_csv import load_ohlc_csv  # noqa: E402

SAGILITY_CSV = Path("/home/vgangireddy/workspace/sagility.csv")


def make_synthetic_ohlc(n: int = 200, seed: int = 42) -> list[dict[str, float | str | int]]:
    rng = random.Random(seed)
    price = 100.0
    rows: list[dict[str, float | str | int]] = []
    for i in range(n):
        drift = rng.uniform(-1.8, 1.8)
        open_p = price
        close_p = price + drift
        if i % 47 == 0:
            close_p = open_p + 0.3
            high = max(open_p, close_p) + 0.4
            low = min(open_p, close_p) - 3.5
        elif i % 53 == 0:
            close_p = open_p + 0.05
            high = max(open_p, close_p) + 0.2
            low = min(open_p, close_p) - 0.2
        else:
            high = max(open_p, close_p) + abs(rng.uniform(0.1, 1.2))
            low = min(open_p, close_p) - abs(rng.uniform(0.1, 1.2))
        vol = abs(rng.gauss(1_200_000, 350_000))
        if i % 47 == 0:
            vol *= 2.2
        rows.append(
            {
                "date": f"2025-{(i // 28) % 12 + 1:02d}-{(i % 28) + 1:02d}",
                "open": round(open_p, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close_p, 4),
                "volume": int(vol),
            }
        )
        price = close_p
    return rows


def _assert_candle_shape(c: dict) -> None:
    assert set(c.keys()) >= {"index", "color", "pattern", "points"}
    assert set(c["points"].keys()) == {"o", "h", "l", "c"}
    assert c["pattern"] in {
        "hammer",
        "hanging_man",
        "inverted_hammer",
        "shooting_star",
        "doji",
        "spinning_top",
        "marubozu",
        "standard",
    }
    assert c["points"]["h"][1] <= c["points"]["l"][1]


def test_synthetic(out_dir: Path) -> None:
    ohlc = make_synthetic_ohlc(220)
    result = run(
        {
            "candles": ohlc,
            "theme": "tradingview_light",
            "source_name": "synthetic_candles",
        }
    )
    paths = save_paired_outputs(result, out_dir)
    assert paths["image"].name == "synthetic_candles_cropped.jpg"
    assert result["candle_count"] == 200
    assert result["has_volume"] is True
    _assert_candle_shape(result["candles"][0])
    print("OK synthetic", paths["image"], "sample", result["candles"][0])


def test_sagility_csv(out_dir: Path) -> None:
    assert SAGILITY_CSV.is_file(), f"missing {SAGILITY_CSV}"
    parsed = load_ohlc_csv(SAGILITY_CSV)
    assert parsed[0]["date"] < parsed[-1]["date"]
    assert parsed[-1]["volume"] > 0
    # Indian commas stripped
    assert isinstance(parsed[-1]["volume"], float)

    result = run(
        {
            "csv_path": str(SAGILITY_CSV),
            "theme": "tradingview_light",
        }
    )
    paths = save_paired_outputs(result, out_dir)
    assert paths["image"].name == "sagility_cropped.jpg"
    assert result["nse_code"] == "SAGILITY"
    assert result["candle_count"] == len(parsed)  # < 200 in current file
    assert result["has_volume"] is True
    _assert_candle_shape(result["candles"][0])
    for candle in result["candles"]:
        for pt in candle["points"].values():
            assert all(math.isfinite(v) for v in pt)
    # also write under /tmp for quick preview
    save_paired_outputs(result, Path("/tmp"))
    print(
        "OK sagility",
        paths["image"],
        "count",
        result["candle_count"],
        "sample",
        result["candles"][-1],
    )


def main() -> int:
    out_dir = ROOT / "testdata"
    test_synthetic(out_dir)
    test_sagility_csv(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
