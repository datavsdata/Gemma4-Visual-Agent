"""n8n Code node snippet — Label Candles step in the Phase 2 draw workflow.

Paste into Label Candles (Language = Python).
Expects Peak Analysis upstream: csv_text (+ optional swings[]) for H/L/HH/… overlays.
"""

from n8n_candle.candle_label_node import run
from n8n_candle.point_index import agent_context, build_point_index

item = _items[0]["json"]
if isinstance(item.get("body"), dict):
    item = {**item, **item["body"]}

result = run(item)
result["point_index"] = build_point_index(result["candles"])
result["agent_context"] = agent_context(result["candles"])

# Keep peak-analysis metadata for downstream / debugging
for k in ("date", "from", "to", "execution_id", "swings", "swing_count", "peak_analysis"):
    if item.get(k) is not None:
        result[k] = item[k]

# Pass through agent geometry (webhook body or prior node)
if item.get("draw_commands") is not None:
    result["draw_commands"] = item["draw_commands"]

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
