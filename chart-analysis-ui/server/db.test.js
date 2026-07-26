const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const { execSync } = require('child_process');
const {
  openDatabase,
  listAnalyses,
  getSummary,
  getFacets,
  getAnalysisById,
  getAnalysisImage,
} = require('./db');

const FIXTURE = path.join(__dirname, '..', 'test-db', 'chart_analysis.duckdb');

before(() => {
  execSync('node server/create-fixture.js', {
    cwd: path.join(__dirname, '..'),
    stdio: 'pipe',
  });
});

let handle;

before(async () => {
  handle = await openDatabase(FIXTURE, { readOnly: true });
});

after(() => {
  if (handle?.db) handle.db.close();
});

test('listAnalyses returns rows', async () => {
  const result = await listAnalyses(handle.conn, { limit: 10 });
  assert.equal(result.total, 3);
  assert.equal(result.analyses.length, 3);
});

test('filter by execution_id', async () => {
  const result = await listAnalyses(handle.conn, { execution_id: 'exec-a' });
  assert.equal(result.total, 2);
  assert.ok(result.analyses.every((r) => r.execution_id === 'exec-a'));
});

test('filter by signal', async () => {
  const result = await listAnalyses(handle.conn, { signal: 'HOLD' });
  assert.equal(result.total, 1);
  assert.equal(result.analyses[0].nse_code, 'RELIANCE');
});

test('filter by created_from / created_to', async () => {
  const result = await listAnalyses(handle.conn, {
    created_from: '2026-07-15',
    created_to: '2026-07-15',
  });
  assert.equal(result.total, 1);
  assert.equal(result.analyses[0].id, 2);
});

test('summary aggregates by signal and date', async () => {
  const summary = await getSummary(handle.conn, { nse_code: 'TIPSMUSIC' });
  assert.equal(summary.total, 2);
  assert.equal(summary.bySignal.BUY, 2);
  assert.equal(summary.byDate.length, 2);
});

test('facets lists symbols', async () => {
  const facets = await getFacets(handle.conn);
  assert.deepEqual(facets.nse_codes.sort(), ['RELIANCE', 'TIPSMUSIC']);
});

test('getAnalysisImage returns jpeg bytes', async () => {
  const row = await getAnalysisById(handle.conn, 1);
  assert.equal(row.has_image, true);
  const buf = await getAnalysisImage(handle.conn, 1);
  assert.ok(Buffer.isBuffer(buf));
  assert.equal(buf[0], 0xff);
});
