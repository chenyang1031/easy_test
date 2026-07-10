import { useCsrf } from '../../test-manager/composables/useCsrf.js'

const BASE = ''

function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-CSRFToken': useCsrf().getToken()
  }
}

async function request(url, options = {}) {
  const resp = await fetch(BASE + url, { ...options, headers: { ...getHeaders(), ...options.headers } })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    const detail = typeof data === 'object' ? (data.detail || data.error || JSON.stringify(data)) : String(data)
    const err = new Error(detail || `HTTP ${resp.status}`)
    err.status = resp.status; err.data = data; throw err
  }
  if (resp.status === 204) return null
  return resp.json()
}

export const projectApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/v1/projects/?${qs}`)
  },
  get: (id) => request(`/api/v1/projects/${id}/`),
  create: (data) => request('/api/v1/projects/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/projects/${id}/`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/api/v1/projects/${id}/`, { method: 'DELETE' }),
}
