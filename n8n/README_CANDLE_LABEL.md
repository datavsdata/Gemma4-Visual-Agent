# Candle Label Node (Phase 1)

NSE equity CSV (or OHLC JSON) → Pillow TradingView-style chart → labeled candle points.

Uses the **existing n8n stack in [`~/workspace/pgwhy`](/home/vgangireddy/workspace/pgwhy)** (external Python task runners).

## Wire into pgwhy n8n

```bash
cd /home/vgangireddy/workspace/pgwhy
podman compose -f compose.yml build task-runners
podman compose -f compose.yml up -d task-runners
```

That builds `local/n8n-runners-candle:2.30.7` (Pillow + `n8n_candle`) and mounts this package live from:

`Gemma4-Visual-Agent/n8n/python/n8n_candle` → `/opt/runners/task-runner-python/n8n_candle`

Allowlist: [`pgwhy/n8n-task-runners.json`](/home/vgangireddy/workspace/pgwhy/n8n-task-runners.json).

Import [`workflows/candle-label.json`](workflows/candle-label.json) into n8n (https://n8n.dataversusdata.com/).

### Code node (Language = Python)

```python
from n8n_candle.candle_label_node import run

item = items[0]["json"]
if isinstance(item.get("body"), dict):
    item = {**item, **item["body"]}

result = run(item)
if not item.get("include_image_b64"):
    result = {k: v for k, v in result.items() if k != "crop_b64"}
return [{"json": result}]
```

Also: [`scripts/code_node_candle_label.py`](scripts/code_node_candle_label.py).

## Locked CSV schema (going forward)

NSE-style daily equity export — same shape as `sagility.csv`:

```
DATE,SERIES,OPEN,HIGH,LOW,PREV. CLOSE,LTP,CLOSE,VWAP,52W H,52W L,VOLUME,VALUE,NO. OF  TRADES
```

| Field | Source | Notes |
|-------|--------|--------|
| `date` | `DATE` | `DD-Mon-YYYY` → ISO |
| OHLC | `OPEN`/`HIGH`/`LOW`/`CLOSE` | |
| `volume` | `VOLUME` | Indian commas stripped |
| `nse_code` | filename stem | `sagility.csv` → `SAGILITY` |

## Input

Inside the runner:

```json
{
  "csv_path": "/workspace/sagility.csv",
  "theme": "tradingview_light"
}
```

(`pgwhy` compose bind-mounts `~/workspace/sagility.csv` → `/workspace/sagility.csv`. Add more CSV mounts in `pgwhy/compose.yml` as needed.)

Or `csv_text` / `candles`. Optional: `width`, `height`, `max_bars`, `include_image_b64`.

## Local smoke test (no n8n)

```bash
cd n8n && python3 scripts/test_candle_label.py
```

---

# Phase 2: Pillow geometry drawer

Agent-agnostic overlay: your Chat/AI Agent emits `draw_commands`; the drawer resolves candle refs to pixels and draws with Pillow.

Workflow [`workflows/candle-draw.json`](workflows/candle-draw.json) is imported on the pgwhy n8n stack as **Candle Draw (Phase 2)** (`candleDrawPhase2`).

```
Webhook → Unfold Dates → Loop Dates
  → DuckDB OHLC (last 200 as-of date; skip if date missing)
  → IF Has Rows → Label Candles → AI Agent → Draw Shapes
  → Fetch Prior Analysis → Validation AI Agent → Merge Validation
  → Stage Store → DuckDB Store → Loop
  → (done) Respond
```

OHLC source: `pgwhy/data/tips_5years.csv` → `/data/tips_5years.csv` in n8n.

Results DB: `pgwhy/data/candle_draw_results.duckdb` → `/data/candle_draw_results.duckdb`  
Table `chart_analysis`: `nse_code`, `as_of_date`, `from_date`, `to_date`, `summary`, `image_jpeg`, `review_comments`, `signal` (`BUY`|`SELL`|`HOLD`), `confidence` (0–100), `execution_id`, `created_at`  
(only after a successful draw with summary; validation fields from the Validation AI Agent).

Webhook body fields: `nse_code`, `from`, `to` (required); `theme`, `execution_id` (optional).  
`execution_id` is copied onto every stored row for the sweep so you can filter:  
`SELECT * FROM chart_analysis WHERE execution_id = 'your-id'`.

Calendar days in `from`/`to` that are not trading sessions for `nse_code` are skipped silently (no chart, no store).

**Production:**
```bash
curl -sS -X POST 'https://n8n.dataversusdata.com/webhook/candle-draw' \
  -H 'Content-Type: application/json' \
  -d '{
    "nse_code": "TIPSMUSIC",
    "from": "2026-07-18",
    "to": "2026-07-21",
    "theme": "tradingview_light",
    "execution_id": "req-20260722-001"
  }'
```


After editing `workflows/candle-draw.json`, import/sync then **publish** so production webhooks pick it up:

```bash
podman exec -u node n8n n8n publish:workflow --id=candleDrawPhase2
podman restart n8n
```

Scripts: [`scripts/code_node_unfold_dates.js`](scripts/code_node_unfold_dates.js), [`scripts/code_node_fetch_ohlc_csv.py`](scripts/code_node_fetch_ohlc_csv.py), [`scripts/code_node_prepare_validation_context.js`](scripts/code_node_prepare_validation_context.js), [`scripts/code_node_merge_validation.js`](scripts/code_node_merge_validation.js), [`scripts/code_node_stage_store_results.py`](scripts/code_node_stage_store_results.py), [`scripts/ai_agent_prompt_validation.md`](scripts/ai_agent_prompt_validation.md).

Code snippets: [`scripts/code_node_candle_draw_label.py`](scripts/code_node_candle_draw_label.py), [`scripts/code_node_shape_draw.py`](scripts/code_node_shape_draw.py).

### Agent → drawer contract (locked)

Agent emits **only** shape + candle-label endpoints (no freeform pixels):

```json
{
  "draw_commands": [
    {
      "shape": "line",
      "from": "c12_l",
      "to": "c45_l",
      "label": "Support",
      "color": "#2962ff",
      "width": 2
    },
    {
      "shape": "hline",
      "at": "c30_c",
      "label": "Pivot",
      "color": "#e91e63",
      "width": 1
    },
    {
      "shape": "polyline",
      "points": ["c5_l", "c18_l", "c40_l"],
      "label": "Trend",
      "color": "#26a69a",
      "width": 2
    }
  ]
}
```

**Candle ref syntax:** `c{index}_{o|h|l|c}` matching Phase 1 `candles[].index` + `points.o/h/l/c`.

| `shape` | Required fields | Geometry |
|---------|-----------------|----------|
| `line` | `from`, `to` | Straight segment |
| `hline` | `at` | Horizontal across plot through that point’s y |
| `polyline` | `points[]` (≥2 refs) | Connected segments |

Optional on every command: `label`, `color` (hex), `width` (px). Invalid refs → skip + `errors[]` (node does not crash).

### Fields your agent must pass through / add

| Field | Role |
|-------|------|
| `candles` or `point_index` | Pass through from Label Candles |
| `plot_bbox`, `theme` | Pass through (hline uses plot width) |
| `crop_b64` or binary `chart` | Chart image to annotate |
| `draw_commands` | **Agent adds this** (via Structured Output Parser) |
| `summary` | **Agent adds this** — Stage Analysis text (passed through to webhook response) |
| `agent_context` | Fed into the Agent user prompt (IDs only, no pixels) |

### AI Agent prompt (copy-paste)

Full prompt text: [`scripts/ai_agent_prompt_draw.md`](scripts/ai_agent_prompt_draw.md)

**System Message** — includes EXPECTED SCHEMA (same as Structured Output Parser + Draw Shapes):

```text
You are a chart geometry assistant for candlestick charts.

Your output is consumed directly by the Draw Shapes node. Emit draw_commands only — candle label IDs, never pixel coordinates.

RULES
1. Follow the EXPECTED SCHEMA exactly (top-level key: draw_commands).
2. Each command MUST use key "shape" (never "type"): line | hline | polyline.
3. Candle refs MUST be c{index}_{o|h|l|c} from the provided candle list only.
4. Prefer _l for support, _h for resistance, _c for pivots.
5. Return 1–5 commands. If nothing clear, return { "draw_commands": [] }.

SHAPE REQUIREMENTS (Draw Shapes resolves refs → pixels)
| shape     | required fields      | geometry                          |
| line      | from, to             | straight segment between two refs |
| hline     | at                   | horizontal line at that ref's y   |
| polyline  | points[] (≥2 refs)   | connected segments through refs   |

EXPECTED SCHEMA
{
  "draw_commands": [
    { "shape": "line", "from": "c12_l", "to": "c45_l", "label": "Support", "color": "#2962ff", "width": 2 },
    { "shape": "hline", "at": "c30_c", "label": "Pivot", "color": "#e91e63", "width": 1 },
    { "shape": "polyline", "points": ["c5_l", "c18_l", "c40_l"], "label": "Trend", "color": "#26a69a", "width": 2 }
  ]
}
```

**User Prompt** (expression `=`):

```text
={{ `Symbol: ${$json.nse_code}
Candle count: ${$json.candle_count}

Candle labels:
${$json.agent_context}

Task: Return draw_commands matching the EXPECTED SCHEMA in your system instructions.` }}
```

### Troubleshooting: "Model output doesn't fit required format"

Common causes we saw with Gemma:

| Issue | Fix |
|-------|-----|
| Model wraps in `"output": { "draw_commands": [...] }` | Parser schema uses **one** example command only; Merge Chart Context now unwraps `output.draw_commands` |
| Schema example had line + hline + polyline | Parser inferred all fields required — use **single** `line` example in Structured Output Parser |
| Model mixes fields (`line` + `points` + `at`) | Prompt says shape-specific fields only; Merge strips extras |
| Parser fails after retries | Set **AI Agent → On Error → Continue**; Merge salvages raw JSON |

**Structured Output Parser JSON example** (use this single-command version):

```json
{
  "draw_commands": [
    {
      "shape": "line",
      "from": "c12_l",
      "to": "c45_l",
      "label": "Support",
      "color": "#2962ff",
      "width": 2
    }
  ]
}
```

**AI Agent settings:** `On Error: Continue` + retry enabled (same as parser).


1. **Require Specific Output Format** → attach **Structured Output Parser** (`hasOutputParser: true`).
2. Enable **Retry On Fail** on the parser (same pattern as `pg_why`).
3. **Structured Output Parser JSON example** — use the same object as EXPECTED SCHEMA above:

```json
{
  "draw_commands": [
    {
      "shape": "line",
      "from": "c12_l",
      "to": "c45_l",
      "label": "Support",
      "color": "#2962ff",
      "width": 2
    },
    {
      "shape": "hline",
      "at": "c30_c",
      "label": "Pivot",
      "color": "#e91e63",
      "width": 1
    },
    {
      "shape": "polyline",
      "points": ["c5_l", "c18_l", "c40_l"],
      "label": "Trend",
      "color": "#26a69a",
      "width": 2
    }
  ]
}
```

4. After the Agent, keep **Merge Chart Context** ([`scripts/code_node_merge_chart_context.js`](scripts/code_node_merge_chart_context.js)) — restores `candles` + binary chart from Label Candles. Draw Shapes then reads:

| Draw Shapes input | Source |
|-------------------|--------|
| `draw_commands` | Agent (parsed) |
| `summary` | Agent (parsed) — included in webhook JSON response |
| `candles` / `point_index` | Label Candles (via Merge) |
| binary `chart` | Label Candles (via Merge) |
| `plot_bbox`, `theme` | Label Candles (via Merge) |

Output from Draw Shapes: `summary`, `applied[]`, `errors[]`, binary `chart` (annotated JPEG).

Sample `agent_context` lines (already built by Label Candles):

```
c12 green hammer o,h,l,c
c13 red none o,h,l,c
```

### Draw Shapes Code node

```python
from n8n_candle.shape_draw_node import run_as_n8n_item

item = dict(_items[0]["json"])
if isinstance(item.get("body"), dict):
    item = {**item, **item["body"]}

chart_b64 = item.get("crop_b64")
binary = _items[0].get("binary") or {}
if not chart_b64 and isinstance(binary, dict):
    chart = binary.get("chart") or binary.get("data") or {}
    if isinstance(chart, dict):
        chart_b64 = chart.get("data")

return [run_as_n8n_item(item, chart_b64=chart_b64)]
```

Output: `applied`, `errors`, binary `chart` (annotated JPEG). Set `include_image_b64` to also keep `crop_b64` in JSON.

### Local smoke test

```bash
cd n8n && python3 scripts/test_shape_draw.py
```
