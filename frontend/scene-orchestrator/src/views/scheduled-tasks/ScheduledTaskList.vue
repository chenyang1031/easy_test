<template>
  <div class="st-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">定时任务</h2>
        <span class="page-subtitle" v-if="store.total !== null">共 {{ store.total }} 个任务</span>
      </div>
      <div class="page-header-right">
        <el-button @click="$router.push('/task-monitor')">
          <el-icon><Monitor /></el-icon> 任务监控
        </el-button>
        <el-button type="primary" @click="$router.push('/scheduled-tasks/create')">
          <el-icon><Plus /></el-icon> 新增定时任务
        </el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="12" class="filter-row">
          <el-col :xs="24" :sm="8" :md="6">
            <el-input
              v-model="search"
              placeholder="搜索任务名称/描述..."
              clearable
              class="filter-item"
              @keyup.enter="doSearch"
              @clear="doSearch"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </el-col>
          <el-col :xs="12" :sm="6" :md="4">
            <el-select
              v-model="statusFilter"
              placeholder="状态筛选"
              clearable
              class="filter-item"
              @change="doSearch"
            >
              <el-option label="激活" value="active" />
              <el-option label="暂停" value="paused" />
              <el-option label="停用" value="inactive" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="6" :md="3">
            <el-button type="primary" @click="doSearch" class="filter-item" style="width: 100%">
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

      <!-- 空状态 -->
      <el-empty v-else-if="store.list.length === 0" description="暂无定时任务">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><Clock /></el-icon>
        </template>
        <el-button type="primary" @click="$router.push('/scheduled-tasks/create')">创建定时任务</el-button>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table :data="store.list" stripe class="data-table">
          <el-table-column label="任务名称" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <router-link :to="`/scheduled-tasks/${row.id}`" class="name-link" @click.stop>
                {{ row.name }}
              </router-link>
              <div v-if="row.description" class="name-desc">{{ row.description }}</div>
            </template>
          </el-table-column>
          <el-table-column label="测试套件/场景" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              <template v-if="row.test_scene_name">
                <el-tag size="small" type="warning" effect="plain" style="margin-right:4px">场景</el-tag>
                {{ row.test_scene_name }}
              </template>
              <template v-else>
                <el-tag size="small" type="primary" effect="plain" style="margin-right:4px">套件</el-tag>
                {{ row.test_suite_name || '-' }}
              </template>
            </template>
          </el-table-column>
          <el-table-column label="执行环境" width="120">
            <template #default="{ row }">
              {{ row.environment_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="调度类型" width="140">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ scheduleTypeLabel(row.schedule_type) }}</el-tag>
              <div v-if="row.schedule_type === 'cron' && row.cron_expression" class="schedule-detail">
                <code>{{ row.cron_expression }}</code>
              </div>
              <div v-else-if="row.scheduled_time" class="schedule-detail">
                {{ formatScheduleTime(row) }}
              </div>
            </template>
          </el-table-column>
          <el-table-column label="下次执行" width="180">
            <template #default="{ row }">
              <span v-if="row.next_run_time" class="text-primary">{{ formatTime(row.next_run_time) }}</span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusType(row)" size="small">
                {{ statusLabel(row) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="成功率" width="100">
            <template #default="{ row }">
              <span v-if="row.total_runs > 0" :class="successRateClass(row.success_rate)">
                {{ row.success_rate?.toFixed(1) }}%
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-tooltip content="查看详情">
                  <el-button size="small" text @click.stop="$router.push(`/scheduled-tasks/${row.id}`)">
                    <el-icon><View /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="编辑">
                  <el-button size="small" text @click.stop="$router.push(`/scheduled-tasks/${row.id}/edit`)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="立即执行">
                  <el-button size="small" text type="success" @click.stop="handleRunNow(row)">
                    <el-icon><CaretRight /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip :content="row.status === 'active' ? '暂停' : '激活'">
                  <el-button
                    size="small"
                    text
                    :type="row.status === 'active' ? 'warning' : 'info'"
                    @click.stop="handleToggleStatus(row)"
                  >
                    <el-icon><template v-if="row.status === 'active'"><VideoPause /></template><template v-else><VideoPlay /></template></el-icon>
                  </el-button>
                </el-tooltip>
                <el-popconfirm title="确定删除此定时任务？" @confirm="handleDelete(row)">
                  <template #reference>
                    <el-tooltip content="删除">
                      <el-button size="small" text type="danger" @click.stop>
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </el-tooltip>
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
            :page-size="store.pageSize"
            :total="store.total"
            layout="prev, pager, next, total"
            @current-change="onPageChange"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Plus, Search, Loading, Clock, Monitor,
  View, Edit, Delete, CaretRight, VideoPause, VideoPlay,
} from "@element-plus/icons-vue";
import { useScheduledTaskStore } from "../../test-manager/stores/scheduledTask";

const router = useRouter();
const store = useScheduledTaskStore();

const search = ref("");
const statusFilter = ref("");

// 初始化加载
onMounted(() => {
  store.page = 1;
  store.loadList();
});

function doSearch() {
  store.page = 1;
  store.loadList({
    search: search.value || undefined,
    status: statusFilter.value || undefined,
  });
}

function onPageChange(page) {
  store.page = page;
  store.loadList({
    search: search.value || undefined,
    status: statusFilter.value || undefined,
  });
}

// 操作
async function handleRunNow(task) {
  try {
    const res = await store.runNow(task.id);
    ElMessage.success(res.message || "任务已开始执行");
  } catch (e) {
    ElMessage.error(e.message || "执行失败");
  }
}

async function handleToggleStatus(task) {
  try {
    const res = await store.toggleStatus(task.id);
    ElMessage.success(res.message);
    store.loadList({
      search: search.value || undefined,
      status: statusFilter.value || undefined,
    });
  } catch (e) {
    ElMessage.error(e.message || "操作失败");
  }
}

async function handleDelete(task) {
  try {
    await store.remove(task.id);
    ElMessage.success("已删除");
    store.loadList({
      search: search.value || undefined,
      status: statusFilter.value || undefined,
    });
  } catch (e) {
    ElMessage.error(e.message || "删除失败");
  }
}

// 格式化辅助
function scheduleTypeLabel(type) {
  const map = {
    once: "单次执行",
    daily: "每日执行",
    weekly: "每周执行",
    monthly: "每月执行",
    cron: "Cron",
  };
  return map[type] || type;
}

function formatScheduleTime(row) {
  if (row.schedule_type === "daily" && row.scheduled_time) {
    return row.scheduled_time;
  }
  if (row.schedule_type === "weekly" && row.weekday && row.scheduled_time) {
    return `周${row.weekday} ${row.scheduled_time}`;
  }
  if (row.schedule_type === "monthly" && row.day_of_month && row.scheduled_time) {
    return `每月${row.day_of_month}日 ${row.scheduled_time}`;
  }
  return "";
}

function formatTime(val) {
  if (!val) return "-";
  const d = new Date(val);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return `${y}-${mo}-${dd} ${hh}:${mi}:${ss}`;
}

function statusType(row) {
  if (!row.is_enabled) return "info";
  const map = { active: "success", paused: "warning", inactive: "info" };
  return map[row.status] || "info";
}

function statusLabel(row) {
  if (!row.is_enabled) return "已禁用";
  const map = { active: "激活", paused: "暂停", inactive: "停用" };
  return map[row.status] || row.status;
}

function successRateClass(rate) {
  if (rate >= 80) return "text-success";
  if (rate >= 60) return "text-warning";
  return "text-danger";
}
</script>

<style scoped>
.st-list {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #0f172a);
}
.page-subtitle {
  font-size: 0.85rem;
  color: var(--text-secondary, #64748b);
}
.page-header-right {
  display: flex;
  gap: 8px;
}

.filter-bar {
  margin-bottom: 16px;
}
.filter-item {
  width: 100%;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 60px 0;
  color: var(--text-secondary, #64748b);
}

.name-link {
  color: var(--primary-color, #1e40af);
  text-decoration: none;
  font-weight: 500;
}
.name-link:hover {
  text-decoration: underline;
}
.name-desc {
  font-size: 0.75rem;
  color: var(--text-secondary, #64748b);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}

.schedule-detail {
  font-size: 0.75rem;
  color: var(--text-secondary, #64748b);
  margin-top: 2px;
}
.schedule-detail code {
  font-family: var(--font-mono, monospace);
  font-size: 0.7rem;
}

.text-primary { color: var(--primary-color, #1e40af); }
.text-success { color: var(--success-color, #10b981); }
.text-warning { color: var(--warning-color, #f59e0b); }
.text-danger { color: var(--danger-color, #ef4444); }
.text-muted { color: var(--text-secondary, #94a3b8); }

.table-actions {
  display: flex;
  gap: 2px;
  flex-wrap: nowrap;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* 适配暗色模式 */
.dark-mode .name-link { color: var(--primary-color, #3b82f6); }
</style>
