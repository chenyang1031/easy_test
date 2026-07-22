<template>
  <div class="data-card">
    <div class="data-card-header">
      <h3 class="data-card-title">快捷操作</h3>
    </div>
    <div class="data-card-body">
      <a
        v-for="item in actions"
        :key="item.label"
        :href="item.link"
        class="quick-action"
      >
        <div class="action-icon" :class="item.accent">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"
            v-html="item.iconPath"
          ></svg>
        </div>
        <div class="action-text">
          <div class="action-label">{{ item.label }}</div>
          <div class="action-desc">{{ item.desc }}</div>
        </div>
      </a>
    </div>
  </div>
</template>

<script setup>
const actions = [
  {
    label: '创建项目',
    desc: '添加一个新的项目',
    link: '/projects/create/',
    accent: 'indigo',
    iconPath: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /><line x1="12" y1="11" x2="12" y2="17" /><line x1="9" y1="14" x2="15" y2="14" />',
  },
  {
    label: '创建用例',
    desc: '新增一个测试用例',
    link: '/test-cases-vue/#/test-cases/create',
    accent: 'emerald',
    iconPath: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="12" y1="18" x2="12" y2="12" /><line x1="9" y1="15" x2="15" y2="15" />',
  },
  {
    label: '创建测试套件',
    desc: '组织测试套件',
    link: '/test-suites-vue/#/test-suites/create',
    accent: 'violet',
    iconPath: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />',
  },
  {
    label: '配置环境',
    desc: '配置环境信息',
    link: '/environments/create/',
    accent: 'amber',
    iconPath: '<circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />',
  },
]
</script>

<style scoped>
.data-card {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #E2E8F0);
  border-radius: 12px;
  overflow: hidden;
}

.data-card-header {
  padding: 16px 20px 12px;
}

.data-card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary, #0F172A);
  margin: 0;
}

.data-card-body {
  padding: 0 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.quick-action {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  text-decoration: none;
  transition: background 0.15s;
}
.quick-action:hover {
  background: var(--sidebar-hover-bg, #F8FAFC);
}

.action-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-icon.indigo {
  background: rgba(79, 70, 229, 0.08);
  color: #4F46E5;
}
.action-icon.emerald {
  background: rgba(16, 185, 129, 0.08);
  color: #10B981;
}
.action-icon.violet {
  background: rgba(124, 58, 237, 0.08);
  color: #7C3AED;
}
.action-icon.amber {
  background: rgba(245, 158, 11, 0.08);
  color: #F59E0B;
}

.action-text {
  min-width: 0;
}
.action-label {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-primary, #0F172A);
}
.action-desc {
  font-size: 0.72rem;
  color: var(--text-secondary, #94A3B8);
  margin-top: 1px;
}
</style>
