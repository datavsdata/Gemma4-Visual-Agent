"""n8n Code node snippet — Python (Native) runner.

Paste into Label Candles (Language = Python).
Attaches binary JPEG as `chart` for the Executions image viewer.
"""

from n8n_candle.candle_label_node import run

item = _items[0]["json"]
if isinstance(item.get("body"), dict):
    item = {**item, **item["body"]}

result = run(item)
b64 = result.pop("crop_b64", "") or ""
name = result.get("cropped_image_name") or "chart.jpg"

if item.get("include_image_b64") and b64:
    result["crop_b64"] = b64

out = {"json": result}
if b64:
    out["binary"] = {
        "chart": {
            "data": b64,
            "mimeType": "image/jpeg",
            "fileName": name,
            "fileExtension": "jpg",
        }
    }
return [out]
