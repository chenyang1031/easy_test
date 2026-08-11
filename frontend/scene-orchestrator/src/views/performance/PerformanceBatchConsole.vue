<template>
  <div class="perf-batch-console-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">批量任务实时监控</h2>
        <span class="page-subtitle">{{ batchName }}</span>
      </div>
      <div class="page-header-right">
        <el-button @click="goBack">返回</el-button>
        <el-button type="primary" @click="refreshData">刷新数据</el-button>
        <el-button type="danger" @click="confirmStop" :disabled="!canStop">
          停止任务
        </el-button>
      </div>
    </div>

    <!-- 状态卡片 -->
    <el-card v-if="batchData" class="status-card">
      <el-row :gutter="24">
        <el-col :span="6">
          <div class="status-item">
            <div class="status-label">当前状态</div>
            <el-tag :type="batchStatusTagType(batchData.status)" size="large">
              {{ batchStatusLabel(batchData.status) }}
            </el-tag>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <div class="status-label">执行模式</div>
            <div class="status-value">{{ batchData.execute_mode === 'parallel' ? '并行' : '串行' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <div class="status-label">总任务数</div>
            <div class="status-value">{{ batchData.total_tasks || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <div class="status-label">已完成</div>
            <div class="status-value">{{ batchData.completed_tasks || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <div class="status-label">运行中</div>
            <div class="status-value warning-text">{{ batchData.running_tasks || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <div class="status-label">成功</div>
            <div class="status-value success-text">{{ batchData.successful_tasks || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <div class="status-label">失败</div>
            <div class="status-value error-text">{{ batchData.failed_tasks || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <div class="status-label">成功率</div>
            <div class="status-value success-rate">{{ batchData.success_rate_percent }}%</div>
          </div>
        </el-col>
      </el-row>
      
      <el-divider />
      
      <el-row :gutter="24">
        <el-col :span="12">
          <div class="progress-section">
            <div class="section-label">总体进度</div>
            <el-progress 
              :percentage="batchData.progress_percent" 
              :color="computeProgressColor(batchData)"
              :stroke-width="20"
              :text-inside="true"
            />
          </div>
        </el-col>
        <el-col :span="12">
          <div class="time-section">
            <div class="section-label">开始时间</div>
            <div class="time-value">{{ formatDate(batchData.started_at) }}</div>
            <div class="section-label mt-8">结束时间</div>
            <div class="time-value">{{ formatDate(batchData.finished_at) }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 任务项列表 -->
    <el-card v-if="!loading && batchItems.length > 0" class="items-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">任务项详情</span>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索任务名称或接口"
            clearable
            style="width: 240px;"
            size="small"
            prefix-icon="Search"
          />
        </div>
      </template>
      
      <el-table :data="filteredBatchItems" stripe size="small" max-height="600">
        <el-table-column prop="order_index" label="#" width="60" align="center" />
        <el-table-column prop="task_name" label="任务名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="interface_url" label="接口 URL" min-width="300" show-overflow-tooltip />
        <el-table-column prop="method" label="方法" width="70" align="center" />
        <el-table-column prop="environment_name" label="环境" width="100" align="center" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="itemStatusTagType(row.status)" size="small">
              {{ itemStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column label="结束时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.finished_at) }}
          </template>
        </el-table-column>
        <el-table-column label="结果摘要" min-width="200">
          <template #default="{ row }">
            <div v-if="row.result_summary" class="result-summary">
              <div v-for="(value, key) in summarizeResult(row.result_summary)" :key="key">
                <span class="summary-label">{{ getLabel(key) }}:</span>
                <span class="summary-value">{{ value }}</span>
              </div>
            </div>
            <span v-else class="no-data">暂无数据</span>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag v-if="row.error_message" type="danger" size="small">
              {{ row.error_message }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-empty v-if="!loading && !searchKeyword && batchItems.length === 0" description="暂无任务项数据" />
    
    <!-- 加载动画 -->
    <el-loading v-if="loading" text="加载中..." />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { fetchBatchReport, fetchBatchDetail, fetchBatchItems } from "../../api/performance";
import { stopBatch } from "../../api/performance";
import { confirmWarning, msgError, msgSuccess } from "../../utils/uiMessage.js";

const router = useRouter();
const route = useRoute();

const loading = ref(false);
const batchData = ref(null);
const batchItems = ref([]);
const searchKeyword = ref("");

const batchName = computed(() => batchData.value?.name || '');

let refreshTimer = null;

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

// canStop 用 computed 以便模板响应式绑定
const canStop = computed(
  () => batchData.value?.status === "running" || batchData.value?.status === "partial_success"
);

function computeProgressColor(data) {
  if (data.status === "completed") return "#67c23a";
  if (data.status === "failed") return "#f56c6c";
  if (data.status === "running") return "#e6a23c";
  return "#409eff";
}

function itemStatusLabel(status) {
  const map = {
    pending: "待执行",
    running: "执行中",
    success: "成功",
    failed: "失败",
    skipped: "跳过",
  };
  return map[status] || status;
}

function itemStatusTagType(status) {
  const map = {
    pending: "info",
    running: "warning",
    success: "success",
    failed: "danger",
    skipped: "info",
  };
  return map[status] || "info";
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

function summarizeResult(summary) {
  if (!summary) return {};
  
  const result = {};
  const keys = ["max_rps", "avg_response_time_50_ms", "avg_failure_rate_percent"];
  
  keys.forEach((key) => {
    if (summary[key] !== undefined && summary[key] !== null) {
      const mappedKey = {
        max_rps: "最大 QPS",
        avg_response_time_50_ms: "平均 P50",
        avg_failure_rate_percent: "失败率",
      }[key];
      result[mappedKey] = Number(summary[key]).toFixed(2);
    }
  });
  
  return result;
}

function getLabel(key) {
  const labels = {
    "最大 QPS": "最大 QPS",
    "平均 P50": "平均 P50",
    "失败率": "失败率",
  };
  return labels[key] || key;
}

// 筛选
const filteredBatchItems = computed(() => {
  if (!searchKeyword.value) {
    return batchItems.value;
  }
  
  const keyword = searchKeyword.value.toLowerCase();
  return batchItems.value.filter((item) => {
    return (
      item.task_name?.toLowerCase().includes(keyword) ||
      item.interface_url?.toLowerCase().includes(keyword)
    );
  });
});

async function loadBatchData() {
  try {
    const [detailRes, itemsRes] = await Promise.all([
      fetchBatchDetail(route.params.id),
      fetchBatchItems(route.params.id, { page_size: 1000 }),
    ]);
    
    batchData.value = detailRes.data || detailRes;
    batchItems.value = itemsRes.results || [];
  } catch (e) {
    msgError(e?.message || "加载数据失败");
  }
}

async function refreshData() {
  loading.value = true;
  try {
    await loadBatchData();
  } finally {
    loading.value = false;
  }
}

async function confirmStop() {
  try {
    await confirmWarning("确定要停止该批量任务吗？正在执行的任务将被中断。");
  } catch {
    return;
  }
  
  try {
    await stopBatch(route.params.id);
    msgSuccess("批量任务已停止");
    await loadBatchData();
  } catch (e) {
    msgError(e?.message || "停止失败");
  }
}

function goBack() {
  clearInterval(refreshTimer);
  router.back();
}

// 自动刷新（每 5 秒）
onMounted(() => {
  refreshData();
  refreshTimer = setInterval(() => {
    const status = batchData.value?.status;
    if (status === "running" || status === "partial_success") {
      loadBatchData();
    }
  }, 5000);
});

onUnmounted(() => {
  clearInterval(refreshTimer);
});
</script>

<style scoped>
.perf-batch-console-page {
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

.mt-8 {
  margin-top: 8px;
}

.status-card {
  background: #fafafa;
}

.status-item {
  text-align: center;
  padding: 12px 0;
}

.status-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.status-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.warning-text {
  color: #e6a23c;
}

.success-text {
  color: #67c23a;
}

.error-text {
  color: #f56c6c;
}

.success-rate {
  color: #67c23a;
  font-size: 24px;
}

.section-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.time-value {
  font-size: 14px;
  color: #606266;
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

.items-card {
  background: #fff;
}

.result-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  color: #909399;
}

.summary-value {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

.no-data {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
