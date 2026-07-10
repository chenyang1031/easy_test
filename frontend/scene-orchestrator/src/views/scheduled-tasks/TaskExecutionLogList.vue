<template>
  <div class="log-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button size="default" @click="$router.push('/scheduled-tasks')">
          <el-icon><ArrowLeft /></el-icon> 返回定时任务
        </el-button>
        <h2 class="page-title">执行日志</h2>
        <span v-if="taskName" class="page-subtitle">{{ taskName }}</span>
      </div>
      <div class="page-header-right">
        <el-button @click="fetchLogs" :loading="loading" :icon="Refresh">刷新</el-button>
        <span v-if="lastUpdated" class="last-updated">更新于 {{ lastUpdated }}</span>
      </div>
    </div>

    <!-- 统计概览 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6" :md="6">
        <div class="stat-card">
          <div class="stat-card-body">
            <div class="stat-card-icon" style="background:rgba(59,130,246,0.1);color:#3b82f6;">
              <el-icon :size="20"><List /></el-icon>
            </div>
            <div class="stat-card-info">
              <div class="stat-card-value">{{ stats.total }}</div>
              <div class="stat-card-label">总日志</div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="6">
        <div class="stat-card">
          <div class="stat-card-body">
            <div class="stat-card-icon" style="background:rgba(16,185,129,0.1);color:#10b981;">
              <el-icon :size="20"><CircleCheckFilled /></el-icon>
            </div>
            <div class="stat-card-info">
              <div class="stat-card-value">{{ stats.success }}</div>
              <div class="stat-card-label">成功</div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="6">
        <div class="stat-card">
          <div class="stat-card-body">
            <div class="stat-card-icon" style="background:rgba(239,68,68,0.1);color:#ef4444;">
              <el-icon :size="20"><CircleCloseFilled /></el-icon>
            </div>
            <div class="stat-card-info">
              <div class="stat-card-value">{{ stats.failed }}</div>
              <div class="stat-card-label">失败</div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="6">
        <div class="stat-card">
          <div class="stat-card-body">
            <div class="stat-card-icon" style="background:rgba(245,158,11,0.1);color:#f59e0b;">
              <el-icon :size="20"><Clock /></el-icon>
            </div>
            <div class="stat-card-info">
              <div class="stat-card-value">{{ stats.pending }}</div>
              <div class="stat-card-label">待执行/运行中</div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <div class="panel-card filter-card">
      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="6" :md="5">
          <el-input
            v-model="filters.search"
            placeholder="搜索定时任务名称..."
            clearable
            :prefix-icon="Search"
            @change="onFilterChange"
            @clear="onFilterChange"
          />
        </el-col>
        <el-col :xs="12" :sm="5" :md="4">
          <el-select
            v-model="filters.status"
            placeholder="状态筛选"
            clearable
            style="width:100%"
            @change="onFilterChange"
          >
            <el-option label="全部" value="" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="执行中" value="running" />
            <el-option label="待执行" value="pending" />
          </el-select>
        </el-col>
        <el-col :xs="12" :sm="6" :md="5">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width:100%"
            @change="onFilterChange"
          />
        </el-col>
        <el-col :xs="12" :sm="4" :md="3">
          <el-select
            v-model="filters.pageSize"
            placeholder="每页"
            style="width:100%"
            @change="onPageSizeChange"
          >
            <el-option label="10条/页" :value="10" />
            <el-option label="20条/页" :value="20" />
            <el-option label="50条/页" :value="50" />
          </el-select>
        </el-col>
        <el-col :xs="12" :sm="3" :md="2" style="text-align:right;">
          <el-button text type="primary" @click="resetFilters">
            重置
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 表格卡片 -->
    <div class="panel-card table-card">
      <!-- 加载 -->
      <div v-if="loading" class="loading-state">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="!logs.length" description="暂无执行日志" :image-size="80">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><Document /></el-icon>
        </template>
        <p v-if="hasActiveFilters" class="text-muted">当前筛选条件无匹配结果，试试调整筛选条件</p>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table :data="logs" stripe class="data-table" @row-click="viewDetail" :highlight-current-row="true">
          <el-table-column label="ID" width="60" prop="id" />
          <el-table-column label="定时任务" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              <router-link
                v-if="row.scheduled_task"
                :to="`/scheduled-tasks/${row.scheduled_task}`"
                class="name-link"
                @click.stop
              >
                {{ row.scheduled_task_name }}
              </router-link>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status).type" size="small" effect="light" round>
                {{ statusTag(row.status).text }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="测试结果" min-width="180">
            <template #default="{ row }">
              <div v-if="row.total_test_cases > 0" class="cell-result">
                <div class="cell-result-bar">
                  <div class="result-bar-item success-bg" :style="resultBarStyle(row, 'success')" title="通过" />
                  <div class="result-bar-item danger-bg" :style="resultBarStyle(row, 'failed')" title="失败" />
                  <div class="result-bar-item warning-bg" :style="resultBarStyle(row, 'error')" title="错误" />
                </div>
                <div class="cell-result-text">
                  <span class="text-success">{{ row.passed_test_cases || 0 }}</span>
                  /
                  <span class="text-danger">{{ row.failed_test_cases || 0 }}</span>
                  /
                  <span class="text-warning">{{ row.error_test_cases || 0 }}</span>
                  <span class="text-muted" style="margin-left:4px;">({{ row.total_test_cases }})</span>
                </div>
              </div>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="开始时间" width="160">
            <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
          </el-table-column>
          <el-table-column label="执行时长" width="85" align="center">
            <template #default="{ row }">{{ row.duration != null ? Number(row.duration).toFixed(2) : '-' }}秒</template>
          </el-table-column>
          <el-table-column label="重试" width="55" align="center">
            <template #default="{ row }">{{ row.retry_count || 0 }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click.stop="viewDetail(row)">
                <el-icon><View /></el-icon> 详情
              </el-button>
              <el-popconfirm
                title="确定删除此日志？"
                @confirm.stop="handleDelete(row)"
              >
                <template #reference>
                  <el-button size="small" text type="danger" @click.stop>
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrapper" v-if="total > 0">
          <el-pagination
            v-model:current-page="filters.page"
            :page-size="filters.pageSize"
            :total="total"
            layout="total, prev, pager, next, jumper"
            background
            small
            @current-change="onPageChange"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import {
  ArrowLeft, Loading, Document, View, Delete,
  Refresh, Search, List, CircleCheckFilled, CircleCloseFilled, Clock,
} from "@element-plus/icons-vue";
import { taskExecutionLogApi } from "../../api/scheduledTask";

const route = useRoute();
const router = useRouter();

// 数据
const logs = ref([]);
const loading = ref(false);
const taskName = ref("");
const total = ref(0);
const lastUpdated = ref("");

// 统计
const stats = reactive({
  total: 0,
  success: 0,
  failed: 0,
  pending: 0,
});

// 筛选条件
const filters = reactive({
  search: "",
  status: "",
  dateRange: null,
  page: 1,
  pageSize: 10,
});

const hasActiveFilters = computed(() => {
  return filters.search || filters.status || filters.dateRange;
});

function statusTag(status) {
  const map = {
    success: { type: "success", text: "成功" },
    running: { type: "primary", text: "执行中" },
    failed: { type: "danger", text: "失败" },
    pending: { type: "info", text: "待执行" },
  };
  return map[status] || { type: "info", text: status || "未知" };
}

function formatTime(val) {
  if (!val) return "-";
  const d = new Date(val);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function resultBarStyle(row, type) {
  const total = row.total_test_cases || 1;
  let count = 0;
  if (type === "success") count = row.passed_test_cases || 0;
  else if (type === "failed") count = row.failed_test_cases || 0;
  else if (type === "error") count = row.error_test_cases || 0;
  return { width: Math.round(count / total * 100) + "%" };
}

function viewDetail(row) {
  router.push(`/task-execution-logs/${row.id}`);
}

function onFilterChange() {
  filters.page = 1;
  fetchLogs();
}

function onPageChange(page) {
  filters.page = page;
  fetchLogs();
}

function onPageSizeChange() {
  filters.page = 1;
  fetchLogs();
}

function resetFilters() {
  filters.search = "";
  filters.status = "";
  filters.dateRange = null;
  filters.page = 1;
  fetchLogs();
}

async function handleDelete(row) {
  try {
    await taskExecutionLogApi.remove(row.id);
    ElMessage.success(`日志 #${row.id} 已删除`);
    await fetchLogs();
  } catch (e) {
    ElMessage.error(e.message || "删除失败");
  }
}

function buildParams() {
  const params = {};
  if (route.query.scheduled_task) {
    params.scheduled_task = route.query.scheduled_task;
  }
  if (filters.search) params.search = filters.search;
  if (filters.status) params.status = filters.status;
  if (filters.dateRange) {
    params.date_from = filters.dateRange[0];
    params.date_to = filters.dateRange[1];
  }
  params.page = filters.page;
  params.page_size = filters.pageSize;
  return params;
}

async function fetchLogs() {
  loading.value = true;
  try {
    const params = buildParams();
    const data = await taskExecutionLogApi.list(params);
    logs.value = data.results || data || [];
    total.value = data.count ?? logs.value.length;

    // 更新统计（在所有日志上统计，但分页场景只能用当前数据估算）
    stats.total = total.value;
    stats.success = data.success_count ?? logs.value.filter(l => l.status === "success").length;
    stats.failed = data.failed_count ?? logs.value.filter(l => l.status === "failed").length;
    stats.pending = data.pending_count ?? logs.value.filter(l => l.status === "running" || l.status === "pending").length;

    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    lastUpdated.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  } catch {
    // ignore
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  if (route.query.task_name) {
    taskName.value = route.query.task_name;
  }
  fetchLogs();
});
</script>

<style scoped>
.log-list-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* 页面标题 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  line-height: 1.3;
}
.page-subtitle {
  font-size: 14px;
  color: #909399;
}
.last-updated {
  font-size: 12px;
  color: #c0c4cc;
  white-space: nowrap;
}

/* 统计卡片 */
.stats-row {
  width: 100%;
}
.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
}
.stat-card-body {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stat-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-card-value {
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.2;
}
.stat-card-label {
  font-size: 0.78rem;
  color: #64748b;
  margin-top: 2px;
}

/* 卡片通用 */
.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  width: 100%;
}

.filter-card {
  padding: 16px 20px;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 60px 0;
  color: #909399;
}

.data-table {
  width: 100%;
}

.data-table :deep(.el-table__row) {
  cursor: pointer;
}

/* 单元格内测试结果 */
.cell-result {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cell-result-bar {
  display: flex;
  height: 4px;
  border-radius: 2px;
  overflow: hidden;
  background: #f0f0f0;
}
.result-bar-item {
  height: 100%;
  transition: width 0.2s ease;
}
.result-bar-item.success-bg { background: #67c23a; }
.result-bar-item.danger-bg { background: #f56c6c; }
.result-bar-item.warning-bg { background: #e6a23c; }

.cell-result-text {
  font-size: 12px;
  line-height: 1.3;
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f2f3f5;
}

.name-link {
  color: #409eff;
  text-decoration: none;
  font-weight: 500;
}
.name-link:hover {
  text-decoration: underline;
}

.text-muted { color: #909399; }
.text-success { color: #67c23a; font-weight: 500; }
.text-danger { color: #f56c6c; font-weight: 500; }
.text-warning { color: #e6a23c; font-weight: 500; }
</style>
