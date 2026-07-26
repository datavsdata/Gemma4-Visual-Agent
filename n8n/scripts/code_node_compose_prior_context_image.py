"""n8n Code node — Compose Prior Context Image (Python, Pillow).

If binary.prior_chart and binary.chart both exist, stitch them into one JPEG
(left=prior, right=today) and replace binary.chart. gemma4 then receives a
single image containing both sessions. Draw Shapes still uses Label Candles.
"""

import base64
import io

from PIL import Image, ImageDraw, ImageFont

item = dict(_items[0]["json"])
binary = dict(_items[0].get("binary") or {})

PANEL_W, PANEL_H = 640, 360
LABEL_H = 22
JPEG_QUALITY = 40


def _from_binary(entry):
    if not isinstance(entry, dict):
        return None
    b64 = entry.get("data")
    if not b64:
        return None
    try:
        return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    except Exception:
        return None


def _fit(im: Image.Image, w: int, h: int) -> Image.Image:
    im = im.copy()
    im.thumbnail((w, h))
    canvas = Image.new("RGB", (w, h), (245, 245, 245))
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return canvas


def _panel(im: Image.Image, title: str) -> Image.Image:
    body = _fit(im, PANEL_W, PANEL_H)
    out = Image.new("RGB", (PANEL_W, PANEL_H + LABEL_H), (32, 32, 32))
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((6, 4), title, fill=(240, 240, 240), font=font)
    out.paste(body, (0, LABEL_H))
    return out


today = _from_binary(binary.get("chart") or binary.get("data"))
prior = _from_binary(binary.get("prior_chart"))

if today is not None and prior is not None:
    as_of = ""
    pd = item.get("prior_day") if isinstance(item.get("prior_day"), dict) else {}
    if pd:
        as_of = str(pd.get("as_of_date") or "").strip()
    left = _panel(prior, f"Prior {as_of}".strip() or "Prior day")
    right = _panel(today, f"Today {item.get('date') or ''}".strip() or "Today")
    canvas = Image.new("RGB", (left.width + right.width + 4, left.height), (20, 20, 20))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (left.width + 4, 0))
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    raw = buf.getvalue()
    binary = {
        "chart": {
            "data": base64.b64encode(raw).decode("ascii"),
            "mimeType": "image/jpeg",
            "fileName": "prior_today_composite.jpg",
            "fileExtension": "jpg",
        }
    }
    item["prior_composite"] = {
        "image_bytes": len(raw),
        "image_size": list(canvas.size),
    }
elif "prior_chart" in binary:
    # Prefer a single image: drop prior if we could not composite.
    binary = {k: v for k, v in binary.items() if k != "prior_chart"}
    item["prior_composite"] = None

out = {"json": item}
if binary:
    out["binary"] = binary
return [out]
