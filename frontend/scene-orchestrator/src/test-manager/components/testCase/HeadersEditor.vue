<template>
  <div class="editor">
    <div class="editor-header">
      <h6>请求头 (Headers)</h6>
      <div class="editor-actions">
        <el-dropdown @command="applyPreset">
          <el-button size="small">Presets <el-icon><ArrowDown /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="json">JSON</el-dropdown-item>
              <el-dropdown-item command="form">Form Data</el-dropdown-item>
              <el-dropdown-item command="xml">XML</el-dropdown-item>
              <el-dropdown-item command="auth">Authorization</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button size="small" @click="addRow"><el-icon><Plus /></el-icon> 添加</el-button>
      </div>
    </div>
    <el-table :data="rows" size="small" style="width:100%">
      <el-table-column width="50">
        <template #default="{row}"><el-checkbox v-model="row.checked" @change="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Key" min-width="140">
        <template #default="{row}">
          <el-autocomplete v-model="row.key" size="small" placeholder="Key" :fetch-suggestions="keySuggestions" @select="emitChange" @input="emitChange" />
        </template>
      </el-table-column>
      <el-table-column label="Value" min-width="160">
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
const rows = ref([])

const presets = {
  json: [{ key:'Content-Type', value:'application/json', checked:true }],
  form: [{ key:'Content-Type', value:'application/x-www-form-urlencoded', checked:true }],
  xml: [{ key:'Content-Type', value:'application/xml', checked:true }],
  auth: [{ key:'Authorization', value:'Bearer ', checked:true }],
}

const commonKeys = ['Content-Type','Accept','Authorization','Cache-Control','User-Agent','Cookie','Referer','Origin','Host','X-Requested-With']
function keySuggestions(qs, cb) {
  cb(commonKeys.filter(k => k.toLowerCase().includes((qs||'').toLowerCase())).map(k => ({ value: k })))
}

function syncFromProp() {
  rows.value = (props.modelValue || []).map(r => ({ ...r, checked: r.checked !== false }))
}
syncFromProp()

function emitChange() { emit('update:modelValue', rows.value.map(({key,value,description,checked}) => ({key,value,description,checked}))) }
function addRow() { rows.value.push({ key:'', value:'', description:'', checked:true }); emitChange() }
function removeRow(i) { rows.value.splice(i,1); emitChange() }
function applyPreset(cmd) {
  rows.value = rows.value.filter(r => !presets[cmd].find(p => p.key === r.key)).concat(presets[cmd].map(r => ({...r, description:''})))
  emitChange()
}

watch(() => props.modelValue, () => syncFromProp(), { deep: true })
</script>

<style scoped>
.editor { margin-bottom:8px; background:#f9fafb; border-radius:8px; padding:10px 12px; }
.editor-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.editor-header h6 { margin:0; font-size:13px; font-weight:500; color:#606266; }
.editor-actions { display:flex; gap:6px; }
</style>
