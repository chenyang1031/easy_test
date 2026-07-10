<template>
  <div class="stat-cards-row">
    <div
      v-for="card in cards"
      :key="card.key"
      class="stat-card-wrapper"
    >
      <div class="card h-100">
        <div class="card-body stat-card" :class="card.color">
          <div class="stat-title">{{ card.label }}</div>
          <a :href="card.link" class="stat-value">{{ stats[card.key] }}</a>
        </div>
      </div>
    </div>
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
  { key: 'projects',         label: '项目',         color: 'primary', link: '/projects/' },
  { key: 'testCases',       label: '测试用例',      color: 'success', link: '/test-cases-vue/#/test-cases' },
  { key: 'testSuites',      label: '测试套件',      color: 'info',    link: '/test-suites-vue/#/test-suites' },
  { key: 'testRuns',        label: '测试运行',      color: 'warning', link: '/test-suites-vue/#/test-runs' },
  { key: 'reports',         label: '测试报告',      color: 'danger',  link: '/reports/' },
  { key: 'testScenes',      label: '测试场景',      color: 'primary', link: '/test-scene-orchestrator/' },
  { key: 'sceneExecutions', label: '场景执行',      color: 'info',    link: '/test-suites-vue/#/scene-executions' },
]
</script>

<style scoped>
.stat-cards-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.stat-card-wrapper .card {
  margin-bottom: 0;
}
.stat-card {
  border-radius: 10px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.stat-card .stat-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: #6c757d;
  margin-bottom: 0.5rem;
}
.stat-card .stat-value {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  display: inline-block;
  text-decoration: underline;
  text-underline-offset: 3px;
  color: inherit;
  cursor: pointer;
}
.stat-card .stat-value:hover {
  opacity: 0.75;
}

.stat-card.primary {
  background-color: rgba(67, 97, 238, 0.1);
  color: #4361ee;
}
.stat-card.success {
  background-color: rgba(76, 201, 240, 0.1);
  color: #4cc9f0;
}
.stat-card.info {
  background-color: rgba(72, 149, 239, 0.1);
  color: #4895ef;
}
.stat-card.warning {
  background-color: rgba(247, 37, 133, 0.1);
  color: #f72585;
}
.stat-card.danger {
  background-color: rgba(230, 57, 70, 0.1);
  color: #e63946;
}
</style>
