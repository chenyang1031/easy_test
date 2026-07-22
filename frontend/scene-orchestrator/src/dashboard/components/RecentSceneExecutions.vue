<template>
  <div class="data-card">
    <div class="data-card-header">
      <h3 class="data-card-title">最近场景执行</h3>
      <a href="/test-suites-vue/#/scene-executions" class="view-all-link">
        查看全部
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <path d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </a>
    </div>
    <div class="data-card-body">
      <el-empty v-if="executions.length === 0" description="暂无场景执行记录" :image-size="80" />

      <div v-else class="exec-list">
        <a
          v-for="ex in executions"
          :key="ex.sceneId + '-' + ex.createdAt"
          :href="`/test-scene-orchestrator/#/scenes/${ex.sceneId}/executions/${ex.executionId}`"
          class="exec-item"
        >
          <div class="exec-info">
            <span class="exec-name">{{ ex.sceneName }}</span>
            <span class="exec-meta">
              {{ ex.environmentName }}
              <span v-if="ex.durationDisplay" class="meta-sep">&middot;</span>
              <span v-if="ex.durationDisplay">{{ ex.durationDisplay }}</span>
            </span>
          </div>
          <div class="exec-right">
            <span class="exec-status" :class="statusClass(ex.status)">
              {{ statusLabel(ex.status) }}
            </span>
            <span class="exec-time">{{ ex.startedAt }}</span>
          </div>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  executions: {
    type: Array,
    required: true,
  },
})

const SCENE_STATUS_MAP = {
  success: { cls: 'success', label: '成功' },
  failed: { cls: 'danger', label: '失败' },
  running: { cls: 'running', label: '执行中' },
  partial_success: { cls: 'partial', label: '部分成功' },
  stopped: { cls: 'partial', label: '已停止' },
}

function statusClass(status) {
  return SCENE_STATUS_MAP[status]?.cls || 'pending'
}
function statusLabel(status) {
  return SCENE_STATUS_MAP[status]?.label || status
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

.view-all-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--primary-color, #4F46E5);
  text-decoration: none;
  font-weight: 500;
  transition: opacity 0.15s;
}
.view-all-link:hover {
  opacity: 0.75;
}

.data-card-body {
  padding: 0 20px 16px;
}

.exec-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.exec-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  text-decoration: none;
  transition: background 0.15s;
  gap: 12px;
}
.exec-item:hover {
  background: var(--sidebar-hover-bg, #F8FAFC);
}

.exec-info {
  min-width: 0;
  flex: 1;
}
.exec-name {
  display: block;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-primary, #0F172A);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.exec-meta {
  display: block;
  font-size: 0.72rem;
  color: var(--text-secondary, #94A3B8);
  margin-top: 2px;
}
.meta-sep {
  margin: 0 4px;
}

.exec-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  gap: 3px;
}

.exec-status {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 500;
}
.exec-status.success {
  background: rgba(16, 185, 129, 0.08);
  color: #059669;
}
.exec-status.danger {
  background: rgba(244, 63, 94, 0.08);
  color: #E11D48;
}
.exec-status.running {
  background: rgba(79, 70, 229, 0.08);
  color: #4F46E5;
}
.exec-status.partial {
  background: rgba(245, 158, 11, 0.08);
  color: #D97706;
}
.exec-status.pending {
  background: rgba(100, 116, 139, 0.08);
  color: #64748B;
}

.exec-time {
  font-size: 0.7rem;
  color: var(--text-secondary, #94A3B8);
}
</style>
