"""n8n entry: chart + candles/point_index + draw_commands → annotated chart."""

from __future__ import annotations

import base64
import io
import json
from typing import Any

from PIL import Image

from .point_index import agent_context, build_point_index
from .shape_draw import draw_shapes


def _decode_chart_b64(image_b64: str) -> Image.Image:
    raw = image_b64.strip()
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    data = base64.b64decode(raw)
    img = Image.open(io.BytesIO(data))
    return img.convert("RGB")


def _extract_draw_commands(data: dict[str, Any]) -> list[dict[str, Any]]:
    cmds = data.get("draw_commands")
    if isinstance(cmds, str):
        cmds = json.loads(cmds)
    if isinstance(cmds, dict) and "draw_commands" in cmds:
        cmds = cmds["draw_commands"]
    if not isinstance(cmds, list):
        raise ValueError("draw_commands must be a list")
    return cmds


def run(item: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """
    Overlay agent geometry on the Phase 1 chart.

    Required:
      - draw_commands
      - candles or point_index
      - crop_b64 (or chart_b64 / image_b64)

    Returns json fields + binary-ready crop_b64; caller may attach n8n binary.
    """
    data = dict(item or {})
    data.update({k: v for k, v in kwargs.items() if v is not None})

    commands = _extract_draw_commands(data)

    point_index = data.get("point_index")
    candles = data.get("candles")
    if not isinstance(point_index, dict) or not point_index:
        if not isinstance(candles, list) or not candles:
            raise ValueError("candles or point_index is required")
        point_index = build_point_index(candles)
    else:
        # normalize keys to list[int]
        point_index = {
            str(k): [int(v[0]), int(v[1])]
            for k, v in point_index.items()
            if isinstance(v, (list, tuple)) and len(v) >= 2
        }

    chart_b64 = (
        data.get("crop_b64")
        or data.get("chart_b64")
        or data.get("image_b64")
        or kwargs.get("chart_b64")
    )
    if not chart_b64:
        raise ValueError("crop_b64 / chart_b64 is required")

    img = _decode_chart_b64(str(chart_b64))
    plot_bbox = data.get("plot_bbox")
    theme = data.get("theme")

    out_img, applied, errors = draw_shapes(
        img,
        commands,
        point_index,
        plot_bbox=plot_bbox if isinstance(plot_bbox, list) else None,
        theme_name=theme,
    )

    buf = io.BytesIO()
    out_img.save(buf, format="JPEG", quality=92)
    out_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    stem = str(
        data.get("output_stem")
        or str(data.get("cropped_image_name") or "chart").removesuffix(".jpg")
    )
    if not stem.endswith("_drawn"):
        stem = f"{stem}_drawn"
    file_name = f"{stem}.jpg"

    result: dict[str, Any] = {
        "summary": data.get("summary"),
        "nse_code": data.get("nse_code"),
        "theme": theme or data.get("theme"),
        "plot_bbox": plot_bbox,
        "image_width": out_img.width,
        "image_height": out_img.height,
        "candle_count": data.get("candle_count")
        or (len(candles) if isinstance(candles, list) else None),
        "candles": candles,
        "point_index": point_index,
        "agent_context": agent_context(candles) if isinstance(candles, list) else None,
        "draw_commands": commands,
        "applied": applied,
        "errors": errors,
        "cropped_image_name": file_name,
        "output_stem": stem,
        "crop_b64": out_b64,
    }

    # n8n-friendly binary payload (Code node can attach as item.binary.chart)
    result["_binary_chart"] = {
        "data": out_b64,
        "mimeType": "image/jpeg",
        "fileName": file_name,
        "fileExtension": "jpg",
    }
    return result


def run_as_n8n_item(item: dict[str, Any], chart_b64: str | None = None) -> dict[str, Any]:
    """Return {json, binary} for a native Python Code node."""
    payload = dict(item)
    if chart_b64:
        payload["crop_b64"] = chart_b64
    result = run(payload)
    binary = result.pop("_binary_chart", None)
    include_b64 = bool(payload.get("include_image_b64"))
    if not include_b64:
        result.pop("crop_b64", None)
    out: dict[str, Any] = {"json": result}
    if binary:
        out["binary"] = {"chart": binary}
    return out
