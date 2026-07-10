import { createRouter, createWebHashHistory } from 'vue-router'
import TestCaseList from './views/TestCaseList.vue'
import TestCaseDetail from './views/TestCaseDetail.vue'
import TestCaseForm from './views/TestCaseForm.vue'
import TestCaseRun from './views/TestCaseRun.vue'
import TestCaseGroupList from './views/TestCaseGroupList.vue'
import TestSuiteList from './views/TestSuiteList.vue'
import TestSuiteDetail from './views/TestSuiteDetail.vue'
import TestSuiteForm from './views/TestSuiteForm.vue'
import TestSuiteRun from './views/TestSuiteRun.vue'
import TestSuiteGroupList from './views/TestSuiteGroupList.vue'
import TestRunList from './views/TestRunList.vue'
import TestRunDetail from './views/TestRunDetail.vue'
import SceneExecutionList from './views/SceneExecutionList.vue'
import SceneExecutionDetail from './views/SceneExecutionDetail.vue'

const routes = [
  { path: '/', redirect: '/test-cases' },
  // 测试用例分组
  { path: '/test-case-groups', name: 'tcgList', component: TestCaseGroupList },
  // 测试用例
  { path: '/test-cases', name: 'tcList', component: TestCaseList },
  { path: '/test-cases/create', name: 'tcCreate', component: TestCaseForm },
  { path: '/test-cases/:id', name: 'tcDetail', component: TestCaseDetail, props: true },
  { path: '/test-cases/:id/edit', name: 'tcEdit', component: TestCaseForm, props: true },
  { path: '/test-cases/:id/run', name: 'tcRun', component: TestCaseRun, props: true },
  // 测试套件分组
  { path: '/test-suite-groups', name: 'tsgList', component: TestSuiteGroupList },
  // 测试套件
  { path: '/test-suites', name: 'tsList', component: TestSuiteList },
  { path: '/test-suites/create', name: 'tsCreate', component: TestSuiteForm },
  { path: '/test-suites/:id', name: 'tsDetail', component: TestSuiteDetail, props: true },
  { path: '/test-suites/:id/edit', name: 'tsEdit', component: TestSuiteForm, props: true },
  { path: '/test-suites/:id/run', name: 'tsRun', component: TestSuiteRun, props: true },
  // 测试运行
  { path: '/test-runs', name: 'trList', component: TestRunList },
  { path: '/test-runs/:id', name: 'trDetail', component: TestRunDetail, props: true },
  // 场景执行
  { path: '/scene-executions', name: 'seList', component: SceneExecutionList },
  { path: '/scene-executions/:id', name: 'seDetail', component: SceneExecutionDetail, props: true },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
