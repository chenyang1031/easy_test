<template>
  <div class="chart-card">
    <div class="chart-card-header">
      <h3 class="chart-card-title">增长趋势</h3>
      <div class="chart-card-actions">
        <el-radio-group v-model="activePeriod" size="small" @change="onPeriodChange">
          <el-radio-button value="week">周</el-radio-button>
          <el-radio-button value="month">月</el-radio-button>
          <el-radio-button value="year">年</el-radio-button>
        </el-radio-group>
        <el-button size="small" text @click="exportChart" class="export-btn">
          <el-icon style="margin-right:4px"><Download /></el-icon>
          导出
        </el-button>
      </div>
    </div>
    <div class="chart-card-body">
      <div v-if="!hasData" class="chart-empty-hint">暂无数据</div>
      <div ref="chartRef" class="chart-container"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Download } from '@element-plus/icons-vue'

const props = defineProps({
  trends: {
    type: Object,
    required: true,
  },
})

const chartRef = ref(null)
const activePeriod = ref('week')
let chartInstance = null

const currentData = computed(() => {
  return props.trends?.[activePeriod.value]
})

const hasData = computed(() => {
  const ds = currentData.value?.datasets
  if (!ds) return false
  return Object.values(ds).some(series => series?.some(v => v > 0))
})

/* 新配色 — 与设计系统协调 */
const COLOR_MAP = {
  projects: '#4F46E5',
  test_cases: '#10B981',
  test_suites: '#7C3AED',
  test_runs: '#F59E0B',
  test_reports: '#F43F5E',
  test_scenes: '#06B6D4',
  test_scene_executions: '#14B8A6',
}

const LABEL_MAP = {
  projects: '项目',
  test_cases: '测试用例',
  test_suites: '测试套件',
  test_runs: '测试运行',
  test_reports: '测试报告',
  test_scenes: '测试场景',
  test_scene_executions: '场景执行',
}

function buildOption() {
  const data = currentData.value
  if (!data) return {}

  const series = Object.entries(data.datasets).map(([key, values]) => ({
    name: LABEL_MAP[key] || key,
    type: 'line',
    smooth: true,
    data: values,
    symbol: 'circle',
    symbolSize: 5,
    lineStyle: { width: 2.5 },
    areaStyle: {
      opacity: 0.06,
    },
    itemStyle: {
      color: COLOR_MAP[key] || '#4F46E5',
    },
  }))

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      textStyle: { fontSize: 12, color: '#334155' },
      extraCssText: 'border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.06);',
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      textStyle: { fontSize: 12, color: '#64748B' },
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 3,
    },
    grid: {
      left: 44,
      right: 20,
      top: 16,
      bottom: 48,
    },
    xAxis: {
      type: 'category',
      data: data.labels || [],
      axisLine: { lineStyle: { color: '#E2E8F0' } },
      axisLabel: { color: '#94A3B8', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
      axisLabel: { color: '#94A3B8', fontSize: 11 },
    },
    series,
  }
}

function renderChart() {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  chartInstance.setOption(buildOption(), true)
}

function onPeriodChange() {
  nextTick(() => renderChart())
}

function exportChart() {
  if (!chartInstance) return
  const url = chartInstance.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
  const link = document.createElement('a')
  link.download = `growth-trends-${activePeriod.value}.png`
  link.href = url
  link.click()
}

watch(() => props.trends, () => {
  nextTick(() => renderChart())
}, { deep: true })

onMounted(() => {
  nextTick(() => renderChart())
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.chart-card {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #E2E8F0);
  border-radius: 12px;
  overflow: hidden;
}

.chart-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 12px;
  gap: 12px;
  flex-wrap: wrap;
}

.chart-card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary, #0F172A);
  margin: 0;
}

.chart-card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.export-btn {
  color: var(--text-secondary, #64748B) !important;
  font-size: 0.8rem;
}
.export-btn:hover {
  color: var(--primary-color, #4F46E5) !important;
}

.chart-card-body {
  padding: 0 20px 16px;
  position: relative;
}

.chart-container {
  width: 100%;
  height: 320px;
}

.chart-empty-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  color: var(--text-secondary, #94A3B8);
  z-index: 1;
  pointer-events: none;
}
</style>
