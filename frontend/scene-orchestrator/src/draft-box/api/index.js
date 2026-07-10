import { useCsrf } from '../composables/useCsrf.js'

function getHeaders() {
  const { getToken } = useCsrf()
  return { 'Content-Type': 'application/json', 'X-CSRFToken': getToken() }
}

async function request(url, options = {}) {
  const resp = await fetch(url, { ...options, headers: { ...getHeaders(), ...options.headers } })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    const err = new Error(data.detail || `HTTP ${resp.status}`)
    err.status = resp.status; err.data = data; throw err
  }
  if (resp.status === 204) return null
  return resp.json()
}

export const draftApi = {
  groups: (projectId, page = 1, pageSize = 10) => {
    const params = new URLSearchParams()
    if (projectId) params.set('project_id', projectId)
    params.set('page', page)
    params.set('page_size', pageSize)
    return request(`/api/v1/ai/draft-box/?${params.toString()}`)
  },
  drafts: (groupId, page = 1, pageSize = 10) => {
    const params = new URLSearchParams()
    params.set('draft_group_id', groupId)
    params.set('page', page)
    params.set('page_size', pageSize)
    return request(`/api/v1/ai/draft-box/drafts/?${params.toString()}`)
  },
  suites: (projectId) => request(`/api/v1/ai/draft-box/suites/?project_id=${projectId}`),
  importCases: (data) => request('/api/v1/ai/import-test-cases/', { method: 'POST', body: JSON.stringify(data) }),
  deleteDrafts: (draftIds) => request('/api/v1/ai/draft-box/delete-drafts/', { method: 'POST', body: JSON.stringify({ draft_ids: draftIds }) }),
  deleteGroup: (groupId) => request('/api/v1/ai/draft-box/delete-group/', { method: 'POST', body: JSON.stringify({ draft_group_id: groupId }) }),
}
