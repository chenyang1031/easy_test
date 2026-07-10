<template>
  <div class="tr-detail" v-loading="store.detailLoading">
    <!-- 页面标题 -->
    <div class="detail-header">
      <div class="detail-header-left">
        <el-button text @click="$router.back()" class="back-btn"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h3 class="detail-title">{{ store.current?.name || '测试运行详情' }}</h3>
      </div>
      <div class="detail-header-actions">
        <el-button type="primary" plain size="small" @click="generateReport">
          <el-icon><Document /></el-icon> 生成报告
        </el-button>
        <el-button v-if="store.current?.test_suite" type="primary" plain size="small" @click="$router.push(`/test-suites/${store.current.test_suite}`)">
          <el-icon><Collection /></el-icon> 查看测试套件
        </el-button>
        <el-button v-if="store.current?.status === 'running'" type="info" plain size="small" @click="refreshDetail">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 运行中提示 -->
    <el-alert
      v-if="store.current?.status === 'running'"
      type="info"
      :closable="false"
      show-icon
      class="running-alert"
    >
      <template #title>此测试运行仍在执行中。页面将每10秒自动刷新一次</template>
    </el-alert>

    <template v-if="store.current">
      <el-row :gutter="20">
        <!-- 左侧：运行信息 -->
        <el-col :xs="24" :lg="8">
          <el-card shadow="never" class="info-card">
            <template #header>
              <span class="card-title"><el-icon><InfoFilled /></el-icon> 运行详情</span>
            </template>
            <div class="info-section">
              <div class="info-item">
                <div class="info-label">项目</div>
                <div class="info-value">{{ store.current.project_name }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">环境</div>
                <div class="info-value">{{ store.current.environment_name }}</div>
              </div>
              <div class="info-item" v-if="store.current.test_suite_name">
                <div class="info-label">测试套件</div>
                <div class="info-value">
                  <router-link :to="`/test-suites/${store.current.test_suite}`" class="suite-link">
                    {{ store.current.test_suite_name }}
                  </router-link>
                </div>
              </div>
              <div class="info-item">
                <div class="info-label">状态</div>
                <div class="info-value">
                  <el-tag :type="statusTag(store.current.status).type" size="small" effect="light" round>
                    {{ statusTag(store.current.status).text }}
                  </el-tag>
                </div>
              </div>
              <div class="info-item">
                <div class="info-label">创建人</div>
                <div class="info-value creator-value">
                  <span class="creator-avatar">{{ store.current.created_by_name?.charAt(0)?.toUpperCase() || '?' }}</span>
                  <span>{{ store.current.created_by_name }}</span>
                </div>
              </div>
              <div class="info-item">
                <div class="info-label">创建时间</div>
                <div class="info-value">{{ formatTime(store.current.created_at) }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">开始时间</div>
                <div class="info-value">{{ store.current.start_time ? formatTime(store.current.start_time) : '-' }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">结束时间</div>
                <div class="info-value">{{ store.current.end_time ? formatTime(store.current.end_time) : '-' }}</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：统计 + 结果 -->
        <el-col :xs="24" :lg="16">
          <!-- 统计卡片（总计/Passed/Failed/Error） -->
          <div class="stats-row" v-loading="store.statsLoading">
            <div class="stat-card total">
              <div class="stat-label">总计</div>
              <div class="stat-value">{{ store.stats.total }}</div>
            </div>
            <div class="stat-card passed">
              <div class="stat-label">通过</div>
              <div class="stat-value">{{ store.stats.passed }}</div>
            </div>
            <div class="stat-card failed">
              <div class="stat-label">失败</div>
              <div class="stat-value">{{ store.stats.failed }}</div>
            </div>
            <div class="stat-card error">
              <div class="stat-label">错误</div>
              <div class="stat-value">{{ store.stats.error }}</div>
            </div>
          </div>

          <!-- 进度条 -->
          <div v-if="store.stats.total > 0" class="progress-bar-wrap">
            <div
              class="progress-segment"
              :style="{ width: statsPercent.passed + '%', backgroundColor: '#67c23a' }"
              :title="'通过: ' + store.stats.passed"
            />
            <div
              class="progress-segment"
              :style="{ width: statsPercent.failed + '%', backgroundColor: '#f56c6c' }"
              :title="'失败: ' + store.stats.failed"
            />
            <div
              class="progress-segment"
              :style="{ width: statsPercent.error + '%', backgroundColor: '#e6a23c' }"
              :title="'错误: ' + store.stats.error"
            />
            <div
              class="progress-segment"
              :style="{ width: statsPercent.skipped + '%', backgroundColor: '#909399' }"
              :title="'跳过: ' + store.stats.skipped"
            />
          </div>

          <!-- 统计标签 -->
          <div class="stats-badges" v-if="store.stats.total > 0">
            <span class="badge-tag passed">通过: {{ store.stats.passed }}</span>
            <span class="badge-tag failed">失败: {{ store.stats.failed }}</span>
            <span class="badge-tag error">错误: {{ store.stats.error }}</span>
            <span class="badge-tag skipped">跳过: {{ store.stats.skipped }}</span>
          </div>

          <!-- 测试结果 -->
          <el-card shadow="never" class="result-card">
            <template #header>
              <div class="result-header">
                <span class="card-title"><el-icon><List /></el-icon> 测试结果</span>
                <div class="result-filters">
                  <el-radio-group v-model="store.resultsStatusFilter" size="small" @change="onFilterChange">
                    <el-radio-button value="">全部</el-radio-button>
                    <el-radio-button value="passed">通过</el-radio-button>
                    <el-radio-button value="failed">失败</el-radio-button>
                    <el-radio-button value="error">错误</el-radio-button>
                  </el-radio-group>
                </div>
              </div>
            </template>

            <el-table
              :data="store.results"
              v-loading="store.resultsLoading"
              size="small"
              border
              class="data-table"
              style="width:100%"
            >
              <el-table-column label="测试用例" min-width="160" show-overflow-tooltip>
                <template #default="{ row }">
                  <router-link :to="`/test-cases/${row.test_case}`" class="case-link" @click.stop>
                    {{ row.test_case_name }}
                  </router-link>
                </template>
              </el-table-column>
              <el-table-column label="请求方法" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="methodTag(row.request_method).type" size="small" effect="plain">
                    {{ row.request_method }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="URL" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <code class="url-text">{{ row.request_url || '-' }}</code>
                </template>
              </el-table-column>
              <el-table-column label="环境" width="100" align="center">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain" type="info">{{ row.environment_name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="90" align="center">
                <template #default="{ row }">
                  <el-tag :type="statusTag(row.status).type" size="small" effect="light" round>
                    {{ statusTag(row.status).text }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="响应时间" width="100" align="right">
                <template #default="{ row }">
                  <span>{{ row.response_time != null ? row.response_time.toFixed(2) + ' ms' : '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="响应状态码" width="80" align="center">
                <template #default="{ row }">
                  <el-tag
                    :type="row.response_status_code >= 400 ? 'danger' : row.response_status_code >= 300 ? 'warning' : 'success'"
                    size="small" effect="plain"
                  >
                    {{ row.response_status_code || '-' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="70" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click.stop="showResultDetail(row)">
                    详情
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <el-empty v-if="!store.resultsLoading && store.results.length === 0" description="暂无测试结果" :image-size="50" />

            <!-- 分页 -->
            <div class="pagination-wrap" v-if="store.resultsTotal > 0">
              <el-pagination
                v-model:current-page="store.resultsPage"
                v-model:page-size="store.resultsPageSize"
                :total="store.resultsTotal"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next"
                @current-change="onResultsPageChange"
                @size-change="onResultsSizeChange"
              />
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- 未找到 -->
    <el-empty v-if="!store.detailLoading && !store.current" description="未找到该测试运行" :image-size="80">
      <el-button type="primary" @click="$router.push('/test-runs')">返回列表</el-button>
    </el-empty>

    <!-- 结果详情弹窗 -->
    <el-dialog v-model="resultDialog.visible" title="测试结果详情" width="750px" destroy-on-close append-to-body class="result-dialog">
      <template v-if="resultDialog.result">
        <el-tabs v-model="resultDialog.activeTab">
          <!-- 全览 -->
          <el-tab-pane label="全览" name="overview">
            <el-descriptions :column="2" border size="small" class="result-desc">
              <el-descriptions-item label="状态" :span="2">
                <el-tag :type="statusTag(resultDialog.result.status).type" size="small" effect="light" round>
                  {{ statusTag(resultDialog.result.status).text }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="请求方式">
                <el-tag :type="methodTag(resultDialog.result.request_method).type" size="small" effect="plain">
                  {{ resultDialog.result.request_method }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="URL">
                <code class="detail-url">{{ resultDialog.result.request_url || '-' }}</code>
              </el-descriptions-item>
              <el-descriptions-item label="环境" :span="2">
                {{ resultDialog.result.environment_name }}
              </el-descriptions-item>
              <el-descriptions-item label="响应时间">
                {{ resultDialog.result.response_time != null ? resultDialog.result.response_time.toFixed(2) + ' ms' : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="响应状态码">
                <el-tag
                  :type="resultDialog.result.response_status_code >= 400 ? 'danger' : resultDialog.result.response_status_code >= 300 ? 'warning' : 'success'"
                  size="small" effect="plain"
                >
                  {{ resultDialog.result.response_status_code || '-' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="预期状态码">
                {{ resultDialog.result.expected_status_code || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ formatTime(resultDialog.result.created_at) }}
              </el-descriptions-item>
            </el-descriptions>

            <el-alert
              v-if="resultDialog.result.error_message"
              type="error"
              :closable="false"
              show-icon
              class="error-alert"
            >
              <template #title>错误信息</template>
              <pre class="error-pre">{{ resultDialog.result.error_message }}</pre>
            </el-alert>
          </el-tab-pane>

          <!-- 请求 -->
          <el-tab-pane label="请求" name="request">
            <div class="tab-section">
              <h4 class="tab-section-title">请求 URL</h4>
              <div class="request-url-bar">
                <span class="method-tag">{{ resultDialog.result.request_method }}</span>
                <code class="url-display">{{ resultDialog.result.request_url || '-' }}</code>
              </div>
            </div>
            <div class="tab-section">
              <h4 class="tab-section-title">请求头</h4>
              <pre class="code-block" v-if="hasContent(resultDialog.result.request_headers)">{{ formatJson(resultDialog.result.request_headers) }}</pre>
              <el-empty v-else description="无自定义请求头" :image-size="30" />
            </div>
            <div class="tab-section">
              <h4 class="tab-section-title">请求体</h4>
              <pre class="code-block" v-if="hasContent(resultDialog.result.request_body)">{{ formatJson(resultDialog.result.request_body) }}</pre>
              <el-empty v-else description="无请求体" :image-size="30" />
            </div>
          </el-tab-pane>

          <!-- 响应 -->
          <el-tab-pane label="响应" name="response">
            <div class="tab-section">
              <h4 class="tab-section-title">响应状态码</h4>
              <div class="response-status-bar">
                <el-tag
                  :type="resultDialog.result.response_status_code >= 400 ? 'danger' : resultDialog.result.response_status_code >= 300 ? 'warning' : 'success'"
                  size="medium" effect="dark"
                >
                  {{ resultDialog.result.response_status_code || '-' }}
                </el-tag>
                <span class="response-time-text">响应时间: {{ resultDialog.result.response_time != null ? resultDialog.result.response_time.toFixed(2) + ' ms' : '-' }}</span>
              </div>
            </div>
            <div class="tab-section">
              <h4 class="tab-section-title">响应头</h4>
              <pre class="code-block" v-if="hasContent(resultDialog.result.response_headers)">{{ formatJson(resultDialog.result.response_headers) }}</pre>
              <el-empty v-else description="无响应头" :image-size="30" />
            </div>
            <div class="tab-section">
              <h4 class="tab-section-title">响应体</h4>
              <pre class="code-block" v-if="hasContent(resultDialog.result.response_body)">{{ formatJson(resultDialog.result.response_body) }}</pre>
              <el-empty v-else description="无响应体" :image-size="30" />
            </div>
          </el-tab-pane>

          <!-- 断言 -->
          <el-tab-pane v-if="hasValidators(resultDialog.result)" label="断言" name="validators">
            <el-table :data="parsedValidators(resultDialog.result)" size="small" border class="sub-table">
              <el-table-column label="Check" prop="check" min-width="150" />
              <el-table-column label="Comparator" prop="comparator" width="100" />
              <el-table-column label="Expected" prop="expect" min-width="150" />
              <el-table-column label="Actual" prop="check_value" min-width="150" />
              <el-table-column label="Result" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.check_result === 'pass' ? 'success' : 'danger'" size="small" effect="light">
                    {{ row.check_result === 'pass' ? '通过' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 提取参数 -->
          <el-tab-pane v-if="hasExtractedParams(resultDialog.result)" label="提取参数" name="extracted">
            <el-table :data="formatExtractedParams(resultDialog.result)" size="small" border class="sub-table">
              <el-table-column label="参数名称" prop="name" width="180" />
              <el-table-column label="提取结果" prop="value" min-width="200">
                <template #default="{ row }">
                  <code>{{ row.value || '-' }}</code>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Refresh, InfoFilled, List, Collection, Document } from '@element-plus/icons-vue'
import { useTestRunStore } from '../stores/testRun.js'

const route = useRoute()
const router = useRouter()
const store = useTestRunStore()

const runId = computed(() => Number(route.params.id))

// 结果详情弹窗
const resultDialog = reactive({
  visible: false,
  result: null,
  activeTab: 'overview',
})

// 进度百分比
const statsPercent = computed(() => store.statsPercent)

function statusTag(status) {
  const map = {
    passed: { type: 'success', text: '通过' },
    failed: { type: 'danger', text: '失败' },
    error: { type: 'warning', text: '错误' },
    skipped: { type: 'info', text: '跳过' },
    completed: { type: 'success', text: '已完成' },
    running: { type: 'primary', text: '运行中' },
    pending: { type: 'info', text: '待执行' },
  }
  return map[status] || { type: 'info', text: status || '未知' }
}

function methodTag(method) {
  const map = { GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return { type: map[method] || 'info' }
}

function formatTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatJson(val) {
  if (!val) return '-'
  if (typeof val === 'string') {
    try { return JSON.stringify(JSON.parse(val), null, 2) } catch { return val }
  }
  return JSON.stringify(val, null, 2)
}

function hasContent(val) {
  if (!val) return false
  if (typeof val === 'object' && Object.keys(val).length === 0) return false
  return true
}

function hasValidators(result) {
  if (!result.validators) return false
  if (Array.isArray(result.validators) && result.validators.length === 0) return false
  return true
}

function parsedValidators(result) {
  if (!result.validators) return []
  if (Array.isArray(result.validators)) return result.validators
  if (typeof result.validators === 'string') {
    try { return JSON.parse(result.validators) } catch { return [] }
  }
  return []
}

function hasExtractedParams(result) {
  if (!result.extracted_params) return false
  if (typeof result.extracted_params === 'object' && Object.keys(result.extracted_params).length === 0) return false
  return true
}

function formatExtractedParams(result) {
  const ep = result.extracted_params
  if (!ep) return []
  if (typeof ep === 'string') {
    try {
      const parsed = JSON.parse(ep)
      return Object.entries(parsed).map(([name, value]) => ({ name, value }))
    } catch { return [] }
  }
  if (typeof ep === 'object') {
    return Object.entries(ep).map(([name, value]) => ({ name, value }))
  }
  return []
}

function onFilterChange() {
  store.resultsPage = 1
  loadResults()
}

function onResultsPageChange(page) {
  store.resultsPage = page
  loadResults()
}

function onResultsSizeChange(size) {
  store.resultsPageSize = size
  store.resultsPage = 1
  loadResults()
}

function loadResults() {
  store.loadResults(runId.value)
}

async function showResultDetail(row) {
  resultDialog.result = row
  resultDialog.activeTab = 'overview'
  resultDialog.visible = true
}

function generateReport() {
  router.push({ name: 'testRunReportForm', params: { testRunId: runId.value } })
}

function refreshDetail() {
  Promise.all([
    store.loadDetail(runId.value).then(r => { if (!r && !store.current) ElMessage.error('加载运行详情失败') }),
    store.loadStats(runId.value),
    loadResults(),
  ])
}

onMounted(() => {
  Promise.all([
    store.loadDetail(runId.value),
    store.loadStats(runId.value),
    loadResults(),
  ]).catch(() => {})
})
</script>

<style scoped>
.tr-detail { display: flex; flex-direction: column; gap: 16px; flex: 1; }

.detail-header {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
}
.detail-header-left { display: flex; align-items: center; gap: 4px; }
.back-btn { font-size: var(--el-font-size-base); color: #606266; padding: 6px 8px; }
.back-btn:hover { color: #409eff; }
.detail-title { font-size: var(--el-font-size-large); font-weight: 600; color: #303133; margin: 0; }
.detail-header-actions { display: flex; gap: 8px; }

.running-alert { margin-bottom: 0; }

/* ── 运行信息卡片 ── */
.info-card { border: 1px solid #d4d7dd; border-radius: 8px; }
.info-card :deep(.el-card__header) {
  padding: 12px 16px; border-bottom: 1px solid #ebeef5;
  background: #fafafa; border-radius: 8px 8px 0 0;
}
.info-card :deep(.el-card__body) { padding: 16px; }
.card-title { font-size: var(--fs-card-title); font-weight: 600; color: #303133; display: flex; align-items: center; gap: 6px; }

.info-section { display: flex; flex-direction: column; gap: 0; }
.info-item {
  display: flex; padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}
.info-item:last-child { border-bottom: none; }
.info-label {
  font-size: var(--el-font-size-small); font-weight: 600; color: #606266;
  width: 80px; min-width: 80px; flex-shrink: 0;
}
.info-value { font-size: var(--el-font-size-small); color: #303133; word-break: break-word; }
.suite-link { color: #409eff; text-decoration: none; }
.suite-link:hover { text-decoration: underline; }
.creator-value { display: flex; align-items: center; gap: 6px; }
.creator-avatar {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 50%;
  background: #409eff; color: #fff;
  font-size: var(--el-font-size-extra-small); font-weight: 600; flex-shrink: 0;
}

/* ── 统计卡片（一行） ── */
.stats-row { display: flex; gap: 12px; margin-bottom: 12px; }
.stat-card {
  flex: 1; min-width: 0; border-radius: 8px; padding: 16px 8px;
  text-align: center; border: 1px solid #ebeef5;
}
.stat-label { font-size: var(--el-font-size-small); font-weight: 500; color: #606266; margin-bottom: 4px; }
.stat-value { font-size: var(--fs-display); font-weight: 700; line-height: 1.2; }
.stat-card.total { background: #f5f7fa; }
.stat-card.total .stat-value { color: #303133; }
.stat-card.passed { background: rgba(103, 194, 58, 0.1); }
.stat-card.passed .stat-value { color: #67c23a; }
.stat-card.failed { background: rgba(245, 108, 108, 0.1); }
.stat-card.failed .stat-value { color: #f56c6c; }
.stat-card.error { background: rgba(230, 162, 60, 0.1); }
.stat-card.error .stat-value { color: #e6a23c; }

/* ── 进度条 ── */
.progress-bar-wrap {
  display: flex; height: 20px; border-radius: 10px; overflow: hidden;
  margin-bottom: 12px; background: #f0f0f0;
}
.progress-segment { transition: width 0.3s ease; min-width: 2px; }
.progress-segment:first-child { border-radius: 10px 0 0 10px; }
.progress-segment:last-child { border-radius: 0 10px 10px 0; }

/* ── 统计标签 ── */
.stats-badges { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.badge-tag {
  display: inline-block; padding: 3px 10px; font-size: var(--el-font-size-extra-small); font-weight: 500;
  border-radius: 12px; line-height: 1.4;
}
.badge-tag.passed { background: rgba(103, 194, 58, 0.15); color: #67c23a; }
.badge-tag.failed { background: rgba(245, 108, 108, 0.15); color: #f56c6c; }
.badge-tag.error { background: rgba(230, 162, 60, 0.15); color: #e6a23c; }
.badge-tag.skipped { background: rgba(144, 147, 153, 0.15); color: #909399; }

/* ── 结果卡片 ── */
.result-card { border: 1px solid #d4d7dd; border-radius: 8px; }
.result-card :deep(.el-card__header) {
  padding: 12px 16px; border-bottom: 1px solid #ebeef5;
  background: #fafafa; border-radius: 8px 8px 0 0;
}
.result-card :deep(.el-card__body) { padding: 16px; }
.result-header {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
}
.result-filters { display: flex; gap: 4px; }

.data-table { width: 100%; }
.data-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
.case-link { color: #409eff; text-decoration: none; font-weight: 500; }
.case-link:hover { text-decoration: underline; }
.url-text {
  font-size: var(--el-font-size-extra-small); color: #606266; background: #f5f7fa;
  padding: 2px 6px; border-radius: 4px;
  display: inline-block; max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.pagination-wrap {
  display: flex; justify-content: flex-end; align-items: center;
  padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px;
}

/* ── 弹窗 ── */
.result-dialog :deep(.el-dialog__body) { padding: 20px; }
.result-desc { margin-bottom: 16px; }
.result-desc :deep(.desc-label) { width: 90px; }
.tab-section { margin-bottom: 16px; }
.tab-section-title {
  font-size: var(--el-font-size-base); font-weight: 600; color: #606266;
  margin-bottom: 8px; padding-bottom: 4px;
  border-bottom: 1px solid #ebeef5;
}
.code-block {
  background: #f6f8fa; border-radius: 6px; padding: 10px 14px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: var(--el-font-size-extra-small); line-height: 1.6; white-space: pre-wrap; word-break: break-all;
  max-height: 300px; overflow-y: auto; margin: 0; border: 1px solid #f0f0f0;
}
.request-url-bar {
  display: flex; align-items: center; gap: 8px;
  background: #f6f8fa; border-radius: 6px; padding: 8px 12px;
  border: 1px solid #d4d7dd;
}
.method-tag {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  background: #409eff; color: #fff; font-size: var(--el-font-size-extra-small); font-weight: 600;
  white-space: nowrap;
}
.url-display {
  font-family: 'Consolas', monospace; font-size: var(--el-font-size-small); color: #303133;
  word-break: break-all;
}
.response-status-bar {
  display: flex; align-items: center; gap: 12px; margin-bottom: 4px;
}
.response-time-text { font-size: var(--el-font-size-small); color: #606266; }
.detail-url {
  font-size: var(--el-font-size-extra-small); color: #409eff; background: #ecf5ff;
  padding: 1px 4px; border-radius: 3px; word-break: break-all;
}
.error-alert { margin-top: 16px; }
.error-alert :deep(.el-alert__content) { width: 100%; }
.error-pre {
  margin: 4px 0 0; font-size: var(--el-font-size-small); line-height: 1.5; white-space: pre-wrap;
  font-family: 'Consolas', monospace; max-height: 200px; overflow-y: auto;
}
.sub-table { width: 100%; }
</style>
