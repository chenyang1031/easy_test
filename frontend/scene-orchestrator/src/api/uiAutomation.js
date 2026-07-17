/**
 * UI 自动化 API 模块
 */
import { http } from './http'

const BASE = '/api'

// ============================================================
// 模块管理
// ============================================================
export const uiModuleApi = {
  tree(project) { return http.get(`${BASE}/ui-modules/tree/?project=${project}`) },
  list(project) { return http.get(`${BASE}/ui-modules/?project=${project}`) },
  create(data) { return http.post(`${BASE}/ui-modules/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-modules/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-modules/${id}/`) },
  move(id, data) { return http.post(`${BASE}/ui-modules/${id}/move/`, data) },
}

// ============================================================
// 页面管理
// ============================================================
export const uiPageApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-pages/?${q}`)
  },
  detail(id) { return http.get(`${BASE}/ui-pages/${id}/`) },
  create(data) { return http.post(`${BASE}/ui-pages/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-pages/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-pages/${id}/`) },
}

// ============================================================
// 元素管理
// ============================================================
export const uiElementApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-elements/?${q}`)
  },
  create(data) { return http.post(`${BASE}/ui-elements/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-elements/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-elements/${id}/`) },
  validate(id) { return http.post(`${BASE}/ui-elements/${id}/validate/`, {}) },
  usages(id) { return http.get(`${BASE}/ui-elements/${id}/usages/`) },
}

// ============================================================
// 操作步骤
// ============================================================
export const uiPageStepApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-page-steps/?${q}`)
  },
  detail(id) { return http.get(`${BASE}/ui-page-steps/${id}/`) },
  create(data) { return http.post(`${BASE}/ui-page-steps/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-page-steps/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-page-steps/${id}/`) },
}

export const uiPageStepDetailedApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-page-steps-detailed/?${q}`)
  },
  batchUpdate(data) { return http.post(`${BASE}/ui-page-steps-detailed/batch_update/`, data) },
}

// ============================================================
// 测试用例
// ============================================================
export const uiTestCaseApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-test-cases/?${q}`)
  },
  detail(id) { return http.get(`${BASE}/ui-test-cases/${id}/`) },
  create(data) { return http.post(`${BASE}/ui-test-cases/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-test-cases/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-test-cases/${id}/`) },
  batchDelete(ids) { return http.post(`${BASE}/ui-test-cases/batch_delete/`, { ids }) },
  run(id, data) { return http.post(`${BASE}/ui-test-cases/${id}/run/`, data) },
}

export const uiCaseStepApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-case-steps-detailed/?${q}`)
  },
  batchUpdate(data) { return http.post(`${BASE}/ui-case-steps-detailed/batch_update/`, data) },
}

// ============================================================
// 脚本管理
// ============================================================
export const uiScriptApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-test-scripts/?${q}`)
  },
  detail(id) { return http.get(`${BASE}/ui-test-scripts/${id}/`) },
  create(data) { return http.post(`${BASE}/ui-test-scripts/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-test-scripts/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-test-scripts/${id}/`) },
}

// ============================================================
// Page Object
// ============================================================
export const uiPageObjectApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-page-objects/?${q}`)
  },
  detail(id) { return http.get(`${BASE}/ui-page-objects/${id}/`) },
  create(data) { return http.post(`${BASE}/ui-page-objects/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-page-objects/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-page-objects/${id}/`) },
  generateCode(id) { return http.post(`${BASE}/ui-page-objects/${id}/generate_code/`, {}) },
  addElement(id, data) { return http.post(`${BASE}/ui-page-objects/${id}/add_element/`, data) },
}

// ============================================================
// 执行记录
// ============================================================
export const uiBatchApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-batch-records/?${q}`)
  },
  detail(id) { return http.get(`${BASE}/ui-batch-records/${id}/`) },
  delete(id) { return http.delete(`${BASE}/ui-batch-records/${id}/`) },
}

export const uiExecutionApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-execution-records/?${q}`)
  },
  detail(id) { return http.get(`${BASE}/ui-execution-records/${id}/`) },
  trace(id) { return http.get(`${BASE}/ui-execution-records/${id}/trace/`) },
}

export const uiTriggerApi = {
  batch(data) { return http.post(`${BASE}/ui-trigger-batch/`, data) },
}

// ============================================================
// 环境配置
// ============================================================
export const uiEnvApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-environments/?${q}`)
  },
  create(data) { return http.post(`${BASE}/ui-environments/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-environments/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-environments/${id}/`) },
}

// ============================================================
// 公共数据
// ============================================================
export const uiPublicDataApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-public-data/?${q}`)
  },
  create(data) { return http.post(`${BASE}/ui-public-data/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-public-data/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-public-data/${id}/`) },
}

// ============================================================
// 执行器
// ============================================================
export const uiActuatorApi = {
  list() { return http.get(`${BASE}/ui-actuators/`) },
  status() { return http.get(`${BASE}/ui-actuators/status/`) },
}

// ============================================================
// 定时任务
// ============================================================
export const uiScheduledTaskApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-scheduled-tasks/?${q}`)
  },
  create(data) { return http.post(`${BASE}/ui-scheduled-tasks/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-scheduled-tasks/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-scheduled-tasks/${id}/`) },
  runNow(id) { return http.post(`${BASE}/ui-scheduled-tasks/${id}/run_now/`, {}) },
  pause(id) { return http.post(`${BASE}/ui-scheduled-tasks/${id}/pause/`, {}) },
  resume(id) { return http.post(`${BASE}/ui-scheduled-tasks/${id}/resume/`, {}) },
}

// ============================================================
// AI 用例
// ============================================================
export const uiAICaseApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-ai-cases/?${q}`)
  },
  create(data) { return http.post(`${BASE}/ui-ai-cases/`, data) },
  update(id, data) { return http.put(`${BASE}/ui-ai-cases/${id}/`, data) },
  delete(id) { return http.delete(`${BASE}/ui-ai-cases/${id}/`) },
  run(id, data) { return http.post(`${BASE}/ui-ai-cases/${id}/run/`, data || {}) },
}

export const uiAIExecutionApi = {
  list(params = {}) {
    const q = new URLSearchParams(params).toString()
    return http.get(`${BASE}/ui-ai-execution-records/?${q}`)
  },
  detail(id) { return http.get(`${BASE}/ui-ai-execution-records/${id}/`) },
  stop(id) { return http.post(`${BASE}/ui-ai-execution-records/${id}/stop/`, {}) },
  report(id) { return http.get(`${BASE}/ui-ai-execution-records/${id}/report/`) },
  exportPdf(id) { return http.get(`${BASE}/ui-ai-execution-records/${id}/export_pdf/`) },
}

// ============================================================
// 仪表盘
// ============================================================
export const uiDashboardApi = {
  stats(project) {
    return http.get(`${BASE}/ui-dashboard/stats/?project=${project}`)
  },
}
