<template>
  <el-dialog
    v-model="visible"
    title="AI批量生成测试用例"
    width="700px"
    :close-on-click-modal="false"
    @open="onOpen"
  >
    <!-- 选中接口 -->
    <div style="margin-bottom:14px">
      <el-text type="info" size="small">选中接口（{{ store.aiSelectedAssets.length }} 个）</el-text>
      <div class="asset-list-preview" style="max-height:180px;overflow-y:auto;border:1px solid #ebeef5;border-radius:6px;padding:8px;margin-top:6px">
        <div v-for="a in store.aiSelectedAssets" :key="a.id" class="asset-item">
          <strong>{{ a.name }}</strong>
          <el-tag size="small" style="margin-left:6px">{{ a.method }}</el-tag>
          <span class="url-text">{{ a.url }}</span>
        </div>
      </div>
    </div>

    <!-- AI模型选择 -->
    <div style="margin-bottom:14px">
      <el-text type="info" size="small">AI模型</el-text>
      <el-select
        v-model="selectedModelProviderId"
        placeholder="选择AI模型"
        style="width:100%;margin-top:6px"
        :loading="providersLoading"
      >
        <el-option
          v-for="p in store.aiModelProviders"
          :key="p.id"
          :label="p.name"
          :value="p.id"
        >
          <span>{{ p.name }}</span>
          <el-tag size="small" type="info" style="margin-left:6px">{{ providerTypeLabel(p.provider_type) }}</el-tag>
          <el-tag v-if="p.is_default" size="small" type="warning" style="margin-left:4px">默认</el-tag>
        </el-option>
      </el-select>
    </div>

    <!-- 用例类型 -->
    <div style="margin-bottom:14px">
      <el-text type="info" size="small">生成用例类型</el-text>
      <el-select
        v-model="selectedCaseType"
        placeholder="选择用例类型"
        style="width:100%;margin-top:6px"
      >
        <el-option
          v-for="ct in caseTypeOptions"
          :key="ct.value"
          :label="ct.label"
          :value="ct.value"
        />
      </el-select>
    </div>

    <!-- 提示词模板（仅显示"用例生成"分类） -->
    <div style="margin-bottom:14px">
      <el-text type="info" size="small"><span style="color:#f56c6c;margin-right:2px">*</span>提示词模板</el-text>
      <el-select
        v-model="selectedPromptTemplateId"
        placeholder="选择提示词模板"
        style="width:100%;margin-top:6px"
      >
        <el-option
          v-for="t in caseGenTemplates"
          :key="t.id"
          :label="t.name"
          :value="t.id"
        >
          <span>{{ t.name }}</span>
          <el-tag v-if="t.is_default" size="small" type="warning" style="margin-left:4px">默认</el-tag>
        </el-option>
      </el-select>
    </div>

    <!-- 规则选择 -->
    <div style="margin-bottom:14px">
      <el-text type="info" size="small">应用规则（可多选，不选则仅按默认规则生成）</el-text>
      <el-select
        v-model="selectedRuleIds"
        multiple
        placeholder="选择规则"
        style="width:100%;margin-top:6px"
        :loading="rulesLoading"
      >
        <el-option v-for="r in store.aiRules" :key="r.id" :label="`[${r.category_name||r.category}] ${r.name}`" :value="r.id" />
      </el-select>
    </div>

    <!-- 提交状态 -->
    <div v-if="submitted" class="result-msg">
      <el-alert title="已提交生成任务，请到 AI 生成记录查看进度" type="success" show-icon :closable="false" />
    </div>
    <div v-else-if="generating" class="generate-progress">
      <el-progress :percentage="100" :stroke-width="8" indeterminate />
      <el-text size="small">正在提交...</el-text>
    </div>

    <!-- 结果 -->
    <div v-if="resultMsg && !submitted" class="result-msg">
      <el-alert :title="resultMsg" :type="resultType" show-icon :closable="false" />
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="generating" @click="startGenerate" :disabled="store.aiSelectedAssets.length===0">
        <el-icon style="margin-right:4px"><MagicStick /></el-icon>开始生成
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { useApiAssetStore } from '../stores/apiAsset.js'
import { ElMessage } from 'element-plus'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue'])
const store = useApiAssetStore()

