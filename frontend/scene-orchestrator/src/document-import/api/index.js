/**
 * 文档导入 API 封装 */
import { useCsrf } from '../../test-manager/composables/useCsrf.js'

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

export const documentImportApi = {
  /** 获取记录列表 */
  list(params = {}) {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/v1/ai/document-gen-records/?${qs}`)
  },

  /** 获取单条记录详情 */
  get(id) {
    return request(`/api/v1/ai/document-gen-records/${id}/`)
  },

  /** 删除记录 */
  remove(id) {
    return request(`/api/v1/ai/document-gen-records/${id}/`, { method: 'DELETE' })
  },

  /** 上传文档（multipart） */
  upload(formData) {
    return fetch(BASE + '/api/v1/ai/document-gen-records/upload/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getHeaders()['X-CSRFToken']
      },
      body: formData
    }).then(async (resp) => {
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        const err = new Error(data.detail || `HTTP ${resp.status}`)
        err.status = resp.status
        err.data = data
        throw err
      }
      return resp.json()
    })
  },

  /** 重新生成 */
  regenerate(id) {
    return request(`/api/v1/ai/document-gen-records/${id}/regenerate/`, { method: 'POST' })
  },

  /** 获取提取的 API 列表 */
  getApis(id) {
    return request(`/api/v1/ai/document-gen-records/${id}/apis/`)
  },

  /** 获取 AI 模型供应商列表 */
  getModelProviders() {
    return request('/api/v1/ai/model-providers/')
  },

  /** 获取提示词模板（筛选 API 生成分类） */
  getPromptTemplates() {
    return request('/api/v1/ai/prompt-templates/?category=api_gen')
  },

  /** 获取 API 项目列表 */
  getApiProjects() {
    return request('/api/v1/api-projects/')
  },

  /** 获取 API 分组列表 */
  getApiGroups(projectId) {
    const qs = new URLSearchParams({ project: String(projectId), page_size: '1000' }).toString()
    return request(`/api/v1/api-groups/?${qs}`)
  },

  /** 导入预览（检测冲突），支持指定分组 */
  previewImport(id, apiIndices, groupId = null) {
    const body = { api_indices: apiIndices }
    if (groupId) body.group_id = groupId
    return request(`/api/v1/ai/document-gen-records/${id}/preview-import/`, {
      method: 'POST',
      body: JSON.stringify(body)
    })
  },

  /** 确认导入，支持指定分组 */
  confirmImport(id, apiIndices, conflictStrategy = 'skip', groupId = null) {
    const body = {
      api_indices: apiIndices,
      conflict_strategy: conflictStrategy
    }
    if (groupId) body.group_id = groupId
    return request(`/api/v1/ai/document-gen-records/${id}/confirm-import/`, {
      method: 'POST',
      body: JSON.stringify(body)
    })
  },
}
