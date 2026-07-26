// n8n Code node — Prepare Validation Context
// Draw Shapes + Fetch Prior Analysis + prior-day context (same as draw AI Agent).
// Forwards prior_day summary into validation_context and prior_chart binary.

const draw = $('Draw Shapes').item;
const fetchOut = $('Fetch Prior Analysis').first().json || {};

let prior = [];
try {
  const parsed = JSON.parse(String(fetchOut.stdout || '{}').trim());
  prior = Array.isArray(parsed.prior) ? parsed.prior : [];
} catch {
  prior = [];
}

// Same prior-day payload already fetched before the draw AI Agent.
let attach = null;
try {
  attach = $('Attach Prior Day Context').item;
} catch {
  attach = null;
}

const j = { ...(draw.json || {}) };
const nse = String(j.nse_code || '').trim().toUpperCase();
const asOf = String(j.date || j.as_of_date || '').trim();
const todaySummary = String(j.summary || '').trim();

const priorDay =
  (j.prior_day && typeof j.prior_day === 'object' ? j.prior_day : null)
  || (attach && attach.json && attach.json.prior_day && typeof attach.json.prior_day === 'object'
    ? attach.json.prior_day
    : null);

const priorLines = prior.length
  ? prior.map((r) => `- ${r.as_of_date}: ${String(r.summary || '').trim()}`).join('\n')
  : '(none — first stored analysis for this symbol)';

const priorDayBlock = priorDay && (priorDay.summary || priorDay.as_of_date)
  ? [
      `Prior day (${priorDay.as_of_date || 'unknown'}) summary: ${String(priorDay.summary || '').trim() || '(none)'}`,
      priorDay.has_image
        ? 'Prior day drawn chart is attached as image input (prior_chart).'
        : 'Prior day drawn chart: not available.',
      '',
    ]
  : ['Prior day context: (none)', ''];

const validation_context = [
  `Symbol: ${nse}`,
  `As-of: ${asOf}`,
  '',
  ...priorDayBlock,
  'Prior analyses (newest first, up to 5 trading days before as-of):',
  priorLines,
  '',
  "Today's analysis:",
  todaySummary || '(empty)',
  '',
  'Task: Compare today vs prior sessions. Note trend shifts, support/resistance consistency, and risk.',
  'Return review_comments, signal (BUY|SELL|HOLD), confidence (0-100 integer).',
].join('\n');

const outBinary = { ...(draw.binary || {}) };
const attachPrior =
  attach && attach.binary && attach.binary.prior_chart
    ? attach.binary.prior_chart
    : null;
if (attachPrior && !outBinary.prior_chart) {
  outBinary.prior_chart = attachPrior;
}

return [{
  json: {
    ...j,
    prior_day: priorDay,
    validation_context,
    prior_count: prior.length,
  },
  binary: outBinary,
}];
