<template>
  <div class="perf-batch-report-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">批量压测报告</h2>
        <span class="page-subtitle">{{ batchData?.name || '' }}</span>
      </div>
      <div class="page-header-right">
        <el-button @click="goBack">返回</el-button>
        <el-button type="primary" @click="refreshReport">刷新报告</el-button>
      </div>
    </div>

    <!-- 基本信息卡片 -->
    <el-card v-if="batchData" class="info-card">
      <el-row :gutter="24">
        <el-col :span="6">
          <div class="info-item">
            <div class="info-label">状态</div>
            <el-tag :type="batchStatusTagType(batchData.status)" size="large">
              {{ batchStatusLabel(batchData.status) }}
            </el-tag>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="info-item">
            <div class="info-label">执行模式</div>
            <div class="info-value">{{ batchData.execute_mode === 'parallel' ? '并行' : '串行' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="info-item">
            <div class="info-label">总任务数</div>
            <div class="info-value">{{ batchData.total_tasks || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="info-item">
            <div class="info-label">成功率</div>
            <div class="info-value success-rate">{{ batchData.success_rate_percent }}%</div>
          </div>
        </el-col>
      </el-row>
      
      <el-row :gutter="24" class="mt-16">
        <el-col :span="8">
          <div class="info-item">
            <div class="info-label">开始时间</div>
            <div class="info-value">{{ formatDate(batchData.started_at) }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="info-item">
            <div class="info-label">结束时间</div>
            <div class="info-value">{{ formatDate(batchData.finished_at) }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="info-item">
            <div class="info-label">进度</div>
            <el-progress 
              :percentage="batchData.progress_percent" 
              :color="computeProgressColor(batchData)"
              :text-inside="true"
            />
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 整体聚合指标 -->
    <el-card v-if="report && report.overall_report && report.overall_report.aggregated_metrics" class="metrics-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">整体聚合指标</span>
        </div>
      </template>
      
      <el-row :gutter="32" class="metrics-grid">
        <el-col :span="6" v-for="(value, key) in report.overall_report.aggregated_metrics" :key="key">
          <div class="metric-item">
            <div class="metric-label">{{ getMetricLabel(key) }}</div>
            <div class="metric-value">{{ value }}{{ getMetricUnit(key) }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 任务性能对比 -->
    <el-card v-if="report?.overall_report?.task_performance_comparison?.length > 0" class="comparison-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">各任务性能对比</span>
        </div>
      </template>
      
      <el-table :data="report.overall_report.task_performance_comparison" stripe size="small">
        <el-table-column prop="task_name" label="任务名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="interface" label="接口 URL" min-width="250" show-overflow-tooltip />
        <el-table-column prop="method" label="方法" width="70" align="center" />
        <el-table-column prop="env" label="环境" width="100" />
        <el-table-column label="采样点" width="80" align="center">
          <template #default="{ row }">
            {{ row.sample_count || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="最大 QPS" width="90" align="center">
          <template #default="{ row }">
            {{ formatNumber(row.max_rps) }}
          </template>
        </el-table-column>
        <el-table-column label="平均 QPS" width="90" align="center">
          <template #default="{ row }">
            {{ formatNumber(row.avg_rps) }}
          </template>
        </el-table-column>
        <el-table-column label="P50 (ms)" width="85" align="center">
          <template #default="{ row }">
            {{ formatNumber(row.avg_response_time_50_ms) }}
          </template>
        </el-table-column>
        <el-table-column label="P90 (ms)" width="85" align="center">
          <template #default="{ row }">
            {{ formatNumber(row.avg_response_time_90_ms) }}
          </template>
        </el-table-column>
        <el-table-column label="P95 (ms)" width="85" align="center">
          <template #default="{ row }">
            {{ formatNumber(row.avg_p95_ms) }}
          </template>
        </el-table-column>
        <el-table-column label="P99 (ms)" width="85" align="center">
          <template #default="{ row }">
            {{ formatNumber(row.avg_p99_ms) }}
          </template>
        </el-table-column>
        <el-table-column label="失败率 (%)" width="90" align="center">
          <template #default="{ row }">
            <span :class="failureRateClass(row.avg_failure_rate_percent)">
              {{ formatNumber(row.avg_failure_rate_percent) }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 环境分组统计 -->
    <el-card v-if="report?.overall_report?.environment_breakdown" class="env-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">按环境分组统计</span>
        </div>
      </template>
      
      <el-row :gutter="24">
        <el-col :span="24" v-for="(envData, envName) in report.overall_report.environment_breakdown" :key="envName">
          <div class="env-stats-box">
            <div class="env-name">{{ envName }}</div>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="任务数">{{ envData.task_count }}</el-descriptions-item>
              <el-descriptions-item label="总采样点">{{ envData.total_samples }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 错误分析 -->
    <el-card v-if="report?.overall_report?.error_analysis?.total_errors > 0" class="error-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">错误分析</span>
        </div>
      </template>
      
      <el-table :data="errorAnalysisTable" stripe size="small">
        <el-table-column prop="type" label="错误类型" min-width="150" />
        <el-table-column prop="count" label="发生次数" width="100" align="center" />
        <el-table-column label="占比" width="120" align="center">
          <template #default="{ $index }">
            {{ computeErrorPercentage($index) }}%
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 加载动画 -->
    <el-empty v-if="!loading && !report && !errorMessage" description="暂无报告数据" />
    
    <!-- 错误提示 -->
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" class="mt-16" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { fetchBatchReport, fetchBatchDetail } from "../../api/performance";
import { msgError } from "../../utils/uiMessage.js";

const router = useRouter();
const route = useRoute();

const loading = ref(false);
const errorMessage = ref("");
const batchData = ref(null);
const report = ref(null);

// 标签翻译
function batchStatusLabel(status) {
  const map = {
    pending: "待执行",
    running: "执行中",
    partial_success: "部分成功",
    completed: "全部完成",
    failed: "执行失败",
  };
  return map[status] || status;
}

function batchStatusTagType(status) {
  const map = {
    pending: "info",
    running: "warning",
    partial_success: "warning",
    completed: "success",
    failed: "danger",
  };
  return map[status] || "info";
}

// 进度条颜色
function computeProgressColor(data) {
  if (data.status === "completed") return "#67c23a";
  if (data.status === "failed") return "#f56c6c";
  if (data.status === "running") return "#e6a23c";
  return "#409eff";
}

// 格式化数字
function formatNumber(value) {
  if (value === undefined || value === null || value === "") return "-";
  return Number(value).toFixed(2);
}

// 失败率样式
function failureRateClass(failureRate) {
  const rate = parseFloat(failureRate) || 0;
  if (rate >= 10) return "text-danger";
  if (rate >= 5) return "text-warning";
  return "";
}

// 指标标签映射
const metricsMap = {
  max_rps: { label: "最大 QPS" },
  avg_rps: { label: "平均 QPS" },
  rt50: { label: "平均 P50" },
  rt90: { label: "平均 P90" },
  users: { label: "最大并发用户" },
  failure: { label: "平均失败率" },
  p95: { label: "平均 P95" },
  p99: { label: "平均 P99" },
  max_p95: { label: "最大 P95" },
  max_p99: { label: "最大 P99" },
  max_rt: { label: "最大响应时间" },
};

function getMetricLabel(key) {
  return metricsMap[key]?.label || key;
}

function getMetricUnit(key) {
  const units = {
    max_rps: " QPS",
    avg_rps: " QPS",
    rt50: " ms",
    rt90: " ms",
    users: " 人",
    failure: " %",
    p95: " ms",
    p99: " ms",
    max_p95: " ms",
    max_p99: " ms",
    max_rt: " ms",
  };
  return units[key] || "";
}

// 错误分析表
const errorAnalysisTable = computed(() => {
  if (!report.value?.overall_report?.error_analysis?.by_type) {
    return [];
  }
  
  const errors = report.value.overall_report.error_analysis.by_type;
  const total = report.value.overall_report.error_analysis.total_errors;
  
  return Object.entries(errors).map(([type, count]) => ({
    type,
    count,
  })).sort((a, b) => b.count - a.count);
});

function computeErrorPercentage(index) {
  const table = errorAnalysisTable.value;
  if (table.length === 0) return 0;
  
  const current = table[index];
  const total = report.value.overall_report.error_analysis.total_errors;
  
  if (total === 0) return 0;
  return ((current.count / total) * 100).toFixed(2);
}

function formatDate(dateStr) {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

async function loadBatchDetail() {
  try {
    const res = await fetchBatchDetail(route.params.id);
    batchData.value = res.data || res;
  } catch (e) {
    msgError(e?.message || "加载批量任务详情失败");
  }
}

async function refreshReport() {
  loading.value = true;
  errorMessage.value = "";
  
  try {
    const res = await fetchBatchReport(route.params.id);
    const data = res.data || res;
    report.value = data.report || data;
  } catch (e) {
    errorMessage.value = e?.message || "加载报告失败";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await loadBatchDetail();
  await refreshReport();
});

function goBack() {
  router.back();
}
</script>

<style scoped>
.perf-batch-report-page {
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
.page-header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  line-height: 1.3;
}
.page-subtitle {
  font-size: var(--el-font-size-base);
  color: #909399;
}
.page-header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.mt-16 {
  margin-top: 16px;
}

.info-card {
  background: #fafafa;
}

.info-item {
  text-align: center;
  padding: 12px 0;
}

.info-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.info-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.success-rate {
  color: #67c23a;
}

/* 指标卡片 */
.metrics-card {
  background: #fafafa;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.metrics-grid {
  display: flex;
  flex-wrap: wrap;
}

.metric-item {
  text-align: center;
  padding: 12px 0;
}

.metric-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #409eff;
}

/* 任务对比表格 */
.comparison-card {
  background: #fff;
}

/* 环境统计卡片 */
.env-card {
  background: #fff;
}

.env-stats-box {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: #fafafa;
}

.env-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

/* 错误分析卡片 */
.error-card {
  background: #fff;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}

.text-warning {
  color: #e6a23c;
  font-weight: 600;
}
</style>
