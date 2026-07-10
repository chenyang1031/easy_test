/**
 * AI 大模型供应商 API 封装 ? */
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

export const modelProviderApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/v1/ai/model-providers/?${qs}`)
  },
  get: (id) => request(`/api/v1/ai/model-providers/${id}/`),
  create: (data) => request('/api/v1/ai/model-providers/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/ai/model-providers/${id}/`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/api/v1/ai/model-providers/${id}/`, { method: 'DELETE' }),
  setDefault: (id) => request('/api/v1/ai/model-providers/set-default/', {
    method: 'POST', body: JSON.stringify({ provider_id: id })
  }),
  test: (id) => request(`/api/v1/ai/model-providers/${id}/test/`, { method: 'POST' }),
}
