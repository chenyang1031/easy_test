<template>
  <div class="ui-page-manager">
    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索页面..." size="small" clearable style="width: 200px" @input="loadPages" />
      <el-button type="primary" size="small" @click="showDialog = true">+ 新增页面</el-button>
    </div>
    <el-table :data="pages" size="small" stripe v-loading="loading" empty-text="暂无页面">
      <el-table-column prop="name" label="页面名称" min-width="150" />
      <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip />
      <el-table-column prop="module_name" label="模块" width="120" />
      <el-table-column prop="element_count" label="元素数" width="80" align="center" />
      <el-table-column label="操作" width="150" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="editPage(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deletePage(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showDialog" :title="editing ? '编辑页面' : '新增页面'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="URL"><el-input v-model="form.url" /></el-form-item>
        <el-form-item label="模块">
          <el-input v-model="form.module" type="number" placeholder="模块ID" />
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="savePage" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { uiPageApi } from '../../api/uiAutomation'

const props = defineProps({ projectId: [Number, String], moduleId: [Number, String] })
const pages = ref([])
const loading = ref(false)
const search = ref('')
const showDialog = ref(false)
const saving = ref(false)
const editing = ref(false)
const form = ref({ name: '', url: '', module: '', description: '' })

async function loadPages() {
  loading.value = true
  try {
    const params = { project: props.projectId }
    if (props.moduleId) params.module = props.moduleId
    const data = await uiPageApi.list(params)
    pages.value = data.results || data || []
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function editPage(row) {
  editing.value = true
  form.value = { ...row }
  showDialog.value = true
}

async function savePage() {
  saving.value = true
  try {
    if (editing.value && form.value.id) {
      await uiPageApi.update(form.value.id, form.value)
    } else {
      await uiPageApi.create({ ...form.value, module: props.moduleId || form.value.module })
    }
    showDialog.value = false
    editing.value = false
    form.value = { name: '', url: '', module: '', description: '' }
    loadPages()
  } catch (e) { console.error(e) }
  finally { saving.value = false }
}

async function deletePage(id) {
  if (!confirm('确定删除此页面？')) return
  try { await uiPageApi.delete(id); loadPages() } catch (e) { console.error(e) }
}

watch(() => [props.projectId, props.moduleId], loadPages)
onMounted(loadPages)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 12px; }
</style>
