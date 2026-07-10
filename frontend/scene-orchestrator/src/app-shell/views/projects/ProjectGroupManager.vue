<template>
  <div class="project-group-manager">
    <!-- 头部 -->
    <div class="gm-header">
      <div class="gm-header-left">
        <el-icon :size="16" color="#409eff"><Folder /></el-icon>
        <span class="gm-title">项目分组</span>
        <el-tag v-if="totalGroupCount > 0" size="small" type="info" effect="plain" class="group-count-tag">
          {{ totalGroupCount }} 个分组
        </el-tag>
      </div>
      <div class="gm-header-actions">
        <el-button size="small" @click="loadGroups" :icon="Refresh" circle />
        <el-button size="small" type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon> 新建分组
        </el-button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="gm-loading">
      <el-icon class="is-loading"><Loading /></el-icon> 加载中...
    </div>

    <!-- 分组树 -->
    <div v-else-if="groupTree.length > 0" class="gm-tree">
      <div
        class="gm-tree-item gm-all-item"
        :class="{ active: !selectedGroupId }"
        @click="selectedGroupId = null"
      >
        <div class="gm-tree-item-left">
          <el-icon :size="14" color="#409eff"><FolderOpened /></el-icon>
          <span class="gm-tree-label">全部分组</span>
        </div>
        <span class="gm-tree-badge">{{ totalAssetCount }}</span>
      </div>
      <GroupTreeNode
        v-for="node in groupTree"
        :key="node.id"
        :node="node"
        :depth="0"
        :selected-group-id="selectedGroupId"
        @select="selectedGroupId = $event"
        @delete="(n) => handleDeleteGroupNode(n)"
      />
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && !noApiProject" class="gm-empty">
      <el-empty description="暂无分组，点击上方按钮创建" :image-size="48" />
    </div>

    <!-- 无 API 项目 -->
    <div v-else-if="noApiProject" class="gm-empty">
      <el-empty description="该项目未关联 API 资产项目" :image-size="48" />
    </div>

    <!-- 新建分组弹窗 -->
    <el-dialog
      v-model="showCreateDialog"
      title="新建分组"
      width="420px"
      :close-on-click-modal="false"
      @open="resetForm"
    >
      <el-form :model="form" label-position="top" @submit.prevent="handleCreate">
        <el-form-item label="分组名称" required>
          <el-input
            v-model="form.name"
            placeholder="请输入分组名称"
            maxlength="100"
            ref="nameInputRef"
          />
        </el-form-item>
        <el-form-item label="父分组">
          <el-select
            v-model="form.parentId"
            placeholder="根目录"
            clearable
            style="width:100%"
          >
            <el-option
              v-for="g in flatGroupList"
              :key="g.id"
              :label="g.displayName"
              :value="g.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <div v-if="createError" class="gm-error">{{ createError }}</div>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useCsrf } from '../../../api-asset-manager/composables/useCsrf.js'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Folder, FolderOpened, Plus, Refresh, Loading } from '@element-plus/icons-vue'
import GroupTreeNode from './ProjectGroupTreeNode.vue'

const props = defineProps({
  projectId: { type: [Number, String], required: true },
})

// ========== API 请求封装 ==========
const BASE = ''
function getHeaders() {
  const { getToken } = useCsrf()
  return {
    'Content-Type': 'application/json',
    'X-CSRFToken': getToken(),
  }
}
async function request(url, options = {}) {
  const resp = await fetch(BASE + url, {
    ...options,
    headers: { ...getHeaders(), ...options.headers },
  })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    const detail = typeof data === 'object' ? (data.detail || data.error || JSON.stringify(data)) : String(data)
    const err = new Error(detail || `HTTP ${resp.status}`)
    err.status = resp.status
    err.data = data
    throw err
  }
  if (resp.status === 204) return null
  return resp.json()
}

// ========== State ==========
const loading = ref(false)
const groupTree = ref([])
const flatGroupList = ref([])
const selectedGroupId = ref(null)
const totalAssetCount = ref(0)
const noApiProject = ref(false)

// 创建分组
const showCreateDialog = ref(false)
const creating = ref(false)
const createError = ref('')
const form = ref({ name: '', parentId: null })
const nameInputRef = ref(null)

// API 项目 ID
const apiProjectId = ref(null)

const totalGroupCount = computed(() => {
  return flatGroupList.value.length
})

// ========== API 项目解析 ==========
async function resolveApiProject() {
  try {
    noApiProject.value = false
    const data = await request('/api/v1/api-projects/resolve-platform-project/', {
      method: 'POST',
      body: JSON.stringify({ platform_project_id: Number(props.projectId) })
    })
    apiProjectId.value = data.api_project_id
    return data.api_project_id
  } catch (e) {
    apiProjectId.value = null
    if (e.status === 404) {
      noApiProject.value = true
    }
    return null
  }
}

