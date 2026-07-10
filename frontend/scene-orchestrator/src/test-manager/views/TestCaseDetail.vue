<template>
  <div class="tc-detail" v-loading="store.loading">
    <!-- 页面标题 -->
    <div class="detail-header">
      <div class="detail-header-left">
        <el-button text @click="$router.back()" class="back-btn"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h3 class="detail-title">{{ store.current?.name || '测试用例详情' }}</h3>
      </div>
      <div class="detail-header-actions">
        <el-button type="success" @click="$router.push(`/test-cases/${id}/run`)"><el-icon><CaretRight /></el-icon> 运行</el-button>
        <el-button type="primary" @click="$router.push(`/test-cases/${id}/edit`)"><el-icon><Edit /></el-icon> 编辑</el-button>
      </div>
    </div>

    <el-row :gutter="20" v-if="store.current">
      <!-- 左侧：基本信息 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="info-card">
          <template #header><span class="card-title">基本信息</span></template>
          <el-descriptions :column="1" border size="small" class="info-desc">
            <el-descriptions-item label="项目" label-class-name="desc-label">
              <el-tag size="small" effect="plain">{{ store.current.project_name || store.current.project }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="描述" label-class-name="desc-label">
              {{ store.current.description || '暂无描述' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建人" label-class-name="desc-label">
              <AvatarName :username="store.current.created_by_name" />
            </el-descriptions-item>
            <el-descriptions-item label="创建时间" label-class-name="desc-label">
              {{ formatDateTime(store.current.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="更新时间" label-class-name="desc-label">
              {{ formatDateTime(store.current.updated_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 右侧：请求详情 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="info-card">
          <template #header><span class="card-title">请求详情</span></template>
          <el-descriptions :column="1" border size="small" class="info-desc">
            <el-descriptions-item label="请求方法" label-class-name="desc-label">
              <RequestMethodBadge :method="store.current.request_method" />
            </el-descriptions-item>
            <el-descriptions-item label="请求URL" label-class-name="desc-label">
              <code class="detail-url">{{ store.current.request_url }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="预期状态码" label-class-name="desc-label">
              <el-tag size="small" type="info" effect="plain">{{ store.current.expected_status_code }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="请求体格式" label-class-name="desc-label">
              <el-tag size="small" effect="plain">{{ store.current.request_body_format || 'json' }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <!-- 请求头 -->
          <div v-if="headers.length" class="sub-section">
            <h6 class="sub-title"><el-icon><List /></el-icon> 请求头</h6>
            <el-table :data="headers" size="small" border class="sub-table">
              <el-table-column prop="key" label="Key" />
              <el-table-column prop="value" label="Value" show-overflow-tooltip />
            </el-table>
          </div>

          <!-- 请求体 -->
          <div v-if="requestBody" class="sub-section">
            <h6 class="sub-title"><el-icon><Document /></el-icon> 请求体</h6>
            <template v-if="store.current.request_body_format === 'form-data' && Array.isArray(requestBody)">
              <el-table :data="requestBody" size="small" border class="sub-table">
                <el-table-column prop="key" label="Key" />
                <el-table-column prop="value" label="Value" show-overflow-tooltip />
              </el-table>
            </template>
            <pre v-else class="code-block"><code>{{ JSON.stringify(requestBody, null, 2) }}</code></pre>
          </div>

          <!-- 断言 -->
          <div v-if="assertions.length" class="sub-section">
            <h6 class="sub-title"><el-icon><Select /></el-icon> 断言</h6>
            <pre class="code-block"><code>{{ JSON.stringify(assertions, null, 2) }}</code></pre>
          </div>

          <!-- 提取参数 -->
          <div v-if="extractParams.length" class="sub-section">
            <h6 class="sub-title"><el-icon><SetUp /></el-icon> 提取参数</h6>
            <pre class="code-block"><code>{{ JSON.stringify(extractParams, null, 2) }}</code></pre>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行结果 -->
    <el-card shadow="never" class="result-card">
      <template #header>
        <div class="card-header-row">
          <div class="card-header-left">
            <span class="card-title"><el-icon><DataBoard /></el-icon> 最近运行结果</span>
            <el-tag v-if="resultTotal" size="small" type="info" effect="plain" round>{{ resultTotal }} 条</el-tag>
          </div>
          <!-- 去掉了立即运行按钮 -->
        </div>
      </template>

      <!-- 统计摘要 -->
      <div v-if="testResults.length" class="result-summary">
        <div class="summary-item summary-pass">
          <span class="summary-icon"><el-icon><CircleCheckFilled /></el-icon></span>
          <span class="summary-label">通过</span>
          <span class="summary-value">{{ passedCount }}</span>
        </div>
        <div class="summary-divider" />
        <div class="summary-item summary-fail">
          <span class="summary-icon"><el-icon><CircleCloseFilled /></el-icon></span>
          <span class="summary-label">失败</span>
          <span class="summary-value">{{ failedCount }}</span>
        </div>
        <div class="summary-divider" />
        <div class="summary-item">
          <span class="summary-icon"><el-icon><Clock /></el-icon></span>
          <span class="summary-label">平均响应</span>
          <span class="summary-value" :class="{ 'text-warning': avgResponseTime > 1000 }">{{ avgResponseTime }}ms</span>
        </div>
        <div class="summary-divider" />
        <div class="summary-item">
          <span class="summary-icon"><el-icon><TrendCharts /></el-icon></span>
          <span class="summary-label">通过率</span>
          <span class="summary-value" :class="passRateClass">{{ passRate }}%</span>
        </div>
      </div>

      <el-table :data="testResults" size="small" border v-loading="resultsLoading" class="result-table" empty-text="暂无数据" style="width:100%">
        <el-table-column label="名称" prop="test_run_name" min-width="400" show-overflow-tooltip />
        <el-table-column label="环境" prop="environment_name" width="140" show-overflow-tooltip />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{row}"><StatusBadge :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="响应时间" width="95" align="center">
          <template #default="{row}">
            <span :class="{ 'text-warning': row.response_time > 1000 }">{{ Math.round(row.response_time) }}ms</span>
          </template>
        </el-table-column>
        <el-table-column label="响应状态" width="85" align="center">
          <template #default="{row}">
            <el-tag size="small" :type="statusCodeType(row.response_status_code)" effect="plain" round>
              {{ row.response_status_code }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="165" align="right">
          <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{row}">
            <el-button
              v-if="row.test_run"
              type="primary"
              size="small"
              link
              @click="goToTestRun(row.test_run)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div v-if="resultTotal > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="resultPage"
          v-model:page-size="resultPageSize"
          :total="resultTotal"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadResults"
          @size-change="loadResults"
        />
      </div>

      <EmptyState v-if="!resultsLoading && testResults.length===0" class="result-empty" description="暂无运行记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { CircleCheckFilled, CircleCloseFilled, Clock, TrendCharts } from '@element-plus/icons-vue'
import { useTestCaseStore } from '../stores/testCase.js'
import { testResultApi } from '../api/index.js'
import { formatDateTime } from '../composables/useFormat.js'
import RequestMethodBadge from '../components/common/RequestMethodBadge.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import AvatarName from '../components/common/AvatarName.vue'
import EmptyState from '../components/common/EmptyState.vue'

const props = defineProps({ id: [String, Number] })
const store = useTestCaseStore()
const resultsLoading = ref(false)
const testResults = ref([])
const resultPage = ref(1)
const resultPageSize = ref(20)
const resultTotal = ref(0)

/* ---- 运行结果统计 ---- */
const passedCount = computed(() => testResults.value.filter(r => r.status === 'passed').length)
const failedCount = computed(() => testResults.value.filter(r => r.status === 'failed').length)
const avgResponseTime = computed(() => {
  const times = testResults.value.map(r => r.response_time).filter(t => t != null)
  if (!times.length) return 0
  return Math.round(times.reduce((a, b) => a + b, 0) / times.length)
})
const passRate = computed(() => {
  if (!testResults.value.length) return 0
  return Math.round((passedCount.value / testResults.value.length) * 100)
})
const passRateClass = computed(() => {
  if (passRate.value >= 80) return 'text-success'
  if (passRate.value >= 50) return 'text-warning'
  return 'text-danger'
})

function statusCodeType(code) {
  const n = Number(code)
  if (n >= 200 && n < 300) return 'success'
  if (n >= 300 && n < 400) return 'warning'
  if (n >= 400) return 'danger'
  return 'info'
}

function goToTestRun(testRunId) {
  window.open(`/test-runs/${testRunId}/`, '_blank')
}

/* ---- 用例详情数据 ---- */
const headers = computed(() => {
  const h = store.current?.request_headers
  if (!h) return []
  if (Array.isArray(h)) return h
  return Object.entries(h).map(([k, v]) => ({ key: k, value: v }))
})

const requestBody = computed(() => store.current?.request_body || null)
const assertions = computed(() => store.current?.validation_rules || [])
const extractParams = computed(() => store.current?.extract_params || [])

async function loadResults() {
  resultsLoading.value = true
  try {
    const data = await testResultApi.list({ test_case: props.id, page: resultPage.value, page_size: resultPageSize.value })
    testResults.value = data.results || []
    resultTotal.value = data.count || testResults.value.length
  } catch (e) { /* ignore */ }
  finally { resultsLoading.value = false }
}

onMounted(async () => {
  await store.loadDetail(props.id)
  if (store.current) loadResults()
})
</script>

<style scoped>
.tc-detail { padding:0; }

/* ---- 页面标题 ---- */
.detail-header {
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:20px; flex-wrap:wrap; gap:12px;
}
.detail-header-left { display:flex; align-items:center; gap:8px; }
.back-btn { font-size: var(--el-font-size-base); color:#606266; }
.detail-title { font-size:22px; font-weight:600; color:#303133; margin:0; line-height:1.3; }
.detail-header-actions { display:flex; gap:8px; }

/* ---- 信息卡片 ---- */
.info-card { margin-bottom:20px; border:1px solid #ebeef5; border-radius:8px; }
.info-card :deep(.el-card__header) {
  padding:12px 16px; border-bottom:1px solid #f0f0f0; background:#fafafa;
}
.card-title { font-size: var(--el-font-size-medium); font-weight:600; color:#303133; display:flex; align-items:center; gap:6px; }

.info-desc :deep(.desc-label) { width:100px; color:#606266; font-weight:500; background:#fafafa; }
.detail-url {
  font-size: var(--el-font-size-small); color:#409eff; background:#ecf5ff;
  padding:2px 8px; border-radius:4px; word-break:break-all;
}

/* ---- 子段落 ---- */
.sub-section { margin-top:16px; padding-top:12px; border-top:1px dashed #ebeef5; }
.sub-title {
  font-size: var(--el-font-size-base); font-weight:600; color:#606266; margin:0 0 8px;
  display:flex; align-items:center; gap:6px;
}
.sub-table { width:100%; }
.code-block {
  background:#f6f8fa; padding:12px 16px; border-radius:6px;
  font-size: var(--el-font-size-base); line-height:1.6;
  max-height:300px; overflow:auto;
  border:1px solid #f0f0f0;
}
.code-block code { font-family:'Cascadia Code','Fira Code',monospace; color:#476582; }

/* ---- 运行结果卡片 ---- */
.result-card {
  margin-top:20px; border:1px solid #ebeef5; border-radius:8px;
}
.result-card :deep(.el-card__header) {
  padding:14px 20px; border-bottom:1px solid #f0f0f0; background:#fafafa;
}
.card-header-row { display:flex; justify-content:space-between; align-items:center; }
.card-header-left { display:flex; align-items:center; gap:10px; }

/* ---- 统计摘要栏 ---- */
.result-summary {
  display:flex; align-items:center; gap:0;
  padding:14px 20px; background:#fafcff;
  border-bottom:1px solid #f0f0f0;
}
.summary-item { display:flex; align-items:center; gap:6px; padding:0 20px; }
.summary-item:first-child { padding-left:0; }
.summary-icon { display:flex; align-items:center; font-size: var(--el-font-size-medium); }
.summary-label { font-size: var(--el-font-size-base); color:#909399; }
.summary-value { font-size: var(--el-font-size-large); font-weight:700; color:#303133; }
.summary-pass .summary-icon { color:#67c23a; }
.summary-fail .summary-icon { color:#f56c6c; }
.summary-divider {
  width:1px; height:28px; background:#ebeef5; flex-shrink:0;
}

/* ---- 结果表格 ---- */
.result-table { width:100%; }
.result-table :deep(th.el-table__cell) { background:#f6f8fa !important; color:#303133; font-weight:600; }
.result-empty { padding:40px 0; }
.pagination-wrap { display:flex; justify-content:flex-end; align-items:center; padding-top:16px; border-top:1px solid #ebeef5; margin-top:16px; }
.result-card :deep(.el-card__body) { padding:0; }

/* ---- 状态颜色辅助 ---- */
.text-success { color:#67c23a !important; }
.text-warning { color:#e6a23c !important; font-weight:700; }
.text-danger { color:#f56c6c !important; }
</style>
