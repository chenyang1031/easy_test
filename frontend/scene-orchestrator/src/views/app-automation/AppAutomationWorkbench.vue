<template>
  <div class="app-automation-workbench">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">APP 自动化工作台</h2>
        <span class="page-subtitle">用例编排、执行与报告统一入口；项目/设备/包名/元素等资源从 Dashboard 快捷卡进入</span>
      </div>
    </div>

    <el-tabs v-model="activeTab" type="border-card" class="workbench-tabs">
      <el-tab-pane label="Dashboard" name="dashboard" lazy>
        <Dashboard v-if="activeTab === 'dashboard'" />
      </el-tab-pane>
      <el-tab-pane label="用例编排" name="scene-builder" lazy>
        <SceneBuilder v-if="activeTab === 'scene-builder'" />
      </el-tab-pane>
      <el-tab-pane label="测试用例" name="test-cases" lazy>
        <TestCaseList v-if="activeTab === 'test-cases'" />
      </el-tab-pane>
      <el-tab-pane label="测试套件" name="test-suites" lazy>
        <SuiteList v-if="activeTab === 'test-suites'" />
      </el-tab-pane>
      <el-tab-pane label="执行记录" name="executions" lazy>
        <ExecutionList v-if="activeTab === 'executions'" />
      </el-tab-pane>
      <el-tab-pane label="测试报告" name="reports" lazy>
        <ReportList v-if="activeTab === 'reports'" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Dashboard from './dashboard/Dashboard.vue'
import SceneBuilder from './test-cases/SceneBuilder.vue'
import TestCaseList from './test-cases/TestCaseList.vue'
import SuiteList from './suites/SuiteList.vue'
import ExecutionList from './executions/ExecutionList.vue'
import ReportList from './reports/ReportList.vue'

const route = useRoute()
const router = useRouter()

const TABS = ['dashboard', 'scene-builder', 'test-cases', 'test-suites', 'executions', 'reports']

// 支持 ?tab= 直达对应页签（旧路由重定向进来时携带）
const activeTab = ref(TABS.includes(route.query.tab) ? route.query.tab : 'dashboard')

watch(() => route.query.tab, (v) => {
  if (TABS.includes(v)) activeTab.value = v
})

// 页签切换同步地址栏，便于收藏/分享具体页签
watch(activeTab, (v) => {
  if (route.query.tab !== v) {
    router.replace({ query: { ...route.query, tab: v } })
  }
})
</script>

<style scoped>
.app-automation-workbench { display: flex; flex-direction: column; gap: 12px; }
.page-header { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.page-title { font-size: 20px; font-weight: 600; color: #303133; margin: 0; }
.page-subtitle { font-size: 13px; color: #909399; }
.workbench-tabs :deep(.el-tabs__content) { padding: 12px; }
</style>
