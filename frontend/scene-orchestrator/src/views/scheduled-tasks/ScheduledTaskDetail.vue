<template>
  <div class="st-detail" v-loading="store.loading">
    <!-- 页面标题 -->
    <div class="detail-header">
      <div class="detail-header-left">
        <el-button text @click="$router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h3 class="detail-title">{{ store.current?.name || '定时任务详情' }}</h3>
      </div>
      <div class="detail-header-actions">
        <el-button type="success" @click="handleRunNow">
          <el-icon><CaretRight /></el-icon> 立即执行
        </el-button>
        <el-button :type="store.current?.status === 'active' ? 'warning' : 'info'" @click="handleToggleStatus">
          <el-icon><template v-if="store.current?.status === 'active'"><VideoPause /></template><template v-else><VideoPlay /></template></el-icon>
          {{ store.current?.status === 'active' ? '暂停' : '激活' }}
        </el-button>
        <el-button type="primary" @click="$router.push(`/scheduled-tasks/${taskId}/edit`)">
          <el-icon><Edit /></el-icon> 编辑
        </el-button>
        <el-popconfirm title="确定删除此定时任务？" @confirm="handleDelete">
          <template #reference>
            <el-button type="danger">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <el-row :gutter="20" v-if="store.current">
      <!-- 左侧：主内容 -->
      <el-col :xs="24" :lg="16">
        <!-- 基本信息 -->
        <el-card shadow="never" class="info-card mb-4">
          <template #header><span class="card-title"><el-icon><InfoFilled /></el-icon> 基本信息</span></template>
          <el-descriptions :column="2" border size="small" class="info-desc">
            <el-descriptions-item label="任务名称" :span="2">{{ store.current.name }}</el-descriptions-item>
            <el-descriptions-item label="测试对象">
              <template v-if="store.current.test_scene">
                场景编排：{{ store.current.test_scene_name }}
              </template>
              <template v-else>
                测试套件：{{ store.current.test_suite_name || '-' }}
              </template>
            </el-descriptions-item>
            <el-descriptions-item label="执行环境">
              {{ store.current.environment_name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="状态" :span="2">
              <el-tag :type="statusType" size="small">{{ statusLabel }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="上次执行" v-if="store.current.last_run_time">
              {{ formatDateTime(store.current.last_run_time) }}
            </el-descriptions-item>
            <el-descriptions-item label="下次执行" v-if="store.current.next_run_time">
              <span class="text-primary">{{ formatDateTime(store.current.next_run_time) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="创建人">
              {{ store.current.created_by_name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDateTime(store.current.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ formatDateTime(store.current.updated_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2" v-if="store.current.description">
              {{ store.current.description }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 执行历史 -->
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header-row">
              <span class="card-title"><el-icon><Timer /></el-icon> 执行历史</span>
            </div>
          </template>

          <div v-if="store.logsLoading" class="loading-state">
            <el-icon class="is-loading" :size="22"><Loading /></el-icon>
            <span>加载中...</span>
          </div>

          <el-empty v-else-if="store.logs.length === 0" description="暂无执行记录" :image-size="80" />

          <template v-else>
            <el-table :data="store.logs" size="small" border class="sub-table" style="width: 100%">
              <el-table-column label="开始时间" width="160">
                <template #default="{ row }">
                  {{ formatDateTime(row.start_time) }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="80" align="center">
                <template #default="{ row }">
                  <el-tooltip
                    v-if="row.status === 'failed' && row.error_message"
                    :content="row.error_message"
                    placement="top"
                    :show-after="300"
                  >
                    <el-tag :type="logStatusType(row.status)" size="small">
                      {{ logStatusLabel(row.status) }}
                    </el-tag>
                  </el-tooltip>
                  <el-tag v-else :type="logStatusType(row.status)" size="small">
                    {{ logStatusLabel(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="执行时长" width="110" align="center">
                <template #default="{ row }">
                  {{ row.duration ? formatDuration(row.duration) : '-' }}
                </template>
              </el-table-column>
              <el-table-column label="结束时间" width="160">
                <template #default="{ row }">
                  {{ row.end_time ? formatDateTime(row.end_time) : '-' }}
                </template>
              </el-table-column>
              <el-table-column label="测试结果" min-width="180">
                <template #default="{ row }">
                  <div v-if="row.total_test_cases > 0" class="test-results">
                    <span class="tr-item tr-pass" :title="'通过 ' + row.passed_test_cases + ' 项'">
                      <span class="tr-dot pass"></span>{{ row.passed_test_cases }}
                    </span>
                    <span class="tr-item tr-fail" :title="'失败 ' + row.failed_test_cases + ' 项'">
                      <span class="tr-dot fail"></span>{{ row.failed_test_cases }}
                    </span>
                    <span v-if="row.error_test_cases" class="tr-item tr-error" :title="'错误 ' + row.error_test_cases + ' 项'">
                      <span class="tr-dot error"></span>{{ row.error_test_cases }}
                    </span>
                    <span class="tr-divider" />
                    <span class="tr-total">/ {{ row.total_test_cases }}</span>
                  </div>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column label="成功率" width="80" align="center">
                <template #default="{ row }">
                  <span v-if="row.total_test_cases > 0" :class="rateClass(calcSuccessRate(row))">
                    {{ calcSuccessRate(row) }}%
                  </span>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" align="center">
                <template #default="{ row }">
                  <el-button
                    v-if="row.scene_execution"
                    size="small"
                    text
                    type="primary"
                    @click="goToSceneExecution(row.scene_execution, row.scene_execution_scene_id)"
                    title="查看场景执行详情"
                  >
                    <el-icon><View /></el-icon>
                  </el-button>
                  <el-button
                    v-else-if="row.test_run"
                    size="small"
                    text
                    type="primary"
                    @click="goToTestRun(row.test_run)"
                    title="查看测试运行详情"
                  >
                    <el-icon><View /></el-icon>
                  </el-button>
                  <el-button
                    v-else
                    size="small"
                    text
                    type="info"
                    @click="goToLogDetail(row.id)"
                    title="查看执行日志"
                  >
                    <el-icon><Document /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrap" v-if="store.logsTotal > 10">
              <el-pagination
                v-model:current-page="logPage"
                :page-size="10"
                :total="store.logsTotal"
                layout="prev, pager, next"
                size="small"
                @current-change="loadLogs"
              />
            </div>
          </template>
        </el-card>
      </el-col>

      <!-- 右侧：统计 & 配置 -->
      <el-col :xs="24" :lg="8">
        <!-- 执行统计 -->
        <el-card shadow="never" class="info-card mb-4">
          <template #header><span class="card-title"><el-icon><DataBoard /></el-icon> 执行统计</span></template>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ store.current.total_runs }}</div>
              <div class="stat-label">总执行次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value text-success">{{ store.current.successful_runs }}</div>
              <div class="stat-label">成功次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value text-danger">{{ store.current.failed_runs }}</div>
              <div class="stat-label">失败次数</div>
            </div>
          </div>
          <div v-if="store.current.total_runs > 0" class="progress-section">
            <div class="progress-label">
              <span>成功率</span>
              <span :class="rateClass(store.current.success_rate)">{{ store.current.success_rate?.toFixed(1) }}%</span>
            </div>
            <el-progress
              :percentage="Math.round(store.current.success_rate || 0)"
              :stroke-width="8"
              :color="progressColor"
              :format="() => ''"
            />
          </div>
        </el-card>

        <!-- 调度配置 -->
        <el-card shadow="never" class="info-card mb-4">
          <template #header><span class="card-title"><el-icon><Timer /></el-icon> 调度配置</span></template>
          <el-descriptions :column="1" border size="small" class="info-desc">
            <el-descriptions-item label="类型">
              {{ scheduleTypeLabel(store.current.schedule_type) }}
            </el-descriptions-item>
            <!-- 单次执行：合并日期+时间显示 -->
            <el-descriptions-item label="执行时间" v-if="store.current.schedule_type === 'once' && store.current.scheduled_date">
              <span class="text-primary">
                {{ store.current.scheduled_date }}
                <template v-if="store.current.scheduled_time">
                  {{ store.current.scheduled_time }}
                </template>
                <template v-else>
                  <span class="text-muted">(时间未设置)</span>
                </template>
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="执行时间" v-else-if="store.current.scheduled_time">
              {{ store.current.scheduled_time }}
            </el-descriptions-item>
            <el-descriptions-item label="星期几" v-if="store.current.weekday">
              周{{ store.current.weekday }}
            </el-descriptions-item>
            <el-descriptions-item label="每月第几天" v-if="store.current.day_of_month">
              {{ store.current.day_of_month }}日
            </el-descriptions-item>
            <el-descriptions-item label="Cron表达式" v-if="store.current.cron_expression">
              <code>{{ store.current.cron_expression }}</code>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 通知配置 -->
        <el-card shadow="never" class="info-card">
          <template #header><span class="card-title"><el-icon><Message /></el-icon> 通知配置</span></template>
          <el-descriptions :column="1" border size="small" class="info-desc">
            <el-descriptions-item label="邮件通知">
              <el-tag :type="store.current.send_email_notification ? 'success' : 'info'" size="small">
                {{ store.current.send_email_notification ? '启用' : '禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="成功时通知" v-if="store.current.send_email_notification">
              <el-icon v-if="store.current.notify_on_success" color="#10b981" size="16"><CircleCheck /></el-icon>
              <el-icon v-else color="#94a3b8" size="16"><CloseBold /></el-icon>
            </el-descriptions-item>
            <el-descriptions-item label="失败时通知" v-if="store.current.send_email_notification">
              <el-icon v-if="store.current.notify_on_failure" color="#10b981" size="16"><CircleCheck /></el-icon>
              <el-icon v-else color="#94a3b8" size="16"><CloseBold /></el-icon>
            </el-descriptions-item>
            <el-descriptions-item label="通知邮箱" v-if="store.current.send_email_notification && store.current.notification_emails">
              <small>{{ store.current.notification_emails }}</small>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import {
  ArrowLeft, InfoFilled, Timer, DataBoard, Message,
  CaretRight, VideoPause, VideoPlay, Edit, Delete, View, Loading,
  CircleCheck, CloseBold, Document,
} from "@element-plus/icons-vue";
import { useScheduledTaskStore } from "../../test-manager/stores/scheduledTask";

const router = useRouter();
const route = useRoute();
const store = useScheduledTaskStore();

const taskId = computed(() => Number(route.params.id));
const logPage = ref(1);

onMounted(async () => {
  await store.loadDetail(taskId.value);
  loadLogs();
});

async function loadLogs() {
  await store.loadLogs(taskId.value, { page: logPage.value, page_size: 10 });
}

async function handleRunNow() {
  try {
    const res = await store.runNow(taskId.value);
    ElMessage.success(res.message || "任务已开始执行");
  } catch (e) {
    ElMessage.error(e.message || "执行失败");
  }
}

async function handleToggleStatus() {
  try {
    const res = await store.toggleStatus(taskId.value);
    ElMessage.success(res.message);
    await store.loadDetail(taskId.value);
  } catch (e) {
    ElMessage.error(e.message || "操作失败");
  }
}

async function handleDelete() {
  try {
    await store.remove(taskId.value);
    ElMessage.success("已删除");
    router.push("/scheduled-tasks");
  } catch (e) {
    ElMessage.error(e.message || "删除失败");
  }
}

function goToTestRun(runId) {
  router.push(`/test-runs/${runId}`);
}

function goToSceneExecution(executionId, sceneId) {
  if (sceneId) {
    router.push(`/scenes/${sceneId}/executions/${executionId}`);
  } else {
    router.push(`/scene-executions/${executionId}/generate-report`);
  }
}

function goToLogDetail(logId) {
  router.push(`/task-execution-logs/${logId}`);
}

function calcSuccessRate(row) {
  if (!row.total_test_cases || row.total_test_cases === 0) return 0;
  if (row.success_rate != null) return Math.round(row.success_rate * 10) / 10;
  return Math.round((row.passed_test_cases / row.total_test_cases) * 1000) / 10;
}

// 格式化
function formatDateTime(val) {
  if (!val) return "-";
  const d = new Date(val);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  const s = String(d.getSeconds()).padStart(2, "0");
  return `${y}-${mo}-${dd} ${h}:${mi}:${s}`;
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return "-";
  if (seconds < 1) return (seconds * 1000).toFixed(0) + "ms";
  if (seconds < 60) return seconds.toFixed(1) + "秒";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (m < 60) return `${m}分${s}秒`;
  const h = Math.floor(m / 60);
  const remainM = m % 60;
  return `${h}时${remainM}分${s}秒`;
}

const statusType = computed(() => {
  if (!store.current?.is_enabled) return "info";
  const map = { active: "success", paused: "warning", inactive: "info" };
  return map[store.current?.status] || "info";
});

const statusLabel = computed(() => {
  if (!store.current?.is_enabled) return "已禁用";
  const map = { active: "激活", paused: "暂停", inactive: "停用" };
  return map[store.current?.status] || store.current?.status;
});

function scheduleTypeLabel(type) {
  const map = { once: "单次执行", daily: "每日执行", weekly: "每周执行", monthly: "每月执行", cron: "Cron表达式" };
  return map[type] || type;
}

function logStatusType(status) {
  const map = { success: "success", failed: "danger", running: "primary", timeout: "warning", cancelled: "info" };
  return map[status] || "info";
}

function logStatusLabel(status) {
  const map = { success: "成功", failed: "失败", running: "运行中", timeout: "超时", cancelled: "已取消" };
  return map[status] || status;
}

function rateClass(rate) {
  if (rate >= 80) return "text-success";
  if (rate >= 60) return "text-warning";
  return "text-danger";
}

function progressColor(percentage) {
  if (percentage >= 80) return "#10b981";
  if (percentage >= 60) return "#f59e0b";
  return "#ef4444";
}
</script>

<style scoped>
.mb-4 { margin-bottom: 20px; }

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.detail-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #0f172a);
}
.detail-header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.back-btn { padding: 0 4px; }

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.95rem;
  font-weight: 600;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--text-secondary, #64748b);
}

/* 统计区域 */
.stats-grid {
  display: flex;
  text-align: center;
  border-bottom: 1px solid var(--border-color, #e2e8f0);
  padding-bottom: 16px;
  margin-bottom: 16px;
}
.stat-item {
  flex: 1;
  border-right: 1px solid var(--border-color, #e2e8f0);
}
.stat-item:last-child { border-right: none; }
.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 4px;
}
.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary, #64748b);
}

.progress-section { padding: 0 4px; }
.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  margin-bottom: 6px;
}

.test-results {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  white-space: nowrap;
}
.tr-item { display: inline-flex; align-items: center; gap: 3px; }
.tr-dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
}
.tr-dot.pass { background: #10b981; }
.tr-dot.fail { background: #ef4444; }
.tr-dot.error { background: #f59e0b; }
.tr-pass { color: #10b981; font-weight: 600; }
.tr-fail { color: #ef4444; font-weight: 600; }
.tr-error { color: #f59e0b; font-weight: 600; }
.tr-divider {
  display: inline-block;
  width: 1px; height: 12px;
  background: var(--border-color, #e2e8f0);
}
.tr-total { color: var(--text-secondary, #94a3b8); }

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.text-primary { color: var(--primary-color, #1e40af); }
.text-success { color: var(--success-color, #10b981); }
.text-warning { color: var(--warning-color, #f59e0b); }
.text-danger { color: var(--danger-color, #ef4444); }
.text-muted { color: var(--text-secondary, #94a3b8); }
</style>
