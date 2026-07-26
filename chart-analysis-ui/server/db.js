const fs = require('fs');
const path = require('path');
const duckdb = require('duckdb');

const DEFAULT_DB = path.join(__dirname, '..', '..', 'pgwhy', 'data', 'candle_draw_results.duckdb');
const LIST_COLUMNS = `
  id,
  created_at,
  nse_code,
  as_of_date,
  from_date,
  to_date,
  summary,
  review_comments,
  signal,
  confidence,
  execution_id,
  (image_jpeg IS NOT NULL) AS has_image
`;

function resolveDbPath(explicitPath) {
  const raw = explicitPath || process.env.CHART_ANALYSIS_DB || DEFAULT_DB;
  return path.resolve(raw);
}

function run(conn, sql, params = []) {
  return new Promise((resolve, reject) => {
    conn.run(sql, ...params, (err) => (err ? reject(err) : resolve()));
  });
}

function all(conn, sql, params = []) {
  return new Promise((resolve, reject) => {
    conn.all(sql, ...params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows || []);
    });
  });
}

function normalizeRow(row) {
  if (!row || typeof row !== 'object') return row;
  const out = {};
  for (const [key, value] of Object.entries(row)) {
    if (typeof value === 'bigint') out[key] = Number(value);
    else if (value instanceof Date) out[key] = value.toISOString().slice(0, 10);
    else out[key] = value;
  }
  return out;
}

function normalizeRows(rows) {
  return (rows || []).map(normalizeRow);
}

async function openDatabase(dbPath, { readOnly = true } = {}) {
  const resolved = resolveDbPath(dbPath);
  if (!fs.existsSync(resolved)) {
    const err = new Error(`Database file not found: ${resolved}`);
    err.code = 'CHART_DB_NOT_FOUND';
    throw err;
  }
  const options = readOnly ? { access_mode: 'READ_ONLY' } : undefined;
  const db = new duckdb.Database(resolved, options);
  const conn = db.connect();
  await validateSchema(conn);
  return { db, conn, path: resolved };
}

async function closeDatabase(handle) {
  if (!handle?.db) return;
  await new Promise((resolve) => {
    try {
      handle.db.close(() => resolve());
    } catch (_err) {
      resolve();
    }
  });
}

function isLockError(err) {
  const msg = String(err?.message || err || '').toLowerCase();
  return msg.includes('conflicting lock') || msg.includes('could not set lock');
}

async function withReadOnlyDatabase(dbPath, fn, { retries = 5, delayMs = 250 } = {}) {
  return withDbQueue(() => withReadOnlyDatabaseInner(dbPath, fn, { retries, delayMs }));
}

let dbQueue = Promise.resolve();

function withDbQueue(task) {
  const next = dbQueue.then(task, task);
  dbQueue = next.catch(() => {});
  return next;
}

async function withReadOnlyDatabaseInner(dbPath, fn, { retries = 5, delayMs = 250 } = {}) {
  let lastErr;
  for (let attempt = 0; attempt < retries; attempt += 1) {
    let handle;
    try {
      handle = await openDatabase(dbPath, { readOnly: true });
      return await fn(handle.conn, handle.path);
    } catch (err) {
      lastErr = err;
      if (!isLockError(err) || attempt === retries - 1) throw err;
      await new Promise((r) => setTimeout(r, delayMs * (attempt + 1)));
    } finally {
      await closeDatabase(handle);
    }
  }
  throw lastErr;
}

async function validateSchema(conn) {
  const tables = await all(
    conn,
    `SELECT table_name FROM information_schema.tables
     WHERE table_schema = 'main' AND table_name = 'chart_analysis'`,
  );
  if (tables.length === 0) {
    const err = new Error('Expected table "chart_analysis" was not found.');
    err.code = 'CHART_SCHEMA_INVALID';
    throw err;
  }
}

