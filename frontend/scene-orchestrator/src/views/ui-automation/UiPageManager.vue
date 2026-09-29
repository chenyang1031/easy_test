<template>
  <div class="ui-page-manager">
    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索页面..." size="small" clearable style="width: 200px" @input="loadPages" />
      <el-button type="primary" size="small" @click="openAddPage">+ 新增页面</el-button>
    </div>
    <el-table :data="pages" size="small" stripe v-loading="loading" empty-text="暂无页面">
      <el-table-column prop="name" label="页面名称" min-width="150" />
      <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip />
      <el-table-column prop="module_name" label="模块" width="120" />
      <el-table-column prop="element_count" label="元素数" width="80" align="center" />
      <el-table-column label="操作" width="210" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="success" @click="openStepManager(row)">步骤</el-button>
          <el-button size="small" text type="primary" @click="editPage(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deletePage(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination" v-if="total > pageSize">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, jumper"
        @current-change="p => { page = p; loadPages() }"
      />
    </div>

    <el-dialog v-model="showDialog" :title="editing ? '编辑页面' : '新增页面'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="URL"><el-input v-model="form.url" /></el-form-item>
        <el-form-item label="模块">
          <el-tree-select
            v-model="form.module"
            :data="moduleTreeOptions"
            :props="{ label: 'name', value: 'id', children: 'children' }"
            check-strictly
            placeholder="选择所属模块"
            clearable
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="savePage" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <UiPageStepManager
      v-model:visible="stepManagerVisible"
      :page="stepManagerPage"
      :project-id="projectId"
      @changed="loadPages"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { uiPageApi } from '../../api/uiAutomation'
import UiPageStepManager from './UiPageStepManager.vue'

const props = defineProps({
  projectId: [Number, String],
  moduleId: [Number, String],
  moduleTree: { type: Array, default: () => [] }
})
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const pages = ref([])
const loading = ref(false)
const search = ref('')
const showDialog = ref(false)
const saving = ref(false)
const editing = ref(false)
const form = ref({ name: '', url: '', module: '', description: '' })

const moduleTreeOptions = computed(() => props.moduleTree || [])

async function loadPages() {
  loading.value = true
  try {
    const params = { project: props.projectId, page: page.value, page_size: pageSize.value }
    if (props.moduleId) params.module = props.moduleId
    const data = await uiPageApi.list(params)
    pages.value = data.results || data || []
    total.value = data.count ?? pages.value.length
    if (!pages.value.length && page.value > 1) { page.value -= 1; loadPages(); return }
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function openAddPage() {
  editing.value = false
  form.value = { name: '', url: '', module: props.moduleId || '', description: '' }
  showDialog.value = true
}

function editPage(row) {
  editing.value = true
  form.value = { ...row }
  showDialog.value = true
}

async function savePage() {
  // 模型层 module 外键不允许为空，不选模块必然保存失败，提前拦截给出明确提示
  const moduleId = props.moduleId || form.value.module
  if (!moduleId) {
    ElMessage.error('请先选择所属模块（左侧模块树或下方模块选择器）')
    return
  }
  saving.value = true
  try {
    if (editing.value && form.value.id) {
      await uiPageApi.update(form.value.id, { ...form.value, module: moduleId })
    } else {
      await uiPageApi.create({ ...form.value, module: moduleId })
    }
    showDialog.value = false
    editing.value = false
    form.value = { name: '', url: '', module: '', description: '' }
    loadPages()
  } catch (e) {
    console.error(e)
    ElMessage.error(e.message || '保存页面失败，请检查填写内容')
  } finally { saving.value = false }
}

async function deletePage(id) {
  if (!confirm('确定删除此页面？')) return
  try { await uiPageApi.delete(id); loadPages() } catch (e) { console.error(e) }
}

const stepManagerVisible = ref(false)
const stepManagerPage = ref(null)
function openStepManager(row) {
  stepManagerPage.value = row
  stepManagerVisible.value = true
}

watch(() => [props.projectId, props.moduleId], loadPages)
onMounted(loadPages)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 12px; }

.pagination { margin-top: 12px; display: flex; justify-content: flex-end; }
</style>
