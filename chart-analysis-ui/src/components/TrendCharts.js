import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export default function TrendCharts({ summary }) {
  if (!summary) return null;
  const byDate = summary.byDate || [];
  const confidenceTrend = summary.confidenceTrend || [];

  if (!byDate.length && !confidenceTrend.length) {
    return (
      <section className="panel charts-section">
        <h2>Trends</h2>
        <p className="muted">No data for current filters.</p>
      </section>
    );
  }

  const symbols = [...new Set(confidenceTrend.map((r) => r.nse_code))];
  const palette = ['#2962ff', '#26a69a', '#e91e63', '#ff9800', '#9c27b0'];

  const confidenceByDate = {};
  for (const row of confidenceTrend) {
    if (!confidenceByDate[row.as_of_date]) {
      confidenceByDate[row.as_of_date] = { as_of_date: row.as_of_date };
    }
    confidenceByDate[row.as_of_date][row.nse_code] = row.confidence;
  }
  const confidenceChartData = Object.values(confidenceByDate).sort((a, b) =>
    String(a.as_of_date).localeCompare(String(b.as_of_date)),
  );

  return (
    <section className="panel charts-section">
      <div className="section-heading">
        <h2>Trends</h2>
        <span className="muted">Signal mix and confidence over as-of dates</span>
      </div>

      <div className="charts-grid">
        {byDate.length > 0 && (
          <div className="chart-card">
            <h3>Signals by date</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={byDate}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="as_of_date" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="buy" name="BUY" stackId="s" fill="#26a69a" />
                <Bar dataKey="sell" name="SELL" stackId="s" fill="#e91e63" />
                <Bar dataKey="hold" name="HOLD" stackId="s" fill="#78909c" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {confidenceTrend.length > 0 && (
          <div className="chart-card">
            <h3>Confidence trend</h3>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={confidenceChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="as_of_date" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Legend />
                {symbols.map((sym, i) => (
                  <Line
                    key={sym}
                    type="monotone"
                    dataKey={sym}
                    name={sym}
                    stroke={palette[i % palette.length]}
                    dot={{ r: 3 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </section>
  );
}
