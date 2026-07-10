/**
 * 测试管理 API  ? */
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

// ========== 项目 ==========
export const projectApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams({ page_size: 1000, ...params }).toString()
    return request(`/api/v1/projects/?${qs}`)
  }
}

// ========== 环境 ==========
export const environmentApi = {
  list: (projectId) => {
    const qs = projectId ? `?project=${projectId}` : ''
    return request(`/api/v1/environments/${qs}`)
  }
}

// ========== 测试用例 ==========
export const testCaseApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/v1/test-cases/?${qs}`)
  },
  get: (id) => request(`/api/v1/test-cases/${id}/`),
  create: (data) => request('/api/v1/test-cases/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/test-cases/${id}/`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/api/v1/test-cases/${id}/`, { method: 'DELETE' }),
  run: (id, data) => request(`/api/v1/test-cases/${id}/run/`, { method: 'POST', body: JSON.stringify(data) }),
  batchDelete: (ids) => request('/api/v1/test-cases/batch_delete/', { method: 'POST', body: JSON.stringify({ ids }) }),
}

// ========== 测试用例分组 ==========
export const testCaseGroupApi = {
  list: (projectId) => {
    const qs = projectId ? `?project=${projectId}` : ''
    return request(`/api/v1/test-case-groups/${qs}`)
  },
  tree: (projectId) => {
    const qs = projectId ? `?project=${projectId}` : ''
    return request(`/api/v1/test-case-groups/tree/${qs}`)
  },
  create: (data) => request('/api/v1/test-case-groups/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/test-case-groups/${id}/`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/api/v1/test-case-groups/${id}/`, { method: 'DELETE' }),
}

// ========== 测试套件 ==========
export const testSuiteApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/v1/test-suites/?${qs}`)
  },
  get: (id) => request(`/api/v1/test-suites/${id}/`),
  create: (data) => request('/api/v1/test-suites/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/test-suites/${id}/`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/api/v1/test-suites/${id}/`, { method: 'DELETE' }),
  addTestCase: (id, data) => request(`/api/v1/test-suites/${id}/add_test_case/`, { method: 'POST', body: JSON.stringify(data) }),
  removeTestCase: (id, data) => request(`/api/v1/test-suites/${id}/remove_test_case/`, { method: 'POST', body: JSON.stringify(data) }),
  updateTestCaseEnv: (id, data) => request(`/api/v1/test-suites/${id}/update_test_case_environment/`, { method: 'POST', body: JSON.stringify(data) }),
  run: (id, data) => request(`/api/v1/test-suites/${id}/run/`, { method: 'POST', body: JSON.stringify(data) }),
  cases: (id, params = {}) => request(`/api/v1/test-suites/${id}/cases/?${new URLSearchParams(params)}`),
}

// ========== 测试套件分组 ==========
export const testSuiteGroupApi = {
  list: (projectId) => {
    const qs = projectId ? `?project=${projectId}` : ''
    return request(`/api/v1/test-suite-groups/${qs}`)
  },
  tree: (projectId) => {
    const qs = projectId ? `?project=${projectId}` : ''
    return request(`/api/v1/test-suite-groups/tree/${qs}`)
  },
  create: (data) => request('/api/v1/test-suite-groups/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/test-suite-groups/${id}/`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/api/v1/test-suite-groups/${id}/`, { method: 'DELETE' }),
}

// ========== 测试运行 ==========
export const testRunApi = {
  list: (params = {}) => request(`/api/v1/test-runs/?${new URLSearchParams(params)}`),
  get: (id) => request(`/api/v1/test-runs/${id}/`),
  results: (id, params = {}) => request(`/api/v1/test-runs/${id}/results/?${new URLSearchParams(params)}`),
  stats: (id) => request(`/api/v1/test-runs/${id}/stats/`),
  remove: (id) => request(`/api/v1/test-runs/${id}/`, { method: 'DELETE' }),
}

// ========== 测试结果 ==========
export const testResultApi = {
  list: (params = {}) => request(`/api/v1/test-results/?${new URLSearchParams(params)}`),
  get: (id) => request(`/api/v1/test-results/${id}/`),
}

// ========== 场景执行 ==========
export const sceneExecutionApi = {
  list: (params = {}) => request(`/api/v1/test-scene-executions/?${new URLSearchParams(params)}`),
  get: (id) => request(`/api/v1/test-scene-executions/${id}/`),
  remove: (id) => request(`/api/v1/test-scene-executions/${id}/`, { method: 'DELETE' }),
}
