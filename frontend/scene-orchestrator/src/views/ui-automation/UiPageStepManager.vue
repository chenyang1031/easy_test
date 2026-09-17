<template>
  <el-dialog
    :model-value="visible"
    :title="`页面步骤管理 - ${page?.name || ''}`"
    width="980px"
    top="4vh"
    append-to-body
    @update:model-value="v => emit('update:visible', v)"
  >
    <div class="step-layout">
      <!-- 左栏：步骤列表 -->
      <div class="step-list-pane card p-2">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <strong class="small">步骤列表</strong>
          <el-button size="small" type="primary" @click="createStep">+ 新建步骤</el-button>
        </div>
        <el-input v-model="newStepName" size="small" placeholder="新步骤名称，如：填充登录表单" class="mb-2" @keyup.enter="createStep" />
        <div v-if="stepLoading" class="text-muted small p-2">加载中...</div>
        <div v-else-if="!steps.length" class="text-muted small p-2">暂无步骤。页面步骤是可复用的操作序列，供测试用例编排引用。</div>
        <div
          v-for="s in steps"
          :key="s.id"
          class="step-item"
          :class="{ active: s.id === activeStepId }"
          @click="selectStep(s)"
        >
          <div class="d-flex justify-content-between align-items-center">
            <span class="step-name">{{ s.name }}</span>
            <el-button size="small" text type="danger" @click.stop="deleteStep(s)">删</el-button>
          </div>
          <span class="text-muted small">{{ s.detail_count || 0 }} 条明细</span>
        </div>
      </div>

      <!-- 右栏：明细编辑 -->
      <div class="detail-pane card p-2">
        <template v-if="activeStep">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong class="small">步骤明细：{{ activeStep.name }}</strong>
            <div>
              <el-button size="small" @click="addRow(0)">+ 元素操作</el-button>
              <el-button size="small" @click="addRow(1)">+ 断言</el-button>
            </div>
          </div>
          <div class="detail-table-wrap">
            <table class="table table-sm align-middle mb-1">
              <thead>
                <tr>
                  <th style="width:42px">#</th>
                  <th style="width:92px">类型</th>
                  <th style="width:150px">元素</th>
                  <th style="width:110px">操作</th>
                  <th>值</th>
                  <th style="width:96px">操作列</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(d, idx) in details" :key="idx">
                  <td class="text-muted small">{{ idx + 1 }}</td>
                  <td>
                    <span class="badge" :class="d.step_type === 1 ? 'bg-warning text-dark' : 'bg-primary'">
                      {{ d.step_type === 1 ? '断言' : '元素操作' }}
                    </span>
                  </td>
                  <td>
                    <el-select
                      v-if="d.step_type === 0 || ['assert_text', 'assert_visible', 'assert_enabled', 'assert_attribute'].includes(d.ope_key)"
                      :model-value="d.element"
                      size="small"
                      filterable
                      placeholder="选择元素"
                      style="width: 100%"
                      @update:model-value="v => d.element = v"
                    >
                      <el-option v-for="el in elements" :key="el.id" :label="el.name" :value="el.id" />
                    </el-select>
                    <span v-else class="text-muted small">-</span>
                  </td>
                  <td>
                    <el-select v-model="d.ope_key" size="small" style="width: 100%" @change="onOpeKeyChange(d)">
                      <el-option v-for="k in opsForType(d.step_type)" :key="k" :label="k" :value="k" />
                    </el-select>
                  </td>
                  <td>
                    <el-input
                      v-if="needValue(d)"
                      v-model="d.ope_value"
                      size="small"
                      :placeholder="valuePlaceholder(d)"
                    />
                    <span v-else class="text-muted small">-</span>
                  </td>
                  <td>
                    <el-button size="small" text @click="moveRow(idx, -1)">↑</el-button>
                    <el-button size="small" text @click="moveRow(idx, 1)">↓</el-button>
                    <el-button size="small" text type="danger" @click="details.splice(idx, 1)">删</el-button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="!details.length" class="text-muted small p-3 text-center">
              暂无明细。点击上方「+ 元素操作 / + 断言」添加。
            </div>
          </div>
          <div class="text-end">
            <el-button size="small" type="primary" :loading="savingDetails" @click="saveDetails">保存明细</el-button>
          </div>
          <p class="text-muted small mb-0 mt-1">
            提示：元素需先在「元素管理」中登记。填充值支持 <code>{{ '\{\{变量\}\}' }}</code> 占位符。
          </p>
        </template>
        <div v-else class="text-muted small p-3 text-center">左侧选择或新建一个步骤后编辑明细</div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { uiPageStepApi, uiPageStepDetailedApi, uiElementApi } from '../../api/uiAutomation'

const props = defineProps({
  visible: Boolean,
  page: { type: Object, default: null },
  projectId: [Number, String],
})
const emit = defineEmits(['update:visible', 'changed'])

const ELEMENT_OPS = ['fill', 'click', 'type', 'select', 'check', 'uncheck', 'hover', 'get_text', 'press_key', 'wait_visible', 'wait_hidden']
const ASSERT_OPS = ['assert_visible', 'assert_enabled', 'assert_text', 'assert_attribute']

function opsForType(stepType) {
  return stepType === 1 ? ASSERT_OPS : ELEMENT_OPS
}

