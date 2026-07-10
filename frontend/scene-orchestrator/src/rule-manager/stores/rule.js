import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ruleApi } from '../api/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const CATEGORY_LABELS = {
  param_validate: '参数校验',
  biz_logic: '业务逻辑',
  error_handle: '异常处理',
  boundary: '边界值',
  security: '安全',
  performance: '性能',
  other: '其他'
}

const PRIORITY_LABELS = { high: '高', medium: '中', low: '低' }

export const useRuleStore = defineStore('rule', () => {
  // ---- 列表状态 ----
  const rules = ref([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const loading = ref(false)

  // 筛选
  const keyword = ref('')
  const filterCategory = ref('')
  const filterPriority = ref('')
  const filterEnabled = ref('')

  // 全选
  const selectedIds = ref(new Set())

  // ---- 模态框 ----
  const modalVisible = ref(false)
  const modalTitle = ref('新建规则')
  const editingId = ref(null)
  const formData = ref({
    name: '',
    description: '',
    category: 'param_validate',
    priority: 'medium',
    rule_content: '',
    is_enabled: true
  })
  const saving = ref(false)

  // ---- 导入 ----
  const importModalVisible = ref(false)
  const importJsonContent = ref('')
  const importing = ref(false)

  // ---- 计算 ----
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  // ---- 工具 ----
  function categoryLabel(cat) { return CATEGORY_LABELS[cat] || cat }
  function priorityLabel(pri) { return PRIORITY_LABELS[pri] || pri }

  // ---- 数据加载 ----
  async function loadRules(page = 1) {
    loading.value = true
    currentPage.value = page
    selectedIds.value = new Set()
    try {
      const params = { page, page_size: pageSize.value }
      if (keyword.value) params.keyword = keyword.value
      if (filterCategory.value) params.category = filterCategory.value
      if (filterPriority.value) params.priority = filterPriority.value
      if (filterEnabled.value) params.is_enabled = filterEnabled.value

      const resp = await ruleApi.list(params)
      rules.value = resp.results || resp
      total.value = resp.count || 0
    } catch (err) {
      ElMessage.error('加载失败：' + err.message)
    } finally {
      loading.value = false
    }
  }

  async function applyFilter() { await loadRules(1) }

  // ---- 选择 ----
  function toggleSelect(id) {
    const s = new Set(selectedIds.value)
    if (s.has(id)) s.delete(id); else s.add(id)
    selectedIds.value = s
  }
  function toggleSelectAll() {
    if (selectedIds.value.size === rules.value.length) {
      selectedIds.value = new Set()
    } else {
      selectedIds.value = new Set(rules.value.map(r => r.id))
    }
  }
  function clearSelection() { selectedIds.value = new Set() }

  // ---- 批量操作 ----
  async function batchDelete() {
    if (selectedIds.value.size === 0) { ElMessage.warning('请选择规则'); return }
    try {
      await ElMessageBox.confirm(
        `确定删除选中的 ${selectedIds.value.size} 条规则吗？`,
        '批量删除', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
      )
      for (const id of selectedIds.value) {
        try { await ruleApi.remove(id) } catch (e) { /* continue */ }
      }
      ElMessage.success('删除完成')
      await loadRules(1)
    } catch (err) { if (err !== 'cancel') ElMessage.error('删除失败：' + err.message) }
  }

  async function batchToggleEnabled(enabled) {
    if (selectedIds.value.size === 0) { ElMessage.warning('请选择规则'); return }
    const label = enabled ? '启用' : '禁用'
    try {
      await ElMessageBox.confirm(`确定${label}选中的 ${selectedIds.value.size} 条规则吗？`, `批量${label}`)
      for (const id of selectedIds.value) {
        try {
          const rule = rules.value.find(r => r.id === id)
          if (rule) await ruleApi.update(id, { is_enabled: enabled })
        } catch (e) { /* continue */ }
      }
      ElMessage.success(`${label}完成`)
      await loadRules(currentPage.value)
    } catch (err) { if (err !== 'cancel') ElMessage.error('操作失败：' + err.message) }
  }

  // ---- CRUD ----
  function openCreateModal() {
    modalTitle.value = '新建规则'
    editingId.value = null
    formData.value = { name: '', description: '', category: 'param_validate', priority: 'medium', rule_content: '', is_enabled: true }
    modalVisible.value = true
  }

  async function openEditModal(id) {
    try {
      const data = await ruleApi.get(id)
      modalTitle.value = '编辑规则'
      editingId.value = data.id
      formData.value = {
        name: data.name,
        description: data.description || '',
        category: data.category || 'param_validate',
        priority: data.priority || 'medium',
        rule_content: data.rule_content || '',
        is_enabled: data.is_enabled
      }
      modalVisible.value = true
    } catch (err) {
      ElMessage.error('加载详情失败：' + err.message)
    }
  }

  async function saveRule() {
    if (!formData.value.name.trim()) { ElMessage.warning('规则名称不能为空'); return }
    if (!formData.value.rule_content.trim()) { ElMessage.warning('规则内容不能为空'); return }

    saving.value = true
    try {
      const data = {
        name: formData.value.name.trim(),
        description: formData.value.description.trim(),
        category: formData.value.category,
        priority: formData.value.priority,
        rule_content: formData.value.rule_content.trim(),
        is_enabled: formData.value.is_enabled
      }
      if (editingId.value) {
        await ruleApi.update(editingId.value, data)
        ElMessage.success('更新成功')
      } else {
        await ruleApi.create(data)
        ElMessage.success('创建成功')
      }
      modalVisible.value = false
      await loadRules(currentPage.value)
    } catch (err) {
      const errors = err.data
      let msg = '保存失败：'
      msg += errors ? Object.values(errors).flat().join('; ') : err.message
      ElMessage.error(msg)
    } finally { saving.value = false }
  }

  async function deleteRule(id, name) {
    try {
      await ElMessageBox.confirm(`确定删除规则「${name}」吗？`, '确认删除', {
        confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
      })
      await ruleApi.remove(id)
      ElMessage.success('删除成功')
      if (rules.value.length <= 1 && currentPage.value > 1) {
        await loadRules(currentPage.value - 1)
      } else {
        await loadRules(currentPage.value)
      }
    } catch (err) { if (err !== 'cancel') ElMessage.error('删除失败：' + err.message) }
  }

  // ---- 导入导出 ----
  function openImportModal() {
    importJsonContent.value = ''
    importModalVisible.value = true
  }

  async function importJson() {
    const content = importJsonContent.value.trim()
    if (!content) { ElMessage.warning('请输入JSON内容'); return }
    let data
    try { data = JSON.parse(content) } catch (e) { ElMessage.error('JSON格式错误：' + e.message); return }
    if (!Array.isArray(data)) { ElMessage.error('JSON必须是数组格式'); return }
    importing.value = true
    try {
      const resp = await ruleApi.importJson(data)
      importModalVisible.value = false
      const msg = `导入完成：创建${resp.created}条，更新${resp.updated}条`
      ElMessage[resp.errors?.length ? 'warning' : 'success'](resp.errors?.length ? msg + `，${resp.errors.length}条失败` : msg)
      await loadRules(1)
    } catch (err) { ElMessage.error('导入失败：' + err.message) }
    finally { importing.value = false }
  }

  async function exportJson() {
    try {
      const params = {}
      if (filterCategory.value) params.category = filterCategory.value
      if (filterPriority.value) params.priority = filterPriority.value
      if (filterEnabled.value) params.is_enabled = filterEnabled.value
      const data = await ruleApi.exportJson(params)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'ai_test_rules_' + new Date().toISOString().slice(0, 10) + '.json'
      a.click()
      URL.revokeObjectURL(url)
      ElMessage.success(`导出成功，共 ${data.length} 条规则`)
    } catch (err) { ElMessage.error('导出失败：' + err.message) }
  }

  return {
    rules, total, currentPage, pageSize, loading, totalPages,
    keyword, filterCategory, filterPriority, filterEnabled,
    selectedIds,
    modalVisible, modalTitle, editingId, formData, saving,
    importModalVisible, importJsonContent, importing,
    categoryLabel, priorityLabel,
    loadRules, applyFilter,
    toggleSelect, toggleSelectAll, clearSelection,
    batchDelete, batchToggleEnabled,
    openCreateModal, openEditModal, saveRule, deleteRule,
    openImportModal, importJson, exportJson
  }
})
