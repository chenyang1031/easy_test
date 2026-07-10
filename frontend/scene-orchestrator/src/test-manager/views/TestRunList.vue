<template>
  <div class="tr-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">测试运行</h2>
        <span class="page-subtitle" v-if="store.total !== null">共 {{ store.total }} 条</span>
      </div>
      <div class="page-header-right">
        <el-button @click="refresh"><el-icon><Refresh /></el-icon> 刷新</el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="12" class="filter-row">
          <el-col :xs="24" :sm="8" :md="6">
            <el-select
              v-model="store.filterProject"
              placeholder="选择项目"
              clearable
              class="filter-item"
              @change="onFilterChange"
            >
              <el-option v-for="p in projectStore.projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-col>
        </el-row>
      </div>

      <!-- 加载中 -->
      <div v-if="store.loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="store.list.length === 0" description="暂无测试运行">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><Monitor /></el-icon>
        </template>
        <el-text type="info">运行测试套件后将在此显示记录</el-text>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table :data="store.list" stripe border class="data-table" @row-click="(row) => $router.push(`/test-runs/${row.id}`)">
          <el-table-column label="名称" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <router-link :to="`/test-runs/${row.id}`" class="name-link" @click.stop>{{ row.name }}</router-link>
            </template>
          </el-table-column>
          <el-table-column label="项目" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.project_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="环境" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag size="small" effect="plain" type="info">{{ row.environment_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status).type" size="small" effect="light" round>
                {{ statusTag(row.status).text }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="开始时间" width="160" align="center">
            <template #default="{ row }">{{ row.start_time ? formatTime(row.start_time) : '-' }}</template>
          </el-table-column>
          <el-table-column label="结束时间" width="160" align="center">
            <template #default="{ row }">{{ row.end_time ? formatTime(row.end_time) : '-' }}</template>
          </el-table-column>
          <el-table-column label="创建人" width="100" align="center">
            <template #default="{ row }">{{ row.created_by_name }}</template>
          </el-table-column>
          <el-table-column label="操作" width="150" align="center" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click.stop="$router.push(`/test-runs/${row.id}`)">
                查看
              </el-button>
              <el-button link type="primary" size="small" @click.stop="handleGenerateReport(row)">
                生成报告
              </el-button>
              <el-popconfirm title="确定删除此运行记录？" @confirm.stop="handleDelete(row)">
                <template #reference>
                  <el-button link type="danger" size="small" @click.stop>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrap" v-if="store.total > 0">
          <el-pagination
            v-model:current-page="store.page"
            v-model:page-size="store.pageSize"
            :total="store.total"
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Loading, Monitor } from '@element-plus/icons-vue'
import { useTestRunStore } from '../stores/testRun.js'
import { useProjectStore } from '../stores/project.js'

const router = useRouter()
const store = useTestRunStore()
const projectStore = useProjectStore()

function statusTag(status) {
  const map = {
    completed: { type: 'success', text: '已完成' },
    failed: { type: 'danger', text: '失败' },
    running: { type: 'primary', text: '运行中' },
    pending: { type: 'info', text: '待执行' },
  }
  return map[status] || { type: 'info', text: status || '未知' }
}

function formatTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function onFilterChange() {
  store.page = 1
  store.loadList()
}

function onPageChange(page) {
  store.page = page
  store.loadList()
}

function onSizeChange(size) {
  store.pageSize = size
  store.page = 1
  store.loadList()
}

function refresh() {
  store.loadList()
}

function handleGenerateReport(row) {
  router.push({ name: 'testRunReportForm', params: { testRunId: row.id } })
}

async function handleDelete(row) {
  try {
    await store.remove(row.id)
    ElMessage.success('删除成功')
    store.loadList()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(() => {
  if (projectStore.projects.length === 0) projectStore.loadProjects()
  store.loadList()
})
</script>

<style scoped>
.tr-list { display: flex; flex-direction: column; gap: 16px; flex: 1; }
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

.pagination-wrap {
  display: flex; justify-content: flex-end; align-items: center;
  padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px;
}
</style>
