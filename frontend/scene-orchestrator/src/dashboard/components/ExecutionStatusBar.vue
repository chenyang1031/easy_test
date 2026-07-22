<template>
  <div class="status-bar">
    <span class="status-bar-label">场景执行状态</span>
    <div class="status-bar-tags">
      <span class="status-tag running" v-if="dist.running">
        <span class="status-dot"></span>
        {{ dist.running }} 执行中
      </span>
      <span class="status-tag success" v-if="dist.success">
        <span class="status-dot"></span>
        {{ dist.success }} 成功
      </span>
      <span class="status-tag partial" v-if="dist.partialSuccess">
        <span class="status-dot"></span>
        {{ dist.partialSuccess }} 部分成功
      </span>
      <span class="status-tag failed" v-if="dist.failed">
        <span class="status-dot"></span>
        {{ dist.failed }} 失败
      </span>
      <span v-if="!dist.running && !dist.success && !dist.partialSuccess && !dist.failed" class="status-empty">
        暂无执行记录
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  dist: {
    type: Object,
    required: true,
  },
})
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #E2E8F0);
  border-radius: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.status-bar-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary, #64748B);
  white-space: nowrap;
}

.status-bar-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-tag.running {
  background: rgba(79, 70, 229, 0.06);
  color: #4F46E5;
}
.status-tag.running .status-dot {
  background: #4F46E5;
  animation: pulse 1.5s infinite;
}

.status-tag.success {
  background: rgba(16, 185, 129, 0.06);
  color: #059669;
}
.status-tag.success .status-dot {
  background: #10B981;
}

.status-tag.partial {
  background: rgba(245, 158, 11, 0.06);
  color: #D97706;
}
.status-tag.partial .status-dot {
  background: #F59E0B;
}

.status-tag.failed {
  background: rgba(244, 63, 94, 0.06);
  color: #E11D48;
}
.status-tag.failed .status-dot {
  background: #F43F5E;
}

.status-empty {
  font-size: 0.78rem;
  color: var(--text-secondary, #94A3B8);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
