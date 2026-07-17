<template>
  <div class="ui-scheduled-task-page">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">UI 定时任务</h2>
        <span class="page-subtitle">管理和调度 UI 自动化测试任务</span>
      </div>
      <div class="page-header-right">
        <el-select v-model="selectedProject" placeholder="选择项目" size="small" style="width: 200px" @change="loadTasks">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-button type="primary" size="small" @click="showDialog = true">+ 新增任务</el-button>
      </div>
    </div>

    <el-table :data="tasks" size="small" stripe v-loading="loading" empty-text="暂无定时任务">
      <el-table-column prop="name" label="任务名称" min-width="180" />
      <el-table-column label="触发类型" width="100">
        <template #default="{ row }">{{ { cron: 'Cron', interval: '间隔', once: '单次' }[row.trigger_type] }}</template>
      </el-table-column>
      <el-table-column label="表达式/间隔" width="150">
        <template #default="{ row }">{{ row.trigger_type === 'cron' ? row.cron_expression : row.interval_seconds ? row.interval_seconds + 's' : '-' }}</template>
      </el-table-column>
      <el-table-column prop="test_case_count" label="用例数" width="70" align="center" />
      <el-table-column label="启用" width="70" align="center">
        <template #default="{ row }">
          <el-switch v-model="row.is_active" size="small" @change="toggleTask(row)" />
        </template>
      </el-table-column>
      <el-table-column label="统计" width="150">
        <template #default="{ row }">成功 {{ row.successful_runs }} / 失败 {{ row.failed_runs }} / 共 {{ row.total_runs }}</template>
      </el-table-column>
      <el-table-column prop="environment_name" label="环境" width="100" />
      <el-table-column label="操作" width="200" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="success" @click="runNow(row)">立即执行</el-button>
          <el-button size="small" text type="primary" @click="editTask(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteTask(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showDialog" :title="editing ? '编辑任务' : '新增任务'" width="650px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="触发类型">
          <el-select v-model="form.trigger_type" style="width: 100%">
            <el-option label="Cron 表达式" value="cron" /><el-option label="固定间隔" value="interval" /><el-option label="单次执行" value="once" />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron表达式" v-if="form.trigger_type === 'cron'">
          <el-input v-model="form.cron_expression" placeholder="0 2 * * *" />
        </el-form-item>
        <el-form-item label="间隔(秒)" v-if="form.trigger_type === 'interval'">
          <el-input-number v-model="form.interval_seconds" :min="60" />
        </el-form-item>
        <el-form-item label="浏览器">
          <el-select v-model="form.browser" style="width: 100%">
            <el-option label="Chromium" value="chromium" /><el-option label="Firefox" value="firefox" /><el-option label="WebKit" value="webkit" />
          </el-select>
        </el-form-item>
        <el-form-item label="无头模式"><el-switch v-model="form.headless" /></el-form-item>
        <el-form-item label="失败通知"><el-switch v-model="form.notify_on_failure" /></el-form-item>
        <el-form-item label="成功通知"><el-switch v-model="form.notify_on_success" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTask" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { uiScheduledTaskApi } from '../../api/uiAutomation'
import { http } from '../../api/http'

const projects = ref([])
const selectedProject = ref(null)
const tasks = ref([])
const loading = ref(false)
const showDialog = ref(false)
const saving = ref(false)
const editing = ref(false)
const form = ref({ name: '', trigger_type: 'cron', cron_expression: '', interval_seconds: 3600, browser: 'chromium', headless: true, notify_on_failure: true, notify_on_success: false })

async function loadProjects() {
  try { const data = await http.get('/api/v1/projects/'); projects.value = data.results || data || []
    if (projects.value.length && !selectedProject.value) { selectedProject.value = projects.value[0].id; loadTasks() }
  } catch (e) { console.error(e) }
}

async function loadTasks() {
  if (!selectedProject.value) return; loading.value = true
  try { const data = await uiScheduledTaskApi.list({ project: selectedProject.value }); tasks.value = data.results || data || [] }
  catch (e) { console.error(e) } finally { loading.value = false }
}

function editTask(row) { editing.value = true; form.value = { ...row }; showDialog.value = true }

async function saveTask() {
  saving.value = true
  try {
    if (editing.value && form.value.id) { await uiScheduledTaskApi.update(form.value.id, form.value) }
    else { await uiScheduledTaskApi.create({ ...form.value, project: selectedProject.value }) }
    showDialog.value = false; editing.value = false
    form.value = { name: '', trigger_type: 'cron', cron_expression: '', interval_seconds: 3600, browser: 'chromium', headless: true, notify_on_failure: true, notify_on_success: false }
    loadTasks()
  } catch (e) { console.error(e) } finally { saving.value = false }
}

async function toggleTask(row) {
  try { row.is_active ? await uiScheduledTaskApi.resume(row.id) : await uiScheduledTaskApi.pause(row.id) }
  catch (e) { console.error(e); row.is_active = !row.is_active }
}

async function runNow(row) {
  try { const r = await uiScheduledTaskApi.runNow(row.id); alert(r.message || '已提交执行') }
  catch (e) { alert('执行失败: ' + e.message) }
}

async function deleteTask(id) { if (!confirm('确定删除？')) return; try { await uiScheduledTaskApi.delete(id); loadTasks() } catch (e) { console.error(e) } }

onMounted(loadProjects)
</script>

<style scoped>
.ui-scheduled-task-page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { margin: 0 0 4px; }
.page-subtitle { color: var(--text-secondary); font-size: 13px; }
.page-header-right { display: flex; gap: 8px; align-items: center; }
</style>
