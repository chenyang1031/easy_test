<template>
  <div class="dashboard-container fade-in" v-loading="loading">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">仪表盘</h2>
      </div>
      <div class="page-header-right">
        <el-button size="default" @click="loadData"><el-icon><Refresh /></el-icon> 刷新</el-button>
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
    >
      <template #default>
        <el-button size="small" type="danger" @click="loadData">重试</el-button>
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
      <div class="row">
        <div class="col-main">
          <RecentTestRuns
            :runs="data.recentTestRuns"
            :loading="runsLoading"
            @page-change="onRunsPageChange"
          />
          <RecentSceneExecutions :executions="data.recentSceneExecutions" />
        </div>
        <div class="col-side">
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
.fade-in { animation: fadeInUp 0.25s ease; }

/* ---- 页面标题 ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}
.page-header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.page-header-right { display: flex; gap: 8px; align-items: center; }

/* 全局重置：dashboard 容器无 card hover 特效和背景干扰 */
.dashboard-container {
  padding: 0;
}
.dashboard-container .card {
  transition: none;
}
.dashboard-container .card:hover {
  transform: none;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.row {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}
.col-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.col-side {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

@media (max-width: 1200px) {
  .row {
    flex-direction: column;
  }
  .col-side {
    width: 100%;
  }
}
</style>
