// n8n Code node — Unfold Dates
// Webhook body → one item per calendar day in from..to (for Loop Dates).

const raw = $input.item.json;
const body =
  raw && typeof raw.body === 'object' && raw.body ? { ...raw, ...raw.body } : { ...raw };

const nse_code = String(body.nse_code || body.symbol || '').trim().toUpperCase();
const fromStr = String(body.from || '').trim();
const toStr = String(body.to || '').trim();

if (!nse_code) throw new Error('nse_code is required');
if (!fromStr || !toStr) throw new Error('from and to are required (YYYY-MM-DD)');

function parseIso(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) throw new Error(`invalid date "${s}" — expected YYYY-MM-DD`);
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  if (d.toISOString().slice(0, 10) !== s) throw new Error(`invalid calendar date "${s}"`);
  return d;
}

const from = parseIso(fromStr);
const to = parseIso(toStr);
if (from > to) throw new Error(`from (${fromStr}) must be <= to (${toStr})`);

const theme = body.theme || 'tradingview_light';
const execution_id = String(body.execution_id || body.executionId || '').trim();
const items = [];
for (let t = from.getTime(); t <= to.getTime(); t += 86400000) {
  const date = new Date(t).toISOString().slice(0, 10);
  items.push({
    json: {
      nse_code,
      date,
      from: fromStr,
      to: toStr,
      theme,
      source_name: nse_code.toLowerCase(),
      ...(execution_id ? { execution_id } : {}),
    },
  });
}

return items;
