<template>
  <div class="execution-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">场景执行</h2>
        <span class="page-subtitle">查看场景执行结果和节点执行详情</span>
      </div>
      <div class="page-header-right">
        <el-button size="default" @click="goDesigner"><el-icon><ArrowLeft /></el-icon> 返回编排</el-button>
        <el-button size="default" type="primary" @click="refreshExecutions"><el-icon><Refresh /></el-icon> 刷新</el-button>
      </div>
    </div>

    <div class="panel-card">
    <div class="alert alert-info py-2" v-if="isRunning">
      正在执行中，页面每2秒自动刷新进度...
    </div>

    <div v-if="!executions.length" class="text-muted py-4 text-center">暂无执行记录</div>
    <div v-else-if="executions.length" class="execution-content">
      <!-- 执行历史列表：与日志抽屉格式一致 -->
      <div class="execution-history-list">
        <div
          v-for="row in executions"
          :key="row.id"
          class="execution-history-item"
          :class="{ 'execution-history-item--active': latestExecution?.id === row.id }"
          @click="selectExecution(row)"
        >
          <div class="d-flex justify-content-between align-items-center">
            <span
              :class="[
                'badge',
                row.status === 'success'
                  ? 'bg-success'
                  : row.status === 'partial_success'
                    ? 'bg-warning text-dark'
                    : row.status === 'failed'
                      ? 'bg-danger'
                      : 'bg-secondary'
              ]"
            >
              {{
                row.status === "success"
                  ? "成功"
                  : row.status === "partial_success"
                    ? "部分成功"
                    : row.status === "failed"
                      ? "失败"
                      : row.status === "running"
                        ? "执行中"
                        : row.status
              }}
            </span>
            <small class="text-muted">{{ formatTime(row.started_at) }}</small>
          </div>
          <div class="small text-muted mt-1">
            成功 {{ row.passed_nodes ?? 0 }}/{{ row.total_nodes ?? 0 }} · 耗时 {{ row.duration_ms || 0 }} ms
          </div>
          <div v-if="row.summary?.environment" class="small text-muted mt-1">
            运行环境：{{ row.summary.environment.name }}
          </div>
        </div>
      </div>
      <!-- 执行详情：与日志抽屉使用相同的 ExecutionLogPanel，含 file 类型参数展示 -->
      <div v-if="latestExecution" class="log-detail-section">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <strong>执行详情</strong>
          <span class="text-muted small">查看详情</span>
        </div>
        <ExecutionLogPanel
          :logs="latestExecution.node_results || []"
          :environment="latestExecution.summary?.environment"
        />
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import ExecutionLogPanel from "../components/ExecutionLogPanel.vue";
import { fetchSceneExecutions } from "../api/scene";

const route = useRoute();
const router = useRouter();
const executions = ref([]);
const latestExecution = ref(null);
const pollTimer = ref(null);

const isRunning = computed(() => latestExecution.value?.status === "running");

function formatTime(raw) {
  return raw ? new Date(raw).toLocaleString() : "-";
}

function goDesigner() {
  router.push({ name: "scene-designer", params: { id: route.params.id } });
}

function selectExecution(row) {
  latestExecution.value = row;
}

async function refreshExecutions() {
  const data = await fetchSceneExecutions(route.params.id);
  const list = Array.isArray(data) ? data : data.results || [];
  executions.value = list;
  if (route.params.executionId) {
    latestExecution.value = list.find((item) => String(item.id) === String(route.params.executionId)) || list[0] || null;
  } else {
    latestExecution.value = list[0] || null;
  }
  if (latestExecution.value?.status === "running") {
    startPolling();
  } else {
    stopPolling();
  }
}

function startPolling() {
  if (pollTimer.value) {
    return;
  }
  pollTimer.value = setInterval(() => {
    refreshExecutions().catch(() => {
      // 轮询异常不打断页面显示，下一轮继续尝试
    });
  }, 2000);
}

function stopPolling() {
  if (!pollTimer.value) {
    return;
  }
  clearInterval(pollTimer.value);
  pollTimer.value = null;
}

onMounted(refreshExecutions);
onUnmounted(stopPolling);
</script>

<style scoped>
.execution-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* ---- 页面标题 ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.page-header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.page-subtitle { font-size: var(--el-font-size-base); color: #909399; }
.page-header-right { display: flex; gap: 8px; align-items: center; }

.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.execution-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.execution-history-list {
  max-height: 240px;
  overflow-y: auto;
}

.execution-history-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid var(--el-border-color-lighter, #e9ecef);
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.execution-history-item:hover {
  background-color: var(--el-fill-color-lighter, #f0f2f5);
}

.execution-history-item--active {
  background-color: #f0f7ff;
  border-color: #409eff;
}

.log-detail-section {
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter, #e9ecef);
}
</style>

