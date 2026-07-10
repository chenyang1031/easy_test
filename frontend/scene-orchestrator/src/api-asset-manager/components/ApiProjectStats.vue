<template>
  <div class="project-stats" v-if="stats && statusBars.length > 0">
    <div class="stats-row" v-for="item in statusBars" :key="item.status">
      <span class="stat-label">
        <span class="status-dot" :style="{ background: statusColor(item.status) }"></span>
        {{ statusText(item.status) }}
      </span>
      <span class="stat-value">{{ item.count }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useApiAssetStore } from '../stores/apiAsset.js'

const store = useApiAssetStore()

const stats = computed(() => store.projectStats)

const statusBars = computed(() => {
  if (!stats.value?.status_distribution) return []
  return stats.value.status_distribution.map(item => ({
    status: item.status,
    count: item.count,
  }))
})

function statusText(status) {
  const map = { draft: '草稿', active: '可用', deprecated: '已废弃' }
  return map[status] || status
}

function statusColor(status) {
  const map = { draft: '#909399', active: '#67c23a', deprecated: '#f56c6c' }
  return map[status] || '#909399'
}
</script>

<style scoped>
.project-stats {
  padding: 12px 0 8px;
  font-size: 13px;
}
.stats-row {
  display: flex;
  align-items: center;
  padding: 3px 0;
  gap: 8px;
}
.stat-label {
  color: #909399;
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 50px;
}
.stat-value {
  color: #303133;
  font-weight: 500;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}
</style>
