"""n8n Code node snippet — Draw Shapes (Language = Python).

Attaches annotated JPEG as binary `chart` for the Executions image viewer
(same pattern as Label Candles / Phase 1). Preserves prior_day + prior_chart
for the Validation AI Agent.
"""

from n8n_candle.shape_draw_node import run

item = dict(_items[0]["json"])
if isinstance(item.get("body"), dict):
    item = {**item, **item["body"]}

chart_b64 = item.get("crop_b64")
binary = _items[0].get("binary") or {}
if not chart_b64 and isinstance(binary, dict):
    chart = binary.get("chart") or binary.get("data") or {}
    if isinstance(chart, dict):
        chart_b64 = chart.get("data")

result = run(item, chart_b64=chart_b64)
result.pop("_binary_chart", None)
b64 = result.pop("crop_b64", "") or ""
name = result.get("cropped_image_name") or "chart_drawn.jpg"

for k in ("date", "from", "to", "summary", "execution_id", "prior_day"):
    if item.get(k) is not None and result.get(k) is None:
        result[k] = item[k]

if item.get("include_image_b64") and b64:
    result["crop_b64"] = b64

out = {"json": result}
out_binary = {}
if b64:
    out_binary["chart"] = {
        "data": b64,
        "mimeType": "image/jpeg",
        "fileName": name,
        "fileExtension": "jpg",
    }
# Keep yesterday's drawn chart for Validation AI Agent.
if isinstance(binary, dict) and isinstance(binary.get("prior_chart"), dict):
    out_binary["prior_chart"] = binary["prior_chart"]
if out_binary:
    out["binary"] = out_binary
return [out]
