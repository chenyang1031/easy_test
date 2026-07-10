<template>
  <div class="tc-form-page" v-loading="loading">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="$router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2 class="page-title">
          <el-icon><EditPen /></el-icon>
          {{ isEdit ? '编辑测试用例' : '新建测试用例' }}
        </h2>
      </div>
    </div>

    <el-form ref="formRef" :model="form" label-width="100px" class="main-form">

      <!-- ===== 基础信息 ===== -->
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="section-header">
            <el-icon color="#409eff"><InfoFilled /></el-icon>
            <span>基础信息</span>
          </div>
        </template>

        <!-- 用例名称 · 整行 -->
        <el-form-item label="用例名称" required class="form-row-full">
          <el-input v-model="form.name" placeholder="输入测试用例名称" maxlength="100" />
        </el-form-item>

        <!-- 所属项目 · 用例分组 · 1:1 -->
        <el-row :gutter="16" class="form-row-split">
          <el-col :xs="24" :sm="12" :md="12">
            <el-form-item label="所属项目">
              <el-select v-model="form.project" disabled style="width:100%">
                <el-option v-for="p in projectStore.projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="12">
            <el-form-item label="用例分组">
              <el-select v-model="form.group" clearable placeholder="选择分组（可选）" style="width:100%">
                <el-option v-for="g in groupStore.flatList" :key="g.id" :label="g.name" :value="g.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 超时时间 · 描述 · 3:7 -->
        <el-row :gutter="16" class="form-row-split">
          <el-col :xs="24" :sm="7" :md="7">
            <el-form-item label="超时时间" class="form-item-timeout">
              <el-input-number
                v-model="form.timeout"
                :min="1" :step="1" :max="60"
                controls-position="right" style="width:100%"
              />
              <span class="timeout-unit">秒</span>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="17" :md="17">
            <el-form-item label="描述信息">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选，测试用例的描述说明..." />
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>

      <!-- ===== 请求配置 ===== -->
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="section-header">
            <el-icon color="#67c23a"><Connection /></el-icon>
            <span>请求配置</span>
          </div>
        </template>

        <!-- 请求方式 15% · 请求地址 85% -->
        <div class="request-bar">
          <div class="request-method" style="width:15%;flex-shrink:0;">
            <el-form-item label="请求方式">
              <el-select v-model="form.request_method" style="width:100%">
                <el-option v-for="m in methods" :key="m" :label="m" :value="m">
                  <span class="method-option">
                    <span class="method-dot" :class="`dot-${m.toLowerCase()}`"></span>
                    <span>{{ m }}</span>
                  </span>
                </el-option>
              </el-select>
            </el-form-item>
          </div>
          <div class="request-url" style="flex:1;min-width:0;">
            <el-form-item label="请求地址">
              <el-input v-model="form.request_url" placeholder="https://api.example.com/v1/endpoint">
                <template #prepend>
                  <span class="url-method-tag" :class="`tag-${form.request_method.toLowerCase()}`">{{ form.request_method }}</span>
                </template>
              </el-input>
            </el-form-item>
          </div>
        </div>

        <!-- 预期状态码 · 紧凑行 -->
        <div class="status-bar">
          <el-form-item label="预期状态码" class="form-item-status">
            <el-input-number v-model="form.expected_status_code" :min="100" :max="599" controls-position="right" style="width:160px" />
          </el-form-item>
        </div>

        <!-- 折叠面板 · 满宽 -->
        <el-collapse v-model="activeEditors" class="request-editors">

          <el-collapse-item name="headers">
            <template #title>
              <div class="collapse-title">
                <el-icon color="#909399"><Tickets /></el-icon>
                <span>请求头</span>
                <el-tag v-if="checkedCount(form.request_headers)" size="small" round>{{ checkedCount(form.request_headers) }}</el-tag>
              </div>
            </template>
            <HeadersEditor v-model="form.request_headers" />
          </el-collapse-item>

          <el-collapse-item name="params">
            <template #title>
              <div class="collapse-title">
                <el-icon color="#909399"><List /></el-icon>
                <span>请求参数</span>
                <el-tag v-if="checkedCount(form.request_params)" size="small" round>{{ checkedCount(form.request_params) }}</el-tag>
              </div>
            </template>
            <UrlParamsEditor v-model="form.request_params" />
          </el-collapse-item>

          <el-collapse-item name="body">
            <template #title>
              <div class="collapse-title">
                <el-icon color="#909399"><Document /></el-icon>
                <span>请求体</span>
              </div>
            </template>
            <div class="body-editor-wrap">
              <el-radio-group v-model="bodyFormat" class="body-format-switch" size="small">
                <el-radio-button value="json">JSON</el-radio-button>
                <el-radio-button value="form-data">Form Data</el-radio-button>
              </el-radio-group>
              <el-input
                v-if="bodyFormat==='json'"
                v-model="requestBodyJson"
                type="textarea" :rows="8"
                placeholder='{"key": "value"}'
                class="json-editor"
              />
              <FormDataEditor v-else v-model="form.request_body" />
            </div>
          </el-collapse-item>

          <el-collapse-item name="validation">
            <template #title>
              <div class="collapse-title">
                <el-icon color="#909399"><Select /></el-icon>
                <span>断言</span>
                <el-tag v-if="checkedCount(form.validation_rules)" size="small" round>{{ checkedCount(form.validation_rules) }}</el-tag>
              </div>
            </template>
            <ValidationRulesEditor v-model="form.validation_rules" />
          </el-collapse-item>

          <el-collapse-item name="extract">
            <template #title>
              <div class="collapse-title">
                <el-icon color="#909399"><SetUp /></el-icon>
                <span>提取参数</span>
                <el-tag v-if="checkedCount(form.extract_params)" size="small" round>{{ checkedCount(form.extract_params) }}</el-tag>
              </div>
            </template>
            <ExtractParamsEditor v-model="form.extract_params" />
          </el-collapse-item>

        </el-collapse>
      </el-card>

      <!-- ===== 底部操作栏 ===== -->
      <div class="form-footer">
        <el-button size="large" @click="$router.back()">
          <el-icon><Close /></el-icon> 取消
        </el-button>
        <el-button size="large" type="primary" :loading="submitting" @click="submit">
          <el-icon><Check /></el-icon> {{ isEdit ? '保存修改' : '创建用例' }}
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, EditPen, InfoFilled, Connection, List, Tickets,
  Document, SetUp, Select, Close, Check
} from '@element-plus/icons-vue'
import { useProjectStore } from '../stores/project.js'
import { useTestCaseStore } from '../stores/testCase.js'
import { useTestCaseGroupStore } from '../stores/testCaseGroup.js'
import { testCaseApi } from '../api/index.js'
import UrlParamsEditor from '../components/testCase/UrlParamsEditor.vue'
import HeadersEditor from '../components/testCase/HeadersEditor.vue'
import FormDataEditor from '../components/testCase/FormDataEditor.vue'
import ExtractParamsEditor from '../components/testCase/ExtractParamsEditor.vue'
import ValidationRulesEditor from '../components/testCase/ValidationRulesEditor.vue'

