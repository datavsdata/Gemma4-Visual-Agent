import React from 'react';

function SignalBadge({ signal }) {
  const s = (signal || 'HOLD').toUpperCase();
  return <span className={`signal-badge signal-${s.toLowerCase()}`}>{s}</span>;
}

export default function AnalysisList({
  analyses,
  total,
  selectedId,
  onSelect,
  offset,
  limit,
  onPageChange,
  loading,
}) {
  return (
    <section className="panel analysis-list">
      <div className="section-heading">
        <h2>Analyses</h2>
        <span className="muted">{total} total</span>
      </div>

      {loading && <p className="muted">Loading analyses…</p>}

      {!loading && analyses.length === 0 && (
        <p className="muted">No analyses match the current filters.</p>
      )}

      {!loading && analyses.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>As-of</th>
                <th>Created</th>
                <th>Symbol</th>
                <th>Signal</th>
                <th>Conf.</th>
                <th>Execution ID</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((row) => (
                <tr
                  key={row.id}
                  className={row.id === selectedId ? 'selected' : ''}
                  onClick={() => onSelect(row.id)}
                >
                  <td>{row.as_of_date}</td>
                  <td>{row.created_at || '—'}</td>
                  <td>{row.nse_code}</td>
                  <td><SignalBadge signal={row.signal} /></td>
                  <td>{row.confidence ?? '—'}</td>
                  <td className="mono">{row.execution_id || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > limit && (
        <div className="pager">
          <button
            type="button"
            className="btn secondary"
            disabled={offset <= 0}
            onClick={() => onPageChange(Math.max(0, offset - limit))}
          >
            Previous
          </button>
          <span className="muted">
            {offset + 1}–{Math.min(offset + limit, total)} of {total}
          </span>
          <button
            type="button"
            className="btn secondary"
            disabled={offset + limit >= total}
            onClick={() => onPageChange(offset + limit)}
          >
            Next
          </button>
        </div>
      )}
    </section>
  );
}

export { SignalBadge };
