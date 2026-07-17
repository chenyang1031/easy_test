<template>
  <div class="ui-test-case-manager">
    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索用例..." size="small" clearable style="width: 200px" @input="loadCases" />
      <el-select v-model="levelFilter" size="small" clearable placeholder="优先级" style="width: 100px" @change="loadCases">
        <el-option label="P0" value="P0" /><el-option label="P1" value="P1" />
        <el-option label="P2" value="P2" /><el-option label="P3" value="P3" />
      </el-select>
      <el-button type="primary" size="small" @click="showDialog = true">+ 新增用例</el-button>
      <el-button type="success" size="small" :disabled="!selected.length" @click="batchRun">批量执行</el-button>
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
      <el-table-column label="操作" width="200" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="success" @click="runCase(row)">执行</el-button>
          <el-button size="small" text type="primary" @click="editCase(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteCase(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pagination" v-if="total > pageSize">
      <el-pagination :current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="p => { page = p; loadCases() }" />
    </div>

    <el-dialog v-model="showDialog" :title="editing ? '编辑用例' : '新增用例'" width="600px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="级别">
          <el-select v-model="form.level" style="width: 100%"><el-option v-for="l in ['P0','P1','P2','P3']" :key="l" :label="l" :value="l" /></el-select>
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
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { uiTestCaseApi, uiTriggerApi } from '../../api/uiAutomation'

const props = defineProps({ projectId: [Number, String], moduleId: [Number, String] })
const emit = defineEmits(['refresh'])
const cases = ref([])
const loading = ref(false)
const search = ref('')
const levelFilter = ref('')
const selected = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const showDialog = ref(false)
const saving = ref(false)
const editing = ref(false)
const form = ref({ name: '', level: 'P2', description: '', front_sql: '', posterior_sql: '' })

async function loadCases() {
  loading.value = true
  try {
    const params = { project: props.projectId, page: page.value }
    if (props.moduleId) params.module = props.moduleId
    if (search.value) params.search = search.value
    if (levelFilter.value) params.level = levelFilter.value
    const data = await uiTestCaseApi.list(params)
    cases.value = data.results || data || []
    total.value = data.count || cases.value.length
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function editCase(row) { editing.value = true; form.value = { ...row }; showDialog.value = true }

async function saveCase() {
  saving.value = true
  try {
    if (editing.value && form.value.id) { await uiTestCaseApi.update(form.value.id, form.value) }
    else { await uiTestCaseApi.create({ ...form.value, project: props.projectId, module: props.moduleId }) }
    showDialog.value = false; editing.value = false
    form.value = { name: '', level: 'P2', description: '', front_sql: '', posterior_sql: '' }
    loadCases()
  } catch (e) { console.error(e) }
  finally { saving.value = false }
}

async function deleteCase(id) {
  if (!confirm('确定删除？')) return
  try { await uiTestCaseApi.delete(id); loadCases(); emit('refresh') } catch (e) { console.error(e) }
}

async function runCase(row) {
  try {
    const env = prompt('请输入环境配置ID:', '1')
    if (!env) return
    const r = await uiTestCaseApi.run(row.id, { environment: parseInt(env) })
    alert(r.message || '执行已提交')
    emit('refresh')
  } catch (e) { alert('执行失败: ' + e.message) }
}

async function batchRun() {
  try {
    const env = prompt('请输入环境配置ID:', '1')
    if (!env) return
    const ids = selected.value.map(c => c.id)
    const r = await uiTriggerApi.batch({ test_case_ids: ids, environment: parseInt(env) })
    alert(r.message || '批量执行已提交')
    emit('refresh')
  } catch (e) { alert('批量执行失败: ' + e.message) }
}

async function batchDelete() {
  if (!confirm(`确定删除 ${selected.value.length} 个用例？`)) return
  try {
    const ids = selected.value.map(c => c.id)
    await uiTestCaseApi.batchDelete(ids)
    loadCases(); emit('refresh')
  } catch (e) { console.error(e) }
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
