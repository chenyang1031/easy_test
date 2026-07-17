<template>
  <div class="ui-element-manager">
    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索元素..." size="small" clearable style="width: 200px" @input="loadElements" />
      <el-select v-model="typeFilter" size="small" clearable placeholder="元素类型" style="width: 120px" @change="loadElements">
        <el-option label="输入框" value="input" /><el-option label="按钮" value="button" />
        <el-option label="链接" value="link" /><el-option label="下拉框" value="dropdown" />
        <el-option label="文本" value="text" /><el-option label="表格" value="table" />
      </el-select>
      <el-button type="primary" size="small" @click="showDialog = true">+ 新增元素</el-button>
    </div>
    <el-table :data="elements" size="small" stripe v-loading="loading" empty-text="暂无元素">
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="element_type" label="类型" width="80" />
      <el-table-column prop="locator_type" label="定位类型" width="80" />
      <el-table-column prop="locator_value" label="定位值" min-width="180" show-overflow-tooltip />
      <el-table-column prop="page_name" label="页面" width="120" />
      <el-table-column label="验证" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.validation_status === 'valid' ? 'success' : row.validation_status === 'invalid' ? 'danger' : 'info'" size="small">
            {{ { valid: '有效', invalid: '无效', unknown: '未知', pending: '待验证' }[row.validation_status] || '未知' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="success" @click="validateElement(row.id)">验证</el-button>
          <el-button size="small" text type="primary" @click="editElement(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteElement(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showDialog" :title="editing ? '编辑元素' : '新增元素'" width="600px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="元素类型">
          <el-select v-model="form.element_type" style="width: 100%">
            <el-option v-for="t in ['input','button','link','dropdown','checkbox','radio','text','image','container','table','form','modal']" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="定位类型">
          <el-select v-model="form.locator_type" style="width: 100%">
            <el-option v-for="t in ['css','xpath','text','role','label','placeholder','testid','id','name']" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="定位值"><el-input v-model="form.locator_value" /></el-form-item>
        <el-form-item label="页面"><el-input v-model.number="form.page" type="number" placeholder="页面ID" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveElement" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { uiElementApi } from '../../api/uiAutomation'

const props = defineProps({ projectId: [Number, String], moduleId: [Number, String] })
const elements = ref([])
const loading = ref(false)
const search = ref('')
const typeFilter = ref('')
const showDialog = ref(false)
const saving = ref(false)
const editing = ref(false)
const form = ref({ name: '', element_type: 'input', locator_type: 'css', locator_value: '', page: '', description: '' })

async function loadElements() {
  loading.value = true
  try {
    const params = { project: props.projectId }
    if (props.moduleId) params.module = props.moduleId
    if (search.value) params.search = search.value
    if (typeFilter.value) params.element_type = typeFilter.value
    const data = await uiElementApi.list(params)
    elements.value = data.results || data || []
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function editElement(row) {
  editing.value = true; form.value = { ...row }; showDialog.value = true
}

async function saveElement() {
  saving.value = true
  try {
    if (editing.value && form.value.id) { await uiElementApi.update(form.value.id, form.value) }
    else { await uiElementApi.create(form.value) }
    showDialog.value = false; editing.value = false
    form.value = { name: '', element_type: 'input', locator_type: 'css', locator_value: '', page: '', description: '' }
    loadElements()
  } catch (e) { console.error(e) }
  finally { saving.value = false }
}

async function validateElement(id) {
  try { const r = await uiElementApi.validate(id); alert(r.message || '验证完成'); loadElements() }
  catch (e) { console.error(e) }
}

async function deleteElement(id) {
  if (!confirm('确定删除此元素？')) return
  try { await uiElementApi.delete(id); loadElements() } catch (e) { console.error(e) }
}

watch(() => [props.projectId, props.moduleId], loadElements)
onMounted(loadElements)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
</style>
