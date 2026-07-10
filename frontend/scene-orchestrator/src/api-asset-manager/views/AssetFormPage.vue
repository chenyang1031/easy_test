<template>
  <div class="form-page" v-loading="loading">
    <!-- 顶部导航 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button @click="$router.push('/api-assets')"><el-icon><ArrowLeft /></el-icon> 返回列表</el-button>
        <h2 class="page-title">{{ isEdit ? '编辑接口详情' : '新增接口详情' }}</h2>
      </div>
      <div class="page-header-right">
        <el-button v-if="isEdit" type="warning" plain @click="handleAiGenerate">
          <el-icon><MagicStick /></el-icon>AI生成测试用例
        </el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          <el-icon><Check /></el-icon>保存变更
        </el-button>
      </div>
    </div>

    <!-- 顶部错误提示 -->
    <div v-if="errorMsg" class="error-bar"><el-alert :title="errorMsg" type="error" show-icon :closable="false" /></div>

    <!-- 基础信息 -->
    <el-card class="section-card" shadow="never">
      <template #header><span class="section-title">基础信息</span></template>
      <el-row :gutter="20">
        <el-col :span="7">
          <el-form-item label="接口名称" required><el-input v-model="form.name" placeholder="如：获取用户列表" maxlength="200" /></el-form-item>
        </el-col>
        <el-col :span="4">
          <el-form-item label="请求方式" required>
            <el-select v-model="form.method" style="width:100%">
              <el-option label="GET" value="GET" /><el-option label="POST" value="POST" />
              <el-option label="PUT" value="PUT" /><el-option label="DELETE" value="DELETE" />
              <el-option label="PATCH" value="PATCH" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="13">
          <el-form-item label="请求URL" required><el-input v-model="form.url" placeholder="如：/api/users" maxlength="500" /></el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="20">
        <el-col :span="5">
          <el-form-item label="项目" required><el-input :model-value="currentProjectName" disabled /></el-form-item>
        </el-col>
        <el-col :span="5">
          <el-form-item label="分组">
            <el-select v-model="form.group" placeholder="根目录" clearable style="width:100%">
              <el-option v-for="g in store.flatGroupsForSelect" :key="g.id??'root'" :label="g.displayName" :value="g.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="4">
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width:100%">
              <el-option label="草稿" value="draft" /><el-option label="可用" value="active" /><el-option label="已废弃" value="deprecated" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="5">
          <el-form-item label="来源"><el-input v-model="form.source" placeholder="如:postman" /></el-form-item>
        </el-col>
        <el-col :span="5">
          <el-form-item label="外部标识"><el-input v-model="form.external_id" placeholder="外部系统ID" /></el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="接口描述"><el-input v-model="form.interface_desc" type="textarea" :rows="2" placeholder="描述该接口的用途" /></el-form-item>
      <el-row :gutter="20">
        <el-col :span="3">
          <el-form-item label="默认必填"><el-switch v-model="form.required" /></el-form-item>
        </el-col>
        <el-col :span="5">
          <el-form-item label="默认参数类型">
            <el-select v-model="form.param_type" style="width:100%">
              <el-option label="string" value="string" /><el-option label="number" value="number" />
              <el-option label="boolean" value="boolean" /><el-option label="object" value="object" />
              <el-option label="array" value="array" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="4">
          <el-form-item label="默认排序">
            <el-input-number v-model="form.sort" :min="0" style="width:130px" controls-position="right" />
          </el-form-item>
        </el-col>
        <el-col :span="6" class="hint-col">
          <span class="text-hint">用于新参数行默认值</span>
        </el-col>
      </el-row>
    </el-card>

    <!-- Tab面板 -->
    <el-card class="section-card" shadow="never">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 请求Tab -->
        <el-tab-pane label="请求" name="request">
          <!-- 请求头-->
          <div class="sub-section">
            <div class="sub-header">
              <span class="sub-title">请求头</span>
              <div class="sub-header-actions">
                <template v-if="environments.length > 0">
                  <el-select
                    v-model="envSelectedId"
                    size="small"
                    placeholder="选择环境"
                    style="width:140px;margin-right:4px"
                    clearable
                  >
                    <el-option
                      v-for="env in environments"
                      :key="env.id"
                      :label="env.name"
                      :value="env.id"
                    />
                  </el-select>
                  <el-button size="small" @click="applyEnvHeaders" :disabled="!envSelectedId">
                    <el-icon><Discount /></el-icon> 填充
                  </el-button>
                </template>
                <el-button size="small" @click="addKeyValue('headers')"><el-icon><Plus /></el-icon>新增请求头</el-button>
              </div>
            </div>
            <KeyValueTable v-model="form.headers" :columns="kvColumns" />
          </div>
          <el-divider />

          <!-- 查询参数 -->
          <div class="sub-section">
            <div class="sub-header">
              <span class="sub-title">
                查询参数（Query Params）                <el-tooltip content="拼接在URL问号后的参数，常用于GET请求" placement="top">
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
              <el-button size="small" @click="addKeyValue('params')"><el-icon><Plus /></el-icon>新增参数</el-button>
            </div>
            <KeyValueTable v-model="form.params" :columns="kvColumns" />
          </div>
          <el-divider />

          <!-- 请求体-->
          <div class="sub-section" :class="{ disabled: isBodyDisabled }">
            <div class="sub-header">
              <span class="sub-title">
                请求体（Request Body）<el-tooltip content="请求载荷，常用于POST/PUT请求，支持JSON/Form格式" placement="top">
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
              <el-checkbox v-if="isBodyDisabled" v-model="forceBody" size="small" @change="onForceBodyChange">
                强制发送请求体
              </el-checkbox>
            </div>

            <!-- GET请求禁用提示 -->
            <el-alert
              v-if="isBodyDisabled && !forceBody"
              title="GET/HEAD/DELETE 请求不支持请求体"
              type="info"
              :closable="false"
              show-icon
              style="margin-bottom:12px"
            >
              <template #default>
                如需发送Body请切换为 <el-tag size="small" type="warning">POST</el-tag> / <el-tag size="small" type="warning">PUT</el-tag> / <el-tag size="small" type="warning">PATCH</el-tag>
              </template>
            </el-alert>
            <el-alert
              v-if="isBodyDisabled && forceBody"
              title="强烈不推荐 GET 请求携带 Body"
              type="warning"
              :closable="false"
              show-icon
              style="margin-bottom:12px"
            >
              部分HTTP客户端和代理可能丢弃GET请求的Body。建议使用POST代替。</el-alert>

            <!-- Body编辑器（仅非GET或强制模式下可用）-->
            <template v-if="!isBodyDisabled || forceBody">
              <el-radio-group v-model="form.request_body_format" style="margin-bottom:8px">
                <el-radio value="json">JSON</el-radio>
                <el-radio value="form-data">Form Data</el-radio>
              </el-radio-group>
              <div v-if="form.request_body_format === 'json'">
                <JsonEditor v-model="form.request_body_json" placeholder='{"key":"value"}' />
              </div>
              <div v-else>
                <div class="sub-header">
                  <span class="sub-title">Form Data</span>
                  <el-button size="small" @click="addKeyValue('form_data')"><el-icon><Plus /></el-icon>新增参数</el-button>
                </div>
                <KeyValueTable v-model="form.form_data" :columns="formDataColumns" />
              </div>
            </template>
          </div>
        </el-tab-pane>

        <!-- 响应Tab -->
        <el-tab-pane label="响应" name="response">
          <div class="sub-section">
            <div class="sub-header"><span class="sub-title">响应Schema (JSON)</span></div>
            <JsonEditor v-model="form.response_schema_json" placeholder='{"type":"object","properties":{}}' />
          </div>
          <el-divider />
          <div class="sub-section">
            <div class="sub-header">
              <span class="sub-title">错误码表</span>
              <el-button size="small" @click="addErrorCode"><el-icon><Plus /></el-icon>新增错误码</el-button>
            </div>
            <el-table :data="form.error_codes" border stripe size="small" style="width:100%">
              <el-table-column label="错误码" width="150">
                <template #default="{row}"><el-input v-model="row.code" size="small" placeholder="如：400" /></template>
              </el-table-column>
              <el-table-column label="错误信息" width="200">
                <template #default="{row}"><el-input v-model="row.message" size="small" placeholder="错误提示" /></template>
              </el-table-column>
              <el-table-column label="说明">
                <template #default="{row}"><el-input v-model="row.desc" size="small" placeholder="补充说明" /></template>
              </el-table-column>
              <el-table-column label="操作" width="70" align="center">
                <template #default="{ $index }">
                  <el-button link type="danger" size="small" @click="form.error_codes.splice($index,1)"><el-icon><Delete /></el-icon></el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 关联Tab -->
        <el-tab-pane label="关联" name="related">
          <el-form-item label="鉴权类型">
            <el-select v-model="form.auth_type" style="width:200px" @change="onAuthTypeChange">
              <el-option label="None" value="none" /><el-option label="BasicAuth" value="basic" />
              <el-option label="Token" value="token" /><el-option label="OAuth2" value="oauth2" />
            </el-select>
          </el-form-item>
          <div class="sub-section" style="margin-top:12px">
            <div class="sub-header"><span class="sub-title">鉴权配置 (JSON)</span></div>
            <JsonEditor v-model="form.auth_config_json" placeholder='{}' />
          </div>
        </el-tab-pane>

        <!-- 版本Tab -->
        <el-tab-pane label="版本" name="version" v-if="isEdit">
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="资产ID">{{ assetId }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ assetData?.created_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ assetData?.updated_at || '-' }}</el-descriptions-item>
          </el-descriptions>
          <el-alert type="info" :closable="false" show-icon style="margin-top:12px">
            历史变更可在 API 资产列表点击"历史"查看与回滚。</el-alert>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- AI生成测试用例弹窗 -->
    <AIGenerateModal v-model="showAiModal" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, MagicStick, Check, Plus, Delete, QuestionFilled, Discount } from '@element-plus/icons-vue'