const steps = ref([])
const stepLoading = ref(false)
const newStepName = ref('')
const activeStepId = ref(null)
const details = ref([])
const elements = ref([])
const savingDetails = ref(false)

const activeStep = computed(() => steps.value.find(s => s.id === activeStepId.value) || null)

async function loadSteps() {
  if (!props.page) return
  stepLoading.value = true
  try {
    // page_id：后端过滤参数（'page' 与 DRF 分页参数冲突）
    const data = await uiPageStepApi.list({ page_id: props.page.id })
    steps.value = data.results || data || []
  } catch (e) {
    console.error(e)
  } finally {
    stepLoading.value = false
  }
}

async function loadElements() {
  if (!props.page) return
  try {
    const data = await uiElementApi.list({ page_id: props.page.id })
    elements.value = data.results || data || []
  } catch (e) { console.error(e) }
}

watch(() => props.visible, (v) => {
  if (v) {
    activeStepId.value = null
    details.value = []
    newStepName.value = ''
    loadSteps()
    loadElements()
  }
})

async function createStep() {
  const name = newStepName.value.trim()
  if (!name) { ElMessage.warning('请输入步骤名称'); return }
  try {
    const created = await uiPageStepApi.create({
      project: props.projectId,
      page: props.page.id,
      name,
    })
    newStepName.value = ''
    await loadSteps()
    const target = steps.value.find(s => s.id === created.id)
    if (target) selectStep(target)
    emit('changed')
  } catch (e) {
    ElMessage.error(e.message || '创建步骤失败')
  }
}

async function deleteStep(s) {
  if (!confirm(`确定删除步骤「${s.name}」及其全部明细？引用它的测试用例也会失去该步骤。`)) return
  try {
    await uiPageStepApi.delete(s.id)
    if (activeStepId.value === s.id) { activeStepId.value = null; details.value = [] }
    await loadSteps()
    emit('changed')
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

async function selectStep(s) {
  activeStepId.value = s.id
  try {
    const data = await uiPageStepDetailedApi.list({ page_step: s.id })
    const rows = data.results || data || []
    details.value = rows.map(d => ({
      step_type: d.step_type,
      element: d.element || null,
      ope_key: d.ope_key || (d.step_type === 1 ? 'assert_visible' : 'fill'),
      ope_value: d.ope_value || '',
    }))
  } catch (e) {
    ElMessage.error(e.message || '加载明细失败')
  }
}

function addRow(stepType) {
  details.value.push({
    step_type: stepType,
    element: null,
    ope_key: stepType === 1 ? 'assert_visible' : 'fill',
    ope_value: '',
  })
}

function onOpeKeyChange(d) {
  // 切换操作后清掉不适用字段由渲染层处理，无需额外逻辑
}

function needValue(d) {
  if (d.step_type === 0) return !['check', 'uncheck', 'hover', 'wait_visible', 'wait_hidden'].includes(d.ope_key)
  return d.ope_key === 'assert_text' || d.ope_key === 'assert_attribute'
}

function valuePlaceholder(d) {
  if (d.step_type === 1) return d.ope_key === 'assert_attribute' ? '属性名=期望值' : '期望包含的文本'
  if (d.ope_key === 'press_key') return '如 Enter / Control+A'
  return '填充/输入的值，支持 {{变量}}'
}

function moveRow(idx, dir) {
  const target = idx + dir
  if (target < 0 || target >= details.value.length) return
  const arr = details.value
  ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
}

async function saveDetails() {
  if (!activeStep.value) return
  // 基本校验：元素操作必须有元素；需要值的操作必须填值
  for (let i = 0; i < details.value.length; i++) {
    const d = details.value[i]
    if (d.step_type === 0 && !d.element) { ElMessage.warning(`第 ${i + 1} 行缺少元素`); return }
    if (needValue(d) && !String(d.ope_value).trim()) { ElMessage.warning(`第 ${i + 1} 行缺少操作值`); return }
  }
  savingDetails.value = true
  try {
    await uiPageStepDetailedApi.batchUpdate({
      page_step: activeStep.value.id,
      details: details.value.map((d, i) => ({
        step_type: d.step_type,
        element: d.element || null,
        step_sort: (i + 1) * 10,
        ope_key: d.ope_key,
        ope_value: String(d.ope_value ?? ''),
      })),
    })
    ElMessage.success('明细已保存')
    await loadSteps()
    emit('changed')
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    savingDetails.value = false
  }
}
</script>

<style scoped>
.step-layout { display: flex; gap: 12px; min-height: 420px; }
.step-list-pane { width: 240px; flex-shrink: 0; border: 1px solid #ebeef5; border-radius: 6px; }
.detail-pane { flex: 1; border: 1px solid #ebeef5; border-radius: 6px; display: flex; flex-direction: column; }
.step-item {
  padding: 6px 8px; border: 1px solid #ebeef5; border-radius: 6px; margin-bottom: 6px;
  cursor: pointer; display: flex; flex-direction: column; gap: 2px;
}
.step-item:hover { border-color: #c6e2ff; background: #f5faff; }
.step-item.active { border-color: #409eff; background: #ecf5ff; }
.step-name { font-weight: 500; font-size: 13px; word-break: break-all; }
.detail-table-wrap { flex: 1; overflow: auto; max-height: 46vh; }
</style>