const props = defineProps({ id: [String, Number] })
const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const testCaseStore = useTestCaseStore()
const groupStore = useTestCaseGroupStore()

const loading = ref(false)
const submitting = ref(false)
const activeEditors = ref([])
const bodyFormat = ref('json')
const requestBodyJson = ref('{}')

const methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']

const form = reactive({
  name: '', project: null, group: null, description: '', timeout: 10,
  request_method: 'GET', request_url: '', expected_status_code: 200,
  request_params: [], request_headers: [], request_body: [],
  extract_params: [], validation_rules: [],
  request_body_format: 'json',
})

const isEdit = computed(() => !!props.id)

function checkedCount(arr) {
  if (!Array.isArray(arr)) return 0
  return arr.filter(r => r.checked !== false).length
}

onMounted(async () => {
  form.project = projectStore.currentProjectId
  if (form.project) groupStore.loadList(form.project)

  if (isEdit.value) {
    loading.value = true
    try {
      const data = await testCaseApi.get(props.id)
      Object.assign(form, {
        name: data.name, project: data.project, group: data.group,
        description: data.description || '', timeout: data.timeout ?? 10,
        request_method: data.request_method, request_url: data.request_url,
        expected_status_code: data.expected_status_code,
        request_params: normalizeKv(data.request_params),
        request_headers: normalizeKv(data.request_headers),
        extract_params: data.extract_params || [],
        validation_rules: normalizeValidationRules(data.validation_rules),
        request_body_format: data.request_body_format || 'json',
      })
      bodyFormat.value = data.request_body_format || 'json'
      if (bodyFormat.value === 'json') {
        requestBodyJson.value = JSON.stringify(data.request_body || {}, null, 2)
      } else {
        form.request_body = data.request_body || []
      }

      // 从 URL 查询字符串解析请求参数（当 request_params 为空时）
      if (form.request_url && form.request_params.length === 0) {
        const qIndex = form.request_url.indexOf('?')
        if (qIndex !== -1) {
          try {
            const qs = form.request_url.substring(qIndex + 1)
            const parsed = []
            for (const part of qs.split('&')) {
              const eq = part.indexOf('=')
              if (eq !== -1) {
                parsed.push({ key: decodeURIComponent(part.substring(0, eq)), value: decodeURIComponent(part.substring(eq + 1)), checked: true })
              } else if (part) {
                parsed.push({ key: decodeURIComponent(part), value: '', checked: true })
              }
            }
            if (parsed.length > 0) {
              form.request_params = parsed
              // 去掉 URL 中的 query string，后续由 mergeParamsToUrl 统一拼接
              form.request_url = form.request_url.substring(0, qIndex)
            }
          } catch (e) { /* 忽略 URL 解析错误 */ }
        }
      }
    } catch (e) { ElMessage.error('加载失败') } finally { loading.value = false }
  }

  const draftData = window.__AI_DRAFT_DATA__
  if (draftData) {
    form.name = draftData.name || form.name
    form.request_method = draftData.request_method || form.request_method
    form.request_url = draftData.request_url || form.request_url
    if (draftData.validation_rules) {
      form.validation_rules = normalizeValidationRules(draftData.validation_rules)
    }
  }
  // 用完即清理，避免再次进入时残留
  window.__AI_DRAFT_DATA__ = null
})

