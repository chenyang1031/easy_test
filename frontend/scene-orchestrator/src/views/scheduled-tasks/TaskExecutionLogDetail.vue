<template>
  <div class="log-detail-page" v-loading="loading">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button size="default" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2 class="page-title">执行日志详情</h2>
        <span class="page-subtitle" v-if="log">#{{ log.id }}</span>
      </div>
      <div class="page-header-right">
        <el-tag v-if="log" :type="statusTag.type" size="large" effect="dark" round>
          <el-icon style="margin-right:4px;"><component :is="statusTag.icon" /></el-icon>
          {{ statusTag.text }}
        </el-tag>
      </div>
    </div>

    <!-- 加载骨架 -->
    <div v-if="loading" class="panel-card">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 错误 -->
    <el-empty v-else-if="loadError" description="无法加载执行日志" :image-size="80">
      <template #description><span>{{ loadError }}</span></template>
      <el-button type="primary" @click="fetchLog">重新加载</el-button>
      <el-button @click="goBack">返回</el-button>
    </el-empty>

    <template v-else-if="log">
      <!-- 状态步骤条 -->
      <div class="panel-card">
        <div class="card-header-row">
          <el-icon style="color:#409eff;"><TrendCharts /></el-icon>
          <span>执行状态</span>
        </div>
        <el-steps :active="stepActive" align-center class="status-steps">
          <el-step title="开始执行" :description="log.start_time ? formatTime(log.start_time) : ''" />
          <el-step title="执行结果" :description="resultSummary" />
          <el-step title="执行完成" :description="log.end_time ? formatTime(log.end_time) : '进行中'" />
        </el-steps>
        <div class="step-extra-info">
          <span v-if="log.duration !== null && log.duration !== undefined">
            <el-icon style="vertical-align:middle;"><Clock /></el-icon>
            耗时：<strong>{{ log.duration != null ? Number(log.duration).toFixed(2) : '-' }}</strong> 秒
          </span>
          <span v-if="log.retry_count > 0" style="margin-left:20px;">
            <el-icon style="vertical-align:middle;"><Refresh /></el-icon>
            重试：<strong>{{ log.retry_count }}</strong> 次
          </span>
        </div>
      </div>

      <!-- 基本信息 + 测试结果统计两列布局 -->
      <el-row :gutter="20" class="detail-row">
        <!-- 基本信息 -->
        <el-col :xs="24" :md="14">
          <div class="panel-card card-fill">
            <div class="card-header-row">
              <el-icon style="color:#409eff;"><InfoFilled /></el-icon>
              <span>基本信息</span>
            </div>
            <el-descriptions :column="2" border size="small" class="detail-descriptions">
              <el-descriptions-item label="日志 ID" label-class-name="desc-label">
                #{{ log.id }}
              </el-descriptions-item>
              <el-descriptions-item label="定时任务" label-class-name="desc-label">
                <router-link v-if="log.scheduled_task" :to="`/scheduled-tasks/${log.scheduled_task}`" class="name-link">
                  {{ log.scheduled_task_name }}
                </router-link>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="开始时间" label-class-name="desc-label">
                {{ log.start_time ? formatTime(log.start_time) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="结束时间" label-class-name="desc-label">
                {{ log.end_time ? formatTime(log.end_time) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="创建时间" label-class-name="desc-label">
                {{ log.created_at ? formatTime(log.created_at) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="邮件通知" label-class-name="desc-label">
                <el-tag v-if="log.email_sent" type="success" size="small">已发送</el-tag>
                <el-tag v-else type="info" size="small">未发送</el-tag>
                <span v-if="log.email_sent_time" style="margin-left:6px;font-size:12px;color:#909399;">
                  {{ formatTime(log.email_sent_time) }}
                </span>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-col>

        <!-- 测试结果统计 -->
        <el-col :xs="24" :md="10">
          <div class="panel-card card-fill">
            <div class="card-header-row">
              <el-icon style="color:#67c23a;"><Document /></el-icon>
              <span>测试结果</span>
            </div>
            <div class="result-stats">
              <div class="result-stat-item">
                <div class="stat-label">总用例</div>
                <div class="stat-value total">{{ log.total_test_cases || 0 }}</div>
              </div>
              <div class="result-stat-item">
                <div class="stat-label">通过</div>
                <div class="stat-value success">{{ log.passed_test_cases || 0 }}</div>
              </div>
              <div class="result-stat-item">
                <div class="stat-label">失败</div>
                <div class="stat-value danger">{{ log.failed_test_cases || 0 }}</div>
              </div>
              <div class="result-stat-item">
                <div class="stat-label">错误</div>
                <div class="stat-value warning">{{ log.error_test_cases || 0 }}</div>
              </div>
            </div>
            <!-- 进度条 -->
            <div v-if="log.total_test_cases > 0" class="progress-section">
              <div class="progress-bar-wrapper">
                <div
                  class="progress-bar-segment success-bg"
                  :style="{ width: passPercent + '%' }"
                  :title="'通过: ' + passPercent + '%'"
                />
                <div
                  class="progress-bar-segment danger-bg"
                  :style="{ width: failPercent + '%' }"
                  :title="'失败: ' + failPercent + '%'"
                />
                <div
                  class="progress-bar-segment warning-bg"
                  :style="{ width: errorPercent + '%' }"
                  :title="'错误: ' + errorPercent + '%'"
                />
              </div>
              <div class="progress-legend">
                <span><span class="dot success-dot" /> 通过 {{ passPercent }}%</span>
                <span><span class="dot danger-dot" /> 失败 {{ failPercent }}%</span>
                <span><span class="dot warning-dot" /> 错误 {{ errorPercent }}%</span>
              </div>
            </div>
            <!-- 成功率的环图简化 -->
            <div v-if="log.total_test_cases > 0" class="rate-summary" :class="rateClass">
              <el-icon :size="16"><component :is="rateIcon" /></el-icon>
              成功率：<strong>{{ successRate }}%</strong>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 错误信息 -->
      <div v-if="log.error_message" class="panel-card">
        <div class="card-header-row">
          <el-icon style="color:#f56c6c;"><WarningFilled /></el-icon>
          <span>错误信息</span>
          <el-button size="small" text @click="showFullError = !showFullError">
            {{ showFullError ? '收起' : '展开全部' }}
          </el-button>
        </div>
        <pre :class="['error-pre', { 'error-pre-collapsed': !showFullError }]">{{ log.error_message }}</pre>
      </div>

      <!-- 相关链接 -->
      <div class="panel-card">
        <div class="card-header-row">
          <el-icon style="color:#909399;"><Link /></el-icon>
          <span>相关链接</span>
        </div>
        <div class="related-links">
          <el-button @click="goBack" plain>
            <el-icon><ArrowLeft /></el-icon> 返回执行日志列表
          </el-button>
          <el-button v-if="log.scheduled_task" type="primary" plain @click="$router.push(`/scheduled-tasks/${log.scheduled_task}`)">
            <el-icon><Clock /></el-icon> 查看定时任务
          </el-button>
          <el-button v-if="log.test_run" type="success" plain @click="$router.push(`/test-runs/${log.test_run}`)">
            <el-icon><View /></el-icon> 查看测试运行
          </el-button>
        </div>
      </div>

      <!-- 同一任务的历史日志 -->
      <div v-if="relatedLogs.length > 0" class="panel-card">
        <div class="card-header-row">
          <el-icon style="color:#909399;"><List /></el-icon>
          <span>同一任务的历史日志</span>
        </div>
        <el-table :data="relatedLogs" stripe size="small" class="data-table" @row-click="goToRelatedLog">
          <el-table-column label="ID" width="60" prop="id" />
          <el-table-column label="开始时间" width="160">
            <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small" effect="light" round>
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="通过率" width="80" align="center">
            <template #default="{ row }">
              <span v-if="row.total_test_cases > 0" :class="getRateClass(row)">
                {{ ((row.passed_test_cases || 0) / row.total_test_cases * 100).toFixed(0) }}%
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="执行时长" width="90">
            <template #default="{ row }">{{ row.duration != null ? Number(row.duration).toFixed(2) : '-' }}秒</template>
          </el-table-column>
        </el-table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowLeft, InfoFilled, Document, WarningFilled, Link,
  Clock, Refresh, View, List, TrendCharts,
  CircleCheckFilled, CircleCloseFilled,
} from "@element-plus/icons-vue";
import { taskExecutionLogApi } from "../../api/scheduledTask";

const route = useRoute();
const router = useRouter();

const log = ref(null);
const loading = ref(false);
const loadError = ref("");
const showFullError = ref(false);
const relatedLogs = ref([]);

const statusTag = computed(() => {
  const map = {
    success: { type: "success", text: "执行成功", icon: CircleCheckFilled },
    running: { type: "primary", text: "执行中", icon: Clock },
    failed: { type: "danger", text: "执行失败", icon: CircleCloseFilled },
    pending: { type: "info", text: "待执行", icon: Clock },
  };
  return map[log.value?.status] || { type: "info", text: log.value?.status || "未知", icon: Clock };
});

const stepActive = computed(() => {
  const map = { pending: 0, running: 1, success: 3, failed: 3 };
  return map[log.value?.status] ?? 1;
});

const resultSummary = computed(() => {
  if (!log.value) return "";
  if (log.value.status === "pending") return "等待执行";
  if (log.value.status === "running") return "执行中";
  const total = log.value.total_test_cases || 0;
  const passed = log.value.passed_test_cases || 0;
  if (total === 0) return "无测试用例";
  return `${passed}/${total} 通过`;
});

const successRate = computed(() => {
  if (!log.value?.total_test_cases) return 0;
  return ((log.value.passed_test_cases || 0) / log.value.total_test_cases * 100).toFixed(1);
});

const passPercent = computed(() => {
  if (!log.value?.total_test_cases) return 0;
  return Math.round((log.value.passed_test_cases || 0) / log.value.total_test_cases * 100);
});
const failPercent = computed(() => {
  if (!log.value?.total_test_cases) return 0;
  return Math.round((log.value.failed_test_cases || 0) / log.value.total_test_cases * 100);
});
const errorPercent = computed(() => {
  if (!log.value?.total_test_cases) return 0;
  return Math.round((log.value.error_test_cases || 0) / log.value.total_test_cases * 100);
});

const rateClass = computed(() => {
  const rate = parseFloat(successRate.value);
  if (rate >= 80) return "rate-success";
  if (rate >= 60) return "rate-warning";
  return "rate-danger";
});

const rateIcon = computed(() => {
  const rate = parseFloat(successRate.value);
  if (rate >= 80) return CircleCheckFilled;
  if (rate >= 60) return WarningFilled;
  return CircleCloseFilled;
});

function getStatusType(st) {
  const map = { success: "success", running: "primary", failed: "danger", pending: "info" };
  return map[st] || "info";
}
function getStatusText(st) {
  const map = { success: "成功", running: "执行中", failed: "失败", pending: "待执行" };
  return map[st] || st || "未知";
}
function getRateClass(row) {
  const rate = row.total_test_cases > 0 ? ((row.passed_test_cases || 0) / row.total_test_cases * 100) : 0;
  if (rate >= 80) return "text-success";
  if (rate >= 60) return "text-warning";
  return "text-danger";
}

function formatTime(val) {
  if (!val) return "-";
  const d = new Date(val);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/scheduled-tasks");
  }
}

function goToRelatedLog(row) {
  router.push(`/task-execution-logs/${row.id}`);
}

async function fetchRelatedLogs() {
  if (!log.value?.scheduled_task) return;
  try {
    const data = await taskExecutionLogApi.list({
      scheduled_task: log.value.scheduled_task,
      page_size: 5,
    });
    const rows = data.results || data || [];
    relatedLogs.value = rows.filter((r) => r.id !== log.value?.id).slice(0, 5);
  } catch {
    relatedLogs.value = [];
  }
}

async function fetchLog() {
  loading.value = true;
  loadError.value = "";
  try {
    const data = await taskExecutionLogApi.get(route.params.id);
    log.value = data;
    await fetchRelatedLogs();
  } catch (e) {
    loadError.value = e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchLog();
});
</script>

<style scoped>
.log-detail-page {
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

/* 卡片通用 */
.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  width: 100%;
}

.card-fill {
  height: 100%;
}

.card-header-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

/* 行间距 */
.detail-row {
  width: 100%;
}

/* 步骤条 */
.status-steps {
  margin: 8px 0 16px;
}
.step-extra-info {
  text-align: center;
  font-size: 13px;
  color: #909399;
  margin-top: 8px;
}

/* 描述列表 */
.detail-descriptions :deep(.el-descriptions__label) {
  font-weight: 500;
  color: #606266;
  white-space: nowrap;
}
.detail-descriptions :deep(.el-descriptions__content) {
  color: #303133;
}
.name-link {
  color: #409eff;
  text-decoration: none;
  font-weight: 500;
}
.name-link:hover {
  text-decoration: underline;
}

/* 测试结果统计 */
.result-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.result-stat-item {
  flex: 1;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px 8px;
  text-align: center;
}
.result-stat-item .stat-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.result-stat-item .stat-value {
  font-size: 22px;
  font-weight: 700;
}
.stat-value.total { color: #303133; }
.stat-value.success { color: #67c23a; }
.stat-value.danger { color: #f56c6c; }
.stat-value.warning { color: #e6a23c; }

/* 进度条 */
.progress-section {
  margin-bottom: 12px;
}
.progress-bar-wrapper {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  background: #f0f0f0;
}
.progress-bar-segment {
  transition: width 0.3s ease;
  height: 100%;
}
.success-bg { background: #67c23a; }
.danger-bg { background: #f56c6c; }
.warning-bg { background: #e6a23c; }

.progress-legend {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
}
.success-dot { background: #67c23a; }
.danger-dot { background: #f56c6c; }
.warning-dot { background: #e6a23c; }

/* 成功率 */
.rate-summary {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}
.rate-success {
  background: #f0f9eb;
  color: #67c23a;
}
.rate-warning {
  background: #fdf6ec;
  color: #e6a23c;
}
.rate-danger {
  background: #fef0f0;
  color: #f56c6c;
}

/* 错误信息 */
.error-pre {
  background: #fdf2f2;
  border: 1px solid #fce4e4;
  border-radius: 6px;
  padding: 16px;
  font-size: 13px;
  line-height: 1.5;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
  color: #f56c6c;
}
.error-pre-collapsed {
  max-height: 120px;
}

/* 相关链接 */
.related-links {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 数据表格 */
.data-table { width: 100%; }

.data-table :deep(.el-table__row) {
  cursor: pointer;
}

.text-success { color: #67c23a; font-weight: 600; }
.text-warning { color: #e6a23c; font-weight: 600; }
.text-danger { color: #f56c6c; font-weight: 600; }
.text-muted { color: #909399; }
</style>
