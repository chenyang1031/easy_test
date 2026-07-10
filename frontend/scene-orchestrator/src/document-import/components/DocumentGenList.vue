<template>
  <div class="doc-import-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">文档导入API资产</h2>
        <span class="page-subtitle" v-if="store.total !== null">共 {{ store.total }} 条记录</span>
      </div>
      <div class="page-header-right">
        <el-button type="primary" @click="store.openUploadDialog()">
          <el-icon><Upload /></el-icon> 上传文档
        </el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="12" class="filter-row">
          <el-col :xs="24" :sm="8" :md="6">
            <el-select v-model="store.projectFilter" placeholder="选择API项目" clearable class="filter-item" @change="store.loadRecords(1)">
              <el-option v-for="p in store.apiProjects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="6" :md="4">
            <el-select v-model="store.statusFilter" placeholder="全部状态" clearable class="filter-item" @change="store.loadRecords(1)">
              <el-option label="上传中" value="uploading" />
              <el-option label="转换中" value="converting" />
              <el-option label="AI生成中" value="generating" />
              <el-option label="生成成功" value="success" />
              <el-option label="生成失败" value="failed" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="4" :md="3">
            <el-button :icon="Refresh" @click="store.loadRecords(store.currentPage)">刷新</el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 加载中 -->
      <div v-if="store.loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon><span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="store.records.length === 0" description="暂无记录">
        <template #image><el-icon :size="64" color="#c0c4cc"><Document /></el-icon></template>
        <el-button type="primary" @click="store.openUploadDialog()">上传文档</el-button>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table :data="store.records" stripe border class="data-table">
          <el-table-column label="任务名称" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="name-link" @click="viewDetail(row)">{{ row.task_name }}</span>
            </template>
          </el-table-column>
          <el-table-column label="文件名" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.original_filename }}</template>
          </el-table-column>
          <el-table-column label="项目" width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.project_name }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small" effect="light" round>
                <el-icon v-if="row.status === 'generating'" class="is-loading" style="margin-right:4px"><Loading /></el-icon>
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="AI模型" width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.model_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="API数量" width="80" align="center">
            <template #default="{ row }">{{ row.api_count || 0 }}</template>
          </el-table-column>
          <el-table-column label="导入状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="importStatusType(row.import_status)" size="small" effect="plain" round>
                {{ importStatusLabel(row.import_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160" align="center">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="240" align="center" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-tooltip content="重新生成" placement="top">
                  <el-button
                    size="small"
                    text
                    type="warning"
                    :loading="regeneratingId === row.id"
                    :disabled="row.status === 'generating'"
                    @click="handleRegenerate(row)"
                  >
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-button size="small" text type="primary" @click="viewDetail(row)">查看</el-button>
                <el-button
                  size="small"
                  text
                  type="success"
                  :disabled="row.status !== 'success' || row.api_count === 0"
                  @click="store.openImportDialog(row)"
                >
                  导入
                </el-button>
                <el-popconfirm title="确定删除此记录？" @confirm="store.deleteRecord(row.id)">
                  <template #reference>
                    <el-button size="small" text type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrap" v-if="store.total > store.pageSize">
          <el-pagination
            v-model:current-page="store.currentPage"
            v-model:page-size="store.pageSize"
            :total="store.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="store.loadRecords"
            @size-change="() => store.loadRecords(1)"
          />
        </div>
      </template>
    </div>

    <!-- 上传弹窗 -->
    <UploadDialog v-model="store.uploadDialogVisible" @saved="onUploadSaved" />

    <!-- 导入弹窗 -->
    <ImportDialog v-model="store.importDialogVisible" :record="store.currentRecordForImport" @imported="onImported" />

    <!-- API 详情抽屉 -->
    <ApiDetailDrawer v-model="detailVisible" :record-id="currentDetailId" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Upload, Refresh, Loading, Document } from '@element-plus/icons-vue'
import { useDocumentImportStore } from '../stores/documentImport.js'
import UploadDialog from './UploadDialog.vue'
import ImportDialog from './ImportDialog.vue'
import ApiDetailDrawer from './ApiDetailView.vue'

const store = useDocumentImportStore()

const regeneratingId = ref(null)
const detailVisible = ref(false)
const currentDetailId = ref(null)

// ---- 轮询：有记录处于 generating 状态时自动刷新 ----
let pollTimer = null
const POLL_INTERVAL = 5000  // 5 秒

function hasPendingTasks() {
  return store.records.some(r => r.status === 'generating' || r.status === 'converting' || r.status === 'uploading')
}

function startPolling() {
  stopPolling()
  if (hasPendingTasks()) {
    pollTimer = setInterval(async () => {
      await store.loadRecords(store.currentPage, true)  // silent refresh
      if (!hasPendingTasks()) stopPolling()
    }, POLL_INTERVAL)
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 监听记录变化，自动启停轮询
watch(() => store.records, () => {
  if (hasPendingTasks()) startPolling()
  else stopPolling()
}, { deep: true })

function statusType(status) {
  const map = { uploading: 'info', converting: 'warning', generating: 'primary', success: 'success', failed: 'danger' }
  return map[status] || 'info'
}
function statusLabel(status) {
  const map = { uploading: '上传中', converting: '转换中', generating: 'AI生成中', success: '生成成功', failed: '生成失败' }
  return map[status] || status || '未知'
}
function importStatusType(s) {
  const map = { pending: 'info', partial_imported: 'warning', imported: 'success' }
  return map[s] || 'info'
}
function importStatusLabel(s) {
  const map = { pending: '待导入', partial_imported: '部分导入', imported: '全部导入' }
  return map[s] || s || '待导入'
}

function formatTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '-'
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function handleRegenerate(row) {
  regeneratingId.value = row.id
  try {
    await store.regenerateRecord(row.id)
  } catch { /* error already handled in store */ }
  finally { regeneratingId.value = null }
}

function viewDetail(row) {
  currentDetailId.value = row.id
  detailVisible.value = true
}

function onUploadSaved() {
  store.loadRecords(1)
}

function onImported() {
  store.loadRecords(store.currentPage)
}

onMounted(() => {
  store.loadOptions()
  store.loadRecords(1).then(() => { if (hasPendingTasks()) startPolling() })
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.doc-import-list { display: flex; flex-direction: column; gap: 16px; flex: 1; }
.page-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.page-header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.page-subtitle { font-size: 14px; color: #909399; }
.page-header-right { display: flex; gap: 8px; }

.panel-card { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.filter-bar { margin-bottom: 16px; }
.filter-item { width: 100%; }
.filter-row { align-items: center; }

.loading-state { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 60px 0; color: #909399; font-size: 14px; }

.data-table { width: 100%; }
.data-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
.name-link { color: #409eff; font-weight: 500; cursor: pointer; }
.name-link:hover { text-decoration: underline; }
.table-actions { display: flex; gap: 4px; align-items: center; justify-content: center; flex-wrap: nowrap; }

.pagination-wrap { display: flex; justify-content: flex-end; padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px; }
</style>