function parseFilters(input = {}) {
  const signals = String(input.signal || '')
    .split(',')
    .map((s) => s.trim().toUpperCase())
    .filter((s) => ['BUY', 'SELL', 'HOLD'].includes(s));

  return {
    nse_code: String(input.nse_code || '').trim().toUpperCase(),
    execution_id: String(input.execution_id || '').trim(),
    signal: signals,
    from: String(input.from || '').trim(),
    to: String(input.to || '').trim(),
    created_from: String(input.created_from || '').trim(),
    created_to: String(input.created_to || '').trim(),
    min_confidence:
      input.min_confidence !== undefined && input.min_confidence !== ''
        ? Number(input.min_confidence)
        : null,
  };
}

function buildWhere(filters) {
  const clauses = [];
  const params = [];

  if (filters.nse_code) {
    clauses.push('nse_code = ?');
    params.push(filters.nse_code);
  }
  if (filters.execution_id) {
    clauses.push('trim(execution_id) = ?');
    params.push(filters.execution_id);
  }
  if (filters.signal && filters.signal.length > 0) {
    clauses.push(`upper(trim(signal)) IN (${filters.signal.map(() => '?').join(', ')})`);
    params.push(...filters.signal);
  }
  if (filters.from) {
    clauses.push('as_of_date >= ?');
    params.push(filters.from);
  }
  if (filters.to) {
    clauses.push('as_of_date <= ?');
    params.push(filters.to);
  }
  if (filters.created_from) {
    clauses.push('CAST(created_at AS DATE) >= ?');
    params.push(filters.created_from);
  }
  if (filters.created_to) {
    clauses.push('CAST(created_at AS DATE) <= ?');
    params.push(filters.created_to);
  }
  if (filters.min_confidence !== null && Number.isFinite(filters.min_confidence)) {
    clauses.push('confidence >= ?');
    params.push(Math.round(filters.min_confidence));
  }

  return {
    sql: clauses.length ? `WHERE ${clauses.join(' AND ')}` : '',
    params,
  };
}

function parseSort(sort) {
  const allowed = {
    newest: 'as_of_date DESC, id DESC',
    oldest: 'as_of_date ASC, id ASC',
    confidence: 'confidence DESC NULLS LAST, as_of_date DESC',
  };
  return allowed[sort] || allowed.newest;
}

async function getHealth(conn, dbPath) {
  const [stats] = normalizeRows(
    await all(
      conn,
      `SELECT
         COUNT(*)::INTEGER AS row_count,
         MIN(as_of_date) AS min_date,
         MAX(as_of_date) AS max_date
       FROM chart_analysis`,
    ),
  );
  return {
    ok: true,
    dbPath,
    rowCount: stats?.row_count ?? 0,
    minDate: stats?.min_date ?? null,
    maxDate: stats?.max_date ?? null,
  };
}

async function getFacets(conn) {
  const nse_codes = normalizeRows(
    await all(
      conn,
      `SELECT DISTINCT nse_code FROM chart_analysis
       WHERE nse_code IS NOT NULL ORDER BY nse_code`,
    ),
  ).map((r) => r.nse_code);

  const execution_ids = normalizeRows(
    await all(
      conn,
      `SELECT execution_id, MAX(created_at) AS last_seen
       FROM chart_analysis
       WHERE execution_id IS NOT NULL AND trim(execution_id) != ''
       GROUP BY execution_id
       ORDER BY last_seen DESC
       LIMIT 50`,
    ),
  ).map((r) => r.execution_id);

  return { nse_codes, execution_ids };
}

