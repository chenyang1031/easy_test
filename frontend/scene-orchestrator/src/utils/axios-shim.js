/**
 * axios 兼容 shim — 复用项目已有的 fetch + CSRF 封装
 * 供从 testfusion 复制过来的 DataFactory.vue 使用
 */
import { useCsrf } from '../shared/composables/useCsrf.js'

function getHeaders() {
  const { getToken } = useCsrf()
  return {
    'Content-Type': 'application/json',
    'X-CSRFToken': getToken()
  }
}

async function _request(url, options = {}) {
  const resp = await fetch(url, {
    ...options,
    headers: { ...getHeaders(), ...options.headers },
    credentials: 'same-origin',
  })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    const err = new Error(data.detail || data.error || `HTTP ${resp.status}`)
    err.response = { status: resp.status, data }
    throw err
  }
  const data = await resp.json().catch(() => null)
  return { data, status: resp.status }
}

const axios = {
  get: (url, config = {}) => {
    const params = config.params
    if (params) {
      const qs = new URLSearchParams(params).toString()
      if (qs) url += (url.includes('?') ? '&' : '?') + qs
    }
    return _request(url, { method: 'GET' })
  },
  post: (url, data) => {
    return _request(url, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  delete: (url) => {
    return _request(url, { method: 'DELETE' })
  },
}

export default axios
