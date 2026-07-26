"""n8n Code node — Prepare Prior Day Image (Python).

Loads the prior drawn JPEG as-is (no resize) and exposes image_base64 for Attach.
Today's labeled chart stays separate as binary.chart.
"""

import base64
import json
from pathlib import Path

item = dict(_items[0]["json"])

prior = None
try:
    parsed = json.loads(str(item.get("stdout") or "{}").strip())
    if isinstance(parsed, dict) and isinstance(parsed.get("prior"), dict):
        prior = parsed["prior"]
except Exception:
    prior = None

if prior is None and isinstance(item.get("prior"), dict):
    prior = item["prior"]

if prior:
    image_path = str(prior.get("image_path") or "").strip()
    p = Path(image_path) if image_path else None
    image_base64 = None
    image_bytes = None
    if p and p.is_file() and p.stat().st_size >= 1024:
        raw = p.read_bytes()
        image_base64 = base64.b64encode(raw).decode("ascii")
        image_bytes = len(raw)

    prior = {
        "as_of_date": prior.get("as_of_date"),
        "summary": prior.get("summary"),
        "image_path": prior.get("image_path"),
        "execution_id": prior.get("execution_id"),
        "image_base64": image_base64,
        "image_bytes": image_bytes,
        "image_resized": False,
    }

item["prior"] = prior
item["stdout"] = json.dumps(
    {
        "ok": True,
        "prior": (
            None
            if prior is None
            else {
                "as_of_date": prior.get("as_of_date"),
                "summary": prior.get("summary"),
                "image_path": prior.get("image_path"),
                "execution_id": prior.get("execution_id"),
                "has_image": bool(prior.get("image_base64")),
                "image_bytes": prior.get("image_bytes"),
            }
        ),
    }
)
return [{"json": item}]
