import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { modelProviderApi } from '../api/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const TYPE_LABELS = { openai: 'OpenAI 兼容', zhipu: '智谱 AI', deepseek: 'DeepSeek', custom: '自定义' }

const DEFAULT_TEMPLATE = [
  '请根据以下接口信息和测试规则，生成{casetype_desc}类型的测试用例。',
  '',
  '【接口基本信息】',
  '接口名称：{api_name}',
  '接口描述：{api_desc}',
  '请求方法：{method}',
  '请求URL：{url}',
  '认证方式：{auth_config}',
  '',
  '【请求参数】',
  'Query/Path参数：{params}',
  '',
  '【请求体】',
  '类型：{body_format}',
  '结构：{request_body}',
  '',
  '【响应结构】',
  '{response_schema}',
  '',
  '【错误码】',
  '{error_codes}',
  '',
  '【测试规则】',
  '{rules_text}',
  '',
  '【生成要求】',
  '1. 每个用例包含：name, request_method, request_url, request_headers, request_body, expected_status_code, validation_rules',
  '2. 覆盖所有规则类别',
  '3. 以纯 JSON 数组格式返回，不要包含任何 markdown 标记或其他文本',
].join('\n')

export const useModelProviderStore = defineStore('modelProvider', () => {
  const providers = ref([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const loading = ref(false)

  // 筛选
  const keyword = ref('')
  const filterType = ref('')
  const filterEnabled = ref('')

  // 模态框
  const modalVisible = ref(false)
  const modalTitle = ref('新增供应商')
  const editingId = ref(null)
  const formData = ref({
    name: '', provider_type: 'openai',
    base_url: '', api_path: '/chat/completions', api_key: '', model_name: '',
    system_prompt: '你是一个专业的API测试工程师，擅长根据接口定义生成全面的测试用例。',
    prompt_template: DEFAULT_TEMPLATE,
    response_cases_path: 'choices.0.message.content',
    temperature: 0.7, max_tokens: 4096,
    timeout: 180,
    is_enabled: true, is_default: false,
  })
  const saving = ref(false)

  // 测试连接
  const testing = ref(false)
  const testResult = ref(null)

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  // ---- 加载 ----
  async function loadProviders(page = 1) {
    loading.value = true; currentPage.value = page
    try {
      const params = { page, page_size: pageSize.value }
      if (keyword.value) params.keyword = keyword.value
      if (filterType.value) params.provider_type = filterType.value
      if (filterEnabled.value) params.is_enabled = filterEnabled.value
      const resp = await modelProviderApi.list(params)
      providers.value = resp.results || resp
      total.value = resp.count || 0
    } catch (err) { ElMessage.error('加载失败：' + err.message) }
    finally { loading.value = false }
  }

  // ---- CRUD ----
  function openCreate() {
    modalTitle.value = '新增供应商'; editingId.value = null; testResult.value = null
    formData.value = {
      name: '', provider_type: 'openai',
      base_url: '', api_path: '/chat/completions', api_key: '', model_name: '',
      system_prompt: '你是一个专业的API测试工程师，擅长根据接口定义生成全面的测试用例。',
      prompt_template: DEFAULT_TEMPLATE,
      response_cases_path: 'choices.0.message.content',
      temperature: 0.7, max_tokens: 4096,
      timeout: 180,
      is_enabled: true, is_default: false,
    }
    modalVisible.value = true
  }

  async function openEdit(id) {
    try {
      const data = await modelProviderApi.get(id)
      modalTitle.value = '编辑供应商'; editingId.value = data.id; testResult.value = null
      formData.value = {
        name: data.name, provider_type: data.provider_type,
        base_url: data.base_url, api_path: data.api_path, api_key: data.api_key,
        model_name: data.model_name,
        system_prompt: data.system_prompt || '',
        prompt_template: data.prompt_template || '',
        response_cases_path: data.response_cases_path || 'choices.0.message.content',
        temperature: data.temperature ?? 0.7, max_tokens: data.max_tokens ?? 4096,
        timeout: data.timeout ?? 180,
        is_enabled: data.is_enabled, is_default: data.is_default,
      }
      modalVisible.value = true
    } catch (err) { ElMessage.error('加载失败：' + err.message) }
  }

  async function save() {
    if (!formData.value.name.trim()) { ElMessage.warning('名称不能为空'); return }
    if (!formData.value.base_url.trim()) { ElMessage.warning('API地址不能为空'); return }
    if (!formData.value.model_name.trim()) { ElMessage.warning('模型名称不能为空'); return }

    saving.value = true
    try {
      const data = { ...formData.value, name: formData.value.name.trim(), base_url: formData.value.base_url.trim(), api_key: formData.value.api_key.trim(), model_name: formData.value.model_name.trim() }
      if (editingId.value) { await modelProviderApi.update(editingId.value, data); ElMessage.success('更新成功') }
      else { await modelProviderApi.create(data); ElMessage.success('创建成功') }
      modalVisible.value = false
      await loadProviders(currentPage.value)
    } catch (err) {
      const errors = err.data
      let msg = '保存失败：'
      if (errors && typeof errors === 'object' && !Array.isArray(errors)) {
        msg += Object.entries(errors).map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join('; ') : msgs}`).join('; ')
      } else {
        msg += errors ? Object.values(errors).flat().join('; ') : err.message
      }
      ElMessage.error(msg)
    } finally { saving.value = false }
  }

  async function remove(id, name) {
    try {
      await ElMessageBox.confirm(`确定删除「${name}」吗？`, '确认删除', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
      await modelProviderApi.remove(id)
      ElMessage.success('删除成功')
      if (providers.value.length <= 1 && currentPage.value > 1) await loadProviders(currentPage.value - 1)
      else await loadProviders(currentPage.value)
    } catch (err) { if (err !== 'cancel') ElMessage.error('删除失败：' + err.message) }
  }

  async function setDefault(id) {
    try {
      await ElMessageBox.confirm('确定设为默认供应商？', '确认', { type: 'warning' })
      await modelProviderApi.setDefault(id)
      ElMessage.success('已设为默认')
      await loadProviders(currentPage.value)
    } catch (err) { if (err !== 'cancel') ElMessage.error('设置失败：' + err.message) }
  }

  // ---- 测试连接 ----
  async function testConnection(id) {
    testing.value = true; testResult.value = null
    try {
      const r = await modelProviderApi.test(id)
      testResult.value = r.success ? { type: 'success', msg: r.message, preview: r.cases_preview } : { type: 'error', msg: r.message }
    } catch (err) { testResult.value = { type: 'error', msg: err.message } }
    finally { testing.value = false }
  }

  function typeLabel(t) { return TYPE_LABELS[t] || t }

  return {
    providers, total, currentPage, pageSize, loading, totalPages,
    keyword, filterType, filterEnabled,
    modalVisible, modalTitle, editingId, formData, saving,
    testing, testResult,
    loadProviders, openCreate, openEdit, save, remove, setDefault, testConnection,
    typeLabel, DEFAULT_TEMPLATE,
  }
})
