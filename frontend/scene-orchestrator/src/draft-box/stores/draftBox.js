import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { draftApi } from '../api/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'

export const useDraftBoxStore = defineStore('draftBox', () => {
  const groups = ref([])
  const groupsLoading = ref(false)
  const groupsPage = ref(1)
  const groupsPageSize = ref(10)
  const groupsTotal = ref(0)

  const activeGroupId = ref(null)
  const activeGroup = computed(() => groups.value.find(g => g.id === activeGroupId.value) || null)

  const drafts = ref([])
  const draftsLoading = ref(false)
  const draftsPage = ref(1)
  const draftsPageSize = ref(10)
  const draftsTotal = ref(0)

  // 项目过滤
  const projects = ref([])
  const filterProjectId = ref(null)

  // 选中导入
  const selectedDraftIds = ref(new Set())
  const importing = ref(false)

  // 导入弹窗 + 套件选择
  const importDialogVisible = ref(false)
  const suites = ref([])
  const suitesLoading = ref(false)
  const importTargetType = ref('none')
  const importExistingSuiteId = ref(null)
  const importNewSuiteName = ref('')

  // 删除
  const deleting = ref(false)

  const validDrafts = computed(() => drafts.value.filter(d => d.can_select))

  // ---- 加载 ----
  async function loadGroups(page) {
    groupsLoading.value = true
    if (page) groupsPage.value = page
    try {
      const resp = await draftApi.groups(filterProjectId.value, groupsPage.value, groupsPageSize.value)
      groups.value = resp.results || resp
      groupsTotal.value = resp.count || groups.value.length
    }
    catch (err) { ElMessage.error('加载草稿组失败：' + err.message) }
    finally { groupsLoading.value = false }
  }

  function handleGroupsPageChange(page) { loadGroups(page) }
  function handleGroupsSizeChange(size) { groupsPageSize.value = size; groupsPage.value = 1; loadGroups(1) }

  async function loadProjects() {
    try {
      const resp = await fetch('/api/v1/projects/?page_size=100')
      const data = await resp.json()
      projects.value = Array.isArray(data.results) ? data.results : (Array.isArray(data) ? data : [])
    } catch { projects.value = [] }
  }

  async function setFilterProject(projectId) {
    filterProjectId.value = projectId || null
    activeGroupId.value = null
    drafts.value = []
    selectedDraftIds.value = new Set()
    groupsPage.value = 1
    await loadGroups(1)
  }

  async function loadDrafts(groupId, page) {
    activeGroupId.value = groupId
    selectedDraftIds.value = new Set()
    if (page) draftsPage.value = page
    draftsLoading.value = true
    try {
      const resp = await draftApi.drafts(groupId, draftsPage.value, draftsPageSize.value)
      drafts.value = resp.results || resp
      draftsTotal.value = resp.count || drafts.value.length
    }
    catch (err) { ElMessage.error('加载草稿失败' + err.message) }
    finally { draftsLoading.value = false }
  }

  function handleDraftsPageChange(page) { loadDrafts(activeGroupId.value, page) }
  function handleDraftsSizeChange(size) { draftsPageSize.value = size; draftsPage.value = 1; loadDrafts(activeGroupId.value, 1) }

  // ---- 选择 ----
  function toggleDraft(id) {
    const s = new Set(selectedDraftIds.value)
    if (s.has(id)) s.delete(id); else s.add(id)
    selectedDraftIds.value = s
  }

  function toggleAll() {
    if (selectedDraftIds.value.size === validDrafts.value.length) {
      selectedDraftIds.value = new Set()
    } else {
      selectedDraftIds.value = new Set(validDrafts.value.map(d => d.id))
    }
  }

  // ---- 导入 ----
  function openImportDialog() {
    if (selectedDraftIds.value.size === 0) { ElMessage.warning('请先选择草稿'); return }
    importTargetType.value = 'none'; importExistingSuiteId.value = null; importNewSuiteName.value = ''
    importDialogVisible.value = true
  }

  async function loadSuites(projectId) {
    suitesLoading.value = true
    try { suites.value = await draftApi.suites(projectId) }
    catch { suites.value = [] }
    finally { suitesLoading.value = false }
  }

  async function doImport() {
    if (importTargetType.value === 'new' && !importNewSuiteName.value.trim()) {
      ElMessage.warning('请输入套件名'); return
    }
    if (importTargetType.value === 'existing' && !importExistingSuiteId.value) {
      ElMessage.warning('请选择目标套件'); return
    }

    importing.value = true
    try {
      const ids = Array.from(selectedDraftIds.value)
      const payload = {
        draft_group_id: activeGroupId.value,
        draft_ids: ids,
        user_id: window.__CURRENT_USER_ID__ || 1,
      }
      if (importTargetType.value === 'existing') payload.target_suite_id = importExistingSuiteId.value
      else if (importTargetType.value === 'new') payload.new_suite_name = importNewSuiteName.value.trim()

      const resp = await draftApi.importCases(payload)
      let msg
      if (resp.success_count > 0) {
        msg = resp.suite_name
          ? `导入完成：${resp.success_count} 条，已导入「${resp.suite_name}」`
          : `导入完成：成功 ${resp.success_count} 条`
        if (resp.failure_count > 0) msg += `，失败 ${resp.failure_count} 条`
      } else {
        msg = `导入失败：${resp.failure_count} 条全部失败`
      }

      if (resp.success_count > 0) {
        ElMessage.success(msg)
      } else if (resp.failure_count > 0) {
        ElMessage.error(msg)
      } else {
        ElMessage.warning('没有可导入的草稿')
      }

      importDialogVisible.value = false
      selectedDraftIds.value = new Set()
      await loadDrafts(activeGroupId.value, 1)
      await loadGroups()
    } catch (err) { ElMessage.error('导入失败' + err.message) }
    finally { importing.value = false }
  }

  // ---- 删除 ----
  async function deleteSelectedDrafts() {
    if (selectedDraftIds.value.size === 0) { ElMessage.warning('请先选择草稿'); return }
    try {
      await ElMessageBox.confirm(`确定删除选中的 ${selectedDraftIds.value.size} 条草稿吗？已导入的不会被删除。`, '确认删除', {
        confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
      })
    } catch { return }

    deleting.value = true
    try {
      const ids = Array.from(selectedDraftIds.value)
      const resp = await draftApi.deleteDrafts(ids)
      ElMessage.success(`已删除 ${resp.deleted_count} 条草稿`)
      selectedDraftIds.value = new Set()
      await loadDrafts(activeGroupId.value, draftsPage.value)
      await loadGroups()
    } catch (err) { ElMessage.error('删除失败' + err.message) }
    finally { deleting.value = false }
  }

  async function deleteGroup() {
    if (!activeGroupId.value) return
    const g = activeGroup.value
    try {
      await ElMessageBox.confirm(`确定删除草稿组「${g?.name || ''}」吗？将同时删除所有草稿。`, '确认删除', {
        confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
      })
    } catch { return }

    deleting.value = true
    try {
      await draftApi.deleteGroup(activeGroupId.value)
      ElMessage.success('草稿组已删除')
      activeGroupId.value = null; drafts.value = []
      await loadGroups()
    } catch (err) { ElMessage.error('删除失败' + err.message) }
    finally { deleting.value = false }
  }

  // ---- 状态标识 ----
  function statusTag(status) {
    const map = { pending: { type: 'info', text: '待导入' }, imported: { type: 'success', text: '全部导入' }, partial_imported: { type: 'warning', text: '部分导入' } }
    return map[status] || { type: 'info', text: status }
  }

  function importStatusTag(s) {
    const map = { pending: { type: 'info', text: '待导入' }, imported: { type: 'success', text: '已导入' }, failed: { type: 'danger', text: '失败' } }
    return map[s] || { type: 'info', text: s }
  }

  function formatTime(dt) { return dt ? new Date(dt).toLocaleString('zh-CN') : '' }

  return {
    groups, groupsLoading, activeGroupId, activeGroup, drafts, draftsLoading, selectedDraftIds, validDrafts,
    groupsPage, groupsPageSize, groupsTotal, draftsPage, draftsPageSize, draftsTotal,
    importing, importDialogVisible, suites, suitesLoading, importTargetType, importExistingSuiteId, importNewSuiteName,
    deleting, projects, filterProjectId,
    loadGroups, loadProjects, setFilterProject, loadDrafts, toggleDraft, toggleAll,
    openImportDialog, loadSuites, doImport,
    deleteSelectedDrafts, deleteGroup,
    handleGroupsPageChange, handleGroupsSizeChange,
    handleDraftsPageChange, handleDraftsSizeChange,
    statusTag, importStatusTag, formatTime,
  }
})
