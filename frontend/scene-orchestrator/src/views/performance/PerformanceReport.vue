<template>
  <div class="card p-3 perf-report-page">
    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <button type="button" class="btn btn-outline-secondary" @click="goList">
        <i class="bi bi-arrow-left" aria-hidden="true" /> 返回列表
      </button>
      <button type="button" class="btn btn-sm btn-outline-primary" @click="reload">刷新</button>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />

    <template v-else-if="task">
      <!-- 顶部统计卡片 -->
      <div class="stat-cards">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ summaryCards.totalReq }}</div>
          <div class="stat-label">总请求数(估算)</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ summaryCards.failedReq }}</div>
          <div class="stat-label">失败请求数(估算)</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ (report?.avg_failure_rate_percent ?? 0).toFixed(2) }}%</div>
          <div class="stat-label">失败率(平均)</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ summaryCards.durationSec }}s</div>
          <div class="stat-label">总耗时</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ rpsAvg.toFixed(2) }}</div>
          <div class="stat-label">RPS(avg)</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ (report?.max_qps ?? 0).toFixed(2) }}</div>
          <div class="stat-label">RPS(max)</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ fmt(report?.avg_response_time_50_ms) }}</div>
          <div class="stat-label">P50(ms) 平均</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ fmt(report?.avg_response_time_90_ms) }}</div>
          <div class="stat-label">P90(ms) 平均</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ fmt(report?.avg_p95_ms) }}</div>
          <div class="stat-label">P95(ms) 平均</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ fmt(report?.avg_p99_ms) }}</div>
          <div class="stat-label">P99(ms) 平均</div>
        </el-card>
        <el-card shadow="hover" class="stat-card">
          <div class="stat-val">{{ fmt(report?.max_response_time_ms) }}</div>
          <div class="stat-label">最大RT(ms)</div>
        </el-card>
      </div>

      <el-collapse v-model="activePanels">
        <el-collapse-item title="响应时间分位数分布" name="pct">
          <div ref="lineChartRef" class="echart-large" />
          <p v-if="!results.length" class="empty-inline">暂无数据</p>
        </el-collapse-item>
        <el-collapse-item title="错误分类" name="err">
          <div ref="pieChartRef" class="echart-medium" />
          <p v-if="!pieHasData" class="empty-inline">暂无数据</p>
        </el-collapse-item>
        <el-collapse-item title="业务断言结果" name="assert">
          <el-table v-if="assertionRows.length" :data="assertionRows" border size="small" stripe>
            <el-table-column prop="jsonpath" label="JSONPath" min-width="180" />
            <el-table-column prop="op" label="操作符" width="100" />
            <el-table-column prop="expect" label="期望值" show-overflow-tooltip />
            <el-table-column prop="pass" label="是否通过" width="120">
              <template #default="{ row }">
                <el-tag :type="row.pass ? 'success' : 'danger'" size="small">{{ row.passText }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="说明" min-width="200" show-overflow-tooltip />
          </el-table>
          <p v-else class="empty-inline">未配置业务断言</p>
        </el-collapse-item>
        <el-collapse-item title="负载阶段回放" name="stage">
          <div v-if="stages.length" ref="stageChartRef" class="echart-medium" />
          <el-timeline v-if="stages.length" class="stage-timeline">
            <el-timeline-item v-for="(s, i) in stages" :key="i" :timestamp="`阶段 ${i + 1}`" placement="top">
              {{ s.duration_sec }} 秒 · {{ s.users }} 用户 · {{ s.spawn_rate }} 用户/秒
            </el-timeline-item>
          </el-timeline>
          <p v-else class="empty-inline">固定并发模式无阶段划分</p>
        </el-collapse-item>
        <el-collapse-item title="参数化(CSV)" name="csv">
          <el-descriptions v-if="csvInfo.used" :column="1" border size="small">
            <el-descriptions-item label="文件名">{{ csvInfo.name }}</el-descriptions-item>
            <el-descriptions-item label="读取策略">{{ csvInfo.strategyLabel }}</el-descriptions-item>
            <el-descriptions-item label="行数说明">后端未返回行数时显示「—」；可在上传时记录于任务备注</el-descriptions-item>
          </el-descriptions>
          <p v-else class="empty-inline">未使用 CSV 参数化</p>
        </el-collapse-item>
      </el-collapse>
    </template>

    <el-empty v-else description="无法加载任务" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { msgError } from "../../utils/uiMessage.js";
import * as echarts from "echarts";
import {
  fetchPerformanceTaskDetail,
  fetchPerformanceResultsAll,
  fetchPerformanceReport
} from "../../api/performance";
import { estimateTotalRequests, ERROR_LABELS } from "./performanceUtils.js";

const route = useRoute();
const router = useRouter();
const taskId = computed(() => route.params.id);

const loading = ref(true);
const task = ref(null);
const report = ref(null);
const results = ref([]);
const activePanels = ref(["pct", "err", "assert", "stage", "csv"]);

const lineChartRef = ref(null);
const pieChartRef = ref(null);
const stageChartRef = ref(null);
let lineChart = null;
let pieChart = null;
let stageChart = null;

const stages = computed(() => {
  const s = task.value?.extra_config?.stages;
  return Array.isArray(s) ? s : [];
});

const rpsAvg = computed(() => {
  if (!results.value.length) return 0;
  const sum = results.value.reduce((s, r) => s + (Number(r.requests_per_second) || 0), 0);
  return sum / results.value.length;
});

const csvInfo = computed(() => {
  const t = task.value;
  if (!t) return { used: false };
  const f = t.csv_file;
  const name = f ? String(f).split("/").pop() : "";
  const strat = t.extra_config?.csv_read_strategy || "per_iteration";
  const strategyLabel = strat === "per_user" ? "每用户一行" : "每迭代一行";
  return {
    used: !!f,
    name: name || "—",
    strategyLabel
  };
});

const summaryCards = computed(() => {
  const totalEst = estimateTotalRequests(results.value);
  const last = results.value.length ? results.value[results.value.length - 1] : null;
  const fr = last ? Number(last.failure_rate) || 0 : 0;
  const failedEst = Math.round((totalEst * fr) / 100);
  let durationSec = 0;
  if (task.value?.executed_at && task.value?.finished_at) {
    durationSec = Math.round(
      (new Date(task.value.finished_at) - new Date(task.value.executed_at)) / 1000
    );
  }
  return { totalReq: totalEst, failedReq: failedEst, durationSec };
});

const assertionRows = computed(() => {
  const rules = task.value?.extra_config?.assertions;
  if (!Array.isArray(rules) || !rules.length) return [];
  const lastRow = results.value.length ? results.value[results.value.length - 1] : null;
  const lastEc = lastRow?.error_classification || {};
  const af = Number(lastEc?.assertion_failure) || 0;
  const overallOk =
    (task.value?.status === "completed" || task.value?.status === "finished") && af === 0;
  const overallFail = af > 0;
  return rules.map((r) => {
    let passText = "—";
    let pass = true;
    let reason = "后端聚合统计未区分单条规则；以整体错误分类为准";
    if (task.value?.status === "running") {
      passText = "压测中";
      pass = true;
      reason = "压测结束后根据错误分类更新";
    } else if (task.value?.status === "stopped") {
      passText = "已停止";
      pass = true;
      reason = "任务已手动停止，以下为停止前采样聚合";
    } else if (overallFail) {
      pass = false;
      passText = "存在失败(整体)";
      reason = `断言类失败累计 ${af} 次（无法区分具体 JSONPath）`;
    } else if (overallOk) {
      passText = "通过(整体)";
      reason = "HTTP 与业务断言均未报告失败";
    } else if (task.value?.status === "failed") {
      passText = "未知";
      reason = "任务失败";
    }
    return {
      jsonpath: r.jsonpath,
      op: r.op,
      expect: r.op === "not_null" ? "—" : JSON.stringify(r.expect),
      pass,
      passText,
      reason
    };
  });
});

const pieHasData = computed(() => {
  const ec = report.value?.error_classification;
  if (!ec || typeof ec !== "object") return false;
  return Object.values(ec).some((v) => Number(v) > 0);
});

function fmt(v) {
  if (v === undefined || v === null || Number.isNaN(Number(v))) return 0;
  return Number(v).toFixed(2);
}

function goList() {
  router.push({ name: "perf-list" });
}

async function reload() {
  loading.value = true;
  try {
    const [t, rep, res] = await Promise.all([
      fetchPerformanceTaskDetail(taskId.value),
      fetchPerformanceReport(taskId.value),
      fetchPerformanceResultsAll(taskId.value)
    ]);
    task.value = t;
    report.value = rep.report ?? null;
    results.value = res.results || [];
  } catch (e) {
    msgError(e?.message || "加载失败");
  } finally {
    loading.value = false;
    await nextTick();
    renderCharts();
  }
}

function renderLine() {
  if (!lineChartRef.value) return;
  if (!results.value.length) {
    lineChart?.dispose();
    lineChart = null;
    return;
  }
  if (!lineChart) lineChart = echarts.init(lineChartRef.value);
  const list = results.value;
  const x = list.map((r) => (r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : ""));
  lineChart.setOption({
    title: { text: "分位数折线（ms）", left: "center", textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    legend: { data: ["P50", "P90", "P95", "P99"], bottom: 0 },
    grid: { left: "3%", right: "4%", bottom: "14%", containLabel: true },
    xAxis: { type: "category", data: x },
    yAxis: { type: "value", name: "ms" },
    series: [
      { name: "P50", type: "line", smooth: true, data: list.map((r) => r.response_time_50 ?? 0) },
      { name: "P90", type: "line", smooth: true, data: list.map((r) => r.response_time_90 ?? 0) },
      { name: "P95", type: "line", smooth: true, data: list.map((r) => r.p95 ?? 0) },
      { name: "P99", type: "line", smooth: true, data: list.map((r) => r.p99 ?? 0) }
    ]
  });
  lineChart.resize();
}

function renderPie() {
  if (!pieChartRef.value) return;
  const ec = report.value?.error_classification || {};
  const data = Object.entries(ec)
    .filter(([, v]) => Number(v) > 0)
    .map(([k, v]) => ({ name: ERROR_LABELS[k] || k, value: v }));
  if (!data.length) {
    pieChart?.dispose();
    pieChart = null;
    return;
  }
  if (!pieChart) pieChart = echarts.init(pieChartRef.value);
  pieChart.setOption({
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [{ type: "pie", radius: ["40%", "70%"], data }]
  });
  pieChart.resize();
}

function renderStageBar() {
  if (!stageChartRef.value || !stages.value.length) return;
  if (!stageChart) stageChart = echarts.init(stageChartRef.value);
  const labels = stages.value.map((_, i) => `阶段${i + 1}`);
  stageChart.setOption({
    title: { text: "各阶段目标用户数", left: "center", textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: labels },
    yAxis: { type: "value", name: "虚拟用户" },
    series: [{ type: "bar", data: stages.value.map((s) => s.users), itemStyle: { color: "#4361ee" } }]
  });
  stageChart.resize();
}

function renderCharts() {
  renderLine();
  renderPie();
  renderStageBar();
}

function onResize() {
  lineChart?.resize();
  pieChart?.resize();
  stageChart?.resize();
}

watch(
  () => results.value.length,
  () => nextTick(renderCharts)
);

onMounted(() => {
  reload();
  window.addEventListener("resize", onResize);
});

onUnmounted(() => {
  lineChart?.dispose();
  pieChart?.dispose();
  stageChart?.dispose();
  window.removeEventListener("resize", onResize);
});
</script>

<style scoped>
.perf-report-page {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  min-height: 0;
  overflow: auto;
}
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.stat-card {
  text-align: center;
  border-radius: 8px;
}
.stat-val {
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}
.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}
.echart-large {
  height: 380px;
  width: 100%;
}
.echart-medium {
  height: 300px;
  width: 100%;
}
.empty-inline {
  text-align: center;
  color: #909399;
  padding: 16px;
}
.stage-timeline {
  margin-top: 16px;
  max-width: 640px;
}
</style>
