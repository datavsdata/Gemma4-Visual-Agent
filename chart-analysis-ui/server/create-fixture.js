#!/usr/bin/env node
/** Create a tiny DuckDB fixture for tests. */
const fs = require('fs');
const path = require('path');
const duckdb = require('duckdb');
const { run } = require('./db');

const OUT = path.join(__dirname, '..', 'test-db', 'chart_analysis.duckdb');

async function main() {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  if (fs.existsSync(OUT)) fs.unlinkSync(OUT);

  const db = new duckdb.Database(OUT);
  const conn = db.connect();

  await run(
    conn,
    `CREATE TABLE chart_analysis (
       id BIGINT PRIMARY KEY,
       created_at TIMESTAMP DEFAULT current_timestamp,
       nse_code VARCHAR NOT NULL,
       as_of_date DATE NOT NULL,
       from_date DATE,
       to_date DATE,
       summary TEXT NOT NULL,
       image_jpeg BLOB NOT NULL,
       review_comments TEXT,
       signal VARCHAR,
       confidence INTEGER,
       execution_id VARCHAR
     )`,
  );

  const blobHex = 'FFD8FFE000104A46';
  const rows = [
    [1, '2026-07-10', 'TIPSMUSIC', '2026-07-20', '2026-07-20', '2026-07-20', 'Stage 2 advancing', 'Prior ok', 'BUY', 70, 'exec-a'],
    [2, '2026-07-15', 'TIPSMUSIC', '2026-07-21', '2026-07-21', '2026-07-21', 'Consolidation near highs', 'Momentum strong', 'BUY', 85, 'exec-a'],
    [3, '2026-07-22', 'RELIANCE', '2026-07-21', '2026-07-21', '2026-07-21', 'Range bound', 'Wait', 'HOLD', 40, 'exec-b'],
  ];

  for (const row of rows) {
    const [id, created, sym, asOf, fromD, toD, summary, review, signal, conf, execId] = row;
    await run(
      conn,
      `INSERT INTO chart_analysis (
         id, created_at, nse_code, as_of_date, from_date, to_date, summary, image_jpeg,
         review_comments, signal, confidence, execution_id
       ) VALUES (
         ?, ?::TIMESTAMP, ?, ?, ?, ?, ?, '\\x${blobHex}'::BLOB, ?, ?, ?, ?
       )`,
      [id, created, sym, asOf, fromD, toD, summary, review, signal, conf, execId],
    );
  }

  await new Promise((resolve, reject) => db.close((e) => (e ? reject(e) : resolve())));
  console.log('Wrote', OUT);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
