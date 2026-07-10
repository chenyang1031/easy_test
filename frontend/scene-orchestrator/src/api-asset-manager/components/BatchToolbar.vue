<template>
  <div class="batch-toolbar" v-if="store.hasSelection">
    <span class="batch-count">已选 <strong>{{ store.selectedAssetIds.size }}</strong> 项</span>
    <el-button size="small" @click="handleBatchExport">批量导出</el-button>
    <el-button size="small" type="danger" @click="handleBatchDelete">批量删除</el-button>
    <el-select v-model="batchStatus" size="small" placeholder="改状态..." clearable style="width:120px" @change="handleBatchStatus">
      <el-option label="draft" value="draft" />
      <el-option label="active" value="active" />
      <el-option label="deprecated" value="deprecated" />
    </el-select>
    <el-select v-model="batchGroup" size="small" placeholder="移动分组" clearable style="width:140px" @change="handleBatchMove">
      <el-option v-for="g in store.flatGroupsForSelect" :key="g.id ?? 'root'" :label="g.displayName" :value="g.id" />
    </el-select>
    <el-button size="small" type="warning" @click="$emit('aiGenerate')">AI生成</el-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useApiAssetStore } from '../stores/apiAsset.js'
import { ElMessageBox, ElMessage } from 'element-plus'

defineEmits(['aiGenerate'])
const store = useApiAssetStore()
const batchStatus = ref('')
const batchGroup = ref(null)

async function handleBatchDelete() {
  const ids = Array.from(store.selectedAssetIds)
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 个接口吗？`, '批量删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await store.batchDelete(ids)
    ElMessage.success(`已删除 ${ids.length} 个接口`)
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.message || '删除失败')
  }
}

async function handleBatchStatus(val) {
  if (!val) return
  const ids = Array.from(store.selectedAssetIds)
  try {
    await store.batchUpdateStatus(ids, val)
    ElMessage.success(`已更新 ${ids.length} 个接口状态`)
    batchStatus.value = ''
  } catch (e) {
    ElMessage.error(e?.message || '更新失败')
  }
}

async function handleBatchMove(val) {
  const ids = Array.from(store.selectedAssetIds)
  try {
    await store.batchMoveGroup(ids, val)
    ElMessage.success(`已移动 ${ids.length} 个接口`)
    batchGroup.value = null
  } catch (e) {
    ElMessage.error(e?.message || '移动失败')
  }
}

async function handleBatchExport() {
  try {
    await store.exportOpenApi()
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error(e?.message || '导出失败')
  }
}
</script>

<style scoped>
.batch-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f0f9ff;
  border: 1px solid #b3d8ff;
  border-radius: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.batch-count {
  font-size: 13px;
  color: #1e3a8a;
  margin-right: 4px;
}
</style>
