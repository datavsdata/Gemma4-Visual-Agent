#!/usr/bin/env python3
"""Smoke test: Phase 1 chart → draw_commands → Pillow overlay."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from n8n_candle.candle_label_node import run as label_run  # noqa: E402
from n8n_candle.point_index import build_point_index, resolve_ref  # noqa: E402
from n8n_candle.shape_draw_node import run as draw_run  # noqa: E402


def make_ohlc(n: int = 40) -> list[dict]:
    rows = []
    price = 100.0
    for i in range(n):
        o = price
        c = price + ((-1) ** i) * (0.5 + (i % 3) * 0.2)
        h = max(o, c) + 0.8
        l = min(o, c) - 0.8
        rows.append(
            {
                "date": f"2025-01-{(i % 28) + 1:02d}",
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": 1_000_000 + i * 10_000,
            }
        )
        price = c
    return rows


def main() -> int:
    out_dir = ROOT / "testdata"
    out_dir.mkdir(parents=True, exist_ok=True)

    labeled = label_run(
        {
            "candles": make_ohlc(40),
            "theme": "tradingview_light",
            "source_name": "shape_draw_demo",
        }
    )
    assert labeled["candle_count"] == 40
    idx = build_point_index(labeled["candles"])
    assert "c0_l" in idx and "c10_l" in idx
    a = resolve_ref("c0_l", idx)
    b = resolve_ref("c10_l", idx)
    assert a[0] < b[0]

    commands = [
        {
            "shape": "line",
            "from": "c0_l",
            "to": "c10_l",
            "label": "Support",
            "color": "#2962ff",
            "width": 2,
        },
        {
            "shape": "hline",
            "at": "c5_c",
            "label": "Pivot",
            "color": "#e91e63",
            "width": 1,
        },
        {
            "shape": "polyline",
            "points": ["c5_l", "c18_l", "c30_l"],
            "label": "Trend",
            "color": "#26a69a",
            "width": 2,
        },
        {
            "shape": "line",
            "from": "c999_l",
            "to": "c10_l",
            "label": "bad",
        },
    ]

    drawn = draw_run(
        {
            "candles": labeled["candles"],
            "crop_b64": labeled["crop_b64"],
            "plot_bbox": labeled["plot_bbox"],
            "theme": labeled["theme"],
            "nse_code": "DEMO",
            "output_stem": labeled["output_stem"],
            "draw_commands": commands,
            "include_image_b64": True,
        }
    )

    assert len(drawn["applied"]) == 3
    assert any("c999" in e or "unknown" in e for e in drawn["errors"])
    assert drawn["crop_b64"]
    img_path = out_dir / drawn["cropped_image_name"]
    img_path.write_bytes(base64.b64decode(drawn["crop_b64"]))
    assert img_path.stat().st_size > 1000
    print(
        "OK",
        img_path,
        "applied",
        len(drawn["applied"]),
        "errors",
        drawn["errors"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
