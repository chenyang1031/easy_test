<template>
  <div class="ts-detail" v-loading="store.loading">
    <!-- 页面标题 -->
    <div class="detail-header">
      <div class="detail-header-left">
        <el-button text @click="$router.back()" class="back-btn"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h3 class="detail-title">{{ store.current?.name || '测试套件详情' }}</h3>
      </div>
      <div class="detail-header-actions">
        <el-button type="success" @click="$router.push(`/test-suites/${id}/run`)"><el-icon><CaretRight /></el-icon> 运行</el-button>
        <el-button type="primary" @click="$router.push(`/test-suites/${id}/edit`)"><el-icon><Edit /></el-icon> 编辑</el-button>
      </div>
    </div>

    <el-row :gutter="20" v-if="store.current">
      <!-- 左侧：套件信息 -->
      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="info-card">
          <template #header><span class="card-title"><el-icon><InfoFilled /></el-icon> 套件信息</span></template>
          <el-descriptions :column="1" border size="small" class="info-desc">
            <el-descriptions-item label="项目" label-class-name="desc-label">
              <el-tag size="small" effect="plain">{{ store.current.project_name || store.current.project }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="描述" label-class-name="desc-label">
              {{ store.current.description || '暂无描述' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建人" label-class-name="desc-label">
              <AvatarName :username="store.current.created_by?.username" />
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

      <!-- 右侧：用例列表 -->
      <el-col :xs="24" :lg="16">
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header-row">
              <span class="card-title"><el-icon><List /></el-icon> 测试用例</span>
              <el-button type="primary" size="small" @click="addDialogVisible=true"><el-icon><Plus /></el-icon> 添加用例</el-button>
            </div>
          </template>
          <el-table :data="suiteCases" size="small" border class="sub-table" style="width:100%">
            <el-table-column label="顺序" width="65" align="center">
              <template #default="{row}"><el-tag size="small" type="info" effect="plain" round>{{ row.order }}</el-tag></template>
            </el-table-column>
            <el-table-column label="名称" min-width="160">
              <template #default="{row}">
                <el-link type="primary" :underline="false" @click="$router.push(`/test-cases/${row.test_case}`)">
                  {{ row.test_case_details?.name }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column label="请求方式" width="90" align="center">
              <template #default="{row}"><RequestMethodBadge :method="row.test_case_details?.request_method" /></template>
            </el-table-column>
            <el-table-column label="URL" min-width="180" show-overflow-tooltip>
              <template #default="{row}"><code class="url-code">{{ row.test_case_details?.request_url }}</code></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{row}">
                <el-popconfirm title="确定移除此用例？" @confirm="removeCase(row.test_case)">
                  <template #reference><el-button size="small" text type="danger">移除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <EmptyState v-if="suiteCases.length===0" description="套件中暂无测试用例" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行记录 -->
    <el-card shadow="never" class="result-card">
      <template #header>
        <div class="card-header-row">
          <div class="card-header-left">
            <span class="card-title"><el-icon><DataBoard /></el-icon> 最近运行记录</span>
            <el-tag v-if="runTotal" size="small" type="info" effect="plain" round>{{ runTotal }} 条</el-tag>
          </div>
        </div>
      </template>

      <!-- 统计摘要 -->
      <div v-if="testRuns.length" class="result-summary">
        <div class="summary-item summary-pass">
          <span class="summary-icon"><el-icon><CircleCheckFilled /></el-icon></span>
          <span class="summary-label">已完成</span>
          <span class="summary-value">{{ completedCount }}</span>
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
          <span class="summary-label">运行中</span>
          <span class="summary-value">{{ runningCount }}</span>
        </div>
        <div class="summary-divider" />
        <div class="summary-item">
          <span class="summary-icon"><el-icon><TrendCharts /></el-icon></span>
          <span class="summary-label">成功率</span>
          <span class="summary-value" :class="passRateClass">{{ passRate }}%</span>
        </div>
      </div>

      <el-table :data="testRuns" size="small" border v-loading="runsLoading" class="result-table" empty-text="暂无数据" style="width:100%">
        <el-table-column label="名称" prop="name" min-width="400" show-overflow-tooltip />
        <el-table-column label="环境" width="140" show-overflow-tooltip prop="environment_name" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{row}"><StatusBadge :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="开始时间" width="165" align="right">
          <template #default="{row}">{{ formatDateTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="165" align="right">
          <template #default="{row}">{{ formatDateTime(row.end_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="75" align="center">
          <template #default="{row}"><el-button size="small" text @click="$router.push(`/test-runs/${row.id}`)">查看</el-button></template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div v-if="runTotal > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="runPage"
          v-model:page-size="runPageSize"
          :total="runTotal"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadRuns"
          @size-change="loadRuns"
        />
      </div>

      <EmptyState v-if="!runsLoading && testRuns.length===0" class="result-empty" description="暂无运行记录" />
    </el-card>

    <!-- 添加用例弹窗 -->
    <el-dialog v-model="addDialogVisible" title="添加测试用例" width="700px" append-to-body class="add-dialog">
      <AddTestCaseDialog :suite-id="Number(id)" :project-id="store.current?.project" @added="onCaseAdded" @close="addDialogVisible=false" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { CircleCheckFilled, CircleCloseFilled, Clock, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useTestSuiteStore } from '../stores/testSuite.js'
import { testRunApi } from '../api/index.js'
import { formatDateTime } from '../composables/useFormat.js'
import RequestMethodBadge from '../components/common/RequestMethodBadge.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import AvatarName from '../components/common/AvatarName.vue'
import EmptyState from '../components/common/EmptyState.vue'
import AddTestCaseDialog from '../components/testSuite/AddTestCaseDialog.vue'

const props = defineProps({ id: [String, Number] })
const store = useTestSuiteStore()
const addDialogVisible = ref(false)
const runsLoading = ref(false)
const testRuns = ref([])
const runPage = ref(1)
const runPageSize = ref(20)
const runTotal = ref(0)

/* ---- 运行记录统计 ---- */
const completedCount = computed(() => testRuns.value.filter(r => r.status === 'completed').length)
const failedCount = computed(() => testRuns.value.filter(r => r.status === 'failed').length)
const runningCount = computed(() => testRuns.value.filter(r => r.status === 'running').length)
const passRate = computed(() => {
  const total = completedCount.value + failedCount.value
  if (!total) return 0
  return Math.round((completedCount.value / total) * 100)
})
const passRateClass = computed(() => {
  if (passRate.value >= 80) return 'text-success'
  if (passRate.value >= 50) return 'text-warning'
  return 'text-danger'
})

const suiteCases = computed(() => store.current?.test_suite_cases || [])

const removeCase = async (caseId) => {
  try { await store.removeTestCase(props.id, { test_case_id: caseId }); await store.loadDetail(props.id) }
  catch (e) { ElMessage.error(e.message) }
}

const onCaseAdded = async () => { await store.loadDetail(props.id) }

async function loadRuns() {
  runsLoading.value = true
  try {
    const data = await testRunApi.list({ test_suite: props.id, page: runPage.value, page_size: runPageSize.value })
    testRuns.value = data.results || []
    runTotal.value = data.count || testRuns.value.length
  } catch (e) { /* ignore */ }
  finally { runsLoading.value = false }
}

onMounted(async () => {
  await store.loadDetail(props.id)
  if (store.current) loadRuns()
})
</script>

<style scoped>
.ts-detail { padding:0; }

/* ---- 页面标题 ---- */
.detail-header {
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:20px; flex-wrap:wrap; gap:12px;
}
.detail-header-left { display:flex; align-items:center; gap:8px; }
.back-btn { font-size:14px; color:#606266; }
.detail-title { font-size:22px; font-weight:600; color:#303133; margin:0; line-height:1.3; }
.detail-header-actions { display:flex; gap:8px; }

/* ---- 信息卡片 ---- */
.info-card { margin-bottom:20px; border:1px solid #ebeef5; border-radius:8px; }
.info-card :deep(.el-card__header) {
  padding:12px 16px; border-bottom:1px solid #f0f0f0; background:#fafafa;
}
.card-title { font-size:16px; font-weight:600; color:#303133; display:flex; align-items:center; gap:6px; }

.info-desc :deep(.desc-label) { width:100px; color:#606266; font-weight:500; background:#fafafa; }
.card-header-row { display:flex; justify-content:space-between; align-items:center; }

.sub-table { width:100%; }
.url-code {
  font-size:13px; color:#606266; background:#f5f7fa;
  padding:2px 6px; border-radius:4px;
  display:inline-block; max-width:100%;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}

/* ---- 运行结果卡片 ---- */
.result-card { margin-top:20px; border:1px solid #ebeef5; border-radius:8px; }
.result-card :deep(.el-card__header) {
  padding:14px 20px; border-bottom:1px solid #f0f0f0; background:#fafafa;
}
.result-table { width:100%; }
.result-card :deep(.el-card__body) { padding:0; }

/* ---- 统计摘要栏 ---- */
.result-summary {
  display:flex; align-items:center; gap:0;
  padding:14px 20px; background:#fafcff;
  border-bottom:1px solid #f0f0f0;
}
.summary-item { display:flex; align-items:center; gap:6px; padding:0 20px; }
.summary-item:first-child { padding-left:0; }
.summary-icon { display:flex; align-items:center; font-size:16px; }
.summary-label { font-size:14px; color:#909399; }
.summary-value { font-size:18px; font-weight:700; color:#303133; }
.summary-pass .summary-icon { color:#67c23a; }
.summary-fail .summary-icon { color:#f56c6c; }
.summary-divider {
  width:1px; height:28px; background:#ebeef5; flex-shrink:0;
} 
.result-empty { margin:40px 0; }
.pagination-wrap { display:flex; justify-content:flex-end; align-items:center; padding-top:16px; border-top:1px solid #ebeef5; margin-top:16px; }

/* ---- 弹窗 ---- */
.add-dialog :deep(.el-dialog__body) { padding:20px; }
</style>
