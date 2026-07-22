<template>
  <div class="dashboard-container fade-in" v-loading="loading">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">仪表盘</h2>
        <span class="page-subtitle">项目概览与活动追踪</span>
      </div>
      <div class="page-header-right">
        <button class="refresh-btn" @click="loadData">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          刷新数据
        </button>
      </div>
    </div>

    <!-- 错误状态 -->
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      closable
      @close="error = null"
      style="border-radius: 10px; margin-bottom: 16px;"
    >
      <template #default>
        <button class="retry-btn" @click="loadData">重试</button>
      </template>
    </el-alert>

    <template v-if="!error">
      <!-- 统计卡片 -->
      <StatCards :stats="data.stats" />

      <!-- 场景执行状态分布 -->
      <ExecutionStatusBar :dist="data.executionStatusDist" />

      <!-- 增长趋势图 -->
      <GrowthTrendChart :trends="data.trends" />

      <!-- 下方区域：表格 + 侧边 -->
      <div class="dashboard-row">
        <div class="dashboard-col-main">
          <RecentTestRuns
            :runs="data.recentTestRuns"
            :loading="runsLoading"
            @page-change="onRunsPageChange"
          />
          <RecentSceneExecutions :executions="data.recentSceneExecutions" />
        </div>
        <div class="dashboard-col-side">
          <ActivityTimeline :activities="data.activities" @refresh="loadData" />
          <QuickActions />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { fetchStats } from './api.js'
import StatCards from './components/StatCards.vue'
import ExecutionStatusBar from './components/ExecutionStatusBar.vue'
import GrowthTrendChart from './components/GrowthTrendChart.vue'
import RecentTestRuns from './components/RecentTestRuns.vue'
import RecentSceneExecutions from './components/RecentSceneExecutions.vue'
import ActivityTimeline from './components/ActivityTimeline.vue'
import QuickActions from './components/QuickActions.vue'

const loading = ref(true)
const error = ref(null)
const runsLoading = ref(false)

const data = reactive({
  stats: {
    projects: 0, testCases: 0, testSuites: 0, testRuns: 0,
    reports: 0, testScenes: 0, sceneExecutions: 0,
  },
  executionStatusDist: { running: 0, success: 0, failed: 0, partialSuccess: 0 },
  trends: { week: { labels: [], datasets: {} }, month: null, year: null },
  recentTestRuns: { results: [], total: 0, totalPages: 0, currentPage: 1 },
  recentSceneExecutions: [],
  activities: [],
})

async function loadData(page = 1) {
  loading.value = true
  error.value = null
  try {
    const result = await fetchStats({ page })
    Object.assign(data, result)
  } catch (e) {
    error.value = e.message || '加载仪表盘数据失败'
  } finally {
    loading.value = false
  }
}

async function onRunsPageChange(page) {
  runsLoading.value = true
  try {
    const result = await fetchStats({ page })
    data.recentTestRuns = result.recentTestRuns
  } catch (e) {
    error.value = e.message || '加载测试运行列表失败'
  } finally {
    runsLoading.value = false
  }
}

onMounted(() => loadData())
</script>

<style>
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeInUp 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
</style>

<style scoped>
/* ---- 页面标题 ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 24px;
}
.page-header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary, #0F172A);
  margin: 0;
  line-height: 1.3;
}
.page-subtitle {
  font-size: 0.85rem;
  color: var(--text-secondary, #94A3B8);
  font-weight: 400;
}
.page-header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: 1px solid var(--border-color, #E2E8F0);
  border-radius: 8px;
  background: var(--bg-card, #fff);
  color: var(--text-secondary, #64748B);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.refresh-btn:hover {
  border-color: var(--primary-color, #4F46E5);
  color: var(--primary-color, #4F46E5);
  background: rgba(79, 70, 229, 0.04);
}

.retry-btn {
  padding: 4px 12px;
  border: none;
  border-radius: 6px;
  background: #EF4444;
  color: #fff;
  font-size: 0.78rem;
  cursor: pointer;
}

/* ---- 全局容器 ---- */
.dashboard-container {
  padding: 0;
}

/* ---- 下方布局 ---- */
.dashboard-row {
  display: flex;
  gap: 20px;
  margin-top: 20px;
}
.dashboard-col-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.dashboard-col-side {
  width: 340px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

@media (max-width: 1200px) {
  .dashboard-row {
    flex-direction: column;
  }
  .dashboard-col-side {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .page-title {
    font-size: 1.25rem;
  }
  .page-subtitle {
    display: none;
  }
}
</style>
