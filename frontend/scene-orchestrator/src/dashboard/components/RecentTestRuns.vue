<template>
  <div class="data-card">
    <div class="data-card-header">
      <h3 class="data-card-title">最近测试运行</h3>
      <a href="/test-suites-vue/#/test-runs" class="view-all-link">
        查看全部
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <path d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </a>
    </div>
    <div class="data-card-body">
      <div v-loading="loading" element-loading-text="加载中...">
        <el-empty v-if="!loading && runs.results.length === 0" description="暂无测试运行" :image-size="80" />

        <div v-else class="runs-list">
          <a
            v-for="run in runs.results"
            :key="run.id"
            :href="run.detailUrl"
            class="run-item"
          >
            <div class="run-info">
              <span class="run-name">{{ run.name }}</span>
              <span class="run-meta">
                {{ run.projectName }}
                <span v-if="run.environmentName" class="meta-sep">&middot;</span>
                <span v-if="run.environmentName">{{ run.environmentName }}</span>
              </span>
            </div>
            <div class="run-right">
              <span class="run-status" :class="statusClass(run.status)">
                {{ statusLabel(run.status) }}
              </span>
              <span class="run-time">{{ run.createdAt }}</span>
            </div>
          </a>
        </div>

        <div v-if="runs.totalPages > 1" class="pagination-wrap">
          <el-pagination
            :current-page="runs.currentPage"
            :page-size="5"
            :total="runs.total"
            layout="prev, pager, next"
            small
            @current-change="$emit('page-change', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  runs: {
    type: Object,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['page-change'])

const STATUS_MAP = {
  completed: { cls: 'success', label: '已完成' },
  failed: { cls: 'danger', label: '失败' },
  running: { cls: 'running', label: '运行中' },
  pending: { cls: 'pending', label: '等待中' },
}

function statusClass(status) {
  return STATUS_MAP[status]?.cls || 'pending'
}
function statusLabel(status) {
  return STATUS_MAP[status]?.label || status
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

.runs-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.run-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  text-decoration: none;
  transition: background 0.15s;
  gap: 12px;
}
.run-item:hover {
  background: var(--sidebar-hover-bg, #F8FAFC);
}

.run-info {
  min-width: 0;
  flex: 1;
}
.run-name {
  display: block;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-primary, #0F172A);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.run-meta {
  display: block;
  font-size: 0.72rem;
  color: var(--text-secondary, #94A3B8);
  margin-top: 2px;
}
.meta-sep {
  margin: 0 4px;
}

.run-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  gap: 3px;
}

.run-status {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 500;
}
.run-status.success {
  background: rgba(16, 185, 129, 0.08);
  color: #059669;
}
.run-status.danger {
  background: rgba(244, 63, 94, 0.08);
  color: #E11D48;
}
.run-status.running {
  background: rgba(79, 70, 229, 0.08);
  color: #4F46E5;
}
.run-status.pending {
  background: rgba(100, 116, 139, 0.08);
  color: #64748B;
}

.run-time {
  font-size: 0.7rem;
  color: var(--text-secondary, #94A3B8);
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding-top: 12px;
}
</style>
