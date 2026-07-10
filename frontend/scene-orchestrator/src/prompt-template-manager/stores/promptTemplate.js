import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { promptTemplateApi } from '../api/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'

export const usePromptTemplateStore = defineStore('promptTemplate', () => {
  // ---- 状态 ----
  const templates = ref([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const loading = ref(false)
  const keyword = ref('')
  const isEnabled = ref('')

  // 筛选
  const categoryFilter = ref('')

  // 模态框状态
  const modalVisible = ref(false)
  const modalTitle = ref('新建AI提示词模板')
  const editingId = ref(null)
  const formData = ref({
    name: '',
    description: '',
    template_text: '',
    category: 'test_case_gen',
    is_default: false,
    is_enabled: true
  })
  const saving = ref(false)

  // 导入模态框
  const importModalVisible = ref(false)
  const importJsonContent = ref('')
  const importing = ref(false)

  // ---- 计算属性 ----
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  // ---- 数据加载 ----
  async function loadTemplates(page = 1) {
    loading.value = true
    currentPage.value = page
    try {
      const params = { page, page_size: pageSize.value }
      if (keyword.value) params.keyword = keyword.value
      if (isEnabled.value) params.is_enabled = isEnabled.value
      if (categoryFilter.value) params.category = categoryFilter.value

      const resp = await promptTemplateApi.list(params)
      templates.value = resp.results || resp
      total.value = resp.count || (resp.results?.length || 0)
    } catch (err) {
      ElMessage.error('加载失败：' + err.message)
    } finally {
      loading.value = false
    }
  }

  async function applyFilter() {
    await loadTemplates(1)
  }

  function resetFilter() {
    keyword.value = ''
    isEnabled.value = ''
    loadTemplates(1)
  }

  // ---- 模态框操作 ----
  function openCreateModal() {
    modalTitle.value = '新建AI提示词模板'
    editingId.value = null
    formData.value = {
      name: '',
      description: '',
      template_text: '',
      category: 'test_case_gen',
      is_default: false,
      is_enabled: true
    }
    modalVisible.value = true
  }

  async function openEditModal(id) {
    try {
      const data = await promptTemplateApi.get(id)
      modalTitle.value = '编辑AI提示词模板'
      editingId.value = data.id
      formData.value = {
        name: data.name,
        description: data.description || '',
        template_text: data.template_text,
        category: data.category || 'test_case_gen',
        is_default: data.is_default,
        is_enabled: data.is_enabled
      }
      modalVisible.value = true
    } catch (err) {
      ElMessage.error('加载模板详情失败：' + err.message)
    }
  }

  async function saveTemplate() {
    if (!formData.value.name.trim()) {
      ElMessage.warning('模板名称不能为空')
      return
    }
    if (!formData.value.template_text.trim()) {
      ElMessage.warning('模板内容不能为空')
      return
    }

    saving.value = true
    try {
      const data = {
        name: formData.value.name.trim(),
        description: formData.value.description.trim(),
        template_text: formData.value.template_text.trim(),
        category: formData.value.category || 'test_case_gen',
        is_default: formData.value.is_default,
        is_enabled: formData.value.is_enabled
      }

      if (editingId.value) {
        await promptTemplateApi.update(editingId.value, data)
        ElMessage.success('更新成功')
      } else {
        await promptTemplateApi.create(data)
        ElMessage.success('创建成功')
      }
      modalVisible.value = false
      await loadTemplates(currentPage.value)
    } catch (err) {
      const errors = err.data
      let msg = '保存失败：'
      if (errors) {
        msg += Object.values(errors).flat().join('; ')
      } else {
        msg += err.message
      }
      ElMessage.error(msg)
    } finally {
      saving.value = false
    }
  }

  // ---- 设置默认 ----
  async function setDefault(id) {
    try {
      await ElMessageBox.confirm('确定要将此模板设为默认模板吗？', '确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      await promptTemplateApi.setDefault(id)
      ElMessage.success('已设为默认模板')
      await loadTemplates(currentPage.value)
    } catch (err) {
      if (err !== 'cancel') {
        ElMessage.error('设置失败：' + err.message)
      }
    }
  }

  // ---- 删除 ----
  async function deleteTemplate(id, name) {
    try {
      await ElMessageBox.confirm(`确定要删除模板「${name}」吗？`, '确认删除', {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      })
      await promptTemplateApi.remove(id)
      ElMessage.success('删除成功')
      // 如果当前页没有数据且不是第一页，回退一页
      if (templates.value.length <= 1 && currentPage.value > 1) {
        await loadTemplates(currentPage.value - 1)
      } else {
        await loadTemplates(currentPage.value)
      }
    } catch (err) {
      if (err !== 'cancel') {
        ElMessage.error('删除失败：' + err.message)
      }
    }
  }

  // ---- 导入导出 ----
  function openImportModal() {
    importJsonContent.value = ''
    importModalVisible.value = true
  }

  async function importJson() {
    const content = importJsonContent.value.trim()
    if (!content) {
      ElMessage.warning('请输入JSON内容')
      return
    }

    let data
    try {
      data = JSON.parse(content)
    } catch (e) {
      ElMessage.error('JSON格式错误：' + e.message)
      return
    }

    if (!Array.isArray(data)) {
      ElMessage.error('JSON必须是数组格式')
      return
    }

    importing.value = true
    try {
      const resp = await promptTemplateApi.importJson(data)
      importModalVisible.value = false
      const msg = `导入完成：创建${resp.created}条，更新${resp.updated}条`
      if (resp.errors?.length) {
        console.warn('导入错误：', resp.errors)
        ElMessage.warning(msg + `，${resp.errors.length}条失败`)
      } else {
        ElMessage.success(msg)
      }
      await loadTemplates(1)
    } catch (err) {
      ElMessage.error('导入失败：' + err.message)
    } finally {
      importing.value = false
    }
  }

  function exportJson() {
    window.location.href = promptTemplateApi.exportJsonUrl()
  }

  return {
    // 状态
    templates, total, currentPage, pageSize, loading, keyword, isEnabled, categoryFilter,
    modalVisible, modalTitle, editingId, formData, saving,
    importModalVisible, importJsonContent, importing,
    // 计算属性
    totalPages,
    // 方法
    loadTemplates, applyFilter, resetFilter,
    openCreateModal, openEditModal, saveTemplate,
    setDefault, deleteTemplate,
    openImportModal, importJson, exportJson
  }
})
