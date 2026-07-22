<template>
  <div class="stat-cards-row">
    <a
      v-for="card in cards"
      :key="card.key"
      :href="card.link"
      class="stat-card"
      :class="card.accent"
    >
      <div class="stat-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"
          v-html="card.icon"
        ></svg>
      </div>
      <div class="stat-body">
        <div class="stat-value">{{ stats[card.key] }}</div>
        <div class="stat-label">{{ card.label }}</div>
      </div>
    </a>
  </div>
</template>

<script setup>
defineProps({
  stats: {
    type: Object,
    required: true,
  },
})

const cards = [
  {
    key: 'projects',
    label: '项目',
    accent: 'indigo',
    link: '/projects/',
    icon: '<rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />',
  },
  {
    key: 'testCases',
    label: '测试用例',
    accent: 'emerald',
    link: '/test-cases-vue/#/test-cases',
    icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />',
  },
  {
    key: 'testSuites',
    label: '测试套件',
    accent: 'violet',
    link: '/test-suites-vue/#/test-suites',
    icon: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />',
  },
  {
    key: 'testRuns',
    label: '测试运行',
    accent: 'amber',
    link: '/test-suites-vue/#/test-runs',
    icon: '<polygon points="5 3 19 12 5 21 5 3" />',
  },
  {
    key: 'reports',
    label: '测试报告',
    accent: 'rose',
    link: '/reports/',
    icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />',
  },
  {
    key: 'testScenes',
    label: '测试场景',
    accent: 'cyan',
    link: '/test-scene-orchestrator/',
    icon: '<circle cx="12" cy="12" r="10" /><polygon points="10 8 16 12 10 16 10 8" />',
  },
  {
    key: 'sceneExecutions',
    label: '场景执行',
    accent: 'teal',
    link: '/test-suites-vue/#/scene-executions',
    icon: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />',
  },
]
</script>

<style scoped>
.stat-cards-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #E2E8F0);
  border-radius: 12px;
  border-left: 4px solid;
  text-decoration: none;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
}

/* 图标容器 */
.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* 文字区域 */
.stat-body {
  min-width: 0;
}
.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1.2;
  color: var(--text-primary, #0F172A);
  font-variant-numeric: tabular-nums;
}
.stat-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary, #64748B);
  margin-top: 2px;
}

/* ============ 配色方案 ============ */
.stat-card.indigo {
  border-left-color: #4F46E5;
}
.stat-card.indigo .stat-icon {
  background: rgba(79, 70, 229, 0.08);
  color: #4F46E5;
}

.stat-card.emerald {
  border-left-color: #10B981;
}
.stat-card.emerald .stat-icon {
  background: rgba(16, 185, 129, 0.08);
  color: #10B981;
}

.stat-card.violet {
  border-left-color: #7C3AED;
}
.stat-card.violet .stat-icon {
  background: rgba(124, 58, 237, 0.08);
  color: #7C3AED;
}

.stat-card.amber {
  border-left-color: #F59E0B;
}
.stat-card.amber .stat-icon {
  background: rgba(245, 158, 11, 0.08);
  color: #F59E0B;
}

.stat-card.rose {
  border-left-color: #F43F5E;
}
.stat-card.rose .stat-icon {
  background: rgba(244, 63, 94, 0.08);
  color: #F43F5E;
}

.stat-card.cyan {
  border-left-color: #06B6D4;
}
.stat-card.cyan .stat-icon {
  background: rgba(6, 182, 212, 0.08);
  color: #06B6D4;
}

.stat-card.teal {
  border-left-color: #14B8A6;
}
.stat-card.teal .stat-icon {
  background: rgba(20, 184, 166, 0.08);
  color: #14B8A6;
}

/* ============ 响应式 ============ */
@media (max-width: 768px) {
  .stat-cards-row {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
  }
  .stat-card {
    padding: 14px 16px;
    gap: 10px;
  }
  .stat-icon {
    width: 36px;
    height: 36px;
  }
  .stat-value {
    font-size: 1.3rem;
  }
}
</style>
