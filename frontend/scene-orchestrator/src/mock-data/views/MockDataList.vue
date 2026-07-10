<template>
  <div class="md-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">Mock 数据</h2>
        <span class="page-subtitle">管理模拟测试数据，支持一键生成、查看和导出</span>
      </div>
      <div class="page-header-right">
        <el-button type="primary" @click="$router.push('/mock-data/create')">
          <el-icon><Plus /></el-icon> 生成测试数据
        </el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="12" class="filter-row">
          <el-col :xs="24" :sm="18" :md="20">
            <el-input
              v-model="search"
              placeholder="搜索用途/描述..."
              clearable
              class="filter-item"
              @keyup.enter="doSearch"
              @clear="doSearch"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </el-col>
          <el-col :xs="24" :sm="6" :md="4">
            <el-button type="primary" @click="doSearch" class="filter-item">
              <el-icon><Search /></el-icon> 查询
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 加载状态 -->
      <div v-if="store.loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 错误状态 -->
      <el-alert
        v-else-if="store.error"
        :title="store.error"
        type="error"
        show-icon
        closable
        class="error-alert"
      />

      <!-- 空状态 -->
      <el-empty v-else-if="store.list.length === 0" description="暂无 Mock 数据">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><Coin /></el-icon>
        </template>
        <el-button type="primary" @click="$router.push('/mock-data/create')">生成测试数据</el-button>
      </el-empty>

      <!-- 数据表格 -->
      <template v-else>
        <el-table :data="store.list" stripe border class="data-table" @row-click="onRowClick">
          <el-table-column label="用途" min-width="150" show-overflow-tooltip prop="aim" />
          <el-table-column label="描述" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.description || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="数据量" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info" effect="plain">{{ row.data_count }} 条</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="生成时间" width="160" align="right">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="更新时间" width="160" align="right">
            <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="创建人" width="120" show-overflow-tooltip prop="created_by_name" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <div class="table-actions" @click.stop>
                <el-button size="small" text @click="viewData(row)">查看</el-button>
                <el-button size="small" text type="primary" @click="exportData(row)">
                  <el-icon><Download /></el-icon> 导出
                </el-button>
                <el-popconfirm title="确定删除此 Mock 数据？" @confirm="deleteData(row)">
                  <template #reference>
                    <el-button size="small" text type="danger">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrap" v-if="store.total > store.pageSize">
          <el-pagination
            v-model:current-page="store.page"
            v-model:page-size="store.pageSize"
            :total="store.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="loadData"
            @size-change="(s) => { store.pageSize = s; loadData() }"
          />
        </div>
      </template>
    </div>

    <!-- 查看数据弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      title="Mock 数据详情"
      width="700px"
      top="5vh"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template v-if="viewingData">
        <div class="dialog-meta">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="用途">{{ viewingData.aim }}</el-descriptions-item>
            <el-descriptions-item label="数据量">{{ viewingData.data_count }} 条</el-descriptions-item>
            <el-descriptions-item label="描述">{{ viewingData.description || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建人">{{ viewingData.created_by_name }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="dialog-data">
          <div class="dialog-data-header">
            <span class="dialog-data-title">数据内容</span>
            <el-button size="small" text type="primary" @click="copyData">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
          </div>
          <el-input
            type="textarea"
            :rows="12"
            :model-value="formattedData"
            readonly
            class="data-viewer"
          />
        </div>
      </template>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="exportData(viewingData)">
          <el-icon><Download /></el-icon> 导出数据
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Loading, Coin, Download, Delete, CopyDocument } from '@element-plus/icons-vue'
import { useMockDataStore } from '../stores/mockData.js'
import { mockDataApi } from '../api/index.js'
import { formatDateTime } from '../../test-manager/composables/useFormat.js'

const store = useMockDataStore()

const search = ref('')
const dialogVisible = ref(false)
const viewingData = ref(null)

const formattedData = computed(() => {
  if (!viewingData.value) return ''
  try {
    const parsed = JSON.parse(viewingData.value.data)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return viewingData.value.data
  }
})

function formatCellData(data) {
  try {
    const parsed = JSON.parse(data)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return data
  }
}

function onRowClick(row) {
  viewData(row)
}

function viewData(row) {
  viewingData.value = row
  dialogVisible.value = true
}

function copyData() {
  navigator.clipboard.writeText(formattedData.value).then(() => {
    ElMessage.success('已复制')
  }).catch(() => {
    ElMessage.warning('复制失败，请手动选择复制')
  })
}

function exportData(row) {
  const url = mockDataApi.exportUrl(row.id)
  // 创建一个隐藏的下载链接
  const a = document.createElement('a')
  a.href = url
  a.download = `mock_data_${row.id}.json`
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  ElMessage.success('开始下载')
}

async function deleteData(row) {
  try {
    await store.remove(row.id)
    ElMessage.success('已删除')
    if (viewingData.value?.id === row.id) {
      dialogVisible.value = false
      viewingData.value = null
    }
  } catch (e) {
    ElMessage.error('删除失败: ' + (e.message || '未知错误'))
  }
}

async function loadData() {
  const params = {}
  if (search.value) params.search = search.value
  await store.loadList(params)
}

function doSearch() {
  store.page = 1
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
/* ---- 页面基础 ---- */
.md-list { padding: 0; }

/* ---- 页面标题 ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.page-header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.page-subtitle { font-size: 14px; color: #909399; }
.page-header-right { display: flex; gap: 8px; }

/* ---- 内容卡片 ---- */
.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
}

/* ---- 筛选栏 ---- */
.filter-bar { margin-bottom: 16px; }
.filter-row { display: flex; align-items: center; }
.filter-item { width: 100%; }

/* ---- 加载状态 ---- */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 0;
  color: #909399;
  font-size: 14px;
}

/* ---- 错误提示 ---- */
.error-alert { margin-bottom: 0; }

/* ---- 数据表格 ---- */
.data-table { width: 100%; }
.data-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
.data-table :deep(.el-table__row) { cursor: pointer; transition: background 0.15s; }
.data-table :deep(.el-table__row:hover) { background: #f0f7ff !important; }
.table-actions { display: flex; gap: 4px; flex-wrap: nowrap; white-space: nowrap; }

/* ---- 分页 ---- */
.pagination-wrap { display: flex; justify-content: flex-end; padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px; }

/* ---- 弹窗 ---- */
.dialog-meta { margin-bottom: 16px; }
.dialog-data-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.dialog-data-title { font-size: 14px; font-weight: 600; color: #303133; }
.data-viewer :deep(textarea) {
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #f8f9fa;
}
</style>