import { useApiAssetStore } from '../stores/apiAsset.js'
import { apiAssetApi } from '../api/index.js'
import { environmentApi } from '../../environment/api/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'
import JsonEditor from '../components/JsonEditor.vue'
import KeyValueTable from '../components/KeyValueTable.vue'
import AIGenerateModal from '../components/AIGenerateModal.vue'

const route = useRoute()
const router = useRouter()
const store = useApiAssetStore()

const isEdit = computed(() => !!route.params.id)
const assetId = computed(() => route.params.id)

const loading = ref(false)
const submitting = ref(false)
const errorMsg = ref('')
const activeTab = ref('request')
const assetData = ref(null)
const forceBody = ref(false)
const showAiModal = ref(false)

// 环境预设请求头
const environments = ref([])
const envSelectedId = ref(null)

// 请求体禁用联动
const methodsWithoutBody = ['GET', 'HEAD', 'DELETE']
const isBodyDisabled = computed(() => methodsWithoutBody.includes(form.method))

const currentProjectName = computed(() => {
  const p = store.platformProjects.find(p => {
    const apiId = store.currentProjectId
    return p.id === store.platformProjectId
  })
  return p?.name || '未选择'
})

const form = reactive({
  name: '', method: 'GET', url: '', group: null, status: 'draft',
  source: 'manual', external_id: '', interface_desc: '',
  required: false, param_type: 'string', sort: 0,
  headers: [], params: [], request_body_format: 'json',
  request_body_json: '', form_data: [],
  response_schema_json: '', error_codes: [],
  auth_type: 'none', auth_config_json: '',
})