const visible = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

// 仅显示"用例生成"分类的模板（向后兼容）
const caseGenTemplates = computed(() => {
  return (store.aiPromptTemplates || []).filter(t => !t.category || t.category === 'test_case_gen')
})

const caseTypeOptions = [
  { value: 'api', label: '接口测试（通用）' },
  { value: 'param_validate', label: '参数校验' },
  { value: 'biz_logic', label: '业务逻辑' },
  { value: 'error_handle', label: '异常处理' },
  { value: 'boundary', label: '边界值' },
  { value: 'security', label: '安全' },
  { value: 'performance', label: '性能' },
]
const selectedRuleIds = ref([])
const selectedCaseType = ref('api')
const selectedPromptTemplateId = ref(null)
const selectedModelProviderId = ref(null)
const rulesLoading = ref(false)
const providersLoading = ref(false)
const generating = ref(false)
const submitted = ref(false)
const resultMsg = ref('')
const resultType = ref('success')

const PROVIDER_TYPE_LABELS = { openai: 'OpenAI', zhipu: '智谱AI', deepseek: 'DeepSeek', custom: '自定义' }
function providerTypeLabel(type) {
  return PROVIDER_TYPE_LABELS[type] || type
}

async function onOpen() {
  resultMsg.value = ''
  submitted.value = false
  selectedRuleIds.value = []
  selectedCaseType.value = 'api'
  selectedPromptTemplateId.value = null
  selectedModelProviderId.value = null
  if (store.aiRules.length === 0) {
    rulesLoading.value = true
    await store.fetchAIGenerationRules()
    rulesLoading.value = false
  }
  await store.fetchAIPromptTemplates()
  // 自动选中默认提示词模板
  const defaultTemplate = store.aiPromptTemplates.find(t => t.is_default)
  if (defaultTemplate) {
    selectedPromptTemplateId.value = defaultTemplate.id
  } else if (store.aiPromptTemplates.length > 0) {
    selectedPromptTemplateId.value = store.aiPromptTemplates[0].id
  }
  // 加载AI模型列表并自动选中默认模型
  providersLoading.value = true
  await store.fetchAIModelProviders()
  const defaultProvider = store.aiModelProviders.find(p => p.is_default)
  if (defaultProvider) {
    selectedModelProviderId.value = defaultProvider.id
  } else if (store.aiModelProviders.length > 0) {
    selectedModelProviderId.value = store.aiModelProviders[0].id
  }
  providersLoading.value = false
}

async function startGenerate() {
  if (!selectedPromptTemplateId.value) {
    ElMessage.warning('请选择提示词模板')
    return
  }
  generating.value = true
  resultMsg.value = ''

  try {
    const result = await store.aiGenerateTestCases(
      selectedRuleIds.value,
      selectedCaseType.value,
      null,
      selectedPromptTemplateId.value,
      selectedModelProviderId.value,
    )
    submitted.value = true
    // 提示用户跳转查看
    setTimeout(() => {
      if (confirm('已提交生成任务，是否跳转到 AI 生成记录查看进度？')) {
        window.location.href = '/ai-generation-records/'
      }
    }, 500)
  } catch (e) {
    resultType.value = 'error'
    resultMsg.value = e?.message || '提交失败'
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.asset-item {
  padding: 4px 6px;
  border-radius: 4px;
  background: #f5f7fa;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.url-text {
  color: #909399;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
  margin-left: auto;
}
.generate-progress {
  margin-top: 14px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.result-msg {
  margin-top: 14px;
}
</style>
