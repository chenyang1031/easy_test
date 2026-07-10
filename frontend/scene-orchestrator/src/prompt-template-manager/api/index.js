/**
 * 提示词模 ?API 封装 ? */
import { useCsrf } from '../composables/useCsrf.js'

const BASE = ''

function getHeaders() {
  const { getToken } = useCsrf()
  return {
    'Content-Type': 'application/json',
    'X-CSRFToken': getToken()
  }
}

async function request(url, options = {}) {
  const resp = await fetch(BASE + url, {
    ...options,
    headers: { ...getHeaders(), ...options.headers }
  })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    const err = new Error(data.detail || `HTTP ${resp.status}`)
    err.status = resp.status
    err.data = data
    throw err
  }
  if (resp.status === 204) return null
  return resp.json()
}

export const promptTemplateApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/v1/ai/prompt-templates/?${qs}`)
  },
  get: (id) => {
    return request(`/api/v1/ai/prompt-templates/${id}/`)
  },
  create: (data) => {
    return request('/api/v1/ai/prompt-templates/', { method: 'POST', body: JSON.stringify(data) })
  },
  update: (id, data) => {
    return request(`/api/v1/ai/prompt-templates/${id}/`, { method: 'PUT', body: JSON.stringify(data) })
  },
  remove: (id) => {
    return request(`/api/v1/ai/prompt-templates/${id}/`, { method: 'DELETE' })
  },
  setDefault: (templateId) => {
    return request('/api/v1/ai/prompt-templates/set-default/', {
      method: 'POST',
      body: JSON.stringify({ template_id: templateId })
    })
  },
  getDefault: () => {
    return request('/api/v1/ai/prompt-templates/default/')
  },
  importJson: (data) => {
    return request('/api/v1/ai/prompt-templates/import-json/', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  },
  exportJsonUrl: () => '/api/v1/ai/prompt-templates/export-json/'
}