const kvColumns = [
  { key: 'key', label: 'Key', width: '200' },
  { key: 'type', label: '类型', width: '100', type: 'select', options: ['string','number','integer','boolean','object','array'] },
  { key: 'value', label: '示例值', width: '200' },
  { key: 'required', label: '必填', width: '80', type: 'checkbox' },
  { key: 'default', label: '默认值', width: '200' },
  { key: 'desc', label: '描述' },
  { key: 'validation', label: '校验规则', width: '180' },
]

/** Form Data 专用列配置，比 kvColumns 多 file 类型 */
const formDataColumns = [  { key: 'key', label: 'Key', width: '200' },
  { key: 'type', label: '类型', width: '100', type: 'select', options: ['string','number','integer','boolean','object','array','file'] },
  { key: 'value', label: '示例值', width: '200' },
  { key: 'required', label: '必填', width: '80', type: 'checkbox' },
  { key: 'default', label: '默认值', width: '200' },
  { key: 'desc', label: '描述' },
  { key: 'validation', label: '校验规则', width: '180' },
]

function addKeyValue(target) { form[target].push({ key: '', type: 'string', value: '', required: false, default: '', desc: '', validation: '' }) }
function addErrorCode() { form.error_codes.push({ code: '', message: '', desc: '' }) }

