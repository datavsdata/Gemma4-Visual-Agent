// n8n Code node — Convert DuckDB OHLC rows → locked NSE csv_text.
// Skips _skip sentinel rows. Metadata from Loop Dates / Unfold Dates.

const meta =
  ($('Loop Dates').item && $('Loop Dates').item.json) ||
  ($('Unfold Dates').item && $('Unfold Dates').item.json) ||
  {};

const rows = $input
  .all()
  .map((i) => i.json)
  .filter((r) => r && r._skip !== true && (r.DATE || r.OPEN));

if (!rows.length) {
  return [];
}

const HEADER =
  'DATE,SERIES,OPEN,HIGH,LOW,PREV. CLOSE,LTP,CLOSE,VWAP,52W H,52W L,VOLUME,VALUE,NO. OF  TRADES';

function cell(v) {
  if (v === null || v === undefined) return '';
  const s = String(v);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

const lines = [HEADER];
for (const r of rows) {
  lines.push(
    [
      r.DATE,
      r.SERIES ?? 'EQ',
      r.OPEN,
      r.HIGH,
      r.LOW,
      r['PREV. CLOSE'],
      r.LTP,
      r.CLOSE,
      r.VWAP,
      r['52W H'],
      r['52W L'],
      r.VOLUME,
      r.VALUE,
      r['NO. OF  TRADES'],
    ]
      .map(cell)
      .join(','),
  );
}

const nse_code = String(meta.nse_code || '').toUpperCase();
return [
  {
    json: {
      ...meta,
      nse_code,
      date: meta.date,
      from: meta.from,
      to: meta.to,
      theme: meta.theme || 'tradingview_light',
      source_name: meta.source_name || nse_code.toLowerCase(),
      csv_text: lines.join('\n') + '\n',
    },
  },
];