function normalizeKv(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  return Object.entries(data).map(([k, v]) => ({ key: k, value: v, checked: true }))
}

function normalizeValidationRules(rules) {
  if (!Array.isArray(rules)) return []
  return rules.map(r => {
    if (typeof r !== 'object' || r === null) return null
    // 原始数据库格式: {"eq": ["$.data.id", 200]} → 统一转内部格式
    const metaKeys = ['checked', 'enabled', 'on_failed', 'description']
    const keys = Object.keys(r).filter(k => !metaKeys.includes(k))
    if (keys.length === 1 && Array.isArray(r[keys[0]]) && r[keys[0]].length === 2) {
      return { comparator: keys[0], path: r[keys[0]][0], expected: r[keys[0]][1], enabled: r.enabled !== false, description: '', on_failed: r.on_failed || 'stop' }
    }
    // 已经是内部格式（comparator）或 AI 格式（comparator）或旧格式（validator legacy）
    const cmp = r.comparator || r.validator || ''
    const en = r.enabled !== undefined ? r.enabled : (r.checked !== undefined ? r.checked : true)
    return { comparator: cmp, path: r.path || '', expected: r.expected ?? '', enabled: en, description: r.description || '', on_failed: r.on_failed || 'stop' }
  }).filter(Boolean)
}

/**
 * 将 request_params 表格中勾选的键值对拼接到 URL 上。
 * TestCase 模型没有独立的 request_params 字段，参数需随 URL 一起保存。
 */
function mergeParamsToUrl(baseUrl, params) {
  const checked = params.filter(r => r.checked !== false && r.key)
  if (checked.length === 0) return baseUrl
  const qs = checked.map(p => `${encodeURIComponent(p.key)}=${encodeURIComponent(String(p.value))}`).join('&')
  const separator = baseUrl.includes('?') ? '&' : '?'
  return `${baseUrl}${separator}${qs}`
}