function onForceBodyChange(val) {
  if (val) {
    ElMessage.warning('已启用强制发送请求体，请谨慎使用')
  }
}

function onAuthTypeChange(type) {
  const presets = {
    basic: { type: 'basic', username: '', password: '' },
    token: { type: 'bearer', token: '' },
    oauth2: { grant_type: 'client_credentials', client_id: '', client_secret: '' },
  }
  if (presets[type]) form.auth_config_json = JSON.stringify(presets[type], null, 2)
}

/** 从环境预设请求头填充到表单 */
async function applyEnvHeaders() {
  if (!environments.value.length) {
    ElMessage.info('该项目暂无关联环境，请先在环境管理中添加')
    return
  }

  // 选择环境
  let envId = envSelectedId.value
  if (!envId) {
    ElMessage.info('请先在上方选择一个环境')
    return
  }

  const env = environments.value.find(e => e.id === envId)
  if (!env) return

  const rawHeaders = env.request_headers || []
  const headers = Array.isArray(rawHeaders) ? rawHeaders : []
  if (!headers.length) {
    ElMessage.info(`环境 "${env.name}" 没有预设请求头`)
    return
  }

  // 现有 key 集合
  const existingKeys = new Set(form.headers.filter(h => h.key).map(h => h.key.toLowerCase()))

  // 如果已有请求头，确认是否覆盖
  let mode = 'merge'
  if (existingKeys.size > 0) {
    try {
      mode = await ElMessageBox.confirm(
        '当前表单已有请求头，请选择填充方式：',
        '填充预设请求头',
        {
          confirmButtonText: '覆盖已有',
          cancelButtonText: '仅补充缺失',
          distinguishCancelAndClose: true,
          type: 'info',
        }
      ).then(() => 'overwrite').catch((action) => {
        if (action === 'cancel') return 'merge'
        throw action  // 关闭弹窗 → 取消操作
      })
    } catch { return }
  }

  const added = []
  const overwritten = []

  for (const h of headers) {
    if (!h.key) continue
    const keyLower = h.key.toLowerCase()
    const idx = form.headers.findIndex(fh => fh.key && fh.key.toLowerCase() === keyLower)
    const entry = {
      key: h.key,
      type: h.type || 'string',
      value: h.value || '',
      required: !!h.required,
      default: h.default || '',
      desc: h.description || h.desc || '',
      validation: h.validation || '',
    }

    if (idx >= 0) {
      if (mode === 'overwrite') {
        form.headers[idx] = entry
        overwritten.push(h.key)
      }
    } else {
      form.headers.push(entry)
      added.push(h.key)
    }
  }

  const parts = []
  if (added.length) parts.push(`补充 ${added.length} 个`)
  if (overwritten.length) parts.push(`覆盖 ${overwritten.length} 个`)
  ElMessage.success(`已从环境 "${env.name}" ${parts.join('、')}`)
}

