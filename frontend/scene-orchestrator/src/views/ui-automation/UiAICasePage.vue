<template>
  <div class="ui-ai-case-page">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">AI 浏览器测试</h2>
        <span class="page-subtitle">自然语言驱动的智能浏览器自动化</span>
      </div>
      <div class="page-header-right">
        <el-select v-model="selectedProject" placeholder="选择项目" size="small" style="width: 200px" @change="loadCases">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-button type="primary" size="small" @click="showDialog = true">+ 新增AI用例</el-button>
      </div>
    </div>

    <el-table :data="cases" size="small" stripe v-loading="loading" empty-text="暂无AI用例">
      <el-table-column prop="name" label="用例名称" min-width="180" />
      <el-table-column prop="task_description" label="任务描述" min-width="300" show-overflow-tooltip />
      <el-table-column prop="creator_name" label="创建者" width="80" />
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN') }}</template>
      </el-table-column>
      <el-table-column label="操作" width="250" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="success" @click="runCase(row)">执行</el-button>
          <el-button size="small" text type="primary" @click="viewHistory(row)">历史</el-button>
          <el-button size="small" text type="warning" @click="editCase(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteCase(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="showDialog" :title="editing ? '编辑AI用例' : '新增AI用例'" width="600px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="用例名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="form.task_description" type="textarea" :rows="6" placeholder="用自然语言描述测试任务，例如：打开登录页面，输入用户名admin和密码123456，点击登录按钮，验证页面跳转到首页" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tagsStr" placeholder="标签用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCase" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 执行历史抽屉 -->
    <el-drawer v-model="showHistory" title="AI执行历史" size="700px">
      <el-table :data="historyRecords" size="small" stripe v-loading="historyLoading" empty-text="暂无执行记录">
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'passed' ? 'success' : row.status === 'failed' ? 'danger' : row.status === 'running' ? 'warning' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="token_cost" label="Token" width="80" />
        <el-table-column prop="duration" label="耗时" width="80">
          <template #default="{ row }">{{ row.duration?.toFixed(1) }}s</template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="viewReport(row)">报告</el-button>
            <el-button size="small" text type="danger" @click="stopExecution(row)" v-if="row.status === 'running'">停止</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { uiAICaseApi, uiAIExecutionApi } from '../../api/uiAutomation'
import { http } from '../../api/http'

const projects = ref([])
const selectedProject = ref(null)
const cases = ref([])
const loading = ref(false)
const showDialog = ref(false)
const saving = ref(false)
const editing = ref(false)
const form = ref({ name: '', task_description: '', tagsStr: '' })
const showHistory = ref(false)
const historyRecords = ref([])
const historyLoading = ref(false)
const currentCaseId = ref(null)

async function loadProjects() {
  try {
    const data = await http.get('/api/v1/projects/')
    projects.value = data.results || data || []
    if (projects.value.length && !selectedProject.value) selectedProject.value = projects.value[0].id
    loadCases()
  } catch (e) { console.error(e) }
}

async function loadCases() {
  if (!selectedProject.value) return
  loading.value = true
  try { const data = await uiAICaseApi.list({ project: selectedProject.value }); cases.value = data.results || data || [] }
  catch (e) { console.error(e) } finally { loading.value = false }
}

function editCase(row) {
  editing.value = true
  form.value = { ...row, tagsStr: Array.isArray(row.tags) ? row.tags.join(', ') : '' }
  showDialog.value = true
}

async function saveCase() {
  saving.value = true
  try {
    const payload = { name: form.value.name, task_description: form.value.task_description, tags: form.value.tagsStr.split(',').map(s => s.trim()).filter(Boolean) }
    if (editing.value && form.value.id) { await uiAICaseApi.update(form.value.id, payload) }
    else { await uiAICaseApi.create({ ...payload, project: selectedProject.value }) }
    showDialog.value = false; editing.value = false
    form.value = { name: '', task_description: '', tagsStr: '' }
    loadCases()
  } catch (e) { console.error(e) } finally { saving.value = false }
}

async function deleteCase(id) { if (!confirm('确定删除？')) return; try { await uiAICaseApi.delete(id); loadCases() } catch (e) { console.error(e) } }

async function runCase(row) {
  try { const r = await uiAICaseApi.run(row.id, {}); alert(r.message || 'AI执行已提交') }
  catch (e) { alert('执行失败: ' + e.message) }
}

async function viewHistory(row) {
  currentCaseId.value = row.id; showHistory.value = true; historyLoading.value = true
  try { const data = await uiAIExecutionApi.list({ ai_case: row.id }); historyRecords.value = data.results || data || [] }
  catch (e) { console.error(e) } finally { historyLoading.value = false }
}

async function viewReport(row) {
  try { const r = await uiAIExecutionApi.report(row.id); alert(JSON.stringify(r, null, 2)) }
  catch (e) { console.error(e) }
}

async function stopExecution(row) {
  try { await uiAIExecutionApi.stop(row.id); viewHistory({ id: currentCaseId.value }) }
  catch (e) { console.error(e) }
}

onMounted(loadProjects)
</script>

<style scoped>
.ui-ai-case-page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { margin: 0 0 4px; }
.page-subtitle { color: var(--text-secondary); font-size: 13px; }
.page-header-right { display: flex; gap: 8px; align-items: center; }
</style>
