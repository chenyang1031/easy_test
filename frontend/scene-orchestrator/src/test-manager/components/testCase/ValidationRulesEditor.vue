<template>
  <div class="editor">
    <div class="editor-header">
      <h6>断言 (Validation Rules)</h6>
      <div class="editor-actions">
        <el-dropdown @command="applyPreset">
          <el-button size="small">Presets</el-button>
          <template #dropdown>
            <el-dropdown-item command="status">Status Code</el-dropdown-item>
            <el-dropdown-item command="success">Success Response</el-dropdown-item>
            <el-dropdown-item command="notempty">Data Not Empty</el-dropdown-item>
          </template>
        </el-dropdown>
        <el-button size="small" @click="addRow"><el-icon><Plus /></el-icon> 添加</el-button>
      </div>
    </div>
    <el-table :data="rows" size="small" style="width:100%">
      <el-table-column width="50">
        <template #default="{row}"><el-checkbox v-model="row.enabled" @change="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Comparator" width="130">
        <template #default="{row}">
          <el-select v-model="row.comparator" size="small" @change="emitChange">
            <el-option v-for="v in operators" :key="v" :label="v" :value="v" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="Path" min-width="130">
        <template #default="{row}"><el-input v-model="row.path" size="small" placeholder="$.status" @input="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Expected" min-width="100">
        <template #default="{row}"><el-input v-model="row.expected" size="small" placeholder="预期值" @input="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Description" width="120">
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

const operators = ['eq','ne','gt','ge','lt','le','contains','startswith','endswith','regex_match','length_eq','length_gt','length_ge','length_lt','length_le']
const presets = {
  status: [{ comparator:'eq', path:'$.status', expected:'200' }],
  success: [{ comparator:'eq', path:'$.success', expected:'true' }],
  notempty: [{ comparator:'length_gt', path:'$.data', expected:'0' }],
}

const rows = ref([])
function sync() {
  rows.value = (props.modelValue || []).map(r => {
    if (typeof r === 'object' && !Array.isArray(r)) {
      const entries = Object.entries(r)
      // 格式1: {"eq": ["$.data.id", 200]} — 单key, value 是数组 [path, expected]
      if (entries.length === 1 && Array.isArray(entries[0][1])) {
        const [[v, [path, exp]]] = entries
        return { comparator:v, path, expected:exp, enabled:true, description:'', on_failed:'stop' }
      }
      // 格式2: {path: "$.data.id", comparator: "eq", expected: 200} — AI生成格式 + 场景格式
      if (r.path && r.comparator) {
        return { comparator: r.comparator, path: r.path, expected: r.expected ?? '', enabled: r.enabled !== false, description: r.description || '', on_failed: r.on_failed || 'stop' }
      }
      // legacy: validator → comparator, checked → enabled
      const cmp = r.comparator || r.validator || 'eq'
      const en = r.enabled !== undefined ? r.enabled : (r.checked !== undefined ? r.checked : true)
      return { comparator: cmp, path: r.path || '', expected: r.expected ?? '', enabled: en, description: r.description || '', on_failed: r.on_failed || 'stop' }
    }
    return { comparator:'eq', path:'', expected:'', enabled:true, description:'', on_failed:'stop' }
  })
}
sync()

function emitChange() {
  const result = rows.value.map(({comparator,path,expected,description,enabled,on_failed}) => ({comparator,path,expected,description,enabled,on_failed}))
  emit('update:modelValue', result)
}
function addRow() { rows.value.push({ comparator:'eq', path:'', expected:'', description:'', enabled:true, on_failed:'stop' }); emitChange() }
function removeRow(i) { rows.value.splice(i,1); emitChange() }
function applyPreset(cmd) { rows.value = rows.value.concat(presets[cmd].map(r => ({...r, description:'', enabled:true, on_failed:'stop' }))); emitChange() }

watch(() => props.modelValue, () => sync(), { deep: true })
</script>

<style scoped>
.editor { margin-bottom:8px; background:#f9fafb; border-radius:8px; padding:10px 12px; }
.editor-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.editor-header h6 { margin:0; font-size:13px; font-weight:500; color:#606266; }
.editor-actions { display:flex; gap:6px; }
</style>
