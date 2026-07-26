import config from '../config';

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value));
    }
  });
  const qs = query.toString();
  return qs ? `?${qs}` : '';
}

async function request(path) {
  const response = await fetch(`${config.API_BASE}${path}`);
  let payload = null;
  try {
    payload = await response.json();
  } catch (_err) {
    payload = null;
  }
  if (!response.ok) {
    const message = payload?.error || `Request failed (${response.status}) for ${path}`;
    const error = new Error(message);
    error.status = response.status;
    error.code = payload?.code;
    throw error;
  }
  return payload;
}

export function fetchHealth() {
  return request('/api/health');
}

export function fetchFacets() {
  return request('/api/facets');
}

export function fetchSummary(filters = {}) {
  return request(`/api/summary${buildQuery(filters)}`);
}

export function fetchAnalyses(params = {}) {
  return request(`/api/analyses${buildQuery(params)}`);
}

export function fetchAnalysis(id) {
  return request(`/api/analyses/${encodeURIComponent(id)}`);
}

export function analysisImageUrl(id) {
  return `${config.API_BASE}/api/analyses/${encodeURIComponent(id)}/image`;
}
