// n8n Code node — Store Results (after Draw Shapes)
// Persists nse_code, dates, summary, annotated image into /data/candle_draw_results.duckdb
// Only inserts when summary + binary chart are present; always pass-through for the loop.

const duckdb = require('duckdb');

const item = $input.item;
const data = item.json || {};
const binary = item.binary || {};
const chart = binary.chart || binary.data || {};

const summary = typeof data.summary === 'string' ? data.summary.trim() : '';
const imageB64 = typeof chart.data === 'string' ? chart.data : '';

const nse_code = String(data.nse_code || '').trim().toUpperCase();
const as_of_date = String(data.date || data.as_of_date || '').trim();
const from_date = data.from || data.from_date || null;
const to_date = data.to || data.to_date || null;

const out = { json: { ...data } };
if (item.binary) out.binary = item.binary;

if (!summary || !imageB64 || !nse_code || !as_of_date) {
  out.json.stored = false;
  return [out];
}

const DB_PATH = '/data/candle_draw_results.duckdb';
const imageBuf = Buffer.from(imageB64, 'base64');

function run(db, sql) {
  return new Promise((resolve, reject) => {
    db.run(sql, (err) => (err ? reject(err) : resolve()));
  });
}

function runInsert(db, values) {
  return new Promise((resolve, reject) => {
    db.run(
      `INSERT INTO chart_analysis (nse_code, as_of_date, from_date, to_date, summary, image_jpeg)
       VALUES (?, ?, ?, ?, ?, ?)`,
      values,
      (err) => (err ? reject(err) : resolve()),
    );
  });
}

function openDb(path) {
  return new Promise((resolve, reject) => {
    const db = new duckdb.Database(path, (err) => (err ? reject(err) : resolve(db)));
  });
}

function closeDb(db) {
  return new Promise((resolve, reject) => {
    db.close((err) => (err ? reject(err) : resolve()));
  });
}

const db = await openDb(DB_PATH);
try {
  await run(
    db,
    `CREATE SEQUENCE IF NOT EXISTS chart_analysis_id START 1;
     CREATE TABLE IF NOT EXISTS chart_analysis (
       id BIGINT PRIMARY KEY DEFAULT nextval('chart_analysis_id'),
       created_at TIMESTAMP DEFAULT current_timestamp,
       nse_code VARCHAR NOT NULL,
       as_of_date DATE NOT NULL,
       from_date DATE,
       to_date DATE,
       summary TEXT NOT NULL,
       image_jpeg BLOB NOT NULL
     );`,
  );
  await runInsert(db, [nse_code, as_of_date, from_date, to_date, summary, imageBuf]);
  out.json.stored = true;
  out.json.results_db = DB_PATH;
} finally {
  await closeDb(db);
}

return [out];
