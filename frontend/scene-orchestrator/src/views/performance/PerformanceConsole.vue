<template>
  <div class="card p-3 perf-console-page">
    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <button type="button" class="btn btn-outline-secondary" @click="goList">
        <i class="bi bi-arrow-left" aria-hidden="true" /> 返回列表
      </button>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-outline-primary" :disabled="loading" @click="refresh">
          <span v-if="loading" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
          刷新
        </button>
      </div>
    </div>

    <el-card v-if="task" shadow="never" class="meta-card">
      <div class="meta-grid">
        <div><strong>任务</strong> {{ task.name }}</div>
        <div><strong>状态</strong> <el-tag :type="statusTag(task.status)" size="small">{{ statusLabel(task.status) }}</el-tag></div>
        <div><strong>思考时间</strong> {{ task.extra_config?.think_time_ms ?? 0 }} ms</div>
        <div>
          <strong>参数化(CSV)</strong>
          {{ csvEnabled ? "已启用" : "未启用" }}
          <span v-if="csvName" class="text-muted">（{{ csvName }}）</span>
        </div>
      </div>
    </el-card>

    <!-- 卡在「执行中」/ 无曲线 时的排查说明（与后端 diagnostics 接口联动） -->
    <el-card v-if="diagnostics" shadow="never" class="diag-card">
      <template #header>
        <span class="diag-header">
          执行排查
          <el-tag v-if="diagnostics.risk_level" size="small" :type="riskTagType(diagnostics.risk_level)" class="diag-risk-tag">
            {{ riskLabel(diagnostics.risk_level) }}
          </el-tag>
        </span>
      </template>
      <el-descriptions :column="2" border size="small" class="diag-desc">
        <el-descriptions-item label="执行器模式">{{ diagnostics.executor_mode }}</el-descriptions-item>
        <el-descriptions-item label="计划时长">{{ diagnostics.run_time_sec }} 秒</el-descriptions-item>
        <el-descriptions-item label="采样条数">{{ diagnostics.results_count }}</el-descriptions-item>
        <el-descriptions-item label="距开始">
          {{ diagnostics.seconds_since_executed != null ? `${diagnostics.seconds_since_executed} 秒` : "—" }}
        </el-descriptions-item>
        <el-descriptions-item label="距最近一条采样">
          {{ diagnostics.seconds_since_last_result != null ? `${diagnostics.seconds_since_last_result} 秒` : "—" }}
        </el-descriptions-item>
        <el-descriptions-item v-if="diagnostics.executor_mode === 'celery'" label="Celery Worker">
          {{
            diagnostics.celery_worker_ok === true
              ? "inspect 可达"
              : diagnostics.celery_worker_ok === false
                ? "inspect 无响应"
                : "—"
          }}
        </el-descriptions-item>
      </el-descriptions>
      <ul v-if="diagnostics.hints?.length" class="diag-hints">
        <li v-for="(h, i) in diagnostics.hints" :key="i">{{ h }}</li>
      </ul>
      <p class="diag-foot text-muted">
        数据来自服务端聚合（task_id={{ diagnostics.task_id }}，server_now={{ diagnostics.server_now }}）。若需进一步确认请查服务器日志中「性能测试任务」或
        <code>performance_locust</code>。
      </p>
    </el-card>

    <!-- 当前阶段 -->
    <el-card v-if="stageInfo && task.extra_config?.stages?.length" shadow="never" class="stage-card">
      <template #header>
        <span>当前负载阶段</span>
      </template>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="阶段序号">
          第 {{ (stageInfo.index ?? 0) + 1 }} / {{ stageInfo.total }} 阶段
        </el-descriptions-item>
        <el-descriptions-item label="目标用户数">{{ stageInfo.stage?.users ?? "-" }}</el-descriptions-item>
        <el-descriptions-item label="加压速率">{{ stageInfo.stage?.spawn_rate ?? "-" }} 用户/秒</el-descriptions-item>
        <el-descriptions-item label="本阶段剩余时间">
          {{ stageInfo.done ? "已结束" : `${Math.ceil(stageInfo.remainingInStage || 0)} 秒` }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
    <el-card v-else-if="task" shadow="never" class="stage-card">
      <template #header>负载模式</template>
      <p class="text-muted">固定并发：{{ task.total_users }} 用户，{{ task.spawn_rate }} 用户/秒，持续 {{ task.run_time }} 秒</p>
    </el-card>

    <!-- 实时 KPI -->
    <div class="kpi-row" v-if="latest">
      <el-card shadow="hover" class="kpi-card"><div class="kpi-val">{{ (latest.requests_per_second ?? 0).toFixed(2) }}</div><div class="kpi-label">RPS</div></el-card>
      <el-card shadow="hover" class="kpi-card"><div class="kpi-val">{{ (latest.active_users ?? 0) }}</div><div class="kpi-label">活跃用户数</div></el-card>
      <el-card shadow="hover" class="kpi-card"><div class="kpi-val">{{ (latest.response_time_90 ?? 0).toFixed(0) }}</div><div class="kpi-label">RT P90(ms)</div></el-card>
      <el-card shadow="hover" class="kpi-card"><div class="kpi-val">{{ (latest.failure_rate ?? 0).toFixed(2) }}%</div><div class="kpi-label">失败率</div></el-card>
    </div>
    <el-alert
      v-if="assertFailHint"
      type="error"
      :closable="false"
      show-icon
      class="assert-alert"
      :title="assertFailHint"
    />

    <div class="charts-row">
      <el-card shadow="never" class="chart-card">
        <template #header>RPS 曲线</template>
        <div ref="rpsChartRef" class="echart-box" />
      </el-card>
      <el-card shadow="never" class="chart-card">
        <template #header>响应时间曲线</template>
        <div ref="rtChartRef" class="echart-box" />
      </el-card>
    </div>

    <p v-if="!loading && !results.length" class="empty-hint">暂无数据</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";
import { msgError } from "../../utils/uiMessage.js";
import * as echarts from "echarts";
import {
  fetchPerformanceTaskDetail,
  fetchPerformanceDiagnostics,
  fetchPerformanceResultsAll
} from "../../api/performance";
import { computeStageProgress } from "./performanceUtils.js";

const route = useRoute();
const router = useRouter();
const taskId = computed(() => route.params.id);

/** 防止快速切换路由时异步结果乱序写回 */
let loadSeq = 0;

const loading = ref(false);
const task = ref(null);
const results = ref([]);
const diagnostics = ref(null);
let pollTimer = null;

const rpsChartRef = ref(null);
const rtChartRef = ref(null);
let rpsChart = null;
let rtChart = null;

const latest = computed(() => (results.value.length ? results.value[results.value.length - 1] : null));

const csvEnabled = computed(() => !!(task.value?.csv_file || task.value?.extra_config?.csv_read_strategy));
const csvName = computed(() => {
  const f = task.value?.csv_file;
  if (!f) return "";
  const s = String(f);
  return s.split("/").pop() || s;
});

const stageInfo = computed(() => {
  if (!task.value) return null;
  return computeStageProgress(task.value, Date.now());
});

const assertFailHint = computed(() => {
  const n = Number(latest.value?.error_classification?.assertion_failure) || 0;
  if (n > 0) return `检测到业务断言失败（累计 ${n} 次，来自错误分类统计）`;
  return "";
});

function statusLabel(s) {
  const m = {
    draft: "草稿",
    running: "执行中",
    stopped: "已停止",
    completed: "已完成",
    finished: "已完成",
    failed: "失败"
  };
  return m[s] || s;
}
function statusTag(s) {
  const m = {
    draft: "info",
    running: "warning",
    stopped: "info",
    completed: "success",
    finished: "success",
    failed: "danger"
  };
  return m[s] || "info";
}

/** diagnostics.risk_level → 中文标签 */
function riskLabel(level) {
  const m = {
    idle: "非执行中",
    unknown: "数据异常",
    zombie_running: "疑似僵死(超时长未结束)",
    warming_up: "启动预热",
    no_samples: "无采样",
    sampling_stalled: "采样中断",
    healthy: "采样正常",
    ok: "已有数据"
  };
  return m[level] || level;
}
/** diagnostics.risk_level → Element Tag 类型 */
function riskTagType(level) {
  const m = {
    idle: "info",
    unknown: "danger",
    zombie_running: "danger",
    warming_up: "warning",
    no_samples: "danger",
    sampling_stalled: "warning",
    healthy: "success",
    ok: "success"
  };
  return m[level] || "info";
}

function goList() {
  router.push({ name: "perf-list" });
}

async function loadTask() {
  const id = taskId.value;
  if (!id) return;
  try {
    task.value = await fetchPerformanceTaskDetail(id);
  } catch (e) {
    msgError(e?.message || "加载任务失败");
  }
}

async function loadDiagnostics() {
  const id = taskId.value;
  if (!id) return;
  try {
    diagnostics.value = await fetchPerformanceDiagnostics(id);
  } catch {
    diagnostics.value = null;
  }
}

async function refresh() {
  const id = taskId.value;
  if (!id) return;
  loading.value = true;
  try {
    const res = await fetchPerformanceResultsAll(id);
    results.value = res.results || [];
    await loadDiagnostics();
  } catch (e) {
    msgError(e?.message || "加载结果失败");
  } finally {
    loading.value = false;
  }
}

function disposeCharts() {
  rpsChart?.dispose();
  rtChart?.dispose();
  rpsChart = null;
  rtChart = null;
}

function renderCharts() {
  if (!rpsChartRef.value || !rtChartRef.value) return;
  const list = results.value;
  if (!list.length) {
    disposeCharts();
    return;
  }
  const x = list.map((r) => (r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : ""));
  if (!rpsChart) rpsChart = echarts.init(rpsChartRef.value);
  if (!rtChart) rtChart = echarts.init(rtChartRef.value);

  rpsChart.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: { type: "category", data: x },
    yAxis: { type: "value", name: "RPS" },
    series: [{ type: "line", smooth: true, data: list.map((r) => r.requests_per_second ?? 0), areaStyle: { opacity: 0.08 } }]
  });
  rtChart.setOption({
    tooltip: { trigger: "axis" },
    legend: { data: ["P50", "P90", "P95", "P99"], bottom: 0 },
    grid: { left: "3%", right: "4%", bottom: "12%", containLabel: true },
    xAxis: { type: "category", data: x },
    yAxis: { type: "value", name: "ms" },
    series: [
      { name: "P50", type: "line", smooth: true, data: list.map((r) => r.response_time_50 ?? 0) },
      { name: "P90", type: "line", smooth: true, data: list.map((r) => r.response_time_90 ?? 0) },
      { name: "P95", type: "line", smooth: true, data: list.map((r) => r.p95 ?? 0) },
      { name: "P99", type: "line", smooth: true, data: list.map((r) => r.p99 ?? 0) }
    ]
  });
  rpsChart.resize();
  rtChart.resize();
}

