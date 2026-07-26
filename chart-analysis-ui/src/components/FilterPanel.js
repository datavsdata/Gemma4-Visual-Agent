import React from 'react';

const EMPTY_FILTERS = {
  nse_code: '',
  execution_id: '',
  signal: '',
  from: '',
  to: '',
  created_from: '',
  created_to: '',
  min_confidence: '',
  sort: 'newest',
};

export { EMPTY_FILTERS };

export default function FilterPanel({
  filters,
  facets,
  onChange,
  onApply,
  onReset,
  loading,
}) {
  const toggleSignal = (sig) => {
    const current = filters.signal ? filters.signal.split(',').filter(Boolean) : [];
    const next = current.includes(sig)
      ? current.filter((s) => s !== sig)
      : [...current, sig];
    onChange({ ...filters, signal: next.join(',') });
  };

  const activeSignals = filters.signal ? filters.signal.split(',').filter(Boolean) : [];

  return (
    <section className="panel filter-panel">
      <div className="section-heading">
        <div>
          <h2>Filters</h2>
          <p className="muted">Narrow analyses by symbol, execution, signal, as-of date, or create date.</p>
        </div>
        <div className="filter-actions">
          <button type="button" className="btn secondary" onClick={onReset} disabled={loading}>
            Reset
          </button>
          <button type="button" className="btn primary" onClick={onApply} disabled={loading}>
            {loading ? 'Loading…' : 'Apply'}
          </button>
        </div>
      </div>

      <div className="filter-grid">
        <label>
          Symbol
          <select
            value={filters.nse_code}
            onChange={(e) => onChange({ ...filters, nse_code: e.target.value })}
          >
            <option value="">All symbols</option>
            {(facets?.nse_codes || []).map((code) => (
              <option key={code} value={code}>{code}</option>
            ))}
          </select>
        </label>

        <label>
          Execution ID
          <input
            list="execution-ids"
            value={filters.execution_id}
            onChange={(e) => onChange({ ...filters, execution_id: e.target.value })}
            placeholder="e.g. req-ping-20260722-001"
          />
          <datalist id="execution-ids">
            {(facets?.execution_ids || []).map((id) => (
              <option key={id} value={id} />
            ))}
          </datalist>
        </label>

        <label>
          As-of from
          <input
            type="date"
            value={filters.from}
            onChange={(e) => onChange({ ...filters, from: e.target.value })}
          />
        </label>

        <label>
          As-of to
          <input
            type="date"
            value={filters.to}
            onChange={(e) => onChange({ ...filters, to: e.target.value })}
          />
        </label>

        <label>
          Created from
          <input
            type="date"
            value={filters.created_from}
            onChange={(e) => onChange({ ...filters, created_from: e.target.value })}
          />
        </label>

        <label>
          Created to
          <input
            type="date"
            value={filters.created_to}
            onChange={(e) => onChange({ ...filters, created_to: e.target.value })}
          />
        </label>

        <label>
          Min confidence
          <input
            type="number"
            min="0"
            max="100"
            value={filters.min_confidence}
            onChange={(e) => onChange({ ...filters, min_confidence: e.target.value })}
            placeholder="0–100"
          />
        </label>

        <label>
          Sort
          <select
            value={filters.sort}
            onChange={(e) => onChange({ ...filters, sort: e.target.value })}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="confidence">Highest confidence</option>
          </select>
        </label>
      </div>

      <div className="signal-toggles">
        <span className="label">Signal</span>
        {['BUY', 'SELL', 'HOLD'].map((sig) => (
          <button
            key={sig}
            type="button"
            className={`signal-chip signal-${sig.toLowerCase()} ${activeSignals.includes(sig) ? 'active' : ''}`}
            onClick={() => toggleSignal(sig)}
          >
            {sig}
          </button>
        ))}
      </div>
    </section>
  );
}
