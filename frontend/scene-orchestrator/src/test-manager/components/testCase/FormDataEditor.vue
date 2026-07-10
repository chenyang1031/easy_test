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
            <span v-if="row.value" class="file-name">{{ row.value }}</span>
            <el-button size="small" @click="pickFile(row)">选择文件</el-button>
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

const props = defineProps({ modelValue: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue'])

const rows = ref([])
function syncFromProp() {
  rows.value = (props.modelValue || []).map(r => ({ type:'text', value:'', description:'', checked:true, ...r }))
}
syncFromProp()

function emitChange() { emit('update:modelValue', rows.value.map(({key,value,description,checked,type}) => ({key,value,description,checked,type}))) }
function addRow() { rows.value.push({ key:'', value:'', description:'', checked:true, type:'text' }); emitChange() }
function removeRow(i) { rows.value.splice(i,1); emitChange() }
function pickFile(row) { row.value = prompt('输入文件名:') || ''; emitChange() }

watch(() => props.modelValue, () => syncFromProp(), { deep: true })
</script>

<style scoped>
.editor { margin-bottom:8px; background:#f9fafb; border-radius:8px; padding:10px 12px; }
.editor-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.editor-header h6 { margin:0; font-size:13px; font-weight:500; color:#606266; }
.file-picker { display:flex; align-items:center; gap:6px; }
.file-name { font-size:12px; color:#909399; max-width:100px; overflow:hidden; text-overflow:ellipsis; }
</style>
