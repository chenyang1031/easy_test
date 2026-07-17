<template>
  <div class="ui-env-manager">
    <div class="toolbar">
      <el-button type="primary" size="small" @click="showDialog = true">+ 新增环境</el-button>
    </div>
    <el-table :data="envs" size="small" stripe v-loading="loading" empty-text="暂无环境配置">
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="base_url" label="基础URL" min-width="200" show-overflow-tooltip />
      <el-table-column prop="browser" label="浏览器" width="100" />
      <el-table-column label="视口" width="120">
        <template #default="{ row }">{{ row.viewport_width }}x{{ row.viewport_height }}</template>
      </el-table-column>
      <el-table-column label="无头" width="60" align="center">
        <template #default="{ row }">{{ row.headless ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="默认" width="60" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="editEnv(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteEnv(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showDialog" :title="editing ? '编辑环境' : '新增环境'" width="600px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="基础URL"><el-input v-model="form.base_url" placeholder="https://example.com" /></el-form-item>
        <el-form-item label="浏览器">
          <el-select v-model="form.browser" style="width: 100%">
            <el-option label="Chromium" value="chromium" /><el-option label="Firefox" value="firefox" /><el-option label="WebKit" value="webkit" />
          </el-select>
        </el-form-item>
        <el-form-item label="无头模式"><el-switch v-model="form.headless" /></el-form-item>
        <el-form-item label="视口宽度"><el-input-number v-model="form.viewport_width" :min="320" :max="3840" /></el-form-item>
        <el-form-item label="视口高度"><el-input-number v-model="form.viewport_height" :min="240" :max="2160" /></el-form-item>
        <el-form-item label="超时(秒)"><el-input-number v-model="form.timeout" :min="5" :max="120" /></el-form-item>
        <el-form-item label="默认环境"><el-switch v-model="form.is_default" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEnv" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { uiEnvApi } from '../../api/uiAutomation'

const props = defineProps({ projectId: [Number, String] })
const envs = ref([])
const loading = ref(false)
const showDialog = ref(false)
const saving = ref(false)
const editing = ref(false)
const form = ref({ name: '', base_url: '', browser: 'chromium', headless: true, viewport_width: 1920, viewport_height: 1080, timeout: 30, is_default: false })

async function loadEnvs() {
  loading.value = true
  try { const data = await uiEnvApi.list({ project: props.projectId }); envs.value = data.results || data || [] }
  catch (e) { console.error(e) } finally { loading.value = false }
}

function editEnv(row) { editing.value = true; form.value = { ...row }; showDialog.value = true }

async function saveEnv() {
  saving.value = true
  try {
    if (editing.value && form.value.id) { await uiEnvApi.update(form.value.id, form.value) }
    else { await uiEnvApi.create({ ...form.value, project: props.projectId }) }
    showDialog.value = false; editing.value = false
    form.value = { name: '', base_url: '', browser: 'chromium', headless: true, viewport_width: 1920, viewport_height: 1080, timeout: 30, is_default: false }
    loadEnvs()
  } catch (e) { console.error(e) } finally { saving.value = false }
}

async function deleteEnv(id) { if (!confirm('确定删除？')) return; try { await uiEnvApi.delete(id); loadEnvs() } catch (e) { console.error(e) } }

watch(() => props.projectId, loadEnvs)
onMounted(loadEnvs)
</script>

<style scoped>
.toolbar { display: flex; justify-content: flex-end; margin-bottom: 12px; }
</style>
