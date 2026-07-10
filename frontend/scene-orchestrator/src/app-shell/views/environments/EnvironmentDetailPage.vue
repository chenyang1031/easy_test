<template>
  <div class="environment-detail-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="goBack" :icon="ArrowLeft" class="back-btn" />
        <h2 class="page-title">{{ env.name }}</h2>
        <el-tag v-if="env.category === 'third_party'" size="small" type="warning" effect="plain" class="env-tag">第三方</el-tag>
        <el-tag v-else size="small" type="info" effect="plain" class="env-tag">默认</el-tag>
      </div>
      <div class="page-header-right">
        <el-button @click="loadDetail" :icon="Refresh">刷新</el-button>
        <el-button type="primary" :icon="Edit" @click="goEdit">编辑环境</el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="28"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <!-- 错误状态 -->
    <el-result
      v-else-if="error"
      icon="error"
      title="加载失败"
      :sub-title="error"
    >
      <template #extra>
        <el-button type="primary" @click="loadDetail">重新加载</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="row">
        <!-- ====== 左列：基本信息 ====== -->
        <div class="col-left">
          <!-- 基本信息 -->
          <div class="panel-card info-card">
            <div class="card-header-row">
              <span class="card-section-title">
                <el-icon><InfoFilled /></el-icon> 基本信息
              </span>
            </div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="环境名称" min-width="120">
                {{ env.name }}
              </el-descriptions-item>
              <el-descriptions-item label="项目" min-width="120">
                <router-link v-if="env.project" :to="`/projects/${env.project}`" class="project-link">
                  <el-icon><FolderOpened /></el-icon> {{ env.project_name }}
                </router-link>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="域名" min-width="120">
                <div class="copy-cell">
                  <code class="base-url-text">{{ env.base_url }}</code>
                  <el-button
                    size="small" text
                    @click="copyText(env.base_url)"
                    title="复制域名"
                  >
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="环境分类" min-width="120">
                <el-tag v-if="env.category === 'third_party'" size="small" type="warning">第三方</el-tag>
                <el-tag v-else size="small" type="info">默认</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="全局可见" min-width="120">
                <el-tag :type="env.is_global_visible ? 'success' : 'info'" size="small" effect="plain">
                  {{ env.is_global_visible ? '是' : '否' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="创建时间" min-width="120">
                <span class="time-value">{{ formatTime(env.created_at) }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="更新时间" min-width="120">
                <span class="time-value">{{ formatTime(env.updated_at) }}</span>
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 前置脚本 -->
          <div class="panel-card script-card">
            <div class="card-header-row">
              <span class="card-section-title">
                <el-icon><EditPen /></el-icon> 前置脚本
              </span>
              <el-tag size="small" effect="plain" :type="env.pre_request_script ? 'warning' : 'info'">
                {{ env.pre_request_script ? '已配置' : '未配置' }}
                <span v-if="env.script_timeout"> | {{ env.script_timeout }}ms</span>
              </el-tag>
            </div>
            <div v-if="env.pre_request_script" class="script-display">
              <pre><code>{{ env.pre_request_script }}</code></pre>
            </div>
            <div v-else class="empty-hint">
              <el-icon :size="20"><Warning /></el-icon>
              <span>未配置前置脚本</span>
            </div>
          </div>
        </div>

        <!-- ====== 右列：变量 & 请求头 ====== -->
        <div class="col-right">
          <!-- 环境变量 -->
          <div class="panel-card vars-card">
            <div class="card-header-row">
              <span class="card-section-title">
                <el-icon><List /></el-icon> 环境变量
              </span>
              <el-tag size="small" round :type="varRows.length > 0 ? 'primary' : 'info'">
                {{ varRows.length }} 项
              </el-tag>
            </div>
            <div v-if="varRows.length > 0">
              <el-table :data="varRows" stripe size="small" class="vars-table">
                <el-table-column type="index" width="36" label="#" />
                <el-table-column label="Key" min-width="120">
                  <template #default="{ row }">
                    <code class="var-key">{{ row.key }}</code>
                  </template>
                </el-table-column>
                <el-table-column label="Value" min-width="160">
                  <template #default="{ row }">
                    <div class="var-value-cell">
                      <code class="var-value">{{ row.value }}</code>
                      <el-button
                        size="small" text
                        @click="copyText(row.value)"
                        title="复制值"
                      >
                        <el-icon><CopyDocument /></el-icon>
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="说明" min-width="100" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.description || '-' }}</template>
                </el-table-column>
              </el-table>
            </div>
            <el-empty v-else description="暂无环境变量" :image-size="48" />
          </div>

          <!-- 请求头预设 -->
          <div class="panel-card headers-card">
            <div class="card-header-row">
              <span class="card-section-title">
                <el-icon><Paperclip /></el-icon> 请求头预设
              </span>
              <el-tag size="small" round :type="headerRows.length > 0 ? 'primary' : 'info'">
                {{ headerRows.length }} 项
              </el-tag>
            </div>
            <div v-if="headerRows.length > 0">
              <el-table :data="headerRows" stripe size="small" class="vars-table">
                <el-table-column type="index" width="36" label="#" />
                <el-table-column label="Header" min-width="120">
                  <template #default="{ row }">
                    <code class="var-key">{{ row.key }}</code>
                  </template>
                </el-table-column>
                <el-table-column label="值" min-width="160" show-overflow-tooltip>
                  <template #default="{ row }">
                    <div class="var-value-cell">
                      <span>{{ row.value }}</span>
                      <el-button
                        size="small" text
                        @click="copyText(row.value)"
                        title="复制值"
                      >
                        <el-icon><CopyDocument /></el-icon>
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="说明" min-width="80" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.description || '-' }}</template>
                </el-table-column>
              </el-table>
            </div>
            <el-empty v-else description="暂无请求头预设" :image-size="48" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Edit, Refresh, Loading,
  InfoFilled, EditPen, List, Paperclip,
  FolderOpened, CopyDocument, Warning,
} from '@element-plus/icons-vue'
import { environmentApi } from '../../../environment/api/index.js'
import { safeJsonParse, rowsFromVariables } from '../../../environment/utils/environmentPayload.js'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const error = ref('')
const env = ref({})
const varRows = ref([])
const headerRows = ref([])

