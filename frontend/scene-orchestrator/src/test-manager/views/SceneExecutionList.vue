<template>
  <div class="sel-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">场景执行</h2>
        <span class="page-subtitle" v-if="total !== null">共 {{ total }} 条</span>
      </div>
      <div class="page-header-right">
        <el-button @click="loadList"><el-icon><Refresh /></el-icon> 刷新</el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="12" class="filter-row">
          <el-col :xs="24" :sm="8" :md="6">
            <el-select
              v-model="filterProject"
              placeholder="选择项目"
              clearable
              class="filter-item"
              @change="onFilterChange"
            >
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="8" :md="6">
            <el-select
              v-model="filterStatus"
              placeholder="执行状态"
              clearable
              class="filter-item"
              @change="onFilterChange"
            >
              <el-option label="执行中" value="running" />
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
              <el-option label="部分成功" value="partial_success" />
              <el-option label="已停止" value="stopped" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="8" :md="6">
            <el-input
              v-model="filterSceneName"
              placeholder="搜索场景名称（模糊）"
              clearable
              class="filter-item"
              :prefix-icon="Search"
              @input="onSearchInput"
              @keyup.enter="onFilterChange"
              @clear="onFilterChange"
            />
          </el-col>
        </el-row>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="list.length === 0" description="暂无场景执行记录">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><Monitor /></el-icon>
        </template>
        <el-text type="info">在「测试场景编排」中运行场景后将在此展示</el-text>
      </el-empty>

      <!-- 混合列表：批量批次（可展开子执行） + 单次执行 -->
      <template v-else>
        <el-table
          ref="tableRef"
          :data="list"
          stripe
          border
          class="data-table"
          row-key="key"
          :row-class-name="rowClassName"
          @row-click="onRowClick"
          @expand-change="onExpandChange"
        >
          <el-table-column type="expand" width="36">
            <template #default="{ row }">
              <!-- 批次：子执行明细 -->
              <div v-if="row.type === 'batch'" class="batch-children">
                <div v-if="childrenLoading[row.id]" class="loading-state small">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>加载子执行...</span>
                </div>
                <template v-else>
                  <div v-if="!(childrenMap[row.id] || []).length" class="text-muted small pad">
                    暂无子执行记录（批次可能仍在排队或启动失败）
                    <div v-if="row.error_message" class="batch-error-msg">{{ row.error_message }}</div>
                  </div>
                  <template v-else>
                    <div class="batch-children-toolbar">
                      <el-checkbox v-model="batchFailOnly[row.id]" size="small">只看失败（含部分成功）</el-checkbox>
                      <span class="text-muted small">批次 ID: #{{ row.id }}</span>
                    </div>
                    <el-table :data="childRows(row)" size="small" border class="child-table">
                    <el-table-column label="场景" min-width="180" show-overflow-tooltip>
                      <template #default="{ row: child }">
                        <router-link
                          :to="`/scene-executions/${child.id}`"
                          class="name-link"
                          @click.stop
                        >{{ child.scene_name }}</router-link>
                        <span class="text-muted small"> #{{ child.id }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="状态" width="90" align="center">
                      <template #default="{ row: child }">
                        <el-tag :type="statusTag(child.status).type" size="small" effect="light" round>
                          {{ statusTag(child.status).text }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="节点" width="90" align="center">
                      <template #default="{ row: child }">{{ child.passed_nodes }}/{{ child.total_nodes }}</template>
                    </el-table-column>
                    <el-table-column label="耗时" width="90" align="center">
                      <template #default="{ row: child }">{{ formatDuration(child.duration_ms) }}</template>
                    </el-table-column>
                    <el-table-column label="开始时间" width="140" align="center">
                      <template #default="{ row: child }">{{ formatTime(child.started_at) }}</template>
                    </el-table-column>
                    <el-table-column label="错误" min-width="160" show-overflow-tooltip>
                      <template #default="{ row: child }">
                        <el-tooltip
                          :content="child.error_message || '-'"
                          :disabled="!child.error_message"
                          placement="top"
                          max-width="480"
                        >
                          <span class="err-text">{{ child.error_message || '-' }}</span>
                        </el-tooltip>
                      </template>
                    </el-table-column>
                  </el-table>
                  </template>
                </template>
              </div>
              <!-- 单次执行：不展示展开内容（箭头已隐藏） -->
              <div v-else class="text-muted small pad">单次执行，点击行可进入详情</div>
            </template>
          </el-table-column>

          <el-table-column label="场景 / 批次" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <template v-if="row.type === 'batch'">
                <el-icon class="batch-icon"><Box /></el-icon>
                <span class="batch-name">{{ row.name }}</span>
                <el-tag v-if="row.execute_mode === 'parallel'" size="small" type="info" effect="plain" class="mode-tag">并发</el-tag>
                <el-tag v-else size="small" type="info" effect="plain" class="mode-tag">串行</el-tag>
                <span class="text-muted small"> #{{ row.id }}</span>
              </template>
              <template v-else>
                <router-link :to="`/scene-executions/${row.id}`" class="name-link" @click.stop>{{ row.scene_name }}</router-link>
                <span class="text-muted small"> #{{ row.id }}</span>
              </template>
            </template>
          </el-table-column>
          <el-table-column label="项目" width="110" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.project_name || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="环境" width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag size="small" effect="plain" type="info">{{ row.environment_name || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tooltip
                :content="row.error_message"
                :disabled="!row.error_message"
                placement="top"
                max-width="420"
              >
                <el-tag :type="statusTag(row.status).type" size="small" effect="light" round>
                  {{ statusTag(row.status).text }}{{ row.error_message ? ' ⚠' : '' }}
                </el-tag>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="统计" width="190" align="center">
            <template #default="{ row }">
              <template v-if="row.type === 'batch'">
                <span class="stat ok">成功 {{ row.success_scenes }}</span>
                <span class="stat warn">部分 {{ row.partial_scenes }}</span>
                <span class="stat bad">失败 {{ row.failed_scenes }}</span>
                <div v-if="row.status === 'running'" class="text-muted small">
                  进度 {{ row.completed_scenes }}/{{ row.total_scenes }}
                </div>
              </template>
              <template v-else>
                <span class="text-muted small">节点</span>
                {{ row.passed_nodes }}/{{ row.total_nodes }}
              </template>
            </template>
          </el-table-column>
          <el-table-column label="开始时间" width="150" align="center">
            <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
          </el-table-column>
          <el-table-column label="结束时间" width="150" align="center">
            <template #default="{ row }">{{ formatTime(row.finished_at) }}</template>
          </el-table-column>
          <el-table-column label="创建人" width="80" align="center">
            <template #default="{ row }">{{ row.created_by_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="170" align="center" fixed="right">
            <template #default="{ row }">
              <template v-if="row.type === 'batch'">
                <el-button link type="primary" size="small" @click.stop="toggleExpand(row)">
                  {{ expandedKeys.has(row.key) ? '收起' : '展开' }}
                </el-button>
                <el-button v-if="row.status === 'running'" link type="warning" size="small" @click.stop="handleStopBatch(row)">
                  停止
                </el-button>
                <el-popconfirm title="删除批次将同时删除其所有子执行记录，确定？" @confirm.stop="handleDelete(row)">
                  <template #reference>
                    <el-button link type="danger" size="small" @click.stop>删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
              <template v-else>
                <el-button link type="primary" size="small" @click.stop="$router.push(`/scene-executions/${row.id}`)">
                  查看
                </el-button>
                <el-button link type="primary" size="small" @click.stop="openInOrchestrator(row)">
                  编排器
                </el-button>
                <el-popconfirm title="确定删除此执行记录？" @confirm.stop="handleDelete(row)">
                  <template #reference>
                    <el-button link type="danger" size="small" @click.stop>删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrap" v-if="total > 0">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Loading, Monitor, Search, Box } from '@element-plus/icons-vue'
import { sceneBatchApi, unifiedExecutionApi, sceneExecutionApi } from '../api/index.js'
import { useProjectStore } from '../stores/project.js'

const router = useRouter()
const projectStore = useProjectStore()

const list = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const filterProject = ref('')
const filterStatus = ref('')
const filterSceneName = ref('') // 场景名称模糊搜索（批次按名称或子场景名匹配）
// 输入停顿 400ms 后自动搜索（回车/清空立即触发）
let searchDebounceTimer = null
function onSearchInput() {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    searchDebounceTimer = null
    onFilterChange()
  }, 400)
}

const projects = computed(() => projectStore.projects)

// 批次子执行：懒加载缓存
const tableRef = ref(null)
const childrenMap = ref({})      // batchId -> 子执行数组
const childrenLoading = ref({})  // batchId -> bool
const expandedKeys = ref(new Set())
const batchFailOnly = ref({})    // batchId -> bool，展开行"只看失败"过滤

// 批次展开行的子执行列表：按"只看失败"开关过滤（失败+部分成功都含失败节点）
function childRows(batchRow) {
  const rows = childrenMap.value[batchRow.id] || []
  if (!batchFailOnly.value[batchRow.id]) return rows
  return rows.filter((c) => c.status === 'failed' || c.status === 'partial_success')
}

function statusTag(status) {
  const map = {
    success: { type: 'success', text: '成功' },
    partial_success: { type: 'warning', text: '部分成功' },
    failed: { type: 'danger', text: '失败' },
    running: { type: 'primary', text: '执行中' },
    stopped: { type: 'warning', text: '已停止' },
  }
  return map[status] || { type: 'info', text: status || '未知' }
}

function formatTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatDuration(ms) {
  if (!ms && ms !== 0) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m${Math.round((ms % 60000) / 1000)}s`
}

function openInOrchestrator(row) {
  const url = `/test-scenes-orchestrator/#/scenes/${row.scene}/executions/${row.id}`
  window.open(url, '_blank')
}

// 单次执行行隐藏展开箭头
function rowClassName({ row }) {
  return row.type === 'batch' ? 'row-batch' : 'row-single'
}

function onRowClick(row) {
  if (row.type === 'batch') {
    toggleExpand(row)
  } else {
    router.push(`/scene-executions/${row.id}`)
  }
}

function toggleExpand(row) {
  tableRef.value?.toggleRowExpansion(row)
}

async function onExpandChange(row, expandedRows) {
  const expanded = expandedRows.some((r) => r.key === row.key)
  const next = new Set(expandedKeys.value)
  if (expanded) next.add(row.key); else next.delete(row.key)
  expandedKeys.value = next

  // 批次首次展开时懒加载子执行
  if (expanded && row.type === 'batch' && !childrenMap.value[row.id]) {
    childrenLoading.value = { ...childrenLoading.value, [row.id]: true }
    try {
      const detail = await sceneBatchApi.get(row.id)
      childrenMap.value = { ...childrenMap.value, [row.id]: detail.executions || [] }
    } catch (e) {
      childrenMap.value = { ...childrenMap.value, [row.id]: [] }
      ElMessage.error(e.message || '加载子执行失败')
    } finally {
      childrenLoading.value = { ...childrenLoading.value, [row.id]: false }
    }
  }
}

function onFilterChange() {
  page.value = 1
  loadList()
}

function onPageChange(p) {
  page.value = p
  loadList()
}

function onSizeChange(size) {
  pageSize.value = size
  page.value = 1
  loadList()
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filterProject.value) params.project = filterProject.value
    if (filterStatus.value) params.status = filterStatus.value
    const kw = filterSceneName.value.trim()
    if (kw) params.scene_name = kw
    const data = await unifiedExecutionApi.list(params)
    list.value = data.results || []
    total.value = data.count || 0
  } catch (e) {
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function handleStopBatch(row) {
  try {
    await sceneBatchApi.stop(row.id)
    ElMessage.success('已发送停止信号')
    await loadList()
  } catch (e) {
    ElMessage.error(e.message || '停止失败')
  }
}

async function handleDelete(row) {
  try {
    if (row.type === 'batch') {
      await sceneBatchApi.remove(row.id)
      ElMessage.success('批次及其子执行已删除')
    } else {
      await sceneExecutionApi.remove(row.id)
      ElMessage.success('删除成功')
    }
    await loadList()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(() => {
  if (projectStore.projects.length === 0) projectStore.loadProjects()
  loadList()
})

onUnmounted(() => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
})
</script>

<style scoped>
.sel-list { display: flex; flex-direction: column; gap: 16px; flex: 1; }
.page-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.page-header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 20px; font-weight: 600; color: #303133; margin: 0; }
.page-subtitle { font-size: 14px; color: #909399; }
.page-header-right { display: flex; gap: 8px; }

.panel-card {
  background: #fff; border-radius: 10px; padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
}
.filter-bar { margin-bottom: 16px; }
.filter-item { width: 100%; }
.filter-row { align-items: end; }

.loading-state {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  padding: 60px 0; color: #909399; font-size: 14px;
}
.loading-state.small { padding: 16px 0; font-size: 13px; }

.data-table { width: 100%; cursor: pointer; }
.data-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
/* 单次执行行隐藏展开箭头 */
.data-table :deep(.row-single .el-table__expand-icon) { display: none; }
.name-link { color: #409eff; font-weight: 500; text-decoration: none; }
.name-link:hover { text-decoration: underline; }
.text-muted { color: #909399; }
.small { font-size: 12px; }
.pad { padding: 8px 12px; }

.batch-icon { vertical-align: -2px; margin-right: 6px; color: #7c3aed; }
.batch-name { font-weight: 600; }
.mode-tag { margin-left: 8px; }
.stat { margin: 0 4px; font-size: 12px; }
.stat.ok { color: #67c23a; }
.stat.warn { color: #e6a23c; }
.stat.bad { color: #f56c6c; }

.batch-children { padding: 4px 12px 8px; background: #fafbfc; }
.batch-error-msg {
  color: #f56c6c;
  margin-top: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}
.batch-children-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 4px 8px;
}
.child-table { background: #fff; }
.err-text { color: #f56c6c; font-size: 12px; }

.pagination-wrap {
  display: flex; justify-content: flex-end; align-items: center;
  padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px;
}
</style>
