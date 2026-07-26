// n8n Code node — Attach Prior Day Context
// When a prior DuckDB analysis exists:
//   - prepend its summary into agent_context (AI Agent prompt unchanged)
//   - attach resized prior drawn JPEG as binary.prior_chart
// Always keep today's labeled chart as binary.chart (two separate JPGs).

const labeled = $('Label Candles').item;
const prep = $input.first().json || {};

let prior = null;
if (prep.prior && typeof prep.prior === 'object') {
  prior = prep.prior;
} else {
  try {
    const parsed = JSON.parse(String(prep.stdout || '{}').trim());
    if (parsed && parsed.prior && typeof parsed.prior === 'object') prior = parsed.prior;
  } catch {
    prior = null;
  }
}

const json = { ...(labeled.json || {}) };
let agentContext = String(json.agent_context || '');

if (prior && (prior.summary || prior.image_base64)) {
  const asOf = String(prior.as_of_date || '').trim() || 'unknown';
  let summary = String(prior.summary || '').trim();
  const MAX_PRIOR_SUMMARY = 500;
  if (summary.length > MAX_PRIOR_SUMMARY) {
    summary = `${summary.slice(0, MAX_PRIOR_SUMMARY).trim()}…`;
  }

  if (summary) {
    agentContext = [
      `Prior day (${asOf}) summary: ${summary}`,
      '',
      agentContext,
    ].join('\n');
  }

  json.prior_day = {
    as_of_date: asOf,
    summary: summary || null,
    has_image: !!prior.image_base64,
  };
} else {
  json.prior_day = null;
}

json.agent_context = agentContext;

// Two separate images when prior exists:
//   binary.chart       — today's labeled chart (from Label Candles)
//   binary.prior_chart — previous day's drawn analysis JPEG
const out = { json, binary: { ...(labeled.binary || {}) } };
const imageB64 = prior && prior.image_base64 ? String(prior.image_base64) : '';
if (imageB64) {
  out.binary.prior_chart = {
    data: imageB64,
    mimeType: 'image/jpeg',
    fileName: `prior_${json.prior_day?.as_of_date || 'day'}.jpg`,
    fileExtension: 'jpg',
  };
}

return [out];
