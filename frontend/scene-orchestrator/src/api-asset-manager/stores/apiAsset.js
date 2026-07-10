/**
 * API资产管理 - Pinia Store
 * 统一管理所有页面状态和API调用
 */
import { defineStore } from 'pinia'
import { projectApi, apiProjectApi, apiGroupApi, apiAssetApi, aiApi } from '../api/index.js'

// sessionStorage key 用于持久化选中项目
const STORAGE_KEY = 'api_asset_manager_state'

function loadPersistedState() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) { /* ignore */ }
  return null
}

function persistState(state) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      platformProjectId: state.platformProjectId,
      currentGroupId: state.currentGroupId,
      currentPage: state.currentPage,
      pageSize: state.pageSize,
      searchKeyword: state.searchKeyword,
      filterMethod: state.filterMethod,
      filterStatus: state.filterStatus,
      expandedGroupIds: Array.from(state.expandedGroupIds),
    }))
  } catch (e) { /* ignore */ }
}

export const useApiAssetStore = defineStore('apiAsset', {
  // ========== State ==========
  state: () => ({
    // --- 项目 ---
    platformProjects: [],        // 业务项目列表 [{id, name, ...}]
    platformProjectId: null,     // 当前选中的业务项目ID
    currentProjectId: null,      // 对应的API项目ID (apiProjectId)
    apiProjects: [],             // API项目列表
    projectStats: null,          // 项目统计数据

    // --- 分组 ---
    groupTreeData: [],           // 分组树数据（扁平后构建）
    flatGroupList: [],           // 扁平分组列表（用于下拉选择）
    currentGroupId: null,        // 当前选中的分组ID（null=全部）
    expandedGroupIds: new Set(), // 展开的分组ID集合
    groupSearchKeyword: '',      // 分组搜索关键词

    // --- 资产 ---
    assets: [],                  // 当前页资产列表
    selectedAssetIds: new Set(), // 选中的资产ID
    currentPage: 1,
    pageSize: 10,
    totalCount: 0,
    searchKeyword: '',
    filterMethod: '',
    filterStatus: '',

    // --- AI生成 ---
    aiRules: [],                 // 可用规则列表
    aiPromptTemplates: [],       // 可用提示词模板列表
    aiModelProviders: [],        // AI大模型供应商列表
    aiSelectedAssets: [],        // 选中要生成的资产
    aiGenerateProgress: null,    // { current, total, success, fail }

    // --- UI ---
    loading: false,
    error: null,
  }),

  // ========== Getters ==========
  getters: {
    totalPages: (state) => Math.ceil(state.totalCount / state.pageSize) || 1,

    currentProject: (state) => state.platformProjects.find(p => p.id === state.platformProjectId),

    hasSelection: (state) => state.selectedAssetIds.size > 0,

    flatGroupsForSelect: (state) => {
      const result = [{ id: null, displayName: '根目录', depth: 0 }]
      state.flatGroupList.forEach(g => {
        result.push({ id: g.id, displayName: g.displayName, depth: g.depth })
      })
      return result
    },
  },

  // ========== Actions ==========
  actions: {
    /** 设置错误 */
    setError(err) {
      this.error = err?.message || String(err || '')
      console.error('[apiAsset store]', err)
    },
    clearError() {
      this.error = null
    },

    // ===== 项目相关 =====

    /** 加载业务项目列表 */
    async fetchProjects() {
      try {
        const data = await projectApi.list()
        const results = Array.isArray(data.results) ? data.results : (Array.isArray(data) ? data : [])
        this.platformProjects = results

        // 尝试恢复上次选中的项目
        const persisted = loadPersistedState()
        if (persisted && persisted.platformProjectId) {
          const found = results.find(p => String(p.id) === String(persisted.platformProjectId))
          if (found) {
            await this.selectProject(found.id, persisted)
            return
          }
        }
        // 默认选中第一个项目
        if (results.length > 0) {
          await this.selectProject(results[0].id)
        }
      } catch (e) {
        this.setError(e)
        throw e
      }
    },

    /** 选择项目 */
    async selectProject(platformProjectId, persistedState = null) {
      this.platformProjectId = platformProjectId

      try {
        const data = await apiProjectApi.resolve(platformProjectId)
        this.currentProjectId = data.api_project_id
      } catch (e) {
        this.setError(e)
        return
      }

      // 恢复状态或重置
      if (persistedState) {
        this.currentGroupId = persistedState.currentGroupId ?? null
        this.currentPage = Math.max(1, persistedState.currentPage || 1)
        this.pageSize = [10, 20, 50, 100].includes(persistedState.pageSize) ? persistedState.pageSize : 10
        this.searchKeyword = persistedState.searchKeyword || ''
        this.filterMethod = persistedState.filterMethod || ''
        this.filterStatus = persistedState.filterStatus || ''
        this.groupSearchKeyword = persistedState.groupSearchKeyword || ''
        this.expandedGroupIds = new Set(Array.isArray(persistedState.expandedGroupIds) ? persistedState.expandedGroupIds : [])
      } else {
        this.currentGroupId = null
        this.currentPage = 1
        this.searchKeyword = ''
        this.filterMethod = ''
        this.filterStatus = ''
        this.expandedGroupIds = new Set()
      }

      await Promise.all([
        this.fetchGroups(),
        this.fetchAssets(),
        this.fetchProjectStats(),
      ])

      persistState(this)
    },

    /** 加载项目统计 */
    async fetchProjectStats() {
      if (!this.currentProjectId) return
      try {
        this.projectStats = await apiProjectApi.stats(this.currentProjectId)
      } catch (e) {
        this.setError(e)
        this.projectStats = null
      }
    },

    // ===== 分组相关 =====

    /** 加载分组列表并构建树 */
    async fetchGroups() {
      if (!this.currentProjectId) return
      try {
        const data = await apiGroupApi.list(this.currentProjectId)
        const rawGroups = data.results || data
        const flat = Array.isArray(rawGroups) ? rawGroups : []

        // 构建树形结构
        this.groupTreeData = this._buildGroupTree(flat)

        // 扁平化分组列表（用于下拉选择）
        this.flatGroupList = this._flattenGroups(this.groupTreeData)
      } catch (e) {
        this.setError(e)
      }
    },

    /** 将扁平分组建为树 */
    _buildGroupTree(flat) {
      const byId = {}
      flat.forEach(g => {
        if (g && g.id != null) {
          byId[g.id] = { ...g, children: [] }
        }
      })
      const roots = []
      flat.forEach(g => {
        if (!g || g.id == null) return
        const node = byId[g.id]
        const pid = g.parent
        if (pid == null || pid === undefined || pid === '') {
          roots.push(node)
        } else {
          const p = byId[pid]
          if (p) p.children.push(node)
          else roots.push(node)
        }
      })
      // 排序
      const sortRec = (nodes) => {
        nodes.sort((a, b) => (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0) || (Number(a.id) - Number(b.id)))
        nodes.forEach(n => n.children && n.children.length && sortRec(n.children))
      }
      sortRec(roots)
      return roots
    },

    /** 递归扁平化分组树 */
    _flattenGroups(groups, prefix = '', depth = 0) {
      const result = []
      ;(groups || []).forEach(g => {
        const displayName = prefix ? prefix + ' / ' + g.name : g.name
        result.push({ id: g.id, name: g.name, displayName, depth, parent: g.parent })
        if (g.children && g.children.length) {
          result.push(...this._flattenGroups(g.children, displayName, depth + 1))
        }
      })
      return result
    },

    /** 选中分组 */
    selectGroup(groupId) {
      this.currentGroupId = groupId
      this.currentPage = 1
      this.selectedAssetIds = new Set()
      this.fetchAssets()
      persistState(this)
    },

    /** 创建分组 */
    async createGroup(name, parentId) {
      if (!this.currentProjectId) throw new Error('未选择项目')
      const payload = { project: this.currentProjectId, name }
      if (parentId) payload.parent = Number(parentId)
      try {
        await apiGroupApi.create(payload)
        await Promise.all([this.fetchGroups(), this.fetchProjectStats()])
      } catch (e) {
        this.setError(e)
        throw e
      }
    },

    /** 删除分组 */
    async deleteGroup(groupId) {
      try {
        await apiGroupApi.remove(groupId)
        if (this.currentGroupId === groupId) {
          this.currentGroupId = null
        }
        await Promise.all([this.fetchGroups(), this.fetchProjectStats(), this.fetchAssets()])
      } catch (e) {
        this.setError(e)
        throw e
      }
    },

    // ===== 资产相关 =====

    /** 加载资产列表 */
    async fetchAssets() {
      if (!this.currentProjectId) return
      try {
        const params = {
          project: this.currentProjectId,
          page: String(this.currentPage),
          page_size: String(this.pageSize),
        }
        if (this.currentGroupId) params.group = String(this.currentGroupId)
        if (this.searchKeyword) params.search = this.searchKeyword
        if (this.filterMethod) params.method = this.filterMethod
        if (this.filterStatus) params.status = this.filterStatus

        const data = await apiAssetApi.list(params)
        const results = data.results || data
        if (Array.isArray(results)) {
          this.assets = results
          this.totalCount = data.count ?? results.length
        } else {
          this.assets = Array.isArray(data) ? data : []
          this.totalCount = this.assets.length
        }
      } catch (e) {
        this.setError(e)
        this.assets = []
        this.totalCount = 0
      }
    },

    /** 切换资产选中状态 */
    toggleAssetSelect(assetId) {
      const newSet = new Set(this.selectedAssetIds)
      if (newSet.has(assetId)) newSet.delete(assetId)
      else newSet.add(assetId)
      this.selectedAssetIds = newSet
    },

    /** 全选/取消全选当前页 */
    toggleSelectAll(checked) {
      if (checked) {
        this.selectedAssetIds = new Set(this.assets.map(a => a.id))
      } else {
        this.selectedAssetIds = new Set()
      }
    },

    /** 批量删除 */
    async batchDelete(ids) {
      try {
        await apiAssetApi.batchDelete(ids)
        this.selectedAssetIds = new Set()
        await this.fetchAssets()
        await this.fetchProjectStats()
      } catch (e) {
        this.setError(e)
        throw e
      }
    },

    /** 批量移动分组 */
    async batchMoveGroup(ids, groupId) {
      try {
        await apiAssetApi.batchMoveGroup(ids, groupId)
        this.selectedAssetIds = new Set()
        await this.fetchAssets()
      } catch (e) {
        this.setError(e)
        throw e
      }
    },

    /** 批量更新状态 */
    async batchUpdateStatus(ids, status) {
      try {
        await apiAssetApi.batchUpdateStatus(ids, status)
        this.selectedAssetIds = new Set()
        await this.fetchAssets()
        await this.fetchProjectStats()
      } catch (e) {
        this.setError(e)
        throw e
      }
    },

    /** 导出 OpenAPI */
    async exportOpenApi() {
      if (!this.currentProjectId) throw new Error('未选择项目')
      try {
        const data = await apiAssetApi.exportOpenApi(this.currentProjectId)
        // 触发浏览器下载
        const blob = new Blob([JSON.stringify(data.content, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `api_project_${this.currentProjectId}_openapi.json`
        a.click()
        URL.revokeObjectURL(url)
      } catch (e) {
        this.setError(e)
        throw e
      }
    },

    // ===== AI生成相关 =====

    /** 加载AI规则列表 */
    async fetchAIGenerationRules() {
      try {
        const data = await aiApi.getRules()
        this.aiRules = data.results || data || []
      } catch (e) {
        this.setError(e)
        this.aiRules = []
      }
    },

    /** 加载提示词模板列表 */
    async fetchAIPromptTemplates() {
      try {
        const data = await aiApi.getPromptTemplates()
        this.aiPromptTemplates = data.results || data || []
      } catch (e) {
        this.setError(e)
        this.aiPromptTemplates = []
      }
    },

    /** 加载AI大模型供应商列表 */
    async fetchAIModelProviders() {
      try {
        const data = await aiApi.getModelProviders()
        this.aiModelProviders = data.results || data || []
      } catch (e) {
        this.setError(e)
        this.aiModelProviders = []
      }
    },

    /** 设置要生成的资产 */
    setAISelectedAssets(assets) {
      this.aiSelectedAssets = assets || []
    },

    /**
     * AI批量生成测试用例（提交到后端异步处理）
     * @param {Array<number>} ruleIds - 选中的规则ID列表
     * @param {string} caseType - 用例类型
     * @param {Function} onProgress - 进度回调 (current, total, success, fail)
     * @param {number|null} promptTemplateId - 提示词模板ID
     * @param {number|null} modelProviderId - AI大模型供应商ID
     */
    async aiGenerateTestCases(ruleIds, caseType, onProgress, promptTemplateId, modelProviderId) {
      if (this.aiSelectedAssets.length === 0) throw new Error('无选中接口')
      if (!this.currentProjectId) throw new Error('未选择项目')

      const total = this.aiSelectedAssets.length

      // 改用 batch 接口：一次提交所有接口ID，后端 Celery 异步处理
      const resp = await aiApi.batchGenerateCases({
        project_id: this.currentProjectId,
        interface_ids: this.aiSelectedAssets.map(a => a.id),
        case_type: caseType || 'api',
        rule_ids: ruleIds.filter(id => id > 0),
        model_provider_id: modelProviderId || null,
        prompt_template_id: promptTemplateId || null,
      })

      // 后端已创建记录（status=generating），通知前端完成提交
      if (onProgress) {
        onProgress(total, total, total, 0)
      }

      return {
        successCount: resp.total || total,
        failCount: 0,
        errors: [],
        record_ids: resp.record_ids || [],
      }
    },
  },
})
