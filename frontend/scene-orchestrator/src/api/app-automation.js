/**
 * APP自动化测试 API — easy_test 适配版
 *
 * 使用项目 http.js fetch 封装，保持与 testfusion 相同的导出函数名。
 */
import { http } from './http.js'

const BASE = '/api/v1/app-automation'

// ---- 内部工具函数 ----
// 将 http.js 的直接返回数据包装为 { data: ... } 格式，
// 兼容 testfusion 中 axios 响应格式（组件统一使用 res.data.xxx）

async function wrap(fn) {
  const result = await fn()
  return { data: result }
}

function get(url, params) {
  let fullUrl = `${BASE}${url}`
  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
    ).toString()
    if (qs) fullUrl += `?${qs}`
  }
  return wrap(() => http.get(fullUrl))
}

function post(url, data, opts = {}) {
  return wrap(() => http.post(`${BASE}${url}`, data, { timeoutMs: opts.timeout }))
}

function put(url, data) {
  return wrap(() => http.put(`${BASE}${url}`, data))
}

function patch(url, data) {
  return wrap(() => http.patch(`${BASE}${url}`, data))
}

function del(url) {
  return wrap(() => http.delete(`${BASE}${url}`))
}

// ========== 项目管理 ==========

export function getAppProjects(params) { return get('/projects/', params) }
export function getAppProject(id) { return get(`/projects/${id}/`) }
export function createAppProject(data) { return post('/projects/', data) }
export function updateAppProject(id, data) { return put(`/projects/${id}/`, data) }
export function deleteAppProject(id) { return del(`/projects/${id}/`) }

// ========== 配置管理 ==========

export function getAppConfig() { return get('/config/current/') }
export function updateAppConfig(data) { return post('/config/save/', data) }

// ========== Dashboard ==========

export function getDashboardStatistics() { return get('/dashboard/statistics/') }

// ========== 设备管理 ==========

export function getDeviceList(params) { return get('/devices/', params) }
export function captureDeviceScreenshot(id) { return post(`/devices/${id}/screenshot/`, null, { timeout: 15000 }) }
export function deleteDevice(id) { return del(`/devices/${id}/`) }
export function discoverDevices(params) { return get('/devices/discover/', params) }
export function lockDevice(id) { return post(`/devices/${id}/lock/`) }
export function unlockDevice(id) { return post(`/devices/${id}/unlock/`) }
export function disconnectDevice(id) { return post(`/devices/${id}/disconnect/`) }
export function connectDevice(data) { return post('/devices/connect/', data) }

// ========== 元素管理 ==========

export function getAppElementList(params) { return get('/elements/', params) }
export function createAppElement(data) { return post('/elements/', data) }
export function updateAppElement(id, data) { return put(`/elements/${id}/`, data) }
export function deleteAppElement(id) { return del(`/elements/${id}/`) }

export function uploadAppElementImage(file, category = 'common', elementId = null) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('category', category)
  if (elementId) {
    formData.append('element_id', String(elementId))
  }
  return wrap(() => http.post(`${BASE}/elements/upload/`, formData))
}

export function getAppImageCategories() { return get('/elements/image-categories/') }
export function createAppImageCategory(name) { return post('/elements/image-categories/create/', { name }) }
export function deleteAppImageCategory(name) { return del(`/elements/image-categories/${name}/`) }

// ========== 应用包名管理 ==========

export function getPackageList(params) { return get('/packages/', params) }
export function createPackage(data) { return post('/packages/', data) }
export function updatePackage(id, data) { return put(`/packages/${id}/`, data) }
export function deletePackage(id) { return del(`/packages/${id}/`) }

// ========== 测试用例管理 ==========

