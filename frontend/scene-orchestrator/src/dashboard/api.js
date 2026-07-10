/**
 * Dashboard API 封装
 */
const API_BASE = '/api/v1/dashboard/stats/'

async function fetchStats(params = {}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', params.page)
  if (params.projectId) qs.set('project_id', params.projectId)
  const url = qs.toString() ? `${API_BASE}?${qs.toString()}` : API_BASE
  const resp = await fetch(url)
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    throw new Error(data.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export { fetchStats }
