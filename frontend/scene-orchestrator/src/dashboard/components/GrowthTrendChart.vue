<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span>增长趋势</span>
      <div class="d-flex gap-2 align-items-center">
        <el-radio-group v-model="activePeriod" size="small" @change="onPeriodChange">
          <el-radio-button value="week">周</el-radio-button>
          <el-radio-button value="month">月</el-radio-button>
          <el-radio-button value="year">年</el-radio-button>
        </el-radio-group>
        <el-button size="small" @click="exportChart">
          <el-icon style="margin-right:4px"><Download /></el-icon>
          导出图片
        </el-button>
      </div>
    </div>
    <div class="card-body position-relative">
      <!-- 空数据提示 -->
      <div v-if="!hasData" class="chart-empty-hint text-muted">暂无数据</div>
      <!-- ECharts 容器 -->
      <div ref="chartRef" style="width:100%; height:320px"></div>
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

// 当前活跃的数据集
const currentData = computed(() => {
  return props.trends?.[activePeriod.value]
})

// 检查是否有数据
const hasData = computed(() => {
  const ds = currentData.value?.datasets
  if (!ds) return false
  return Object.values(ds).some(series => series?.some(v => v > 0))
})

const COLOR_MAP = {
  projects: '#4cc9f0',
  test_cases: '#4361ee',
  test_suites: '#f72585',
  test_runs: '#7209b7',
  test_reports: '#e63946',
  test_scenes: '#2dc653',
  test_scene_executions: '#f4a261',
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
    symbolSize: 6,
    lineStyle: { width: 2 },
    areaStyle: {
      opacity: 0.08,
    },
    itemStyle: {
      color: COLOR_MAP[key] || '#4361ee',
    },
  }))

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: { fontSize: 12 },
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      textStyle: { fontSize: 12 },
    },
    grid: {
      left: 40,
      right: 20,
      top: 20,
      bottom: 50,
    },
    xAxis: {
      type: 'category',
      data: data.labels || [],
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#909399' },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { color: '#909399' },
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
.chart-empty-hint {
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  text-align: center;
  z-index: 1;
  pointer-events: none;
  font-size: 1rem;
}
</style>
