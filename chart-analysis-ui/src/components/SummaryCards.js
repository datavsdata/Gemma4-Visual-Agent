import React from 'react';

export default function SummaryCards({ summary }) {
  if (!summary) return null;
  const { total = 0, bySignal = {} } = summary;

  return (
    <section className="panel summary-section">
      <div className="section-heading">
        <h2>Overview</h2>
        <span className="muted">{total} matching analyses</span>
      </div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total</div>
          <div className="stat-value">{total}</div>
        </div>
        <div className="stat-card signal-buy">
          <div className="stat-label">BUY</div>
          <div className="stat-value">{bySignal.BUY ?? 0}</div>
        </div>
        <div className="stat-card signal-sell">
          <div className="stat-label">SELL</div>
          <div className="stat-value">{bySignal.SELL ?? 0}</div>
        </div>
        <div className="stat-card signal-hold">
          <div className="stat-label">HOLD</div>
          <div className="stat-value">{bySignal.HOLD ?? 0}</div>
        </div>
      </div>
    </section>
  );
}