// ========== 加载分组 ==========
async function loadGroups() {
  loading.value = true
  try {
    const apiId = await resolveApiProject()
    if (!apiId) {
      groupTree.value = []
      flatGroupList.value = []
      totalAssetCount.value = 0
      return
    }
    const qs = new URLSearchParams({ project: apiId, page_size: 1000 }).toString()
    const data = await request(`/api/v1/api-groups/?${qs}`)
    const rawGroups = data.results || data
    const flat = Array.isArray(rawGroups) ? rawGroups : []

    // 构建树
    groupTree.value = buildGroupTree(flat)
    // 扁平化列表（用于下拉选择父分组）
    flatGroupList.value = flattenGroups(groupTree.value)
    // 加载资产数量统计
    await loadAssetStats(apiId)
  } catch (e) {
    console.error('[ProjectGroupManager] 加载分组失败', e)
    groupTree.value = []
    flatGroupList.value = []
  } finally {
    loading.value = false
  }
}

async function loadAssetStats(apiId) {
  try {
    const data = await request(`/api/v1/api-projects/${apiId}/stats/`)
    totalAssetCount.value = data?.total_api_assets || 0
  } catch {
    totalAssetCount.value = 0
  }
}

function buildGroupTree(flat) {
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
  const sortRec = (nodes) => {
    nodes.sort((a, b) => (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0) || (Number(a.id) - Number(b.id)))
    nodes.forEach(n => n.children && n.children.length && sortRec(n.children))
  }
  sortRec(roots)
  return roots
}

function flattenGroups(groups, prefix = '', depth = 0) {
  const result = []
  ;(groups || []).forEach(g => {
    const displayName = prefix ? prefix + ' / ' + g.name : g.name
    result.push({ id: g.id, name: g.name, displayName, depth, parent: g.parent })
    if (g.children && g.children.length) {
      result.push(...flattenGroups(g.children, displayName, depth + 1))
    }
  })
  return result
}

// ========== 创建分组 ==========
function resetForm() {
  form.value = { name: '', parentId: null }
  createError.value = ''
  nextTick(() => {
    nameInputRef.value?.focus()
  })
}

async function handleCreate() {
  const name = (form.value.name || '').trim()
  if (!name) {
    createError.value = '请输入分组名称'
    return
  }
  if (!apiProjectId.value) {
    createError.value = '未找到关联的 API 项目'
    return
  }

  creating.value = true
  createError.value = ''
  try {
    const payload = { project: apiProjectId.value, name }
    if (form.value.parentId) payload.parent = Number(form.value.parentId)
    await request('/api/v1/api-groups/', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    ElMessage.success('分组创建成功')
    showCreateDialog.value = false
    await loadGroups()
  } catch (e) {
    createError.value = e?.message || '创建失败'
  } finally {
    creating.value = false
  }
}

// ========== 删除分组 ==========
async function deleteGroup(groupId) {
  ElMessageBox.confirm('确定删除该分组吗？子分组将变为根分组。', '确认删除',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await request(`/api/v1/api-groups/${groupId}/`, { method: 'DELETE' })
      ElMessage.success('分组已删除')
      await loadGroups()
    } catch (e) {
      ElMessage.error(e?.message || '删除失败')
    }
  }).catch(() => {})
}

function handleDeleteGroupNode(node) {
  deleteGroup(node.id)
}

// ========== 初始化 ==========
watch(() => props.projectId, () => { loadGroups() })
onMounted(() => { loadGroups() })
</script>

<style scoped>
.project-group-manager {
  /* root — inherits padding from parent main-card */
}

/* ===== 头部 ===== */
.gm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.gm-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}
.gm-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.group-count-tag {
  margin-left: 4px;
}
.gm-header-actions {
  display: flex;
  gap: 4px;
}

/* ===== 加载状态 ===== */
.gm-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 32px 0;
  color: #909399;
  font-size: 13px;
}

/* ===== 分组树 ===== */
.gm-tree {
  padding: 2px 0;
}

/* "全部分组" 行 */
.gm-all-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  transition: background 0.12s, color 0.12s;
  margin-bottom: 2px;
}
.gm-all-item:hover {
  background: #f5f7fa;
}
.gm-all-item.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 500;
}
.gm-all-item.active .gm-tree-label {
  color: #409eff;
}

.gm-tree-item-left {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.gm-tree-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  user-select: none;
}
.gm-tree-badge {
  font-size: 12px;
  color: #c0c4cc;
  margin-left: auto;
  padding-left: 8px;
  font-weight: 500;
}

/* ===== 空状态 ===== */
.gm-empty {
  padding: 16px 0;
}
.gm-empty :deep(.el-empty) {
  padding: 20px 0;
}

/* ===== 错误消息 ===== */
.gm-error {
  color: #f56c6c;
  font-size: 13px;
  margin-top: -8px;
  margin-bottom: 8px;
}
</style>
