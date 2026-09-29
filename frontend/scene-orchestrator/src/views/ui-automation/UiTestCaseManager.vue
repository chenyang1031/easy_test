<template>
  <div class="ui-test-case-manager">
    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索用例..." size="small" clearable style="width: 200px" @input="loadCases" />
      <el-select v-model="levelFilter" size="small" clearable placeholder="优先级" style="width: 100px" @change="loadCases">
        <el-option label="P0" value="P0" /><el-option label="P1" value="P1" />
        <el-option label="P2" value="P2" /><el-option label="P3" value="P3" />
      </el-select>
      <el-button type="primary" size="small" @click="openCreate">+ 新增用例</el-button>
      <el-button type="success" size="small" :disabled="!selected.length" @click="runWithEnvPicker(selected.map(c => c.id))">批量执行</el-button>
      <el-button type="danger" size="small" :disabled="!selected.length" @click="batchDelete">批量删除</el-button>
    </div>
    <el-table :data="cases" size="small" stripe v-loading="loading" empty-text="暂无用例" @selection-change="s => selected = s">
      <el-table-column type="selection" width="40" />
      <el-table-column prop="name" label="用例名称" min-width="180" />
      <el-table-column prop="level" label="级别" width="70" align="center">
        <template #default="{ row }">
          <el-tag :type="row.level === 'P0' ? 'danger' : row.level === 'P1' ? 'warning' : 'info'" size="small">{{ row.level }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <span :class="{ 'text-success': row.status === 'success', 'text-danger': row.status === 'failed' }">{{ { pending: '待处理', running: '执行中', success: '成功', failed: '失败' }[row.status] }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="step_count" label="步骤" width="60" align="center" />
      <el-table-column prop="module_name" label="模块" width="120" />
      <el-table-column prop="creator_name" label="创建者" width="80" />
      <el-table-column label="操作" width="240" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="success" @click="runWithEnvPicker([row.id])">执行</el-button>
          <el-button size="small" text type="warning" @click="openOrchestrate(row)">编排</el-button>
          <el-button size="small" text type="primary" @click="editCase(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteCase(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pagination" v-if="total > 0">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="p => { page = p; loadCases() }"
        @size-change="s => { pageSize = s; page = 1; loadCases() }"
      />
    </div>

    <el-dialog v-model="showDialog" :title="editing ? '编辑用例' : '新增用例'" width="600px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="级别">
          <el-select v-model="form.level" style="width: 100%"><el-option v-for="l in ['P0','P1','P2','P3']" :key="l" :label="l" :value="l" /></el-select>
        </el-form-item>
        <el-form-item label="模块">
          <el-tree-select
            v-model="form.module"
            :data="moduleTree"
            :props="{ label: 'name', value: 'id', children: 'children' }"
            check-strictly
            placeholder="选择所属模块"
            clearable
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
        <el-form-item label="前置SQL"><el-input v-model="form.front_sql" type="textarea" /></el-form-item>
        <el-form-item label="后置SQL"><el-input v-model="form.posterior_sql" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCase" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 步骤编排弹窗 -->
    <el-dialog v-model="orchVisible" :title="`步骤编排 - ${orchCase?.name || ''}`" width="760px" top="6vh" append-to-body>
      <div class="d-flex gap-2 mb-2">
        <el-select
          v-model="addStepId"
          size="small"
          filterable
          placeholder="选择要加入的页面步骤"
          style="flex: 1"
        >
          <el-option v-for="s in availableSteps" :key="s.id" :label="`${s.page_name || '未绑定页面'} / ${s.name}`" :value="s.id" />
        </el-select>
        <el-button size="small" type="primary" :disabled="!addStepId" @click="addOrchStep">加入</el-button>
        <el-button size="small" @click="loadPageSteps" :loading="stepsLoading">刷新</el-button>
      </div>
      <el-table :data="orchSteps" size="small" border empty-text="尚未编排任何步骤">
        <el-table-column label="顺序" width="60" align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column prop="page_step_name" label="页面步骤" min-width="180" />
        <el-table-column label="步骤切页" width="110" align="center">
          <template #default="{ row }">
            <el-checkbox v-model="row.switch_step_open_url" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="失败重试" width="100" align="center">
          <template #default="{ row }">
            <el-input-number v-model="row.error_retry" size="small" :min="0" :max="5" controls-position="right" style="width: 84px" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center">
          <template #default="{ $index }">
            <el-button size="small" text @click="moveOrch($index, -1)">↑</el-button>
            <el-button size="small" text @click="moveOrch($index, 1)">↓</el-button>
            <el-button size="small" text type="danger" @click="orchSteps.splice($index, 1)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <p class="text-muted small mt-2 mb-0">「步骤切页」勾选后执行到此步骤时会先导航到该步骤所属页面的 URL；执行开始时始终先打开环境 base_url。</p>
      <template #footer>
        <el-button @click="orchVisible = false">取消</el-button>
        <el-button type="primary" :loading="orchSaving" @click="saveOrchestration">保存编排</el-button>
      </template>
    </el-dialog>

    <!-- 执行环境选择弹窗 -->
    <el-dialog v-model="envPickerVisible" title="选择执行环境" width="520px" append-to-body>
      <el-select v-model="pickedEnvId" placeholder="选择环境配置" style="width: 100%" size="default">
        <el-option v-for="e in envs" :key="e.id" :label="`${e.name}${e.is_default ? '（默认）' : ''}`" :value="e.id" />
      </el-select>
      <p v-if="!envs.length" class="text-danger small mt-2 mb-0">当前项目还没有环境配置，请先到「环境配置」页签创建（需填写基础 URL、浏览器等）。</p>

      <!-- 批量执行时可把当前用例集合固化为定时任务，之后按计划自动重跑 -->
      <el-divider v-if="pendingRunIds.length > 1" class="my-3" />
      <template v-if="pendingRunIds.length > 1">
        <div class="d-flex align-items-center gap-2">
          <el-switch v-model="alsoCreateSchedule" />
          <span class="small">同时创建为定时任务（共 {{ pendingRunIds.length }} 个用例）</span>
        </div>
        <template v-if="alsoCreateSchedule">
          <el-input v-model="scheduleForm.name" size="small" class="mt-2" placeholder="任务名称">
            <template #append>
              <el-button @click="scheduleForm.name = defaultScheduleName()">默认名</el-button>
            </template>
          </el-input>
          <div class="d-flex gap-2 mt-2">
            <el-select v-model="scheduleForm.trigger_type" size="small" style="width: 130px">
              <el-option label="Cron表达式" value="cron" />
              <el-option label="固定间隔" value="interval" />
              <el-option label="单次执行" value="once" />
            </el-select>
            <el-input v-if="scheduleForm.trigger_type === 'cron'" v-model="scheduleForm.cron_expression"
                      size="small" placeholder="分 时 日 月 周，如 0 2 * * *（每天2点）" />
            <el-input v-else-if="scheduleForm.trigger_type === 'interval'" v-model.number="scheduleForm.interval_seconds"
                      size="small" type="number" placeholder="间隔秒数，如 3600" />
            <el-date-picker v-else v-model="scheduleForm.run_at" type="datetime" size="small"
                            placeholder="选择执行时间" style="width: 100%" />
          </div>
          <p class="text-muted small mt-1 mb-0">创建后可在「调度与监控 → 定时任务 → UI自动化」管理</p>
        </template>
      </template>
      <template #footer>
        <el-button @click="envPickerVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!envs.length || !pickedEnvId" :loading="running" @click="confirmRun">开始执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { uiTestCaseApi, uiTriggerApi, uiPageStepApi, uiCaseStepApi, uiEnvApi, uiScheduledTaskApi } from '../../api/uiAutomation'

const props = defineProps({
  projectId: [Number, String],
  moduleId: [Number, String],
  moduleTree: { type: Array, default: () => [] },
})
const emit = defineEmits(['refresh'])
const cases = ref([])
const loading = ref(false)
const search = ref('')
const levelFilter = ref('')
const selected = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const showDialog = ref(false)
const saving = ref(false)
const editing = ref(false)
const form = ref({ name: '', level: 'P2', description: '', front_sql: '', posterior_sql: '' })

async function loadCases() {
  loading.value = true
  try {
    const params = { project: props.projectId, page: page.value, page_size: pageSize.value }
    if (props.moduleId) params.module = props.moduleId
    if (search.value) params.search = search.value
    if (levelFilter.value) params.level = levelFilter.value
    const data = await uiTestCaseApi.list(params)
    cases.value = data.results || data || []
    total.value = data.count || cases.value.length
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function openCreate() {
  editing.value = false
  // 默认归到当前选中的模块，避免创建后按模块过滤时"消失"
  form.value = { name: '', level: 'P2', module: props.moduleId || '', description: '', front_sql: '', posterior_sql: '' }
  showDialog.value = true
}

function editCase(row) { editing.value = true; form.value = { ...row }; showDialog.value = true }

async function saveCase() {
  // 列表按模块过滤，未归属模块的用例选中模块后不可见——保存时规范化为 null 并提示
  const payload = { ...form.value }
  if (!payload.module && props.moduleId) payload.module = props.moduleId
  if (!payload.module) payload.module = null
  saving.value = true
  try {
    if (editing.value && form.value.id) { await uiTestCaseApi.update(form.value.id, payload) }
    else { await uiTestCaseApi.create({ ...payload, project: props.projectId }) }
    showDialog.value = false; editing.value = false
    form.value = { name: '', level: 'P2', module: '', description: '', front_sql: '', posterior_sql: '' }
    loadCases()
  } catch (e) {
    console.error(e)
    ElMessage.error(e.message || '保存用例失败')
  }
  finally { saving.value = false }
}

async function deleteCase(id) {
  if (!confirm('确定删除？')) return
  try { await uiTestCaseApi.delete(id); loadCases(); emit('refresh') } catch (e) { console.error(e) }
}

async function batchDelete() {
  if (!confirm(`确定删除 ${selected.value.length} 个用例？`)) return
  try {
    const ids = selected.value.map(c => c.id)
    await uiTestCaseApi.batchDelete(ids)
    loadCases(); emit('refresh')
  } catch (e) { console.error(e) }
}

// ---- 步骤编排 ----
const orchVisible = ref(false)
const orchCase = ref(null)
const orchSteps = ref([])
const availableSteps = ref([])
const stepsLoading = ref(false)
const orchSaving = ref(false)
const addStepId = ref(null)

async function loadPageSteps() {
  stepsLoading.value = true
  try {
    const data = await uiPageStepApi.list({ project: props.projectId })
    availableSteps.value = data.results || data || []
  } catch (e) { console.error(e) }
  finally { stepsLoading.value = false }
}

async function openOrchestrate(row) {
  orchCase.value = row
  orchSteps.value = []
  addStepId.value = null
  orchVisible.value = true
  await loadPageSteps()
  try {
    const data = await uiCaseStepApi.list({ test_case: row.id })
    orchSteps.value = (data.results || data || []).map(s => ({
      page_step: s.page_step,
      page_step_name: s.page_step_name,
      switch_step_open_url: !!s.switch_step_open_url,
      error_retry: s.error_retry || 0,
    }))
  } catch (e) { console.error(e) }
}

function addOrchStep() {
  const s = availableSteps.value.find(x => x.id === addStepId.value)
  if (!s) return
  if (orchSteps.value.some(x => x.page_step === s.id)) {
    ElMessage.warning('该步骤已在编排中')
    return
  }
  orchSteps.value.push({
    page_step: s.id,
    page_step_name: s.name,
    switch_step_open_url: false,
    error_retry: 0,
  })
  addStepId.value = null
}

function moveOrch(idx, dir) {
  const target = idx + dir
  if (target < 0 || target >= orchSteps.value.length) return
  const arr = orchSteps.value
  ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
}

async function saveOrchestration() {
  if (!orchCase.value) return
  orchSaving.value = true
  try {
    await uiCaseStepApi.batchUpdate({
      test_case: orchCase.value.id,
      steps: orchSteps.value.map((s, i) => ({
        page_step: s.page_step,
        case_sort: (i + 1) * 10,
        switch_step_open_url: !!s.switch_step_open_url,
        error_retry: s.error_retry || 0,
      })),
    })
    ElMessage.success('编排已保存')
    orchVisible.value = false
    loadCases()
    emit('refresh')
  } catch (e) {
    ElMessage.error(e.message || '保存编排失败')
  } finally {
    orchSaving.value = false
  }
}

// ---- 执行（环境选择替代原生 prompt）----
const envPickerVisible = ref(false)
const envs = ref([])
const pickedEnvId = ref(null)
const running = ref(false)
const pendingRunIds = ref([])
const alsoCreateSchedule = ref(false)
const scheduleForm = ref({ name: '', trigger_type: 'cron', cron_expression: '0 2 * * *', interval_seconds: 3600, run_at: null })

function defaultScheduleName() {
  const d = new Date()
  const pad = n => String(n).padStart(2, '0')
  return `UI批量-${pendingRunIds.value.length}用例-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`
}

async function createScheduleFromSelection() {
  const f = scheduleForm.value
  if (!f.name.trim()) { ElMessage.warning('请填写定时任务名称'); return false }
  if (f.trigger_type === 'cron' && !f.cron_expression.trim()) { ElMessage.warning('请填写Cron表达式'); return false }
  if (f.trigger_type === 'interval' && (!f.interval_seconds || f.interval_seconds < 30)) { ElMessage.warning('间隔秒数需不小于30'); return false }
  if (f.trigger_type === 'once' && !f.run_at) { ElMessage.warning('请选择单次执行时间'); return false }
  const payload = {
    project: Number(props.projectId),
    name: f.name.trim(),
    task_type: 'test_case',
    trigger_type: f.trigger_type,
    test_cases: pendingRunIds.value,
    environment: pickedEnvId.value,
    is_active: true,
  }
  if (f.trigger_type === 'cron') payload.cron_expression = f.cron_expression.trim()
  if (f.trigger_type === 'interval') payload.interval_seconds = Number(f.interval_seconds)
  if (f.trigger_type === 'once') payload.run_at = f.run_at.toISOString ? f.run_at.toISOString() : f.run_at
  await uiScheduledTaskApi.create(payload)
  ElMessage.success(`定时任务「${payload.name}」已创建`)
  return true
}

async function runWithEnvPicker(ids) {
  pendingRunIds.value = ids
  pickedEnvId.value = null
  alsoCreateSchedule.value = false
  scheduleForm.value = { name: '', trigger_type: 'cron', cron_expression: '0 2 * * *', interval_seconds: 3600, run_at: null }
  try {
    const data = await uiEnvApi.list({ project: props.projectId })
    envs.value = data.results || data || []
    const def = envs.value.find(e => e.is_default)
    if (def) pickedEnvId.value = def.id
  } catch (e) { console.error(e) }
  envPickerVisible.value = true
}

async function confirmRun() {
  const ids = pendingRunIds.value
  running.value = true
  try {
    if (alsoCreateSchedule.value && ids.length > 1) {
      const ok = await createScheduleFromSelection()
      if (!ok) { running.value = false; return }
    }
    if (ids.length === 1) {
      const r = await uiTestCaseApi.run(ids[0], { environment: pickedEnvId.value })
      ElMessage.success(r.message || '执行已提交，请到「执行记录」查看进度')
    } else {
      const r = await uiTriggerApi.batch({ test_case_ids: ids, environment: pickedEnvId.value })
      ElMessage.success(r.message || '批量执行已提交')
    }
    envPickerVisible.value = false
    emit('refresh')
  } catch (e) {
    ElMessage.error('执行失败: ' + (e.message || '未知错误'))
  } finally {
    running.value = false
  }
}

watch(() => [props.projectId, props.moduleId], () => { page.value = 1; loadCases() })
onMounted(loadCases)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
.text-success { color: #10b981; }
.text-danger { color: #ef4444; }
</style>
