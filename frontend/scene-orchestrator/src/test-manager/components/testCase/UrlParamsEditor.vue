<template>
  <div class="editor">
    <div class="editor-header">
      <h6>请求参数 (URL Params)</h6>
      <el-button size="small" @click="addRow"><el-icon><Plus /></el-icon> 添加</el-button>
    </div>
    <el-table :data="rows" size="small" style="width:100%">
      <el-table-column width="50">
        <template #default="{row}"><el-checkbox v-model="row.checked" @change="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Key">
        <template #default="{row}"><el-input v-model="row.key" size="small" placeholder="Key" @input="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Value">
        <template #default="{row}"><el-input v-model="row.value" size="small" placeholder="Value" @input="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Description" width="150">
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

const rows = ref(props.modelValue.map(r => ({ ...r, checked: r.checked !== false })))

function addRow() { rows.value.push({ key:'', value:'', description:'', checked:true }); emitChange() }
function removeRow(i) { rows.value.splice(i,1); emitChange() }

function emitChange() { emit('update:modelValue', rows.value.map(({key,value,description,checked}) => ({key,value,description,checked}))) }

watch(() => props.modelValue, (v) => {
  if (JSON.stringify(v) !== JSON.stringify(rows.value)) {
    rows.value = (v || []).map(r => ({ ...r, checked: r.checked !== false }))
  }
}, { deep: true })
</script>

<style scoped>
.editor { margin-bottom:8px; background:#f9fafb; border-radius:8px; padding:10px 12px; }
.editor-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.editor-header h6 { margin:0; font-size:13px; font-weight:500; color:#606266; }
</style>