async function getSummary(conn, filterInput = {}) {
  const filters = parseFilters(filterInput);
  const { sql: whereSql, params } = buildWhere(filters);

  const [totals] = normalizeRows(
    await all(
      conn,
      `SELECT COUNT(*)::INTEGER AS total FROM chart_analysis ${whereSql}`,
      params,
    ),
  );

  const bySignalRows = normalizeRows(
    await all(
      conn,
      `SELECT upper(trim(signal)) AS signal, COUNT(*)::INTEGER AS count
       FROM chart_analysis ${whereSql}
       GROUP BY 1`,
      params,
    ),
  );

  const bySignal = { BUY: 0, SELL: 0, HOLD: 0 };
  for (const row of bySignalRows) {
    if (row.signal && bySignal[row.signal] !== undefined) {
      bySignal[row.signal] = row.count;
    }
  }

  const byDate = normalizeRows(
    await all(
      conn,
      `SELECT
         CAST(as_of_date AS VARCHAR) AS as_of_date,
         SUM(CASE WHEN upper(trim(signal)) = 'BUY' THEN 1 ELSE 0 END)::INTEGER AS buy,
         SUM(CASE WHEN upper(trim(signal)) = 'SELL' THEN 1 ELSE 0 END)::INTEGER AS sell,
         SUM(CASE WHEN upper(trim(signal)) = 'HOLD' THEN 1 ELSE 0 END)::INTEGER AS hold,
         ROUND(AVG(confidence), 1) AS avg_confidence
       FROM chart_analysis ${whereSql}
       GROUP BY as_of_date
       ORDER BY as_of_date`,
      params,
    ),
  );

  const confidenceTrend = normalizeRows(
    await all(
      conn,
      `SELECT
         CAST(as_of_date AS VARCHAR) AS as_of_date,
         nse_code,
         confidence
       FROM chart_analysis ${whereSql}
       ORDER BY as_of_date, nse_code`,
      params,
    ),
  );

  return {
    total: totals?.total ?? 0,
    bySignal,
    byDate,
    confidenceTrend,
    filters,
  };
}

async function listAnalyses(conn, filterInput = {}) {
  const filters = parseFilters(filterInput);
  const { sql: whereSql, params } = buildWhere(filters);
  const limit = Math.min(Math.max(parseInt(filterInput.limit, 10) || 25, 1), 200);
  const offset = Math.max(parseInt(filterInput.offset, 10) || 0, 0);
  const sort = parseSort(filterInput.sort);

  const [countRow] = normalizeRows(
    await all(conn, `SELECT COUNT(*)::INTEGER AS total FROM chart_analysis ${whereSql}`, params),
  );

  const rows = normalizeRows(
    await all(
      conn,
      `SELECT ${LIST_COLUMNS}
       FROM chart_analysis ${whereSql}
       ORDER BY ${sort}
       LIMIT ? OFFSET ?`,
      [...params, limit, offset],
    ),
  );

  return {
    analyses: rows,
    total: countRow?.total ?? 0,
    limit,
    offset,
    filters,
  };
}

async function getAnalysisById(conn, id) {
  const numericId = Number(id);
  if (!Number.isFinite(numericId)) {
    const err = new Error('Invalid analysis id');
    err.code = 'BAD_REQUEST';
    throw err;
  }

  const rows = normalizeRows(
    await all(
      conn,
      `SELECT ${LIST_COLUMNS} FROM chart_analysis WHERE id = ?`,
      [numericId],
    ),
  );
  if (!rows.length) {
    const err = new Error(`Analysis ${id} not found`);
    err.code = 'NOT_FOUND';
    throw err;
  }
  return rows[0];
}

async function getAnalysisImage(conn, id) {
  const numericId = Number(id);
  if (!Number.isFinite(numericId)) {
    const err = new Error('Invalid analysis id');
    err.code = 'BAD_REQUEST';
    throw err;
  }

  const rows = await all(conn, 'SELECT image_jpeg FROM chart_analysis WHERE id = ?', [numericId]);
  if (!rows.length || !rows[0].image_jpeg) {
    const err = new Error(`Image for analysis ${id} not found`);
    err.code = 'NOT_FOUND';
    throw err;
  }
  const buf = rows[0].image_jpeg;
  return Buffer.isBuffer(buf) ? buf : Buffer.from(buf);
}

module.exports = {
  resolveDbPath,
  openDatabase,
  closeDatabase,
  withReadOnlyDatabase,
  isLockError,
  validateSchema,
  parseFilters,
  buildWhere,
  getHealth,
  getFacets,
  getSummary,
  listAnalyses,
  getAnalysisById,
  getAnalysisImage,
  run,
  all,
};