async function submit() {
  submitting.value = true
  try {
    const payload = {
      name: form.name,
      project: form.project,
      group: form.group || null,
      description: form.description,
      timeout: form.timeout,
      request_method: form.request_method,
      // 将请求参数拼入 URL，模型没有独立的 request_params 字段
      request_url: mergeParamsToUrl(form.request_url, form.request_params),
      expected_status_code: form.expected_status_code,
      request_headers: kvToObject(form.request_headers),
      request_body_format: bodyFormat.value,
      request_body: bodyFormat.value === 'json' ? JSON.parse(requestBodyJson.value || '{}') : form.request_body,
      validation_rules: buildValidationRules(form.validation_rules),
      extract_params: form.extract_params.filter(r => r.checked !== false),
    }

    if (isEdit.value) {
      await testCaseStore.update(props.id, payload)
      ElMessage.success('更新成功')
    } else {
      await testCaseStore.create(payload)
      ElMessage.success('创建成功')
    }
    router.back()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

function kvToObject(arr) {
  return arr.filter(r => r.checked !== false).reduce((acc, { key, value }) => { if (key) acc[key] = value; return acc }, {})
}

function buildValidationRules(arr) {
  return arr.filter(r => r.enabled !== false).map(r => {
    // 标准路径: {comparator, path, expected} → {"eq": ["$.path", expected]}
    if (r.comparator && r.path) return { [r.comparator]: [r.path, r.expected] }
    // legacy: validator 字段名兼容
    if (r.validator && r.path) return { [r.validator]: [r.path, r.expected] }
    // 兼容原始数据库格式: {"eq": ["$.data.id", 200]}
    const entries = Object.entries(r)
    if (entries.length === 1 && Array.isArray(entries[0][1]) && entries[0][1].length === 2) {
      return { [entries[0][0]]: entries[0][1] }
    }
    return null
  }).filter(Boolean)
}
</script>

<style scoped>
/* ==========================================
   页面容器 — 满宽铺满
   ========================================== */
.tc-form-page {
  width: 100%;
  box-sizing: border-box;
}

/* ==========================================
   页面标题
   ========================================== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 4px;
}
.back-btn {
  font-size: var(--el-font-size-base);
  color: #606266;
  padding: 6px 8px;
  transition: color .2s;
}
.back-btn:hover { color: #409eff; }
.page-title {
  font-size: var(--el-font-size-extra-large);
  font-weight: 600;
  color: #303133;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ==========================================
   表单卡片
   ========================================== */
.section-card {
  width: 100%;
  margin-bottom: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
}
.section-card :deep(.el-card__header) {
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
  border-radius: 8px 8px 0 0;
}
.section-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-card-title);
  font-weight: 600;
  color: #303133;
}

/* ==========================================
   表单项通用
   ========================================== */
.main-form :deep(.el-form-item) {
  margin-bottom: 16px;
}
.main-form :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}
.main-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}
.main-form :deep(.el-input-number) {
  width: 100%;
}

/* 整行 + 分割行共用间距 */
.form-row-full { margin-bottom: 16px; }
.form-row-split { margin-bottom: 12px; }

/* 超时 ms 单位 */
.form-item-timeout {
  display: flex;
  align-items: center;
}
.timeout-unit {
  font-size: var(--el-font-size-small);
  color: #909399;
  white-space: nowrap;
  margin-left: 8px;
  flex-shrink: 0;
}

/* ==========================================
   请求配置 — 方式 + URL 同行
   ========================================== */
.request-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}
.request-bar .el-form-item {
  margin-bottom: 0;
}
.request-method { min-width: 120px; }

.url-method-tag {
  display: inline-block;
  font-weight: 700;
  font-size: var(--el-font-size-small);
  min-width: 52px;
  text-align: center;
  letter-spacing: .5px;
}
.tag-get    { color: #67c23a; }
.tag-post   { color: #409eff; }
.tag-put    { color: #e6a23c; }
.tag-delete { color: #f56c6c; }
.tag-patch  { color: #909399; }

/* 方法下拉颜色点 */
.method-option { display: flex; align-items: center; gap: 8px; }
.method-dot {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}
.dot-get    { background: #67c23a; }
.dot-post   { background: #409eff; }
.dot-put    { background: #e6a23c; }
.dot-delete { background: #f56c6c; }
.dot-patch  { background: #909399; }

/* ==========================================
   预期状态码 — 紧凑行
   ========================================== */
.status-bar {
  margin-bottom: 8px;
}
.form-item-status {
  display: flex;
  align-items: center;
}

/* ==========================================
   请求详情折叠面板
   ========================================== */
.request-editors {
  width: 100%;
  border-top: 1px solid #ebeef5;
}
.request-editors :deep(.el-collapse-item__header) {
  height: 42px;
  padding: 0 8px;
  font-size: var(--el-font-size-base);
  font-weight: 500;
  color: #303133;
  background: transparent;
}
.request-editors :deep(.el-collapse-item__header:hover) {
  background: #f5f7fa;
}
.request-editors :deep(.el-collapse-item__wrap) {
  border: none;
}
.request-editors :deep(.el-collapse-item__content) {
  padding: 12px 4px 16px;
}

.collapse-title {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.collapse-title :deep(.el-tag) {
  margin-left: auto;
  border: none;
  background: #ecf5ff;
  color: #409eff;
}

/* ==========================================
   请求体编辑区
   ========================================== */
.body-editor-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.body-format-switch { align-self: flex-start; }
.json-editor :deep(textarea) {
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13.5px;
  line-height: 1.65;
}

/* ==========================================
   底部操作栏
   ========================================== */
.form-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 4px 0 32px;
  box-sizing: border-box;
}
</style>
