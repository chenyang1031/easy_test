<template>
  <div class="kv-table-wrap">
    <el-table :data="items" border stripe size="small" style="width:100%" table-layout="auto">
      <el-table-column v-for="col in columns" :key="col.key" :label="col.label" :width="col.width">
        <template #default="{ row }">
          <!-- 复选框类型 -->
          <div v-if="col.type === 'checkbox'" style="text-align:center">
            <el-checkbox v-model="row[col.key]" @change="emitUpdate" />
          </div>
          <!-- 下拉选择 -->
          <el-select v-else-if="col.type === 'select'" v-model="row[col.key]" size="small" style="width:100%" @change="emitUpdate">
            <el-option v-for="opt in (col.options||[])" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <!-- file 类型 → 文件上传（仅 value 列） -->
          <div v-else-if="col.key === 'value' && row.type === 'file'" class="file-cell">
            <div v-if="row.value" class="file-info">
              <el-tag size="small" type="success" closable @close="clearFile(row)">{{ row.fileName || row.value.split('/').pop() }}</el-tag>
            </div>
            <el-button size="small" @click="handleFileUpload(row)">选择文件</el-button>
          </div>
          <!-- 默认输入 -->
          <el-input v-else v-model="row[col.key]" size="small" :placeholder="col.key" @input="emitUpdate" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" align="center">
        <template #default="{ $index }">
          <el-button link type="danger" size="small" @click="removeRow($index)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { uploadFile } from '../../api/scene'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const items = computed(() => props.modelValue)

function emitUpdate() {
  emit('update:modelValue', [...items.value])
}

function removeRow(index) {
  const newItems = [...items.value]
  newItems.splice(index, 1)
  emit('update:modelValue', newItems)
}

async function handleFileUpload(row) {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '*/*'
  input.onchange = async (e) => {
    const file = e.target?.files?.[0]
    if (!file) return
    try {
      const res = await uploadFile(file)
      if (res?.success && res?.file_path) {
        row.value = res.file_path
        row.fileName = res.file_name || file.name
        emitUpdate()
      } else {
        ElMessage.error(res?.detail || '上传失败')
      }
    } catch (err) {
      ElMessage.error(err?.message || '上传失败')
    }
  }
  input.click()
}

function clearFile(row) {
  row.value = ''
  row.fileName = ''
  emitUpdate()
}
</script>

<style scoped>
.kv-table-wrap { overflow-x: auto; }
.kv-table-wrap :deep(.el-input__inner) { font-size: 13px; }
.kv-table-wrap :deep(.el-table th) { white-space: nowrap !important; word-break: keep-all !important; }
.file-cell { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.file-info { display: flex; align-items: center; }
</style>