function shouldPoll() {
  return task.value?.status === "running";
}

/**
 * 从列表「开始/重新运行」进入时，任务状态可能尚未从 draft/已完成 更新为 running，需短暂重试 loadTask，
 * 否则 startPoll 永远不会启动，页面像「没刷新」。
 */
async function waitForRunningAfterStart() {
  if (!route.query._run) return;
  for (let i = 0; i < 30; i++) {
    if (task.value?.status === "running") return;
    if (task.value?.status === "failed") return;
    await new Promise((r) => setTimeout(r, 350));
    await loadTask();
  }
}

/** 仅「执行中」任务轮询；每次拉取结果后同步任务状态，若已结束则停止轮询 */
async function pollTick() {
  if (!taskId.value) {
    stopPoll();
    return;
  }
  await refresh();
  await loadTask();
  if (!taskId.value) {
    stopPoll();
    return;
  }
  await nextTick(renderCharts);
  if (!shouldPoll()) {
    stopPoll();
  }
}

function startPoll() {
  stopPoll();
  if (!shouldPoll()) return;
  pollTimer = setInterval(() => {
    pollTick();
  }, 1500);
}
function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function loadConsoleData() {
  if (!taskId.value) return;
  const seq = ++loadSeq;
  stopPoll();
  disposeCharts();
  results.value = [];
  diagnostics.value = null;

  await loadTask();
  if (seq !== loadSeq) return;

  await waitForRunningAfterStart();
  if (seq !== loadSeq) return;

  await refresh();
  if (seq !== loadSeq) return;

  await nextTick(renderCharts);
  startPoll();
}

