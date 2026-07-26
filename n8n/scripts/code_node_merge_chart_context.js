// n8n Code node — Merge Chart Context (JavaScript)
// Place between AI Agent (with Structured Output Parser) and Draw Shapes.
// Preserves prior_day + prior_chart from Attach Prior Day Context for Validation.

const prev = $('Label Candles').item;
const agent = $input.item.json;

let attach = null;
try {
  attach = $('Attach Prior Day Context').item;
} catch {
  attach = null;
}

function parseJson(text) {
  const t = String(text).trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim();
  try { return JSON.parse(t); } catch {
    const m = t.match(/\{[\s\S]*\}/);
    if (m) return JSON.parse(m[0]);
  }
  return null;
}

// Resolve the inner object from agent output.
// AI Agent emits one of:
//   {output: {summary, draw_commands}}    <- parser parsed it
//   {output: "```json\n{...}\n```"}       <- parser passed through raw string
//   {output: "{...}"}                     <- raw JSON string
function resolveInner(data) {
  if (!data) return null;
  // Already a parsed object with draw_commands or summary at top level
  if (Array.isArray(data.draw_commands) || typeof data.summary === 'string') return data;
  // output is already an object
  if (data.output && typeof data.output === 'object' && !Array.isArray(data.output)) {
    return data.output;
  }
  // output is a string — strip fences and parse
  const raw = data.output ?? data.text ?? data.response;
  if (typeof raw === 'string') {
    const parsed = parseJson(raw);
    if (!parsed) return null;
    // model returned { "output": { ... } }
    if (parsed.output && typeof parsed.output === 'object') return parsed.output;
    // model returned { "draw_commands": [...], "summary": "..." }
    if (Array.isArray(parsed.draw_commands) || typeof parsed.summary === 'string') return parsed;
  }
  return null;
}

function extractCommands(data) {
  const inner = resolveInner(data);
  if (inner && Array.isArray(inner.draw_commands)) return inner.draw_commands;
  if (data && Array.isArray(data.draw_commands)) return data.draw_commands;
  return null;
}

function extractSummary(data) {
  if (!data) return null;
  const inner = resolveInner(data);
  if (inner && typeof inner.summary === 'string' && inner.summary.trim()) return inner.summary.trim();
  if (typeof data.summary === 'string' && data.summary.trim()) return data.summary.trim();
  return null;
}

let cmds = extractCommands(agent);
let agentFailed = false;
if (!Array.isArray(cmds)) {
  // Do not fail the date loop when the model returns empty structured output.
  // Draw Shapes will no-op overlays; Stage Store skips if summary is empty.
  agentFailed = true;
  cmds = [];
}

cmds = cmds.map((c) => {
  if (!c || typeof c !== 'object') return c;
  const out = { ...c };
  if (!out.shape && out.type) out.shape = out.type;
  delete out.type;
  const shape = String(out.shape || '').toLowerCase();
  if (shape === 'line') { delete out.at; delete out.points; }
  else if (shape === 'hline') { delete out.from; delete out.to; delete out.points; }
  else if (shape === 'polyline') { delete out.from; delete out.to; delete out.at; }
  return out;
});

const summary = extractSummary(agent);
const json = { ...prev.json, draw_commands: cmds };
if (summary) json.summary = summary;
else if (agentFailed) {
  json.summary = '';
  json._agent_output_missing = true;
}

// Carry prior-day context (fetched before draw AI Agent) downstream to Validation.
if (attach && attach.json && Object.prototype.hasOwnProperty.call(attach.json, 'prior_day')) {
  json.prior_day = attach.json.prior_day;
}

const out = { json, binary: { ...(prev.binary || {}) } };
if (attach && attach.binary && attach.binary.prior_chart) {
  out.binary.prior_chart = attach.binary.prior_chart;
}
return [out];
