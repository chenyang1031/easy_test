<template>
  <div class="record-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">AI生成记录</h2>
        <span class="page-subtitle" v-if="total !== null">共 {{ total }} 条</span>
      </div>
      <div class="page-header-right">
        <el-button :icon="Refresh" size="default" @click="loadData">刷新</el-button>
      </div>
    </div>

    <div class="panel-card">
      <div class="filter-bar">
        <el-select v-model="filterProvider" placeholder="全部模型" clearable style="width:180px" @change="doSearch">
          <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-date-picker v-model="filterStartDate" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width:150px" />
        <el-date-picker v-model="filterEndDate" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width:150px" />
        <el-input v-model="keyword" placeholder="搜索请求内容..." clearable style="width:240px" @keyup.enter="doSearch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="doSearch"><el-icon><Search /></el-icon> 查询</el-button>
        <el-button type="danger" :disabled="selectedIds.size === 0" @click="confirmBatchDelete"><el-icon><Delete /></el-icon> 删除选中 ({{ selectedIds.size }})</el-button>
      </div>

      <div v-if="loading" class="loading-state"><el-icon class="is-loading" :size="24"><Loading /></el-icon><span>加载中...</span></div>

      <el-empty v-else-if="records.length===0" description="暂无AI生成记录" />

      <template v-else>
        <el-table :data="records" stripe style="width:100%" :header-cell-style="{background:'#f5f7fa',color:'#303133',fontWeight:600}" @selection-change="onSelectionChange">
          <el-table-column type="selection" width="42" />
          <el-table-column label="模型" width="140" prop="model_provider_name">
            <template #default="{row}">{{ row.model_provider_name || '旧版参数配置' }}</template>
          </el-table-column>
          <el-table-column label="接口" min-width="300" show-overflow-tooltip>
            <template #default="{row}">
              <span v-if="row.interface_info?.api_name" class="iface-name">{{ row.interface_info.api_name }}</span>
              <span class="text-mono">{{ row.interface_info?.request_method }}</span>
              <code class="url-code">{{ row.interface_info?.request_url }}</code>
            </template>
          </el-table-column>
          <el-table-column label="用例类型" width="100" align="center">
            <template #default="{row}">{{ caseTypeLabel(row.case_type) }}</template>
          </el-table-column>
          <el-table-column label="数量" width="70" align="center">
            <template #default="{row}">
              <span v-if="row.status === 'generating'">-</span>
              <span v-else>{{ row.case_count }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{row}">
              <el-tag v-if="row.status === 'generating'" size="small" type="warning">生成中</el-tag>
              <el-tag v-else size="small" :type="row.success?'success':'danger'">{{ row.success?'成功':'失败' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="调用人" width="90" prop="created_by_name" />
          <el-table-column label="耗时" width="100" align="center">
            <template #default="{row}">
              <span v-if="row.duration_ms != null">{{ formatDuration(row.duration_ms) }}</span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="时间" width="175" show-overflow-tooltip>
            <template #default="{row}">{{ row.created_at?.slice(0,19).replace('T',' ') }}</template>
          </el-table-column>
          <el-table-column label="操作" width="190" align="center">
            <template #default="{row}">
              <el-button size="small" text @click="showDetail(row)">详情</el-button>
              <el-button
                size="small" text type="primary"
                :loading="regeneratingId === row.id"
                :disabled="row.status === 'generating'"
                @click="confirmRegenerate(row)"
              >重新生成</el-button>
              <el-button size="small" text type="danger" @click="confirmDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrap" v-if="total > 0">
          <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="onSizeChange" />
        </div>
      </template>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="AI 调用详情" width="940px" destroy-on-close>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="模型" :span="1">{{ detail.model_provider_name || '旧版参数配置' }}</el-descriptions-item>
        <el-descriptions-item label="提示词模板" :span="1">{{ detail.prompt_template_name || '默认模板' }}</el-descriptions-item>
        <el-descriptions-item label="接口" :span="2">
          {{ detail.interface_info?.api_name }}
          <el-tag size="small" style="margin:0 4px">{{ detail.interface_info?.request_method }}</el-tag>
          <code class="url-text">{{ detail.interface_info?.request_url }}</code>
        </el-descriptions-item>
        <el-descriptions-item label="用例类型" :span="1">{{ caseTypeLabel(detail.case_type) }}</el-descriptions-item>
        <el-descriptions-item label="耗时" :span="1" v-if="detail.duration_ms != null">{{ formatDuration(detail.duration_ms) }}</el-descriptions-item>
        <el-descriptions-item label="状态" :span="1">
          <el-tag v-if="detail.status === 'generating'" size="small" type="warning">生成中</el-tag>
          <el-tag v-else size="small" :type="detail.success?'success':'danger'">{{ detail.success?'成功':'失败' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="返回数量" :span="1" v-if="detail.status !== 'generating'">{{ detail.case_count }} 条</el-descriptions-item>
        <el-descriptions-item label="错误信息" :span="2" v-if="detail.error_message">
          <span class="error-text">{{ detail.error_message }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <div class="code-section">
        <div class="code-header">
          <span class="code-title">请求 Prompt</span>
          <el-button size="small" text :icon="CopyDocument" @click="copyText(detail.request_prompt)">复制</el-button>
        </div>
        <pre class="code-block"><code>{{ detail.request_prompt || '（空）' }}</code></pre>
      </div>

      <div class="code-section">
        <div class="code-header">
          <span class="code-title">AI 返回</span>
          <div class="code-header-actions">
            <el-tag v-if="detail.response_raw" size="small" type="info" effect="plain">JSON</el-tag>
            <el-button size="small" text :icon="CopyDocument" @click="copyText(detail.response_raw)">复制</el-button>
          </div>
        </div>
        <div class="code-wrap">
          <pre class="code-block json-block" :class="{ 'code-collapsed': responseTruncated }"><code v-html="displayResponse"></code></pre>
          <div v-if="responseTruncated" class="code-collapsed-glow"></div>
          <div v-if="responseTruncated" class="show-more-bar">
            <el-button text size="small" @click="responseShowAll = true">全部展示 ({{ formatLength(detail.response_raw.length) }})</el-button>
          </div>
          <div v-else-if="responseWasTruncated" class="show-more-bar">
            <el-button text size="small" @click="responseShowAll = false">收起</el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Search, Delete, Refresh, Loading } from '@element-plus/icons-vue'

const records = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const filterProvider = ref(null)
const filterStartDate = ref('')
const filterEndDate = ref('')
const keyword = ref('')
const providers = ref([])
const detailVisible = ref(false)
const detail = ref({})
const responseShowAll = ref(false)
const regeneratingId = ref(null)

const DISPLAY_LIMIT = 20000
const responseTruncated = computed(() => {
  const raw = detail.value?.response_raw
  return raw && raw.length > DISPLAY_LIMIT && !responseShowAll.value
})
const responseWasTruncated = computed(() => {
  const raw = detail.value?.response_raw
  return raw && raw.length > DISPLAY_LIMIT && responseShowAll.value
})
const displayResponse = computed(() => {
  const raw = detail.value?.response_raw
  if (!raw) return '<span class="j-muted">（空）</span>'
  const text = responseShowAll.value ? raw : raw.slice(0, DISPLAY_LIMIT)
  return highlightJson(text)
})
function formatLength(len) {
  if (len < 1024) return len + 'B'
  return (len / 1024).toFixed(1) + 'KB'
}
const selectedIds = ref(new Set())

const CASE_TYPES = {
  api: '接口测试', biz_logic: '业务逻辑', error_handle: '异常处理',
  param_validate: '参数校验', boundary: '边界值', performance: '性能测试', security: '安全测试',
}
function caseTypeLabel(v) { return CASE_TYPES[v] || v }

function formatDuration(ms) {
  if (ms == null) return '-'
  if (ms < 1000) return ms + 'ms'
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's'
  const min = Math.floor(ms / 60000)
  const sec = Math.round((ms % 60000) / 1000)
  return min + 'm' + sec + 's'
}

function highlightJson(text) {
  if (!text) return '<span class="json-muted">（空）</span>'
  // Pretty-print if valid JSON
  let formatted = text
  try { formatted = JSON.stringify(JSON.parse(text), null, 2) } catch { /* keep as-is */ }
  // Escape HTML
  const escaped = formatted
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // Syntax highlighting via regex
  return escaped
    .replace(/"([^"\\]*(\\.[^"\\]*)*)"(?=\s*:)/g, '<span class="j-key">"$1"</span>')
    .replace(/(:\s*)"([^"\\]*(\\.[^"\\]*)*)"/g, '$1<span class="j-string">"$2"</span>')
    .replace(/(:\s*)(-?\d+\.?\d*(?:[eE][+-]?\d+)?)/g, '$1<span class="j-number">$2</span>')
    .replace(/(:\s*)(true|false|null)\b/g, '$1<span class="j-bool">$2</span>')
}

function copyText(text) {
  if (!text) { ElMessage.warning('无内容可复制'); return }
  const fallback = () => {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'; ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    try { document.execCommand('copy'); ElMessage.success('已复制') } catch { ElMessage.error('复制失败') }
    document.body.removeChild(ta)
  }
  try { navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制')).catch(fallback) } catch { fallback() }
}

const BASE = window.location.port === '5178' ? 'http://localhost:8000' : ''

async function req(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (!BASE) {
    const token = document.querySelector('input[name=csrfmiddlewaretoken]')?.value
    if (token) headers['X-CSRFToken'] = token
  }
  const r = await fetch(BASE + url, { ...options, headers })
  if (!r.ok && r.status !== 400) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

async function loadData() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filterProvider.value) params.set('model_provider', filterProvider.value)
    if (filterStartDate.value) params.set('start_date', filterStartDate.value)
    if (filterEndDate.value) params.set('end_date', filterEndDate.value)
    if (keyword.value) params.set('search', keyword.value)
    params.set('page', page.value)
    params.set('page_size', pageSize.value)
    const qs = params.toString()
    const data = await req(`/api/v1/ai/generation-records/?${qs}`)
    records.value = data.results || data
    total.value = data.count || 0
  } catch (e) { ElMessage.error('加载失败: ' + e.message) }
  finally { loading.value = false }
}

async function loadProviders() {
  try {
    const data = await req('/api/v1/ai/model-providers/')
    providers.value = data.results || data
  } catch (e) { /* ignore */ }
}

function doSearch() { page.value = 1; loadData() }

function onSizeChange() { page.value = 1; loadData() }

function showDetail(row) {
  detail.value = row
  responseShowAll.value = false
  detailVisible.value = true
}

async function confirmDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除该条记录吗？', '确认删除', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  try {
    const r = await fetch(BASE + `/api/v1/ai/generation-records/${row.id}/`, {
      method: 'DELETE',
      headers: (() => {
        const h = {}
        if (!BASE) {
          const token = document.querySelector('input[name=csrfmiddlewaretoken]')?.value
          if (token) h['X-CSRFToken'] = token
        }
        return h
      })(),
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { ElMessage.error('删除失败: ' + e.message) }
}

async function confirmRegenerate(row) {
  if (row.status === 'generating') { ElMessage.warning('该记录正在生成中，请等待完成'); return }
  const draftInfo = row.draft_group_id ? `已有草稿将替换为新生成的内容（草稿组 #${row.draft_group_id}）` : '将创建新的草稿组'
  try {
    await ElMessageBox.confirm(
      `确定重新生成测试用例：${draftInfo}，此操作不可撤销。`,
      '重新生成',
      { confirmButtonText: '确定生成', cancelButtonText: '取消', type: 'info' }
    )
  } catch { return }
  regeneratingId.value = row.id
  try {
    const h = {}
    if (!BASE) {
      const token = document.querySelector('input[name=csrfmiddlewaretoken]')?.value
      if (token) h['X-CSRFToken'] = token
    }
    const r = await fetch(BASE + `/api/v1/ai/generation-records/${row.id}/regenerate/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...h },
    })
    const data = await r.json()
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`)
    ElMessage.success(`重新生成成功，共 ${data.case_count} 条用例`)
    loadData()
  } catch (e) { ElMessage.error('重新生成失败: ' + e.message) }
  finally { regeneratingId.value = null }
}

function onSelectionChange(rows) {
  selectedIds.value = new Set(rows.map(r => r.id))
}

async function confirmBatchDelete() {
  const ids = Array.from(selectedIds.value)
  if (ids.length === 0) { ElMessage.warning('请先选择记录'); return }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 条记录？`, '批量删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
  } catch { return }
  const h = {}
  if (!BASE) {
    const token = document.querySelector('input[name=csrfmiddlewaretoken]')?.value
    if (token) h['X-CSRFToken'] = token
  }
  try {
    const r = await fetch(BASE + '/api/v1/ai/generation-records/batch_delete/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...h },
      body: JSON.stringify({ ids }),
    })
    const data = await r.json()
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`)
    ElMessage.success(`已删除 ${data.deleted_count} 条记录`)
    selectedIds.value = new Set()
    loadData()
  } catch (e) { ElMessage.error('批量删除失败: ' + e.message) }
}

onMounted(() => { loadProviders(); loadData() })
</script>

<style scoped>
.record-list { padding:0; }

/* ---- 页面标题 ---- */
.page-header { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:20px; }
.page-header-left { display:flex; align-items:baseline; gap:12px; }
.page-title { font-size:24px; font-weight:600; color:#303133; margin:0; line-height:1.3; }
.page-subtitle { font-size:14px; color:#909399; }
.page-header-right { display:flex; gap:8px; align-items:center; }

.panel-card { background:#fff; border-radius:10px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04); }
.filter-bar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:12px; }
.loading-state { display:flex; align-items:center; justify-content:center; gap:8px; padding:40px 0; color:#909399; }
.iface-name { font-size: var(--el-font-size-extra-small); color:#409eff; margin-right:6px; font-weight:500; }
.text-mono { font-size: var(--el-font-size-extra-small); color:#909399; margin-right:4px; }
.url-text { font-size: var(--el-font-size-extra-small); color:#606266; background:#f5f7fa; padding:2px 6px; border-radius:3px; }
.pagination-wrap { display:flex; justify-content:flex-end; padding-top:16px; border-top:1px solid #ebeef5; margin-top:16px; }
.error-text { color:#f56c6c; font-size: var(--el-font-size-small); }

/* Code sections */
.code-section { margin-top:18px; }
.code-wrap { position:relative; }
.code-collapsed .code-block { max-height:320px; overflow:hidden; }
.code-collapsed-glow { position:absolute; bottom:36px; left:0; right:0; height:60px; background:linear-gradient(transparent, #1e1e1e); pointer-events:none; }
.show-more-bar {
  text-align:center; padding:6px 0 2px;
}
.show-more-bar .el-button { color:#409eff; font-size: var(--el-font-size-small); }
.code-header {
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:8px; font-weight:600; font-size: var(--el-font-size-base); color:#303133;
}
.code-header-actions { display:flex; align-items:center; gap:6px; }
.code-title { font-size: var(--el-font-size-base); font-weight:600; color:#303133; }
.code-block {
  background:#1e1e1e; color:#d4d4d4;
  padding:14px 18px; border-radius:8px;
  max-height:360px; overflow:auto;
  font-size: var(--el-font-size-small); line-height:1.6;
  white-space:pre-wrap; word-break:break-all;
  margin:0;
}
.code-block code { font-family:'Cascadia Code','Fira Code','Consolas',monospace; }

/* JSON syntax highlighting */
.json-block :deep(.j-key)    { color:#9cdcfe; }  /* keys - light blue */
.json-block :deep(.j-string) { color:#ce9178; }  /* strings - warm orange */
.json-block :deep(.j-number) { color:#b5cea8; }  /* numbers - soft green */
.json-block :deep(.j-bool)   { color:#569cd6; }  /* booleans/null - blue */
.json-block :deep(.j-muted)  { color:#6e6e6e; font-style:italic; }
</style>
