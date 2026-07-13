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
            </el-select>
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

      <!-- 表格 -->
      <template v-else>
        <el-table :data="list" stripe border class="data-table" @row-click="(row) => $router.push(`/scene-executions/${row.id}`)">
          <el-table-column label="场景" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              <router-link :to="`/scene-executions/${row.id}`" class="name-link" @click.stop>{{ row.scene_name }}</router-link>
              <span class="text-muted small"> #{{ row.id }}</span>
            </template>
          </el-table-column>
          <el-table-column label="项目" width="120" show-overflow-tooltip>
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
              <el-tag :type="statusTag(row.status).type" size="small" effect="light" round>
                {{ statusTag(row.status).text }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="开始时间" width="150" align="center">
            <template #default="{ row }">{{ row.started_at ? formatTime(row.started_at) : '-' }}</template>
          </el-table-column>
          <el-table-column label="结束时间" width="150" align="center">
            <template #default="{ row }">{{ row.finished_at ? formatTime(row.finished_at) : '-' }}</template>
          </el-table-column>
          <el-table-column label="创建人" width="80" align="center">
            <template #default="{ row }">{{ row.created_by_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" align="center" fixed="right">
            <template #default="{ row }">
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Loading, Monitor } from '@element-plus/icons-vue'
import { sceneExecutionApi } from '../api/index.js'
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

const projects = computed(() => projectStore.projects)

function statusTag(status) {
  const map = {
    success: { type: 'success', text: '成功' },
    partial_success: { type: 'warning', text: '部分成功' },
    failed: { type: 'danger', text: '失败' },
    running: { type: 'primary', text: '执行中' },
  }
  return map[status] || { type: 'info', text: status || '未知' }
}

function formatTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function openInOrchestrator(row) {
  const url = `/test-scenes-orchestrator/#/scenes/${row.scene}/executions/${row.id}`
  window.open(url, '_blank')
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
    const data = await sceneExecutionApi.list(params)
    list.value = data.results || []
    total.value = data.count || 0
  } catch (e) {
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function handleDelete(row) {
  try {
    await sceneExecutionApi.remove(row.id)
    ElMessage.success('删除成功')
    await loadList()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(() => {
  if (projectStore.projects.length === 0) projectStore.loadProjects()
  loadList()
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

.data-table { width: 100%; cursor: pointer; }
.data-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
.name-link { color: #409eff; font-weight: 500; text-decoration: none; }
.name-link:hover { text-decoration: underline; }
.text-muted { color: #909399; }

.pagination-wrap {
  display: flex; justify-content: flex-end; align-items: center;
  padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px;
}
</style>
