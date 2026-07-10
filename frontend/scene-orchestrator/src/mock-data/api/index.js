/**
 * Mock 数据 API  ? */
import { useCsrf } from '../composables/useCsrf.js'

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

export const mockDataApi = {
  /** 获取列表（分 ?+ 搜索 ?*/
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/v1/mock-data/?${qs}`)
  },

  /** 获取单条 */
  get: (id) => request(`/api/v1/mock-data/${id}/`),

  /** 删除 */
  remove: (id) => request(`/api/v1/mock-data/${id}/`, { method: 'DELETE' }),

  /** 生成并保 ?Mock 数据 */
  generate: (data) => request('/api/v1/mock-data/generate/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  /** 导出数据为下载链接（直接通过浏览器下载） */
  exportUrl: (id) => `${BASE}/api/mock-data/${id}/export/`,
}
