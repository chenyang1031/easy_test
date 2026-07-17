<template>
  <div class="ui-public-data-manager">
    <div class="toolbar">
      <el-button type="primary" size="small" @click="showDialog = true">+ 新增变量</el-button>
    </div>
    <el-table :data="items" size="small" stripe v-loading="loading" empty-text="暂无公共数据">
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="key" label="键名" min-width="120" />
      <el-table-column prop="value" label="值" min-width="200" show-overflow-tooltip />
      <el-table-column label="类型" width="80">
        <template #default="{ row }">{{ ['字符串','整数','列表','字典'][row.data_type] || '未知' }}</template>
      </el-table-column>
      <el-table-column label="启用" width="60" align="center">
        <template #default="{ row }"><el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">{{ row.is_enabled ? '是' : '否' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="editItem(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteItem(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showDialog" :title="editing ? '编辑变量' : '新增变量'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="键名"><el-input v-model="form.key" /></el-form-item>
        <el-form-item label="值"><el-input v-model="form.value" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="数据类型">
          <el-select v-model="form.data_type" style="width: 100%">
            <el-option label="字符串" :value="0" /><el-option label="整数" :value="1" />
            <el-option label="列表" :value="2" /><el-option label="字典" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_enabled" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveItem" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { uiPublicDataApi } from '../../api/uiAutomation'

const props = defineProps({ projectId: [Number, String] })
const items = ref([])
const loading = ref(false)
const showDialog = ref(false)
const saving = ref(false)
const editing = ref(false)
const form = ref({ name: '', key: '', value: '', data_type: 0, is_enabled: true, description: '' })

async function loadItems() {
  loading.value = true
  try { const data = await uiPublicDataApi.list({ project: props.projectId }); items.value = data.results || data || [] }
  catch (e) { console.error(e) } finally { loading.value = false }
}

function editItem(row) { editing.value = true; form.value = { ...row }; showDialog.value = true }

async function saveItem() {
  saving.value = true
  try {
    if (editing.value && form.value.id) { await uiPublicDataApi.update(form.value.id, form.value) }
    else { await uiPublicDataApi.create({ ...form.value, project: props.projectId }) }
    showDialog.value = false; editing.value = false
    form.value = { name: '', key: '', value: '', data_type: 0, is_enabled: true, description: '' }
    loadItems()
  } catch (e) { console.error(e) } finally { saving.value = false }
}

async function deleteItem(id) { if (!confirm('确定删除？')) return; try { await uiPublicDataApi.delete(id); loadItems() } catch (e) { console.error(e) } }

watch(() => props.projectId, loadItems)
onMounted(loadItems)
</script>

<style scoped>
.toolbar { display: flex; justify-content: flex-end; margin-bottom: 12px; }
</style>