// 加载编辑数据
onMounted(async () => {
  if (!store.currentProjectId) await store.fetchProjects()
  loading.value = true
  if (isEdit.value) {
    try {
      // 使用详情接口 /api/api-assets/{id}/
      const resp = await fetch(`/api/v1/api-assets/${assetId.value}/`, {
        headers: { 'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '' }
      })
      const asset = await resp.json()
      if (asset && asset.id) fillForm(asset)
      else throw new Error('接口不存在')
    } catch (e) { errorMsg.value = '加载失败: ' + (e?.message || '') }
  }
  loading.value = false
  if (!isEdit.value && store.currentGroupId) form.group = store.currentGroupId

  // 加载环境预设请求头
  if (store.platformProjectId) {
    try {
      const envData = await environmentApi.list({ project: store.platformProjectId, page_size: 100 })
      environments.value = envData.results || envData || []
      if (environments.value.length) envSelectedId.value = environments.value[0].id
    } catch (e) {
      console.warn('[AssetFormPage] 加载环境列表失败', e)
    }
  }
})

function fillForm(asset) {
  assetData.value = asset
  // 基础字段
  form.name = asset.name || ''
  form.method = asset.method || 'GET'
  form.url = asset.url || ''
  form.group = asset.group || (asset.group_id !== undefined ? asset.group_id : null)
  form.status = asset.status || 'draft'
  form.source = asset.source || ''
  form.external_id = asset.external_id || ''
  form.interface_desc = asset.interface_desc || ''
  form.required = asset.required || false
  form.param_type = asset.param_type || 'string'
  form.sort = asset.sort || 0

  // 请求�? API字段 request_headers �?内部字段 headers
  // 兼容 dict 格式（{"key": "value"}）和 array 格式（[{key, value, ...}]）
  const rawHeaders = asset.request_headers || asset.headers || []
  form.headers = Array.isArray(rawHeaders) ? rawHeaders.map(h => ({ key: h.key || '', type: h.type || 'string', value: h.value || '', required: !!h.required, default: h.default || '', desc: h.desc || h.description || '', validation: h.validation || '' })) : (typeof rawHeaders === 'object' && rawHeaders !== null ? Object.entries(rawHeaders).map(([key, value]) => ({ key, type: 'string', value: String(value ?? ''), required: false, default: '', desc: '', validation: '' })) : [])

  // 请求参数: API字段 request_params → 内部字段 params
  // 兼容 dict 格式（{"key": "value"}）和 array 格式（[{key, type, value, ...}]）
  let rawParams = asset.request_params || asset.params || []
  form.params = Array.isArray(rawParams) ? rawParams.map(p => ({ key: p.key || '', type: p.type || 'string', value: p.value || '', required: !!p.required, default: p.default || '', desc: p.desc || p.description || '', validation: p.validation || '' })) : (typeof rawParams === 'object' && rawParams !== null ? Object.entries(rawParams).map(([key, value]) => ({ key, type: 'string', value: String(value ?? ''), required: false, default: '', desc: '', validation: '' })) : [])

  // 请求体
  form.request_body_format = asset.request_body_format || 'json'
  const rawBody = asset.request_body || asset.body
  if (form.request_body_format === 'form-data') {
    form.request_body_json = ''
    if (Array.isArray(rawBody)) {
      form.form_data = rawBody.map(f => ({ key: f.key || '', type: f.type || 'string', value: f.value || '', required: !!f.required, default: f.default || '', desc: f.desc || '', validation: f.validation || '' }))
    } else if (rawBody && typeof rawBody === 'object') {
      // dict 格式 { fieldName: { type, value, required, desc, ... } }，兼容 OpenAPI 导入数据
      // 同时填充 JSON 内容，方便用户切换到 JSON 标签查看/编辑
      form.request_body_json = JSON.stringify(rawBody, null, 2)
      form.form_data = Object.entries(rawBody).map(([key, val]) => {
        const isObj = val && typeof val === 'object' && !Array.isArray(val)
        return {
          key: key || '',
          type: isObj ? (val.type || 'string') : 'string',
          value: isObj ? (String(val.value ?? '')) : String(val ?? ''),
          required: !!(isObj && val.required),
          default: isObj ? (val.default || '') : '',
          desc: isObj ? (val.desc || val.description || '') : '',
          validation: isObj ? (val.validation || '') : '',
        }
      })
    } else {
      form.form_data = []
    }
  } else {
    form.request_body_json = typeof rawBody === 'object' && rawBody !== null ? JSON.stringify(rawBody, null, 2) : (typeof rawBody === 'string' ? rawBody : '')
    form.form_data = []
  }

  // 响应 & 错误码
  const rawSchema = asset.response_schema || asset.response_schema_json
  form.response_schema_json = typeof rawSchema === 'object' && rawSchema !== null ? JSON.stringify(rawSchema, null, 2) : (typeof rawSchema === 'string' ? rawSchema : '')
  form.error_codes = Array.isArray(asset.error_code || asset.error_codes) ? (asset.error_code || asset.error_codes).map(e => ({ code: e.code || '', message: e.message || '', desc: e.desc || e.description || '' })) : []

  // 鉴权
  form.auth_type = asset.auth_type || asset.auth_config?.type || 'none'
  const rawAuth = asset.auth_config
  form.auth_config_json = typeof rawAuth === 'object' && rawAuth !== null ? JSON.stringify(rawAuth, null, 2) : (typeof rawAuth === 'string' ? rawAuth : '')
}

// 辅助：去除URL中的查询参数部分
function cleanUrl(url) {
  try {
    const u = new URL(url, 'http://localhost')
    return u.pathname + (u.hash || '')
  } catch { return url }
}
// 辅助：合并URL中的参数到params数组
function mergeParams(url, params) {
  const result = [...params]
  try {
    const u = new URL(url, 'http://localhost')
    const existingKeys = new Set(params.map(p => p.key))
    u.searchParams.forEach((value, key) => {
      if (!existingKeys.has(key)) result.push({ key, value })
    })
  } catch { /* ignore */ }
  return result
}

function isBodyNotEmpty() {
  if (form.request_body_format === 'json') {
    const val = (form.request_body_json || '').trim()
    if (!val) return false
    // 空对象 {} 不算有内容
    if (val === '{}' || val === '[]') return false
    try { const obj = JSON.parse(val); return obj && (typeof obj === 'object' ? Object.keys(obj).length > 0 : true) }
    catch { return true }  // 非JSON字符串也算有内容
  }
  return form.form_data.some(f => f.key)
}

async function handleSubmit() {
  if (!form.name.trim()) { errorMsg.value = '请输入接口名称'; return }
  if (!form.url.trim()) { errorMsg.value = '请输入请求URL'; return }

  // 请求方法与Body兼容性校验
  const hasBody = isBodyNotEmpty()
  if (!forceBody.value && methodsWithoutBody.includes(form.method) && hasBody) {
    errorMsg.value = `当前请求方式 ${form.method} 不支持请求体。请切换为 POST/PUT/PATCH，或勾选"强制发送请求体"（不推荐）`
    return
  }

  const payload = {
    project: store.currentProjectId,
    group: form.group || null,
    name: form.name.trim(),
    method: form.method,
    url: cleanUrl(form.url.trim()),   // 去除URL中的查询参数
    status: form.status,
    source: form.source,
    external_id: form.external_id,
    interface_desc: form.interface_desc,
    required: form.required,
    param_type: form.param_type,
    sort: form.sort,
    // 使用API期望的字段名
    request_headers: form.headers.filter(h => h.key),
    request_params: mergeParams(form.url.trim(), form.params.filter(p => p.key)),
    request_body_format: form.request_body_format,
    request_body: form.request_body_format === 'json'
      ? (form.request_body_json || '{}')
      : form.form_data.filter(f => f.key),
    response_schema: form.response_schema_json || '',
    error_code: form.error_codes.filter(e => e.code),
    auth_config: form.auth_config_json || '',
  }

  submitting.value = true; errorMsg.value = ''
  try {
    if (isEdit.value) {
      await apiAssetApi.update(assetId.value, payload)
    } else {
      await apiAssetApi.create(payload)
    }
    ElMessage.success(isEdit.value ? '保存成功' : '创建成功')
    router.push('/api-assets')
  } catch (e) {
    const msg = typeof e?.data === 'object' ? (e.data.detail || Object.values(e.data)[0]?.[0]) : (e?.message || '操作失败')
    errorMsg.value = String(msg)
  } finally { submitting.value = false }
}

function handleAiGenerate() {
  store.setAISelectedAssets([assetData.value])
  showAiModal.value = true
}
</script>

<style scoped>
.form-page { padding: 16px 24px 40px; }

/* ---- 页面标题 ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}
.page-header-left { display: flex; align-items: center; gap: 12px; }
.page-title { font-size: 22px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.page-header-right { display: flex; gap: 8px; align-items: center; }
.section-card { margin-bottom: 20px; }
.section-card :deep(.el-card__header) { padding: 14px 20px; }
.section-card :deep(.el-card__body) { padding: 20px 20px 16px; }
.section-card :deep(.el-table th) { white-space: nowrap !important; word-break: keep-all !important; }
.section-title { font-weight: 600; font-size: 14px; }
.sub-section { margin-bottom: 4px; }
.sub-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.sub-header-actions { display: flex; align-items: center; gap: 4px; }
.sub-title { font-weight: 500; font-size: 13px; color: #606266; }
.error-bar { margin-bottom: 16px; }
.text-hint { font-size: 12px; color: #c0c4cc; display: flex; align-items: center; height: 100%; padding-top: 28px; }
.help-icon { color: #c0c4cc; cursor: help; font-size: 14px; margin-left: 2px; }
.help-icon:hover { color: #409eff; }
.disabled { opacity: 0.5; pointer-events: none; }
.disabled .el-alert,
.disabled .el-alert * { pointer-events: auto; opacity: 1; }
</style>
