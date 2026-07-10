<template>
  <div class="sed-detail" v-loading="loading">
    <!-- 页面标题 -->
    <div class="detail-header">
      <div class="detail-header-left">
        <el-button text @click="$router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h3 class="detail-title">{{ execution?.scene_name || '场景执行详情' }}</h3>
        <span class="text-muted small">#{{ execution?.id }}</span>
      </div>
      <div class="detail-header-actions">
        <el-button type="success" plain size="small" @click="generateReport">
          <el-icon><Document /></el-icon> 生成测试报告
        </el-button>
        <el-button type="primary" plain size="small" @click="openInOrchestrator">
          <el-icon><Box /></el-icon> 在编排器中打开
        </el-button>
        <el-button v-if="execution?.status === 'running'" type="info" plain size="small" @click="loadDetail">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-popconfirm title="确定删除此执行记录？" @confirm="handleDelete">
          <template #reference>
            <el-button type="danger" plain size="small">
              <el-icon><Delete /></el-icon> 删除记录
            </el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <!-- 运行中提示 -->
    <el-alert
      v-if="execution?.status === 'running'"
      type="info"
      :closable="false"
      show-icon
      class="running-alert"
    >
      <template #title>场景仍在执行中，页面将每10秒自动刷新一次</template>
    </el-alert>

    <!-- 未找到 -->
    <el-empty v-if="!loading && !execution" description="未找到该场景执行" :image-size="80">
      <el-button type="primary" @click="$router.push('/scene-executions')">返回列表</el-button>
    </el-empty>

    <template v-if="execution">
      <el-row :gutter="20" class="info-row">
        <!-- 左侧：执行详情 -->
        <el-col :xs="24" :lg="8">
          <el-card shadow="never" class="info-card">
            <template #header>
              <span class="card-title"><el-icon><InfoFilled /></el-icon> 执行详情</span>
            </template>
            <div class="info-section">
              <div class="info-item">
                <div class="info-label">场景</div>
                <div class="info-value">
                  <a :href="orchestratorDesignerUrl" target="_blank" class="scene-link">
                    <el-icon><Connection /></el-icon> {{ execution.scene_name }}
                  </a>
                </div>
              </div>
              <div class="info-item">
                <div class="info-label">项目</div>
                <div class="info-value">{{ execution.project_name || '-' }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">环境</div>
                <div class="info-value">{{ execution.environment_name || '-' }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">状态</div>
                <div class="info-value">
                  <el-tag :type="statusTag(execution.status).type" size="small" effect="light" round>
                    <span v-if="execution.status === 'running'" class="running-dot" />
                    {{ statusTag(execution.status).text }}
                  </el-tag>
                </div>
              </div>
              <div class="info-item">
                <div class="info-label">创建人</div>
                <div class="info-value creator-value">
                  <span class="creator-avatar">{{ (execution.created_by_name || '?').charAt(0).toUpperCase() }}</span>
                  <span>{{ execution.created_by_name || '-' }}</span>
                </div>
              </div>
              <div class="info-item">
                <div class="info-label">创建时间</div>
                <div class="info-value">{{ formatTime(execution.created_at) }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">开始时间</div>
                <div class="info-value">{{ execution.started_at ? formatTime(execution.started_at) : '-' }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">结束时间</div>
                <div class="info-value">{{ execution.finished_at ? formatTime(execution.finished_at) : '-' }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">耗时</div>
                <div class="info-value">{{ durationDisplay }}</div>
              </div>
            </div>

            <!-- 错误信息 -->
            <el-alert
              v-if="execution.error_message"
              type="error"
              :closable="false"
              show-icon
              class="error-alert"
            >
              <template #title>错误信息</template>
              <pre class="error-pre">{{ execution.error_message }}</pre>
            </el-alert>
          </el-card>
        </el-col>

        <!-- 右侧：节点汇总 -->
        <el-col :xs="24" :lg="16">
          <el-card shadow="never" class="stats-card">
            <template #header>
              <span class="card-title"><el-icon><DataAnalysis /></el-icon> 节点汇总</span>
            </template>

            <!-- 统计卡片（一行） -->
            <div class="stats-row">
              <div class="stat-card total">
                <div class="stat-label">总计</div>
                <div class="stat-value">{{ execution.total_nodes || 0 }}</div>
              </div>
              <div class="stat-card passed">
                <div class="stat-label">成功</div>
                <div class="stat-value">{{ execution.passed_nodes || 0 }}</div>
              </div>
              <div class="stat-card failed">
                <div class="stat-label">失败</div>
                <div class="stat-value">{{ execution.failed_nodes || 0 }}</div>
              </div>
              <div class="stat-card skipped">
                <div class="stat-label">跳过</div>
                <div class="stat-value">{{ execution.skipped_nodes || 0 }}</div>
              </div>
            </div>

            <!-- 进度条 -->
            <div v-if="(execution.total_nodes || 0) > 0" class="progress-bar-wrap">
              <div
                class="progress-segment"
                :style="{ width: statsPercent.passed + '%', backgroundColor: '#67c23a' }"
                :title="'成功: ' + (execution.passed_nodes || 0)"
              />
              <div
                class="progress-segment"
                :style="{ width: statsPercent.failed + '%', backgroundColor: '#f56c6c' }"
                :title="'失败: ' + (execution.failed_nodes || 0)"
              />
              <div
                class="progress-segment"
                :style="{ width: statsPercent.skipped + '%', backgroundColor: '#909399' }"
                :title="'跳过: ' + (execution.skipped_nodes || 0)"
              />
            </div>

            <!-- 统计标签 -->
            <div class="stats-badges" v-if="(execution.total_nodes || 0) > 0">
              <span class="badge-tag passed">成功: {{ execution.passed_nodes || 0 }}</span>
              <span class="badge-tag failed">失败: {{ execution.failed_nodes || 0 }}</span>
              <span class="badge-tag skipped">跳过: {{ execution.skipped_nodes || 0 }}</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 节点结果 -->
      <el-card shadow="never" class="node-card">
        <template #header>
          <span class="card-title"><el-icon><List /></el-icon> 节点结果</span>
        </template>

        <el-table
          :data="nodeResults"
          v-loading="loading"
          size="small"
          border
          class="data-table"
          style="width:100%"
        >
          <el-table-column label="节点" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">{{ row.node_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="标识" width="120" show-overflow-tooltip>
            <template #default="{ row }"><code class="node-key-code">{{ row.node_key || '-' }}</code></template>
          </el-table-column>
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="nodeStatusTag(row.status).type" size="small" effect="light" round>
                {{ nodeStatusTag(row.status).text }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="说明" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.reason || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="70" align="center" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click.stop="showNodeDetail(row)">
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loading && nodeResults.length === 0" description="暂无节点结果" :image-size="50" />
      </el-card>
    </template>

    <!-- 节点详情弹窗 -->
    <el-dialog
      v-model="nodeDialog.visible"
      :title="'节点详情: ' + (nodeDialog.node?.node_name || '-')"
      width="750px"
      destroy-on-close
      append-to-body
      class="node-dialog"
    >
      <template v-if="nodeDialog.node">
        <el-tabs v-model="nodeDialog.activeTab">
          <!-- 全览 -->
          <el-tab-pane label="全览" name="overview">
            <el-descriptions :column="2" border size="small" class="node-desc">
              <el-descriptions-item label="状态" :span="2">
                <el-tag :type="nodeStatusTag(nodeDialog.node.status).type" size="small" effect="light" round>
                  {{ nodeStatusTag(nodeDialog.node.status).text }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="节点名称" :span="2">{{ nodeDialog.node.node_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="节点标识" :span="2"><code>{{ nodeDialog.node.node_key || '-' }}</code></el-descriptions-item>
              <el-descriptions-item label="说明" :span="2" class="reason-cell">{{ nodeDialog.node.reason || '-' }}</el-descriptions-item>
              <template v-if="nodeDialog.node.response">
                <el-descriptions-item label="HTTP状态码">
                  <el-tag
                    :type="nodeDialog.node.response.status_code >= 400 ? 'danger' : nodeDialog.node.response.status_code >= 300 ? 'warning' : 'success'"
                    size="small" effect="plain"
                  >
                    {{ nodeDialog.node.response.status_code || '-' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="响应耗时">
                  {{ nodeDialog.node.response.duration_ms != null ? (nodeDialog.node.response.duration_ms === 0 ? '0 ms' : nodeDialog.node.response.duration_ms + ' ms') : '-' }}
                </el-descriptions-item>
              </template>
            </el-descriptions>
          </el-tab-pane>

          <!-- 请求 -->
          <el-tab-pane label="请求" name="request">
            <div class="tab-section">
              <h4 class="tab-section-title">请求报文</h4>
              <pre class="code-block" v-if="nodeDialog.node.request">{{ formatJson(nodeDialog.node.request) }}</pre>
              <el-empty v-else description="暂无请求数据" :image-size="30" />
            </div>
          </el-tab-pane>

          <!-- 响应 -->
          <el-tab-pane label="响应" name="response">
            <template v-if="nodeDialog.node.response">
              <div class="tab-section">
                <h4 class="tab-section-title">响应状态码</h4>
                <div class="response-status-bar">
                  <el-tag
                    :type="nodeDialog.node.response.status_code >= 400 ? 'danger' : nodeDialog.node.response.status_code >= 300 ? 'warning' : 'success'"
                    size="medium" effect="dark"
                  >
                    {{ nodeDialog.node.response.status_code || '-' }}
                  </el-tag>
                  <span class="response-time-text">
                    响应时间:
                    {{ nodeDialog.node.response.duration_ms != null ? (nodeDialog.node.response.duration_ms === 0 ? '0 ms' : nodeDialog.node.response.duration_ms + ' ms') : '-' }}
                  </span>
                </div>
              </div>
              <div class="tab-section">
                <h4 class="tab-section-title">响应头</h4>
                <pre class="code-block" v-if="hasContent(nodeDialog.node.response.headers)">{{ formatJson(nodeDialog.node.response.headers) }}</pre>
                <el-empty v-else description="无响应头" :image-size="30" />
              </div>
              <div class="tab-section">
                <h4 class="tab-section-title">响应体</h4>
                <pre class="code-block" v-if="hasContent(nodeDialog.node.response.body)">{{ formatJson(nodeDialog.node.response.body) }}</pre>
                <el-empty v-else description="无响应体" :image-size="30" />
              </div>
              <!-- 下载文件卡片 -->
              <div class="tab-section" v-if="nodeDialog.node.file_downloads && nodeDialog.node.file_downloads.length > 0">
                <h4 class="tab-section-title">下载文件</h4>
                <div class="download-file-card" v-for="dl in nodeDialog.node.file_downloads" :key="dl.id">
                  <div class="dl-file-row">
                    <el-icon class="dl-file-icon"><Download /></el-icon>
                    <a class="dl-file-link" :href="`/api/v1/downloaded-files/${dl.id}/download/`" target="_blank">
                      {{ dl.filename }}
                    </a>
                    <span class="dl-file-size">{{ formatFileSize(dl.file_size) }}</span>
                  </div>
                  <div class="dl-file-meta" v-if="dl.md5">
                    <span class="dl-meta-label">MD5:</span>
                    <code class="dl-meta-value">{{ dl.md5 }}</code>
                  </div>
                </div>
              </div>
            </template>
            <el-empty v-else description="暂无响应数据" :image-size="30" />
          </el-tab-pane>

          <!-- 断言 -->
          <el-tab-pane v-if="hasAssertResults(nodeDialog.node)" label="断言" name="assert">
            <div class="tab-section">
              <h4 class="tab-section-title">断言结果</h4>
              <pre class="code-block">{{ formatJson(nodeDialog.node.assert_results) }}</pre>
            </div>
          </el-tab-pane>

          <!-- 提取 -->
          <el-tab-pane v-if="hasExtracted(nodeDialog.node)" label="提取" name="extracted">
            <div class="tab-section">
              <h4 class="tab-section-title">提取变量</h4>
              <pre class="code-block">{{ formatJson(nodeDialog.node.extracted) }}</pre>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Refresh, InfoFilled, DataAnalysis, List,
  Connection, Document, Box, Delete, Download,
} from '@element-plus/icons-vue'
import { sceneExecutionApi } from '../api/index.js'

const route = useRoute()
const router = useRouter()

const execution = ref(null)
const loading = ref(false)
const nodeResults = ref([])
const pollTimer = ref(null)

// 节点详情弹窗
const nodeDialog = reactive({
  visible: false,
  node: null,
  activeTab: 'overview',
})

// 编排器URL
const orchestratorDesignerUrl = computed(() => {
  if (!execution.value?.scene) return '#'
  return `/test-scenes-orchestrator/#/scenes/${execution.value.scene}/designer`
})

// 耗时展示
const durationDisplay = computed(() => {
  const ex = execution.value
  if (!ex) return '-'
  if (!ex.finished_at || !ex.started_at) return '执行中...'
  const start = new Date(ex.started_at)
  const end = new Date(ex.finished_at)
  const delta = Math.floor((end - start) / 1000)
  if (delta < 0) return '执行中...'
  if (delta < 60) return `${delta}秒`
  const m = Math.floor(delta / 60)
  const s = delta % 60
  if (m < 60) return `${m}分${s}秒`
  const h = Math.floor(m / 60)
  const min = m % 60
  return `${h}小时${min}分${s}秒`
})

// 进度百分比
const statsPercent = computed(() => {
  const total = execution.value?.total_nodes || 1
  return {
    passed: ((execution.value?.passed_nodes || 0) / total * 100).toFixed(1),
    failed: ((execution.value?.failed_nodes || 0) / total * 100).toFixed(1),
    skipped: ((execution.value?.skipped_nodes || 0) / total * 100).toFixed(1),
  }
})

function statusTag(status) {
  const map = {
    success: { type: 'success', text: '成功' },
    partial_success: { type: 'warning', text: '部分成功' },
    failed: { type: 'danger', text: '失败' },
    running: { type: 'primary', text: '执行中' },
  }
  return map[status] || { type: 'info', text: status || '未知' }
}

function nodeStatusTag(status) {
  const map = {
    passed: { type: 'success', text: '成功' },
    failed: { type: 'danger', text: '失败' },
    skipped: { type: 'info', text: '跳过' },
  }
  return map[status] || { type: 'info', text: status || '-' }
}

function formatTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatFileSize(bytes) {
  if (bytes == null || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const idx = Math.min(i, units.length - 1)
  const size = bytes / Math.pow(1024, idx)
  return size.toFixed(idx === 0 ? 0 : 1) + ' ' + units[idx]
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

function hasAssertResults(node) {
  if (!node.assert_results) return false
  if (Array.isArray(node.assert_results) && node.assert_results.length === 0) return false
  if (typeof node.assert_results === 'object' && Object.keys(node.assert_results).length === 0) return false
  return true
}

function hasExtracted(node) {
  if (!node.extracted) return false
  if (typeof node.extracted === 'object' && Object.keys(node.extracted).length === 0) return false
  return true
}

function openInOrchestrator() {
  if (!execution.value) return
  const url = `/test-scenes-orchestrator/#/scenes/${execution.value.scene}/executions/${execution.value.id}`
  window.open(url, '_blank')
}

function generateReport() {
  if (!execution.value) return
  router.push(`/scene-executions/${execution.value.id}/generate-report`)
}

function showNodeDetail(node) {
  nodeDialog.node = node
  nodeDialog.activeTab = 'overview'
  nodeDialog.visible = true
}

function startPolling() {
  if (pollTimer.value) return
  pollTimer.value = setInterval(() => {
    loadDetail().catch(() => {})
  }, 10000)
}

function stopPolling() {
  if (!pollTimer.value) return
  clearInterval(pollTimer.value)
  pollTimer.value = null
}

async function handleDelete() {
  if (!execution.value) return
  try {
    await sceneExecutionApi.remove(execution.value.id)
    ElMessage.success('执行记录已删除')
    router.push('/scene-executions')
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

async function loadDetail() {
  const id = Number(route.params.id)
  if (!id) return
  loading.value = true
  try {
    const data = await sceneExecutionApi.get(id)
    execution.value = data
    nodeResults.value = data.node_results || []
    // 如果正在执行中，启动轮询
    if (data.status === 'running') {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (e) {
    execution.value = null
    nodeResults.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadDetail)
onUnmounted(stopPolling)
</script>

<style scoped>
.sed-detail { display: flex; flex-direction: column; gap: 16px; flex: 1; }

.detail-header {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
}
.detail-header-left { display: flex; align-items: center; gap: 4px; }
.back-btn { font-size: var(--el-font-size-base); color: #606266; padding: 6px 8px; }
.back-btn:hover { color: #409eff; }
.detail-title { font-size: var(--el-font-size-large); font-weight: 600; color: #303133; margin: 0; }
.detail-header-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.text-muted { color: #909399; }

.running-alert { margin-bottom: 0; }

.info-row { margin-bottom: 0; }

/* ── 执行详情卡片 ── */
.info-card { border: 1px solid #e4e7ed; border-radius: 8px; margin-bottom: 16px; }
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
.scene-link { color: #409eff; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
.scene-link:hover { text-decoration: underline; }
.creator-value { display: flex; align-items: center; gap: 6px; }
.creator-avatar {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 50%;
  background: #409eff; color: #fff;
  font-size: var(--el-font-size-extra-small); font-weight: 600; flex-shrink: 0;
}
.running-dot {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  background: #409eff; margin-right: 4px;
  animation: pulse 1.5s infinite;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

.error-alert { margin-top: 16px; }
.error-alert :deep(.el-alert__content) { width: 100%; }
.error-pre {
  margin: 4px 0 0; font-size: var(--el-font-size-small); line-height: 1.5; white-space: pre-wrap;
  font-family: 'Consolas', monospace; max-height: 200px; overflow-y: auto;
}

/* ── 统计卡片 ── */
.stats-card { border: 1px solid #e4e7ed; border-radius: 8px; margin-bottom: 16px; }
.stats-card :deep(.el-card__header) {
  padding: 12px 16px; border-bottom: 1px solid #ebeef5;
  background: #fafafa; border-radius: 8px 8px 0 0;
}
.stats-card :deep(.el-card__body) { padding: 16px; }

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
.stat-card.skipped { background: rgba(144, 147, 153, 0.15); }
.stat-card.skipped .stat-value { color: #909399; }

/* ── 进度条 ── */
.progress-bar-wrap {
  display: flex; height: 20px; border-radius: 10px; overflow: hidden;
  margin-bottom: 12px; background: #f0f0f0;
}
.progress-segment { transition: width 0.3s ease; min-width: 2px; }
.progress-segment:first-child { border-radius: 10px 0 0 10px; }
.progress-segment:last-child { border-radius: 0 10px 10px 0; }

/* ── 统计标签 ── */
.stats-badges { display: flex; gap: 8px; margin-bottom: 0; flex-wrap: wrap; }
.badge-tag {
  display: inline-block; padding: 3px 10px; font-size: var(--el-font-size-extra-small); font-weight: 500;
  border-radius: 12px; line-height: 1.4;
}
.badge-tag.passed { background: rgba(103, 194, 58, 0.15); color: #67c23a; }
.badge-tag.failed { background: rgba(245, 108, 108, 0.15); color: #f56c6c; }
.badge-tag.skipped { background: rgba(144, 147, 153, 0.15); color: #909399; }

/* ── 节点结果卡片 ── */
.node-card { border: 1px solid #e4e7ed; border-radius: 8px; }
.node-card :deep(.el-card__header) {
  padding: 12px 16px; border-bottom: 1px solid #ebeef5;
  background: #fafafa; border-radius: 8px 8px 0 0;
}
.node-card :deep(.el-card__body) { padding: 16px; }

.data-table { width: 100%; }
.data-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
.node-key-code {
  font-size: var(--el-font-size-extra-small); color: #606266; background: #f5f7fa;
  padding: 2px 6px; border-radius: 4px;
}

/* ── 弹窗 ── */
.node-dialog :deep(.el-dialog__body) { padding: 20px; }
.node-desc { margin-bottom: 16px; }
.node-desc :deep(.desc-label) { width: 90px; }
.reason-cell :deep(.el-descriptions__cell) { word-break: break-word; }
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
.response-status-bar {
  display: flex; align-items: center; gap: 12px; margin-bottom: 4px;
}
.response-time-text { font-size: var(--el-font-size-small); color: #606266; }

/* ── 下载文件卡片 ── */
.download-file-card {
  background: #f6f8fa; border: 1px solid #e8eaed; border-radius: 6px;
  padding: 10px 14px; margin-bottom: 8px;
}
.download-file-card:last-child { margin-bottom: 0; }
.dl-file-row { display: flex; align-items: center; gap: 8px; }
.dl-file-icon { color: #409eff; font-size: 16px; flex-shrink: 0; }
.dl-file-link {
  color: #409eff; font-size: var(--el-font-size-base); font-weight: 500;
  text-decoration: none; word-break: break-all;
}
.dl-file-link:hover { text-decoration: underline; color: #66b1ff; }
.dl-file-size {
  margin-left: auto; font-size: var(--el-font-size-extra-small); color: #909399;
  white-space: nowrap; flex-shrink: 0;
}
.dl-file-meta {
  display: flex; align-items: center; gap: 6px; margin-top: 4px;
  padding-top: 4px; border-top: 1px dashed #e8eaed;
}
.dl-meta-label {
  font-size: var(--el-font-size-extra-small); color: #909399; flex-shrink: 0;
}
.dl-meta-value {
  font-size: var(--el-font-size-extra-small); color: #606266;
  font-family: 'Consolas', monospace; word-break: break-all;
}
</style>
