// API client module with fetch wrappers for the Autonotes API.
// All calls use relative paths under /api/v1/.

const BASE = '/api/v1';

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const resp = await fetch(`${BASE}${path}`, opts);
  if (!resp.ok) {
    const text = await resp.text();
    let detail = text;
    try { detail = JSON.parse(text).detail || text; } catch (_) {}
    throw new Error(`${resp.status}: ${detail}`);
  }
  return resp.json();
}

export function get(path) { return request('GET', path); }
export function post(path, body) { return request('POST', path, body); }

// Convenience methods for each view's API calls
export const api = {
  // Health
  health: () => get('/health'),
  vaultDashboard: (scope = '/') => get(`/vault-health/dashboard?scope=${encodeURIComponent(scope)}`),
  vaultTrends: (metric, scope = '/') => get(`/vault-health/trends?metric=${metric}&scope=${encodeURIComponent(scope)}`),

  // Notes
  vaultStructure: () => get('/vault-structure'),
  folder: (path) => get(`/notes/folder/${encodeURIComponent(path)}`),
  note: (path) => get(`/notes/${encodeURIComponent(path)}`),

  // Patches
  patches: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set('status', params.status);
    if (params.limit) qs.set('limit', params.limit);
    if (params.offset) qs.set('offset', params.offset);
    const q = qs.toString();
    return get(`/patches${q ? '?' + q : ''}`);
  },
  approvePatch: (id) => post(`/patches/${id}/approve`),
  rejectPatch: (id) => post(`/patches/${id}/reject`),

  // Jobs
  jobs: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set('status', params.status);
    if (params.job_type) qs.set('job_type', params.job_type);
    if (params.limit) qs.set('limit', params.limit);
    const q = qs.toString();
    return get(`/jobs${q ? '?' + q : ''}`);
  },
  job: (id) => get(`/jobs/${id}`),
  cancelJob: (id) => post(`/jobs/${id}/cancel`),
  createJob: (jobType, targetPath = '/', parameters = {}) =>
    post('/jobs', { job_type: jobType, target_path: targetPath, parameters }),

  // AI
  chat: (question, scope = null) => post('/ai/chat', { question, scope }),
  analyze: (targetPath, analysisType) =>
    post('/ai/analyze', { target_path: targetPath, analysis_type: analysisType }),

  // Logs
  logs: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.target_path) qs.set('target_path', params.target_path);
    if (params.operation_name) qs.set('operation_name', params.operation_name);
    if (params.status) qs.set('status', params.status);
    if (params.limit) qs.set('limit', params.limit);
    const q = qs.toString();
    return get(`/logs${q ? '?' + q : ''}`);
  },
};
