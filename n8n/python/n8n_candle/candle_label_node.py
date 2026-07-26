"""OHLC JSON → Pillow chart → {index, color, pattern, points} paired outputs."""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

from .candle_pattern import enrich_candle
from .chart_render import render
from .chart_themes import MAX_BARS
from .ohlc_csv import (
    load_ohlc_csv,
    load_ohlc_text,
    nse_code_from_filename,
)
from .swing_annotate import apply_swings_to_candles



def run(item: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """
    Render OHLC → labels. Input is either:

      - csv_path: NSE equity CSV path inside the runner (e.g. /data/sagility.csv)
        NSE code = filename stem uppercased (sagility.csv → SAGILITY)
      - csv_text: raw CSV string (same schema; set nse_code or source_name)
      - candles: list of {date, open, high, low, close, volume?}

    Each candle out:

      { "index": 125, "color": "green", "pattern": "hammer", "points": {"o":[x,y],"h":[x,y],"l":[x,y],"c":[x,y]} }

    Paired files: {stem}_cropped.jpg + {stem}_cropped.json
    """
    data = dict(item or {})
    data.update({k: v for k, v in kwargs.items() if v is not None})

    theme = data.get("theme")
    width = data.get("width")
    height = data.get("height")
    max_bars = int(data.get("max_bars") or MAX_BARS)

    csv_path = data.get("csv_path") or data.get("csv")
    csv_text = data.get("csv_text")
    raw_candles = data.get("candles")
    source_name = data.get("source_name")
    nse_code = data.get("nse_code") or data.get("symbol")

    if csv_path:
        path = Path(str(csv_path))
        raw_candles = load_ohlc_csv(path, max_bars=max_bars)
        if not source_name:
            source_name = path.stem
        if not nse_code:
            nse_code = nse_code_from_filename(path)
    elif isinstance(csv_text, str) and csv_text.strip():
        name = source_name or nse_code or "chart"
        raw_candles = load_ohlc_text(csv_text, source=str(name), max_bars=max_bars)
        if not source_name:
            source_name = str(name)
        if not nse_code:
            nse_code = nse_code_from_filename(source_name)
    elif isinstance(raw_candles, list) and raw_candles:
        if not source_name:
            source_name = "chart"
        if not nse_code and source_name:
            nse_code = nse_code_from_filename(source_name)
    else:
        raise ValueError("csv_path, csv_text, or candles (non-empty OHLC list) is required")

    # Peak Analysis node output — authoritative swing labels by chart index
    raw_candles = apply_swings_to_candles(raw_candles, data.get("swings"))

    source_name = source_name or "chart"
    nse_code = str(nse_code or source_name).strip().upper()

    rendered = render(
        raw_candles,
        theme_name=theme,
        width=width,
        height=height,
        max_bars=max_bars,
    )

    candles: list[dict[str, Any]] = []
    for c in rendered["candles"]:
        enriched = enrich_candle(
            {
                "index": c["index"],
                "color": c["color"],
                "points": c["points"],
                **({"swing": c["swing"]} if c.get("swing") else {}),
            }
        )
        candles.append(enriched)

    stem = Path(str(source_name)).stem
    pair_stem = stem if stem.endswith("_cropped") else f"{stem}_cropped"

    buf = io.BytesIO()
    rendered["image"].save(buf, format="JPEG", quality=92)
    crop_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    layout = rendered["layout"]
    return {
        "nse_code": nse_code,
        "output_stem": pair_stem,
        "cropped_image_name": f"{pair_stem}.jpg",
        "labels_json_name": f"{pair_stem}.json",
        "theme": rendered["theme"],
        "coord_space": "image",
        "plot_bbox": [
            layout.plot_left,
            layout.plot_top,
            layout.plot_right,
            layout.plot_bottom,
        ],
        "image_width": rendered["image_width"],
        "image_height": rendered["image_height"],
        "candle_count": len(candles),
        "candles": candles,
        "has_volume": bool(rendered.get("has_volume")),
        "crop_b64": crop_b64,
    }


def save_paired_outputs(
    result: dict[str, Any],
    out_dir: str | Path,
) -> dict[str, Path]:
    """
    Write:
      {stem}_cropped.jpg  — rendered chart
      {stem}_cropped.json — { nse_code, image, candles: [ ... ] }
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = result["output_stem"]
    img_path = out_dir / f"{stem}.jpg"
    json_path = out_dir / f"{stem}.json"

    img_path.write_bytes(base64.b64decode(result["crop_b64"]))
    payload = {
        "nse_code": result.get("nse_code"),
        "image": f"{stem}.jpg",
        "image_width": result["image_width"],
        "image_height": result["image_height"],
        "candle_count": result["candle_count"],
        "candles": result["candles"],
    }
    json_path.write_text(json.dumps(payload, indent=2))
    return {"image": img_path, "labels": json_path}


def run_n8n_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"json": run(it.get("json", it))} for it in items]
