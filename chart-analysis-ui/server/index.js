const path = require('path');
const express = require('express');
const cors = require('cors');
const {
  resolveDbPath,
  withReadOnlyDatabase,
  isLockError,
  getHealth,
  getFacets,
  getSummary,
  listAnalyses,
  getAnalysisById,
  getAnalysisImage,
} = require('./db');

const PORT = parseInt(process.env.API_PORT || process.env.PORT || '3001', 10);
const HOST = process.env.API_HOST || '0.0.0.0';

function filterParams(query) {
  return {
    nse_code: query.nse_code,
    execution_id: query.execution_id,
    signal: query.signal,
    from: query.from,
    to: query.to,
    created_from: query.created_from,
    created_to: query.created_to,
    min_confidence: query.min_confidence,
  };
}

function createApp({ dbPath, serveStatic = false }) {
  const app = express();
  app.use(cors());
  app.use(express.json({ limit: '1mb' }));

  const queryDb = (fn) => withReadOnlyDatabase(dbPath, fn);

  app.get('/api/health', async (_req, res) => {
    try {
      res.json(await queryDb((conn, resolved) => getHealth(conn, resolved)));
    } catch (err) {
      sendError(res, err);
    }
  });

  app.get('/api/facets', async (_req, res) => {
    try {
      res.json(await queryDb((conn) => getFacets(conn)));
    } catch (err) {
      sendError(res, err);
    }
  });

  app.get('/api/summary', async (req, res) => {
    try {
      res.json(await queryDb((conn) => getSummary(conn, filterParams(req.query))));
    } catch (err) {
      sendError(res, err);
    }
  });

  app.get('/api/analyses', async (req, res) => {
    try {
      res.json(
        await queryDb((conn) =>
          listAnalyses(conn, {
            ...filterParams(req.query),
            limit: req.query.limit,
            offset: req.query.offset,
            sort: req.query.sort,
          }),
        ),
      );
    } catch (err) {
      sendError(res, err);
    }
  });

  app.get('/api/analyses/:id/image', async (req, res) => {
    try {
      const buf = await queryDb((conn) => getAnalysisImage(conn, req.params.id));
      res.set('Content-Type', 'image/jpeg');
      res.set('Cache-Control', 'public, max-age=3600');
      res.send(buf);
    } catch (err) {
      sendError(res, err);
    }
  });

  app.get('/api/analyses/:id', async (req, res) => {
    try {
      res.json(await queryDb((conn) => getAnalysisById(conn, req.params.id)));
    } catch (err) {
      sendError(res, err);
    }
  });

  if (serveStatic) {
    const buildDir = path.join(__dirname, '..', 'build');
    app.use(express.static(buildDir));
    app.get('/{*path}', (_req, res) => {
      res.sendFile(path.join(buildDir, 'index.html'));
    });
  }

  app.use((err, _req, res, _next) => {
    sendError(res, err);
  });

  return app;
}

function sendError(res, err) {
  const code = isLockError(err) ? 'CHART_DB_LOCKED' : (err.code || 'INTERNAL_ERROR');
  const statusByCode = {
    CHART_DB_NOT_FOUND: 503,
    CHART_SCHEMA_INVALID: 503,
    CHART_DB_LOCKED: 503,
    BAD_REQUEST: 400,
    NOT_FOUND: 404,
  };
  res.status(statusByCode[code] || 500).json({
    error: isLockError(err)
      ? 'Database is locked by n8n backtest write — retry in a moment (read-only access).'
      : (err.message || 'Unexpected server error'),
    code,
  });
}

async function startServer() {
  let dbPath;
  try {
    dbPath = resolveDbPath(process.env.CHART_ANALYSIS_DB);
  } catch (err) {
    console.error(`[chart-api] ${err.message}`);
    process.exit(1);
  }

  const serveStatic = process.env.SERVE_STATIC === '1';
  const app = createApp({ dbPath, serveStatic });

  const server = app.listen(PORT, HOST, () => {
    console.log(`[chart-api] listening on http://${HOST}:${PORT} db=${dbPath} (read-only per request)`);
  });

  const shutdown = () => {
    server.close(() => process.exit(0));
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
  return server;
}

if (require.main === module) {
  startServer().catch((err) => {
    console.error(`[chart-api] ${err.message}`);
    process.exit(1);
  });
}

module.exports = { createApp, startServer };
