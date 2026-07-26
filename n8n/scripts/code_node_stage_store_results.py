# Stage annotated chart for DuckDB insert (files under /data/charts).

import base64
import csv
from pathlib import Path

item = dict(_items[0]["json"])
binary = _items[0].get("binary") or {}
chart = binary.get("chart") or binary.get("data") or {}
b64 = chart.get("data") if isinstance(chart, dict) else ""
summary = (item.get("summary") or "").strip()
nse_code = str(item.get("nse_code") or "").strip().upper()
as_of = str(item.get("date") or item.get("as_of_date") or "").strip()
from_date = str(item.get("from") or item.get("from_date") or "")
to_date = str(item.get("to") or item.get("to_date") or "")
review_comments = str(item.get("review_comments") or "").strip()
signal = str(item.get("signal") or "HOLD").strip().upper()
if signal not in ("BUY", "SELL", "HOLD"):
    signal = "HOLD"
try:
    confidence = int(item.get("confidence") if item.get("confidence") is not None else 0)
except (TypeError, ValueError):
    confidence = 0
confidence = max(0, min(100, confidence))
execution_id = str(item.get("execution_id") or "").strip()
out = {"json": dict(item), "binary": binary}
if not summary or not b64 or not nse_code or not as_of:
    out["json"]["stored"] = False
    out["json"]["_store_skip"] = True
    return [out]
charts = Path("/data/charts")
charts.mkdir(parents=True, exist_ok=True)
stem = f"{nse_code}_{as_of}"
image_path = charts / f"{stem}.jpg"
meta_path = charts / f"{stem}.meta.csv"
image_path.write_bytes(base64.b64decode(b64))
with meta_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            "nse_code",
            "as_of_date",
            "from_date",
            "to_date",
            "summary",
            "image_path",
            "review_comments",
            "signal",
            "confidence",
            "execution_id",
        ],
    )
    w.writeheader()
    w.writerow(
        {
            "nse_code": nse_code,
            "as_of_date": as_of,
            "from_date": from_date,
            "to_date": to_date,
            "summary": summary,
            "image_path": str(image_path),
            "review_comments": review_comments,
            "signal": signal,
            "confidence": confidence,
            "execution_id": execution_id,
        }
    )
out["json"]["image_path"] = str(image_path)
out["json"]["meta_path"] = str(meta_path)
out["json"]["_store_skip"] = False
return [out]
