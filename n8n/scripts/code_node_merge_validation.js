// n8n Code node — Merge Validation
// Attach validation agent output onto Draw Shapes payload before Stage Store.

const base = $('Prepare Validation Context').item;
const agent = $input.item.json;

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

function resolveInner(data) {
  if (!data) return null;
  if (typeof data.review_comments === 'string' || data.signal || data.confidence != null) return data;
  if (data.output && typeof data.output === 'object' && !Array.isArray(data.output)) return data.output;
  const raw = data.output ?? data.text ?? data.response;
  if (typeof raw === 'string') {
    const parsed = parseJson(raw);
    if (!parsed) return null;
    if (parsed.output && typeof parsed.output === 'object') return parsed.output;
    return parsed;
  }
  return null;
}

function normalizeSignal(s) {
  const v = String(s || '').trim().toUpperCase();
  if (v === 'BUY' || v === 'SELL' || v === 'HOLD') return v;
  return 'HOLD';
}

function normalizeConfidence(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, Math.round(n)));
}

const inner = resolveInner(agent) || {};
const json = {
  ...(base.json || {}),
  review_comments: String(inner.review_comments || '').trim(),
  signal: normalizeSignal(inner.signal),
  confidence: normalizeConfidence(inner.confidence),
};

const out = { json };
if (base.binary) out.binary = base.binary;
return [out];