watch(
  () => results.value.length,
  () => nextTick(renderCharts)
);

/** 状态由非 running 变为 running（含服务端滞后）：补一次拉数并启动轮询 */
watch(
  () => task.value?.status,
  async (status, prev) => {
    if (prev === undefined) return;
    if (!taskId.value) return;
    if (status === "running") {
      await refresh();
      await nextTick(renderCharts);
      startPoll();
    }
  }
);

/**
 * 同一路径仅 query 变化（如重新运行带 _run）时组件会复用，需重新拉数。
 * 离开控制台时全局路由已变为列表等，此时 params.id 会丢失，若仍调用 loadConsoleData 会请求 .../undefined/results/。
 */
watch(
  () => route.fullPath,
  async (_to, from) => {
    if (from === undefined) return;
    if (route.name !== "perf-console" || !route.params?.id) return;
    await loadConsoleData();
  }
);

onBeforeRouteLeave(() => {
  stopPoll();
});

onMounted(async () => {
  await loadConsoleData();
  window.addEventListener("resize", onResize);
});

function onResize() {
  rpsChart?.resize();
  rtChart?.resize();
}

onUnmounted(() => {
  stopPoll();
  disposeCharts();
  window.removeEventListener("resize", onResize);
});
</script>

<style scoped>
.perf-console-page {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 0;
  overflow: auto;
}
.meta-card,
.stage-card,
.diag-card {
  margin-bottom: 16px;
  border-radius: 8px;
}
.diag-header {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.diag-risk-tag {
  margin-left: 4px;
}
.diag-desc {
  margin-bottom: 12px;
}
.diag-hints {
  margin: 0 0 12px;
  padding-left: 1.25rem;
  line-height: 1.6;
  color: #334155;
  font-size: var(--el-font-size-base);
}
.diag-foot {
  margin: 0;
  font-size: var(--el-font-size-extra-small);
  line-height: 1.5;
}
.diag-foot code {
  font-size: var(--el-font-size-extra-small);
  background: #f1f5f9;
  padding: 0 4px;
  border-radius: 4px;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  font-size: var(--el-font-size-base);
}
.text-muted {
  color: #909399;
  font-size: var(--el-font-size-small);
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.kpi-card {
  text-align: center;
  border-radius: 8px;
}
.kpi-val {
  font-size: var(--fs-h2);
  font-weight: 600;
  color: #4361ee;
}
.kpi-label {
  font-size: var(--el-font-size-small);
  color: #64748b;
  margin-top: 4px;
}
.assert-alert {
  margin-bottom: 16px;
}
.charts-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}
@media (min-width: 900px) {
  .charts-row {
    grid-template-columns: 1fr 1fr;
  }
}
.chart-card {
  border-radius: 8px;
}
.echart-box {
  height: 320px;
  width: 100%;
}
.empty-hint {
  text-align: center;
  color: #909399;
  padding: 24px;
}
</style>
