<template>
  <div class="data-card">
    <div class="data-card-header">
      <h3 class="data-card-title">活动时间线</h3>
      <button class="refresh-btn" @click="$emit('refresh')" title="刷新">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15">
          <path d="M23 4v6h-6M1 20v-6h6" />
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
        </svg>
      </button>
    </div>
    <div class="data-card-body">
      <el-empty v-if="activities.length === 0" description="最近没有活动" :image-size="60" />
      <div v-else class="timeline-list">
        <div
          v-for="(act, idx) in activities.slice(0, 5)"
          :key="idx"
          class="timeline-item"
        >
          <div class="timeline-dot" :class="dotClass(act.status)"></div>
          <div class="timeline-content">
            <div class="timeline-action">{{ act.action }}</div>
            <div class="timeline-desc" v-if="act.description">{{ act.description }}</div>
            <div class="timeline-time">{{ act.timestamp }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  activities: {
    type: Array,
    required: true,
  },
})

defineEmits(['refresh'])

function dotClass(status) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'running'
  if (status === 'pending') return 'pending'
  return 'default'
}
</script>

<style scoped>
.data-card {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #E2E8F0);
  border-radius: 12px;
  overflow: hidden;
}

.data-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 12px;
}

.data-card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary, #0F172A);
  margin: 0;
}

.refresh-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 6px;
  color: var(--text-secondary, #94A3B8);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.refresh-btn:hover {
  background: var(--sidebar-hover-bg, #F1F5F9);
  color: var(--primary-color, #4F46E5);
}

.data-card-body {
  padding: 0 20px 16px;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-item {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  position: relative;
}
.timeline-item + .timeline-item {
  border-top: 1px solid var(--border-color, #F1F5F9);
}

.timeline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 5px;
}
.timeline-dot.success { background: #10B981; }
.timeline-dot.danger { background: #F43F5E; }
.timeline-dot.running {
  background: #4F46E5;
  animation: pulse 1.5s infinite;
}
.timeline-dot.pending { background: #94A3B8; }
.timeline-dot.default { background: #CBD5E1; }

.timeline-content {
  min-width: 0;
  flex: 1;
}

.timeline-action {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-primary, #0F172A);
}

.timeline-desc {
  font-size: 0.75rem;
  color: var(--text-secondary, #64748B);
  margin-top: 2px;
}

.timeline-time {
  font-size: 0.7rem;
  color: var(--text-secondary, #94A3B8);
  margin-top: 3px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
