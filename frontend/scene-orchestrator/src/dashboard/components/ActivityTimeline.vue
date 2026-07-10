<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span>活动时间线</span>
      <el-button size="small" circle @click="$emit('refresh')">
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>
    <div class="card-body p-0">
      <el-empty v-if="activities.length === 0" description="最近没有活动" :image-size="60" />
      <ul v-else class="list-group list-group-flush timeline">
        <li
          v-for="(act, idx) in activities.slice(0, 5)"
          :key="idx"
          class="list-group-item"
        >
          <div class="d-flex">
            <div class="timeline-icon" :class="timelineIconClass(act.status)">
              <el-icon><component :is="timelineIcon(act.status)" /></el-icon>
            </div>
            <div class="ms-3">
              <div class="fw-bold">{{ act.action }}</div>
              <div class="text-muted small">{{ act.timestamp }}</div>
              <div>{{ act.description }}</div>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { Refresh } from '@element-plus/icons-vue'
import { Check, Clock, Close, WarnTriangleFilled, Aim } from '@element-plus/icons-vue'

defineProps({
  activities: {
    type: Array,
    required: true,
  },
})

defineEmits(['refresh'])

function timelineIconClass(status) {
  if (status === 'completed') return 'bg-success'
  if (status === 'failed') return 'bg-danger'
  if (status === 'running') return 'bg-warning'
  if (status === 'pending') return 'bg-primary'
  return 'bg-info'
}

function timelineIcon(status) {
  if (status === 'completed') return Check
  if (status === 'failed') return Close
  if (status === 'running') return Clock
  if (status === 'pending') return Aim
  return WarnTriangleFilled
}
</script>

<style scoped>
.timeline .timeline-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}
.timeline .list-group-item {
  border-left: none;
  border-right: none;
}
.timeline .list-group-item:first-child {
  border-top: none;
}
</style>
