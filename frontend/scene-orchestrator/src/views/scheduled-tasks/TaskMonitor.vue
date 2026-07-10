<template>
  <div class="task-monitor">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">定时任务监控</h2>
      </div>
      <div class="page-header-right">
        <el-button type="primary" @click="refreshStatus">
          <el-icon><Refresh /></el-icon> 刷新状态
        </el-button>
        <el-button type="warning" @click="syncTasks">
          <el-icon><Connection /></el-icon> 同步任务
        </el-button>
        <el-button type="danger" @click="cleanupTasks">
          <el-icon><Remove /></el-icon> 清理孤立任务
        </el-button>
      </div>
    </div>

    <!-- 状态概览 -->
    <el-row :gutter="16" class="mb-4">
      <el-col :xs="12" :sm="6" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-card-body">
            <div class="stat-card-icon" style="background: rgba(59,130,246,0.1); color: #3b82f6;">
              <el-icon :size="22"><Clock /></el-icon>
            </div>
            <div class="stat-card-info">
              <div class="stat-card-value">{{ monitorData.db_tasks_count }}</div>
              <div class="stat-card-label">数据库任务</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-card-body">
            <div class="stat-card-icon" style="background: rgba(16,185,129,0.1); color: #10b981;">
              <el-icon :size="22"><Connection /></el-icon>
            </div>
            <div class="stat-card-info">
              <div class="stat-card-value">{{ monitorData.celery_tasks_count }}</div>
              <div class="stat-card-label">Celery任务</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-card-body">
            <div class="stat-card-icon" :style="beatStyle">
              <el-icon :size="22"><Opportunity /></el-icon>
            </div>
            <div class="stat-card-info">
              <div class="stat-card-value" :style="{ color: beatColor }">
                {{ monitorData.beat_status?.status === 'ok' ? '正常' : '异常' }}
              </div>
              <div class="stat-card-label">Beat状态</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-card-body">
            <div class="stat-card-icon" style="background: rgba(99,102,241,0.1); color: #6366f1;">
              <el-icon :size="22"><UserFilled /></el-icon>
            </div>
            <div class="stat-card-info">
              <div class="stat-card-value">{{ workerCount }}</div>
              <div class="stat-card-label">活动Worker</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务列表 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header-row">
          <span class="card-title"><el-icon><List /></el-icon> 任务详情</span>
        </div>
      </template>

      <div v-if="loading" class="loading-state">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <el-empty v-else-if="monitorData.tasks?.length === 0" description="暂无活动任务" :image-size="80" />

      <el-table v-else :data="monitorData.tasks || []" stripe size="small" class="data-table">
        <el-table-column label="任务名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <router-link :to="`/scheduled-tasks/${row.id}`" class="name-link">
              {{ row.name }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column label="测试套件" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.test_suite_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="调度类型" width="100">
          <template #default="{ row }">{{ row.schedule_type_display }}</template>
        </el-table-column>
        <el-table-column label="下次执行" width="150">
          <template #default="{ row }">
            {{ row.next_run_time || '未设置' }}
          </template>
        </el-table-column>
        <el-table-column label="Celery同步" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.celery_synced ? 'success' : 'warning'" size="small">
              {{ row.celery_synced ? '已同步' : '未同步' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后执行" width="150">
          <template #default="{ row }">
            {{ row.last_run_time || '从未执行' }}
          </template>
        </el-table-column>
        <el-table-column label="成功率" width="80" align="center">
          <template #default="{ row }">
            <span :class="rateClass(row.success_rate)">{{ row.success_rate?.toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="success" @click="handleRunNow(row.id)">
              <el-icon><CaretRight /></el-icon> 执行
            </el-button>
            <el-button size="small" text type="primary" @click="handleResync(row.id)">
              <el-icon><Connection /></el-icon> 同步
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 操作日志 -->
    <el-card shadow="never" class="log-card mt-4">
      <template #header>
        <div class="card-header-row">
          <span class="card-title"><el-icon><Document /></el-icon> 操作日志</span>
          <el-button size="small" @click="logs = []">清空日志</el-button>
        </div>
      </template>
      <div class="log-container" ref="logContainer">
        <div v-if="logs.length === 0" class="log-empty">暂无日志</div>
        <div v-for="(log, i) in logs" :key="i" class="log-line">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.message }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from "vue";
import { ElMessage } from "element-plus";
import {
  Refresh, Connection, Remove, Clock, Opportunity, UserFilled,
  List, Loading, CaretRight, Document,
} from "@element-plus/icons-vue";
import { taskMonitorApi, scheduledTaskApi } from "../../api/scheduledTask";

const loading = ref(false);
const logContainer = ref(null);
const logs = ref([]);
let timer = null;

const monitorData = reactive({
  db_tasks_count: "-",
  celery_tasks_count: "-",
  beat_status: { status: "-", active_workers: [] },
  tasks: [],
});

const beatColor = computed(() =>
  monitorData.beat_status?.status === "ok" ? "#10b981" : "#ef4444"
);

const beatStyle = computed(() => ({
  background: monitorData.beat_status?.status === "ok"
    ? "rgba(16,185,129,0.1)"
    : "rgba(239,68,68,0.1)",
  color: beatColor.value,
}));

const workerCount = computed(() =>
  monitorData.beat_status?.active_workers?.length || 0
);

onMounted(() => {
  refreshStatus();
  // 每30秒自动刷新
  timer = setInterval(refreshStatus, 30000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});

function addLog(message) {
  const now = new Date();
  const time = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
  logs.value.push({ time, message });
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
    }
  });
}

async function refreshStatus() {
  addLog("刷新状态...");
  loading.value = true;
  try {
    const data = await taskMonitorApi.status();
    if (data.success) {
      monitorData.db_tasks_count = data.db_tasks_count;
      monitorData.celery_tasks_count = data.celery_tasks_count;
      monitorData.beat_status = data.beat_status;
      monitorData.tasks = data.tasks || [];
      addLog("状态刷新完成");
    }
  } catch (e) {
    addLog(`刷新失败: ${e.message}`);
  } finally {
    loading.value = false;
  }
}

async function syncTasks() {
  addLog("开始同步所有任务...");
  try {
    const data = await taskMonitorApi.sync();
    if (data.success) {
      addLog(`同步完成: ${data.message}`);
      await refreshStatus();
    }
  } catch (e) {
    addLog(`同步失败: ${e.message}`);
  }
}

async function cleanupTasks() {
  addLog("开始清理孤立任务...");
  try {
    const data = await taskMonitorApi.cleanup();
    if (data.success) {
      addLog(`清理完成: ${data.message}`);
      await refreshStatus();
    }
  } catch (e) {
    addLog(`清理失败: ${e.message}`);
  }
}

async function handleRunNow(taskId) {
  addLog(`立即执行任务 ${taskId}...`);
  try {
    const data = await scheduledTaskApi.runNow(taskId);
    addLog(`任务执行: ${data.message}`);
  } catch (e) {
    addLog(`执行失败: ${e.message}`);
  }
}

async function handleResync(taskId) {
  addLog(`重新同步任务 ${taskId}...`);
  try {
    const data = await taskMonitorApi.sync();
    addLog(`同步结果: ${data.message || "已完成"}`);
    await refreshStatus();
  } catch (e) {
    addLog(`同步失败: ${e.message}`);
  }
}

function rateClass(rate) {
  if (rate >= 80) return "text-success";
  if (rate >= 60) return "text-warning";
  return "text-danger";
}
</script>

<style scoped>
.mb-4 { margin-bottom: 20px; }
.mt-4 { margin-top: 20px; }

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
.page-header-right {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 统计卡片 */
.stat-card {
  border-radius: 8px;
}
.stat-card-body {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-card-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary, #0f172a);
  line-height: 1.2;
}
.stat-card-label {
  font-size: 0.8rem;
  color: var(--text-secondary, #64748b);
  margin-top: 2px;
}

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
  gap: 10px;
  padding: 40px 0;
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

/* 日志区域 */
.log-container {
  height: 240px;
  overflow-y: auto;
  background: #f8fafc;
  border-radius: 6px;
  padding: 12px;
  font-family: var(--font-mono, "Fira Code", monospace);
  font-size: 0.8rem;
  line-height: 1.6;
}
.log-empty {
  color: var(--text-secondary, #94a3b8);
  text-align: center;
  padding: 40px 0;
}
.log-line {
  display: flex;
  gap: 12px;
}
.log-time {
  color: #94a3b8;
  flex-shrink: 0;
}
.log-msg {
  color: var(--text-primary, #0f172a);
  word-break: break-all;
}

/* 暗色模式适配 */
.dark-mode .log-container {
  background: #1e293b;
}
.dark-mode .log-msg {
  color: #e2e8f0;
}
.dark-mode .name-link {
  color: var(--primary-color, #3b82f6);
}

.text-success { color: var(--success-color, #10b981); }
.text-warning { color: var(--warning-color, #f59e0b); }
.text-danger { color: var(--danger-color, #ef4444); }
</style>
