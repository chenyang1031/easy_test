<template>
  <div class="editor">
    <div class="editor-header">
      <h6>提取参数 (Extract)</h6>
      <div class="editor-actions">
        <el-dropdown @command="applyPreset">
          <el-button size="small">Presets</el-button>
          <template #dropdown>
            <el-dropdown-item command="token">Token</el-dropdown-item>
            <el-dropdown-item command="user">User Info</el-dropdown-item>
            <el-dropdown-item command="page">Pagination</el-dropdown-item>
          </template>
        </el-dropdown>
        <el-button size="small" @click="addRow"><el-icon><Plus /></el-icon> 添加</el-button>
      </div>
    </div>
    <el-table :data="rows" size="small" style="width:100%">
      <el-table-column width="50">
        <template #default="{row}"><el-checkbox v-model="row.checked" @change="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Name" min-width="120">
        <template #default="{row}"><el-input v-model="row.name" size="small" placeholder="变量名" @input="emitChange" /></template>
      </el-table-column>
      <el-table-column label="Path" min-width="160">
        <template #default="{row}"><el-input v-model="row.path" size="small" placeholder="$.data.token" @input="emitChange" /></template>
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

const presets = {
  token: [{ name:'token', path:'$.data.token', checked:true }],
  user: [{ name:'userId', path:'$.data.user.id', checked:true }, { name:'userName', path:'$.data.user.name', checked:true }],
  page: [{ name:'total', path:'$.data.total', checked:true }, { name:'page', path:'$.data.page', checked:true }],
}

const rows = ref([])
function sync() { rows.value = (props.modelValue || []).map(r => ({ checked:true, description:'', ...r })) }
sync()

function emitChange() { emit('update:modelValue', rows.value.map(({name,path,description,checked}) => ({name,path,description,checked}))) }
function addRow() { rows.value.push({ name:'', path:'', description:'', checked:true }); emitChange() }
function removeRow(i) { rows.value.splice(i,1); emitChange() }
function applyPreset(cmd) { rows.value = rows.value.concat(presets[cmd].map(r => ({...r, description:''}))); emitChange() }

watch(() => props.modelValue, () => sync(), { deep: true })
</script>

<style scoped>
.editor { margin-bottom:8px; background:#f9fafb; border-radius:8px; padding:10px 12px; }
.editor-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.editor-header h6 { margin:0; font-size:13px; font-weight:500; color:#606266; }
.editor-actions { display:flex; gap:6px; }
</style>
