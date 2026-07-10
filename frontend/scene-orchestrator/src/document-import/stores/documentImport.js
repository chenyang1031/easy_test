import { defineStore } from 'pinia'
import { ref } from 'vue'
import { documentImportApi } from '../api/index.js'
import { ElMessage } from 'element-plus'

export const useDocumentImportStore = defineStore('documentImport', () => {
  // ---- 状态 ----
  const records = ref([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const loading = ref(false)

  const projectFilter = ref(null)
  const statusFilter = ref('')

  // 弹窗
  const uploadDialogVisible = ref(false)
  const importDialogVisible = ref(false)
  const currentRecordForImport = ref(null)

  // 二级页面（查看 API 详情）
  const detailRecord = ref(null)
  const detailApis = ref([])
  const detailLoading = ref(false)

  // 选项数据
  const apiProjects = ref([])
  const aiModelProviders = ref([])
  const promptTemplates = ref([])

  // ---- 方法 ----

  async function loadRecords(page = 1, silent = false) {
    if (!silent) loading.value = true
    currentPage.value = page
    try {
      const params = { page, page_size: pageSize.value }
      if (projectFilter.value) params.project_id = projectFilter.value
      if (statusFilter.value) params.status = statusFilter.value
      const resp = await documentImportApi.list(params)
      records.value = resp.results || []
      total.value = resp.count || 0
    } catch (err) {
      if (!silent) ElMessage.error('加载记录失败：' + err.message)
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function deleteRecord(id) {
    try {
      await documentImportApi.remove(id)
      ElMessage.success('删除成功')
      await loadRecords(currentPage.value)
    } catch (err) {
      ElMessage.error('删除失败：' + err.message)
    }
  }

  async function regenerateRecord(id) {
    try {
      const data = await documentImportApi.regenerate(id)
      // 更新列表中对应的记录
      const idx = records.value.findIndex(r => r.id === id)
      if (idx !== -1) {
        records.value[idx] = data
      }
      ElMessage.success('已加入重新生成队列')
      return data
    } catch (err) {
      ElMessage.error('重新生成失败：' + err.message)
      throw err
    }
  }

  async function loadDetail(id) {
    detailLoading.value = true
    try {
      const [record, apisData] = await Promise.all([
        documentImportApi.get(id),
        documentImportApi.getApis(id),
      ])
      detailRecord.value = record
      detailApis.value = apisData.apis || []
    } catch (err) {
      ElMessage.error('加载详情失败：' + err.message)
      detailRecord.value = null
      detailApis.value = []
    } finally {
      detailLoading.value = false
    }
  }

  async function loadOptions() {
    try {
      const [projects, providers, templates] = await Promise.all([
        documentImportApi.getApiProjects(),
        documentImportApi.getModelProviders(),
        documentImportApi.getPromptTemplates(),
      ])
      apiProjects.value = projects.results || projects || []
      aiModelProviders.value = providers.results || providers || []
      promptTemplates.value = templates.results || templates || []
    } catch (err) {
      console.warn('加载选项数据失败：', err)
    }
  }

  function openUploadDialog() {
    loadOptions()
    uploadDialogVisible.value = true
  }

  function openImportDialog(record) {
    currentRecordForImport.value = record
    importDialogVisible.value = true
  }

  return {
    records, total, currentPage, pageSize, loading,
    projectFilter, statusFilter,
    uploadDialogVisible, importDialogVisible, currentRecordForImport,
    detailRecord, detailApis, detailLoading,
    apiProjects, aiModelProviders, promptTemplates,

    loadRecords, deleteRecord, regenerateRecord,
    loadDetail, loadOptions,
    openUploadDialog, openImportDialog,
  }
})
