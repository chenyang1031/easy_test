/**
 * API 封装 ? * 所有请求统一通过此模块，自动注入 CSRF Token
 */
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
  const { timeout = 30000, ...fetchOptions } = options
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  try {
    const headers = { ...getHeaders(), ...fetchOptions.headers }
    // FormData 由浏览器自动设置 Content-Type（含 boundary），不能手动指定
    if (fetchOptions.body instanceof FormData) {
      delete headers['Content-Type']
    }
    const resp = await fetch(BASE + url, {
      ...fetchOptions,
      signal: controller.signal,
      headers,
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
  } finally {
    clearTimeout(timer)
  }
}

// ========== 业务项目 ==========
export const projectApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams({ page_size: 1000, ...params }).toString()
    return request(`/api/v1/projects/?${qs}`)
  }
}

// ========== API 项目 ==========
export const apiProjectApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams({ page_size: 1000, ...params }).toString()
    return request(`/api/v1/api-projects/?${qs}`)
  },
  resolve: (platformProjectId) => {
    return request('/api/v1/api-projects/resolve-platform-project/', {
      method: 'POST',
      body: JSON.stringify({ platform_project_id: platformProjectId })
    })
  },
  stats: (id) => {
    return request(`/api/v1/api-projects/${id}/stats/`)
  }
}

// ========== API 分组 ==========
export const apiGroupApi = {
  list: (projectId, params = {}) => {
    const qs = new URLSearchParams({ project: projectId, page_size: 1000, ...params }).toString()
    return request(`/api/v1/api-groups/?${qs}`)
  },
  create: (data) => {
    return request('/api/v1/api-groups/', { method: 'POST', body: JSON.stringify(data) })
  },
  update: (id, data) => {
    return request(`/api/v1/api-groups/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
  },
  remove: (id) => {
    return request(`/api/v1/api-groups/${id}/`, { method: 'DELETE' })
  }
}

// ========== API 资产 ==========
export const apiAssetApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/v1/api-assets/?${qs}`)
  },
  create: (data) => {
    return request('/api/v1/api-assets/', { method: 'POST', body: JSON.stringify(data) })
  },
  update: (id, data) => {
    return request(`/api/v1/api-assets/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
  },
  remove: (id) => {
    return request(`/api/v1/api-assets/${id}/`, { method: 'DELETE' })
  },
  batchDelete: (ids) => {
    return request('/api/v1/api-assets/batch-delete/', { method: 'POST', body: JSON.stringify({ ids }) })
  },
  batchMoveGroup: (ids, groupId) => {
    return request('/api/v1/api-assets/batch-move-group/', { method: 'POST', body: JSON.stringify({ ids, group_id: groupId }) })
  },
  batchUpdateStatus: (ids, status) => {
    return request('/api/v1/api-assets/batch-status/', { method: 'POST', body: JSON.stringify({ ids, status }) })
  },
  previewImport: (formData) => {
    return request('/api/v1/api-assets/import/preview', {
      method: 'POST',
      headers: { 'X-CSRFToken': getHeaders()['X-CSRFToken'] },
      body: formData,
      timeout: 120000
    })
  },
  previewImportUrl: (url, projectId) => {
    return request('/api/v1/api-assets/import/preview-url', {
      method: 'POST',
      body: JSON.stringify({ url, project_id: projectId })
    })
  },
  previewImportCurl: (curlText, projectId) => {
    return request('/api/v1/api-assets/import/preview-curl', {
      method: 'POST',
      body: JSON.stringify({ curl_text: curlText, project_id: projectId })
    })
  },
  confirmImport: (data) => {
    return request('/api/v1/api-assets/import/confirm', { method: 'POST', body: JSON.stringify(data) })
  },
  exportOpenApi: (projectId) => {
    return request('/api/v1/api-assets/export', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, format: 'json' })
    })
  }
}

// ========== AI 生成 ==========
export const aiApi = {
  generateCases: (data) => {
    return request('/api/v1/ai/generate-multi-test-cases/', { method: 'POST', body: JSON.stringify(data), timeout: 180000 })
  },
  batchGenerateCases: (data) => {
    return request('/api/v1/ai/generate-multi-test-cases/batch/', { method: 'POST', body: JSON.stringify(data) })
  },
  getRules: (params = {}) => {
    const qs = new URLSearchParams({ is_enabled: true, page_size: 100, ...params }).toString()
    return request(`/api/v1/ai/rules/?${qs}`)
  },
  getPromptTemplates: (params = {}) => {
    const qs = new URLSearchParams({ is_enabled: true, page_size: 200, ...params }).toString()
    return request(`/api/v1/ai/prompt-templates/?${qs}`)
  },
  getModelProviders: (params = {}) => {
    const qs = new URLSearchParams({ is_enabled: true, page_size: 100, ...params }).toString()
    return request(`/api/v1/ai/model-providers/?${qs}`)
  },
}