export function getTestCaseList(params) { return get('/test-cases/', params) }
export function getTestCaseDetail(id) { return get(`/test-cases/${id}/`) }
export function createTestCase(data) { return post('/test-cases/', data) }
export function updateTestCase(id, data) { return put(`/test-cases/${id}/`, data) }
export function deleteTestCase(id) { return del(`/test-cases/${id}/`) }
export function executeTestCase(id, data) { return post(`/test-cases/${id}/execute/`, data) }

// ========== 执行记录管理 ==========

export function getExecutionList(params) { return get('/executions/', params) }
export function getExecutionDetail(id) { return get(`/executions/${id}/`) }
export function getWsStatus() { return get('/executions/ws_status/') }
export function deleteExecution(id) { return del(`/executions/${id}/`) }
export function stopExecution(id) { return post(`/executions/${id}/stop/`) }

// ========== 测试套件管理 ==========

export function getTestSuiteList(params) { return get('/test-suites/', params) }
export function getTestSuiteDetail(id) { return get(`/test-suites/${id}/`) }
export function createTestSuite(data) { return post('/test-suites/', data) }
export function updateTestSuite(id, data) { return patch(`/test-suites/${id}/`, data) }
export function deleteTestSuite(id) { return del(`/test-suites/${id}/`) }
export function getTestSuiteTestCases(id) { return get(`/test-suites/${id}/test_cases/`) }
export function addTestCaseToSuite(suiteId, data) { return post(`/test-suites/${suiteId}/add_test_case/`, data) }
export function addTestCasesToSuite(suiteId, data) { return post(`/test-suites/${suiteId}/add_test_cases/`, data) }
export function removeTestCaseFromSuite(suiteId, data) { return post(`/test-suites/${suiteId}/remove_test_case/`, data) }
export function updateSuiteTestCaseOrder(suiteId, data) { return post(`/test-suites/${suiteId}/update_test_case_order/`, data) }
export function runTestSuite(suiteId, data) { return post(`/test-suites/${suiteId}/run/`, data) }
export function getTestSuiteExecutions(suiteId) { return get(`/test-suites/${suiteId}/executions/`) }

// ========== 组件库管理 ==========

export function getComponents(params) { return get('/components/', params) }
export function getCustomComponents(params) { return get('/custom-components/', params) }
export function createCustomComponent(data) { return post('/custom-components/', data) }
export function updateCustomComponent(id, data) { return put(`/custom-components/${id}/`, data) }
export function deleteCustomComponent(id) { return del(`/custom-components/${id}/`) }
export function importComponentPackage(data) {
  return wrap(() => http.post(`${BASE}/component-packages/`, data))
}
export function exportComponentPackage(params) {
  // blob 响应需要原生 fetch，包装为 axios 风格的 { data, headers } 格式
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  return fetch(`/api/v1${BASE}/component-packages/export/${qs}`, {
    headers: { 'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '' }
  }).then(async r => {
    const blob = await r.blob()
    return { data: blob, headers: Object.fromEntries(r.headers.entries()) }
  })
}

// ========== 定时任务管理 ==========

export function getAppScheduledTasks(params) { return get('/scheduled-tasks/', params) }
export function getAppScheduledTaskDetail(id) { return get(`/scheduled-tasks/${id}/`) }
export function createAppScheduledTask(data) { return post('/scheduled-tasks/', data) }
export function updateAppScheduledTask(id, data) { return patch(`/scheduled-tasks/${id}/`, data) }
export function deleteAppScheduledTask(id) { return del(`/scheduled-tasks/${id}/`) }
export function pauseAppScheduledTask(id) { return post(`/scheduled-tasks/${id}/pause/`) }
export function resumeAppScheduledTask(id) { return post(`/scheduled-tasks/${id}/resume/`) }
export function runAppScheduledTask(id) { return post(`/scheduled-tasks/${id}/run_now/`) }

// ========== 通知日志 ==========

export function getAppNotificationLogs(params) { return get('/notification-logs/', params) }
export function retryAppNotification(id) { return post(`/notification-logs/${id}/retry/`) }
