<template>
  <div class="editor">
    <div class="editor-header">
      <h6>Form Data</h6>
      <el-button size="small" @click="addRow"><el-icon><Plus /></el-icon> 添加</el-button>
    </div>
    <el-table :data="rows" size="small" style="width:100%">
      <el-table-column width="50">
        <template #default="{row}"><el-checkbox v-model="row.checked" @change="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Key" min-width="120">
        <template #default="{row}"><el-input v-model="row.key" size="small" placeholder="Key" @input="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Type" width="100">
        <template #default="{row}">
          <el-select v-model="row.type" size="small" @change="emitChange">
            <el-option label="Text" value="text" />
            <el-option label="File" value="file" />
            <el-option label="JSON" value="json" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="Value" min-width="140">
        <template #default="{row}">
          <el-input v-if="row.type==='text'" v-model="row.value" size="small" placeholder="Value" @input="emitChange" />
          <el-input v-else-if="row.type==='json'" v-model="row.value" size="small" type="textarea" :rows="2" placeholder='{"key":"value"}' @input="emitChange" />
          <div v-else class="file-picker">
            <el-tag v-if="row.value" type="success" size="small" closable @close="clearFile(row)">
              {{ row.fileName || row.value.split('/').pop() }}
            </el-tag>
            <el-button size="small" @click="handleFileUpload(row)">选择文件</el-button>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="Description" width="130">
        <template #default="{row}"><el-input v-model="row.description" size="small" placeholder="Description" @input="emitChange" /></template>
      </el-table-column>
      <el-table-column width="60">
        <template #default="{ $index }">
          <el-button size="small" type="danger" link @click="removeRow($index)"><el-icon><Delete /></el-icon></el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadFile } from '../../api/index.js'

const props = defineProps({ modelValue: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue'])

const rows = ref([])
function syncFromProp() {
  rows.value = (props.modelValue || []).map(r => ({ type:'text', value:'', description:'', checked:true, ...r }))
}
syncFromProp()

function emitChange() { emit('update:modelValue', rows.value.map(({key,value,description,checked,type,fileName}) => ({key,value,description,checked,type,fileName}))) }
function addRow() { rows.value.push({ key:'', value:'', description:'', checked:true, type:'text' }); emitChange() }
function removeRow(i) { rows.value.splice(i,1); emitChange() }

function clearFile(row) {
  row.value = ''
  row.fileName = ''
  emitChange()
}

async function handleFileUpload(row) {
  const input = document.createElement('input')
  input.type = 'file'
  input.onchange = async (e) => {
    const file = e.target?.files?.[0]
    if (!file) return
    try {
      const res = await uploadFile(file)
      if (res?.success && res?.file_path) {
        row.value = res.file_path
        row.fileName = res.file_name || file.name
        row.type = 'file'
        emitChange()
      } else {
        ElMessage.error(res?.detail || '文件上传失败')
      }
    } catch (err) {
      ElMessage.error(err.message || '文件上传失败')
    }
  }
  input.click()
}

watch(() => props.modelValue, () => syncFromProp(), { deep: true })
</script>

<style scoped>
.editor { margin-bottom:8px; background:#f9fafb; border-radius:8px; padding:10px 12px; }
.editor-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.editor-header h6 { margin:0; font-size:13px; font-weight:500; color:#606266; }
.file-picker { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
</style>
