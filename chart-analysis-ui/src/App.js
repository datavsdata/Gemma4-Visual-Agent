import React, { useCallback, useEffect, useState } from 'react';
import './App.css';
import config from './config';
import {
  fetchHealth,
  fetchFacets,
  fetchSummary,
  fetchAnalyses,
  fetchAnalysis,
} from './services/api';
import FilterPanel, { EMPTY_FILTERS } from './components/FilterPanel';
import SummaryCards from './components/SummaryCards';
import TrendCharts from './components/TrendCharts';
import AnalysisList from './components/AnalysisList';
import AnalysisDetail from './components/AnalysisDetail';

function filtersToQuery(filters, offset = 0) {
  return {
    nse_code: filters.nse_code,
    execution_id: filters.execution_id,
    signal: filters.signal,
    from: filters.from,
    to: filters.to,
    created_from: filters.created_from,
    created_to: filters.created_to,
    min_confidence: filters.min_confidence,
    sort: filters.sort,
    limit: config.DEFAULT_PAGE_SIZE,
    offset,
  };
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [facets, setFacets] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const [summary, setSummary] = useState(null);
  const [listResult, setListResult] = useState({ analyses: [], total: 0 });
  const [selectedId, setSelectedId] = useState(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [bootError, setBootError] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [detailError, setDetailError] = useState(null);
  const [booting, setBooting] = useState(true);
  const [searching, setSearching] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      setBooting(true);
      setBootError(null);
      try {
        const [healthResult, facetsResult] = await Promise.all([
          fetchHealth(),
          fetchFacets(),
        ]);
        if (!cancelled) {
          setHealth(healthResult);
          setFacets(facetsResult);
        }
      } catch (err) {
        if (!cancelled) setBootError(err.message);
      } finally {
        if (!cancelled) setBooting(false);
      }
    }
    boot();
    return () => { cancelled = true; };
  }, []);

  const runSearch = useCallback(async (nextFilters, nextOffset = 0) => {
    setSearching(true);
    setSearchError(null);
    try {
      const params = filtersToQuery(nextFilters, nextOffset);
      const [summaryResult, listData] = await Promise.all([
        fetchSummary(params),
        fetchAnalyses(params),
      ]);
      setSummary(summaryResult);
      setListResult(listData);
      setOffset(nextOffset);
      if (listData.analyses.length > 0) {
        setSelectedId(listData.analyses[0].id);
      } else {
        setSelectedId(null);
        setSelectedAnalysis(null);
      }
    } catch (err) {
      setSearchError(err.message);
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    if (!booting && !bootError) {
      runSearch(appliedFilters, 0);
    }
  }, [booting, bootError, appliedFilters, runSearch]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedAnalysis(null);
      return undefined;
    }
    let cancelled = false;
    async function loadDetail() {
      setLoadingDetail(true);
      setDetailError(null);
      try {
        const row = await fetchAnalysis(selectedId);
        if (!cancelled) setSelectedAnalysis(row);
      } catch (err) {
        if (!cancelled) setDetailError(err.message);
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    }
    loadDetail();
    return () => { cancelled = true; };
  }, [selectedId]);

  const handleApply = () => {
    setAppliedFilters({ ...filters });
  };

  const handleReset = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  };

  return (
    <div className="App">
      <header className="App-header">
        <div>
          <h1>Chart Analysis</h1>
          <p>Browse candle-draw analyses, signals, and annotated charts.</p>
        </div>
        <div className="header-meta">
          {health && (
            <span className="badge ok">
              {health.rowCount} rows · {health.minDate || '—'} → {health.maxDate || '—'}
            </span>
          )}
        </div>
      </header>

      <main className="app-shell">
        {booting && <p className="muted">Connecting to analysis database…</p>}
        {bootError && <p className="error-text">{bootError}</p>}
        {searchError && <p className="error-text">{searchError}</p>}

        {!booting && !bootError && (
          <>
            <FilterPanel
              filters={filters}
              facets={facets}
              onChange={setFilters}
              onApply={handleApply}
              onReset={handleReset}
              loading={searching}
            />

            <div className="content-grid">
              <div className="content-main">
                <SummaryCards summary={summary} />
                <TrendCharts summary={summary} />
                <AnalysisList
                  analyses={listResult.analyses}
                  total={listResult.total}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                  offset={offset}
                  limit={config.DEFAULT_PAGE_SIZE}
                  onPageChange={(next) => runSearch(appliedFilters, next)}
                  loading={searching}
                />
              </div>
              <div className="content-side">
                <AnalysisDetail
                  analysis={selectedAnalysis}
                  loading={loadingDetail}
                  error={detailError}
                />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
