<template>
  <el-table
    :data="store.assets"
    stripe
    style="width:100%"
    @selection-change="handleSelectionChange"
    v-loading="store.loading"
    empty-text="暂无接口数据"
  >
    <el-table-column type="selection" width="40" />
    <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip>
      <template #default="{ row }">
        <span class="asset-name">{{ row.name || '-' }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="method" label="Method" width="90" align="center">
      <template #default="{ row }">
        <el-tag
          :type="methodTagType(row.method)"
          size="small"
          effect="dark"
        >
          {{ row.method || '-' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="分组" width="120" show-overflow-tooltip>
      <template #default="{ row }">
        <span class="group-name">{{ row.group_name || '根目录' }}</span>
      </template>
    </el-table-column>
    <el-table-column label="URL" min-width="180" show-overflow-tooltip>
      <template #default="{ row }">
        <span class="asset-url">{{ row.url || '-' }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="status" label="状态" width="80" align="center">
      <template #default="{ row }">
        <el-tag :type="statusTagType(row.status)" size="small">
          {{ statusText(row.status) }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="100" fixed="right" align="center">
      <template #default="{ row }">
        <el-button link type="primary" size="small" @click="$emit('edit', row)">
          <el-icon><Edit /></el-icon>
        </el-button>
        <el-button link type="danger" size="small" @click="$emit('delete', row)">
          <el-icon><Delete /></el-icon>
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { Edit, Delete } from '@element-plus/icons-vue'
import { useApiAssetStore } from '../stores/apiAsset.js'

defineEmits(['edit', 'delete'])

const store = useApiAssetStore()

function handleSelectionChange(rows) {
  const ids = new Set(rows.map(r => r.id))
  store.selectedAssetIds = ids
}

function methodTagType(method) {
  const map = { GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return map[method] || ''
}

function statusText(status) {
  const map = { draft: '草稿', active: '可用', deprecated: '已废弃' }
  return map[status] || status
}

function statusTagType(status) {
  const map = { draft: 'info', active: 'success', deprecated: 'danger' }
  return map[status] || 'info'
}
</script>

<style scoped>
.asset-name {
  font-weight: 500;
  color: #0f172a;
}
.asset-url, .group-name {
  color: #606266;
  font-size: 13px;
}
</style>
