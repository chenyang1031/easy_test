import { createRouter, createWebHashHistory } from 'vue-router'
import MainLayout from './layouts/MainLayout.vue'

/**
 * 统一 SPA 路由表
 *
 * 合并所有现有 Vue SPA 的路由，使用 lazy loading。
 * 路由前缀尽量与 sidebar menuData 中的 matchHashes 保持一致。
 *
 * 路由结构：
 *   认证页面（/login, /register, /password-reset） — 使用 AuthLayout 空白布局
 *   应用页面（/dashboard, /projects, ...）        — 使用 MainLayout（侧栏+顶栏）
 */

const routes = [
  // =====================================================================
  //  认证页面（无 MainLayout，使用 AuthLayout 空白布局）
  // =====================================================================
  {
    path: '/login',
    component: () => import('../views/auth/AuthLayout.vue'),
    children: [
      {
        path: '',
        name: 'login',
        component: () => import('../views/auth/LoginPage.vue'),
        meta: { title: '登录', authPage: true },
      },
    ],
  },
  {
    path: '/register',
    component: () => import('../views/auth/AuthLayout.vue'),
    children: [
      {
        path: '',
        name: 'register',
        component: () => import('../views/auth/RegisterPage.vue'),
        meta: { title: '注册', authPage: true },
      },
    ],
  },
  {
    path: '/password-reset',
    component: () => import('../views/auth/AuthLayout.vue'),
    children: [
      {
        path: '',
        name: 'passwordReset',
        component: () => import('../views/auth/PasswordResetRequestPage.vue'),
        meta: { title: '重置密码', authPage: true },
      },
    ],
  },

  // =====================================================================
  //  应用页面（MainLayout）
  // =====================================================================
  {
    path: '/',
    component: MainLayout,
    children: [
      // ===== 根重定向 =====
      { path: '', redirect: '/dashboard' },

      // ===== 仪表盘 =====
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('../dashboard/App.vue'),
        meta: { title: '仪表盘' },
      },

      // ===== 项目管理 =====
      {
        path: 'projects',
        name: 'projectList',
        component: () => import('./views/projects/ProjectListPage.vue'),
        meta: { title: '项目管理' },
      },
      {
        path: 'projects/create',
        name: 'projectCreate',
        component: () => import('./views/projects/ProjectFormPage.vue'),
        meta: { title: '新建项目' },
      },
      {
        path: 'projects/:id',
        name: 'projectDetail',
        component: () => import('./views/projects/ProjectDetailPage.vue'),
        props: true,
        meta: { title: '项目详情' },
      },
      {
        path: 'projects/:id/edit',
        name: 'projectEdit',
        component: () => import('./views/projects/ProjectFormPage.vue'),
        props: true,
        meta: { title: '编辑项目' },
      },

      // ===== 环境管理 =====
      {
        path: 'environments',
        name: 'environmentList',
        component: () => import('./views/environments/EnvironmentListPage.vue'),
        meta: { title: '环境管理' },
      },
      {
        path: 'environments/create',
        name: 'environmentCreate',
        component: () => import('./views/environments/EnvironmentFormPage.vue'),
        meta: { title: '新建环境' },
      },
      {
        path: 'environments/:id',
        name: 'environmentDetail',
        component: () => import('./views/environments/EnvironmentDetailPage.vue'),
        props: true,
        meta: { title: '环境详情' },
      },
      {
        path: 'environments/:id/edit',
        name: 'environmentEdit',
        component: () => import('./views/environments/EnvironmentFormPage.vue'),
        props: true,
        meta: { title: '编辑环境' },
      },

      // ===== 测试用例分组 =====
      {
        path: 'test-case-groups',
        name: 'tcgList',
        component: () => import('../test-manager/views/TestCaseGroupList.vue'),
        meta: { title: '测试用例分组' },
      },

      // ===== 测试用例 =====
      {
        path: 'test-cases',
        name: 'tcList',
        component: () => import('../test-manager/views/TestCaseList.vue'),
        meta: { title: '测试用例' },
      },
      {
        path: 'test-cases/create',
        name: 'tcCreate',
        component: () => import('../test-manager/views/TestCaseForm.vue'),
        meta: { title: '新建测试用例' },
      },
      {
        path: 'test-cases/:id',
        name: 'tcDetail',
        component: () => import('../test-manager/views/TestCaseDetail.vue'),
        props: true,
        meta: { title: '测试用例详情' },
      },
      {
        path: 'test-cases/:id/edit',
        name: 'tcEdit',
        component: () => import('../test-manager/views/TestCaseForm.vue'),
        props: true,
        meta: { title: '编辑测试用例' },
      },
      {
        path: 'test-cases/:id/run',
        name: 'tcRun',
        component: () => import('../test-manager/views/TestCaseRun.vue'),
        props: true,
        meta: { title: '执行测试用例' },
      },

      // ===== 测试套件分组 =====
      {
        path: 'test-suite-groups',
        name: 'tsgList',
        component: () => import('../test-manager/views/TestSuiteGroupList.vue'),
        meta: { title: '测试套件分组' },
      },

      // ===== 测试套件 =====
      {
        path: 'test-suites',
        name: 'tsList',
        component: () => import('../test-manager/views/TestSuiteList.vue'),
        meta: { title: '测试套件' },
      },
      {
        path: 'test-suites/create',
        name: 'tsCreate',
        component: () => import('../test-manager/views/TestSuiteForm.vue'),
        meta: { title: '新建测试套件' },
      },
      {
        path: 'test-suites/:id',
        name: 'tsDetail',
        component: () => import('../test-manager/views/TestSuiteDetail.vue'),
        props: true,
        meta: { title: '测试套件详情' },
      },
      {
        path: 'test-suites/:id/edit',
        name: 'tsEdit',
        component: () => import('../test-manager/views/TestSuiteForm.vue'),
        props: true,
        meta: { title: '编辑测试套件' },
      },
      {
        path: 'test-suites/:id/run',
        name: 'tsRun',
        component: () => import('../test-manager/views/TestSuiteRun.vue'),
        props: true,
        meta: { title: '执行测试套件' },
      },

      // ===== 测试运行 =====
      {
        path: 'test-runs',
        name: 'trList',
        component: () => import('../test-manager/views/TestRunList.vue'),
        meta: { title: '测试运行' },
      },
      {
        path: 'test-runs/:id',
        name: 'trDetail',
        component: () => import('../test-manager/views/TestRunDetail.vue'),
        props: true,
        meta: { title: '测试运行详情' },
      },
      {
        path: 'test-runs/:testRunId/generate-report',
        name: 'testRunReportForm',
        component: () => import('../views/reports/TestRunReportForm.vue'),
        props: true,
        meta: { title: '生成测试报告' },
      },

      // ===== 场景执行 =====
      {
        path: 'scene-executions',
        name: 'seList',
        component: () => import('../test-manager/views/SceneExecutionList.vue'),
        meta: { title: '场景执行' },
      },
      {
        path: 'scene-executions/:id',
        name: 'seDetail',
        component: () => import('../test-manager/views/SceneExecutionDetail.vue'),
        props: true,
        meta: { title: '场景执行详情' },
      },
      {
        path: 'scene-executions/:executionId/generate-report',
        name: 'sceneExecutionReportForm',
        component: () => import('../views/reports/SceneExecutionReportForm.vue'),
        props: true,
        meta: { title: '生成测试报告' },
      },

      // ===== API 资产管理 =====
      {
        path: 'api-assets',
        name: 'apiAssetList',
        component: () => import('../api-asset-manager/views/AssetList.vue'),
        meta: { title: 'API 资产管理' },
      },
      {
        path: 'api-assets/create',
        name: 'apiAssetCreate',
        component: () => import('../api-asset-manager/views/AssetFormPage.vue'),
        meta: { title: '新建 API 资产' },
      },
      {
        path: 'api-assets/edit/:id',
        name: 'apiAssetEdit',
        component: () => import('../api-asset-manager/views/AssetFormPage.vue'),
        props: true,
        meta: { title: '编辑 API 资产' },
      },

      // ===== 测试场景编排 =====
      {
        path: 'scenes',
        name: 'scene-list',
        component: () => import('../pages/SceneListPage.vue'),
        meta: { title: '测试场景编排' },
      },
      {
        path: 'scenes/:id/designer',
        name: 'scene-designer',
        component: () => import('../pages/SceneDesignerPage.vue'),
        props: true,
        meta: { title: '编辑场景详情' },
      },
      {
        path: 'scenes/:id/executions/:executionId?',
        name: 'scene-execution',
        component: () => import('../pages/SceneExecutionPage.vue'),
        props: true,
        meta: { title: '执行日志' },
      },

      // ===== 性能测试 =====
      {
        path: 'performance',
        name: 'perf-list',
        component: () => import('../views/performance/PerformanceTaskList.vue'),
        meta: { title: '性能测试' },
      },
      {
        path: 'performance/tasks/new',
        name: 'perf-task-new',
        component: () => import('../views/performance/PerformanceTaskEditor.vue'),
        meta: { title: '新建性能任务' },
      },
      {
        path: 'performance/tasks/:id/edit',
        name: 'perf-task-edit',
        component: () => import('../views/performance/PerformanceTaskEditor.vue'),
        meta: { title: '编辑性能任务' },
      },
      {
        path: 'performance/tasks/:id/console',
        name: 'perf-console',
        component: () => import('../views/performance/PerformanceConsole.vue'),
        meta: { title: '压测控制台' },
      },
      {
        path: 'performance/tasks/:id/report',
        name: 'perf-report',
        component: () => import('../views/performance/PerformanceReport.vue'),
        meta: { title: '性能测试报告' },
      },

      // ===== Mock 数据 =====
      {
        path: 'mock-data',
        name: 'mdList',
        component: () => import('../mock-data/views/MockDataList.vue'),
        meta: { title: 'Mock 数据' },
      },
      {
        path: 'mock-data/create',
        name: 'mdCreate',
        component: () => import('../mock-data/views/MockDataForm.vue'),
        meta: { title: '新建 Mock 数据' },
      },

      // ===== 测试报告 =====
      {
        path: 'reports',
        name: 'reportList',
        component: () => import('../views/reports/ReportListPage.vue'),
        meta: { title: '测试报告' },
      },
      {
        path: 'reports/create',
        name: 'reportCreate',
        component: () => import('../views/reports/ReportFormPage.vue'),
        meta: { title: '新建测试报告' },
      },
      {
        path: 'reports/:id',
        name: 'reportDetail',
        component: () => import('../views/reports/ReportDetailPage.vue'),
        props: true,
        meta: { title: '测试报告详情' },
      },
      {
        path: 'reports/:id/edit',
        name: 'reportEdit',
        component: () => import('../views/reports/ReportFormPage.vue'),
        props: true,
        meta: { title: '编辑测试报告' },
      },

      // ===== 定时任务 =====
      {
        path: 'scheduled-tasks',
        name: 'scheduledTaskList',
        component: () => import('../views/scheduled-tasks/ScheduledTaskList.vue'),
        meta: { title: '定时任务' },
      },
      {
        path: 'scheduled-tasks/create',
        name: 'scheduledTaskCreate',
        component: () => import('../views/scheduled-tasks/ScheduledTaskForm.vue'),
        meta: { title: '新建定时任务' },
      },
      {
        path: 'scheduled-tasks/:id',
        name: 'scheduledTaskDetail',
        component: () => import('../views/scheduled-tasks/ScheduledTaskDetail.vue'),
        props: true,
        meta: { title: '定时任务详情' },
      },
      {
        path: 'scheduled-tasks/:id/edit',
        name: 'scheduledTaskEdit',
        component: () => import('../views/scheduled-tasks/ScheduledTaskForm.vue'),
        props: true,
        meta: { title: '编辑定时任务' },
      },

      // ===== 任务监控 =====
      {
        path: 'task-monitor',
        name: 'taskMonitor',
        component: () => import('../views/scheduled-tasks/TaskMonitor.vue'),
        meta: { title: '任务监控' },
      },

      // ===== AI 草稿箱 =====
      {
        path: 'ai/draft-box',
        name: 'aiDraftBox',
        component: () => import('../draft-box/App.vue'),
        meta: { title: 'AI 草稿箱' },
      },

      // ===== AI 生成记录 =====
      {
        path: 'ai/records',
        name: 'aiGenRecord',
        component: () => import('../ai-gen-record/App.vue'),
        meta: { title: 'AI 生成记录' },
      },

      // ===== AI 规则管理 =====
      {
        path: 'ai/rules',
        name: 'aiRules',
        component: () => import('../rule-manager/App.vue'),
        meta: { title: 'AI 规则管理' },
      },

      // ===== AI 提示词管理 =====
      {
        path: 'ai/prompt-templates',
        name: 'aiPromptTemplates',
        component: () => import('../prompt-template-manager/App.vue'),
        meta: { title: 'AI 提示词管理' },
      },

      // ===== AI 大模型管理 =====
      {
        path: 'ai/model-providers',
        name: 'aiModelProviders',
        component: () => import('../model-provider-manager/App.vue'),
        meta: { title: 'AI 大模型管理' },
      },

      // ===== 文档导入 API 资产 =====
      {
        path: 'ai/document-import',
        name: 'aiDocumentImport',
        component: () => import('../document-import/App.vue'),
        meta: { title: '文档导入 API 资产' },
      },

      // ===== 用户设置（MainLayout 内）=====
      {
        path: 'settings/profile',
        name: 'settingsProfile',
        component: () => import('./views/settings/ProfilePage.vue'),
        meta: { title: '个人资料' },
      },
      {
        path: 'settings/password',
        name: 'settingsPassword',
        component: () => import('./views/settings/PasswordChangePage.vue'),
        meta: { title: '修改密码' },
      },

      // ===== 执行日志 =====
      {
        path: 'task-execution-logs',
        name: 'taskExecutionLogList',
        component: () => import('../views/scheduled-tasks/TaskExecutionLogList.vue'),
        meta: { title: '执行日志' },
      },
      {
        path: 'task-execution-logs/:id',
        name: 'taskExecutionLogDetail',
        component: () => import('../views/scheduled-tasks/TaskExecutionLogDetail.vue'),
        props: true,
        meta: { title: '执行日志详情' },
      },

      // ===== 邮件配置 =====
      {
        path: 'email-config',
        name: 'emailConfigList',
        component: () => import('../views/email-config/EmailConfigList.vue'),
        meta: { title: '邮件配置' },
      },
      {
        path: 'email-config/create',
        name: 'emailConfigCreate',
        component: () => import('../views/email-config/EmailConfigForm.vue'),
        meta: { title: '添加邮件配置' },
      },
      {
        path: 'email-config/:id/edit',
        name: 'emailConfigEdit',
        component: () => import('../views/email-config/EmailConfigForm.vue'),
        props: true,
        meta: { title: '编辑邮件配置' },
      },

      // ===== 参数配置 =====
      {
        path: 'parameter-config',
        name: 'parameterConfigList',
        component: () => import('../views/parameter-config/ParameterConfigList.vue'),
        meta: { title: '参数配置' },
      },
    ],
  },

  // =====================================================================
  //  通配路由 — 未匹配到任何路由时跳转到首页
  // =====================================================================
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// =====================================================================
//  导航守卫 — 检查登录状态
// =====================================================================
const publicRoutes = ['login', 'register', 'passwordReset']

router.beforeEach((to, from, next) => {
  // 更新页面标题
  const title = to.meta?.title
    ? `${to.meta.title} - EasyTesting`
    : 'EasyTesting'
  document.title = title

  // 允许访问公开页面
  if (publicRoutes.includes(to.name)) {
    // 如果已登录则跳转到仪表盘
    const isAuth = window.__APP_STATE__?.userAuthenticated === true
    if (isAuth && to.name === 'login') {
      next({ name: 'dashboard' })
      return
    }
    next()
    return
  }

  // 未登录保护 — 已登录用户直接通过
  const isAuth = window.__APP_STATE__?.userAuthenticated === true
  if (!isAuth) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  next()
})

export default router