function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function goBack() { router.push('/environments') }
function goEdit() { router.push(`/environments/${route.params.id}/edit`) }

function copyText(text) {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    // fallback
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.left = '-9999px'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制到剪贴板')
  })
}

async function loadDetail() {
  loading.value = true
  error.value = ''
  try {
    const data = await environmentApi.get(route.params.id)
    env.value = data

    // 解析环境变量
    const variablesObj = safeJsonParse(
      typeof data.variables === 'string' ? data.variables : JSON.stringify(data.variables || {}),
      {}
    )
    varRows.value = rowsFromVariables(variablesObj).filter(r => r.key)

    // 解析请求头
    const headersRaw = safeJsonParse(
      typeof data.request_headers === 'string' ? data.request_headers : JSON.stringify(data.request_headers || []),
      []
    )
    headerRows.value = (Array.isArray(headersRaw) ? headersRaw : []).filter(r => r.key)
  } catch (e) {
    error.value = e.message || '未知错误'
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadDetail() })
</script>

<style scoped>
.environment-detail-page { padding: 0; min-height: 100%; }

/* ---- 页面标题 ---- */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px; margin-bottom: 20px;
}
.page-header-left { display: flex; align-items: center; gap: 8px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.env-tag { margin-left: 4px; }
.back-btn { font-size: 20px; padding: 4px; }
.page-header-right { display: flex; gap: 8px; align-items: center; }

/* ---- 加载状态 ---- */
.loading-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 12px; padding: 80px 0; color: #909399;
}

/* ---- 两列布局 ---- */
.row { display: flex; gap: 20px; flex-wrap: wrap; }
.col-left { flex: 1.2; min-width: 400px; }
.col-right { flex: 1; min-width: 380px; }
@media (max-width: 900px) { .col-left, .col-right { min-width: 100%; } }

/* ---- 卡片 ---- */
.panel-card {
  background: #fff; border-radius: 10px; padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  margin-bottom: 20px;
}
.card-header-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.card-section-title {
  font-size: 15px; font-weight: 600; color: #303133;
  display: flex; align-items: center; gap: 6px;
}

/* ---- 基本信息 ---- */
.project-link {
  color: #409eff; text-decoration: none; font-weight: 500;
  display: inline-flex; align-items: center; gap: 4px;
}
.project-link:hover { text-decoration: underline; }
.base-url-text {
  font-size: 13px; color: #606266; background: #f5f7fa;
  padding: 2px 8px; border-radius: 4px;
  word-break: break-all;
}
.copy-cell { display: flex; align-items: center; gap: 4px; }
.time-value { font-size: 13px; color: #909399; }

/* ---- 前置脚本 ---- */
.script-display {
  background: #1e1e1e; border-radius: 6px; padding: 16px;
  max-height: 320px; overflow: auto;
}
.script-display pre {
  margin: 0; font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 13px; line-height: 1.6; color: #d4d4d4;
  white-space: pre-wrap; word-break: break-all;
}
.empty-hint {
  display: flex; align-items: center; gap: 8px;
  padding: 24px 0; color: #c0c4cc; justify-content: center;
  font-size: 14px;
}

/* ---- 变量 & Header 表格 ---- */
.vars-table { width: 100%; }
.vars-table :deep(.el-table__header th) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
.var-key {
  font-size: 13px; color: #409eff; background: #ecf5ff;
  padding: 1px 6px; border-radius: 3px;
}
.var-value {
  font-size: 12px; color: #606266; background: #f5f7fa;
  padding: 1px 5px; border-radius: 3px;
  display: inline-block; max-width: 180px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.var-value-cell {
  display: flex; align-items: center; gap: 4px;
}
</style>
