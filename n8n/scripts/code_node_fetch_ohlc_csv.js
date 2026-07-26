// n8n Code node — Fetch OHLC + Convert to locked csv_text
// One as-of date in → one item out.
// If as-of date is missing from CSV: { _skip: true } (IF routes silently back to Loop).

const duckdb = require('duckdb');

const meta = $input.item.json || {};
const nse_code = String(meta.nse_code || '').trim().toUpperCase();
const asOf = String(meta.date || '').trim();

if (!nse_code || !asOf) {
  return [{ json: { ...meta, _skip: true, _skip_reason: 'missing nse_code or date' } }];
}

const sql = `
WITH raw AS (
  SELECT * FROM read_csv_auto('/data/tips_5years.csv', header=true)
),
base AS (
  SELECT
    upper(trim(Symbol)) AS symbol,
    strptime(trim(Date), '%d-%b-%Y')::DATE AS trade_date,
    trim(Series) AS series,
    try_cast(replace(trim("Open Price"), ',', '') AS DOUBLE) AS open,
    try_cast(replace(trim("High Price"), ',', '') AS DOUBLE) AS high,
    try_cast(replace(trim("Low Price"), ',', '') AS DOUBLE) AS low,
    try_cast(replace(trim("Close Price"), ',', '') AS DOUBLE) AS close,
    try_cast(replace(trim("Prev Close"), ',', '') AS DOUBLE) AS prev_close,
    try_cast(replace(trim("Last Price"), ',', '') AS DOUBLE) AS ltp,
    try_cast(replace(trim("Average Price"), ',', '') AS DOUBLE) AS vwap,
    try_cast(replace(trim("Total Traded Quantity"), ',', '') AS DOUBLE) AS volume,
    try_cast(replace(trim("Turnover ₹"), ',', '') AS DOUBLE) AS value,
    try_cast(replace(trim("No. of Trades"), ',', '') AS DOUBLE) AS trades
  FROM raw
),
as_of AS (
  SELECT 1 AS ok FROM base
  WHERE symbol = '${nse_code.replace(/'/g, "''")}' AND trade_date = DATE '${asOf.replace(/'/g, "''")}'
)
SELECT
  strftime(trade_date, '%d-%b-%Y') AS DATE,
  series AS SERIES,
  open AS OPEN,
  high AS HIGH,
  low AS LOW,
  prev_close AS "PREV. CLOSE",
  ltp AS LTP,
  close AS CLOSE,
  vwap AS VWAP,
  NULL AS "52W H",
  NULL AS "52W L",
  volume AS VOLUME,
  value AS VALUE,
  trades AS "NO. OF  TRADES"
FROM (
  SELECT * FROM base
  WHERE symbol = '${nse_code.replace(/'/g, "''")}'
    AND trade_date <= DATE '${asOf.replace(/'/g, "''")}'
    AND EXISTS (SELECT 1 FROM as_of)
  ORDER BY trade_date DESC
  LIMIT 200
)
ORDER BY trade_date ASC
`;

const rows = await new Promise((resolve, reject) => {
  const db = new duckdb.Database(':memory:');
  db.all(sql, (err, result) => {
    db.close(() => {
      if (err) reject(err);
      else resolve(result || []);
    });
  });
});

if (!rows.length) {
  return [{ json: { ...meta, nse_code, date: asOf, _skip: true, _skip_reason: 'as-of date not in CSV' } }];
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

return [
  {
    json: {
      ...meta,
      nse_code,
      date: asOf,
      from: meta.from,
      to: meta.to,
      theme: meta.theme || 'tradingview_light',
      source_name: meta.source_name || nse_code.toLowerCase(),
      csv_text: lines.join('\n') + '\n',
      _skip: false,
    },
  },
];
