import React from 'react';
import { analysisImageUrl } from '../services/api';
import { SignalBadge } from './AnalysisList';

export default function AnalysisDetail({ analysis, loading, error }) {
  if (loading) {
    return (
      <section className="panel analysis-detail">
        <h2>Detail</h2>
        <p className="muted">Loading analysis…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel analysis-detail">
        <h2>Detail</h2>
        <p className="error-text">{error}</p>
      </section>
    );
  }

  if (!analysis) {
    return (
      <section className="panel analysis-detail">
        <h2>Detail</h2>
        <p className="muted">Select a row to view chart and analysis text.</p>
      </section>
    );
  }

  return (
    <section className="panel analysis-detail">
      <div className="section-heading">
        <div>
          <h2>{analysis.nse_code}</h2>
          <p className="muted">As of {analysis.as_of_date}</p>
        </div>
        <SignalBadge signal={analysis.signal} />
      </div>

      <div className="detail-meta">
        <div><span className="label">Created</span> {analysis.created_at || '—'}</div>
        <div><span className="label">Confidence</span> {analysis.confidence ?? '—'}</div>
        <div><span className="label">Execution</span> <span className="mono">{analysis.execution_id || '—'}</span></div>
        <div><span className="label">Sweep</span> {analysis.from_date} → {analysis.to_date}</div>
      </div>

      {analysis.has_image && (
        <div className="chart-frame">
          <img
            src={analysisImageUrl(analysis.id)}
            alt={`${analysis.nse_code} chart ${analysis.as_of_date}`}
          />
        </div>
      )}

      <div className="detail-block">
        <h3>Stage analysis</h3>
        <p className="detail-text">{analysis.summary || '—'}</p>
      </div>

      <div className="detail-block">
        <h3>Validation review</h3>
        <p className="detail-text">{analysis.review_comments || '—'}</p>
      </div>
    </section>
  );
}
