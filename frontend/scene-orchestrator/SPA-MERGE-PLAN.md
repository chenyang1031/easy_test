# SPA 合并 & 全 Vue 迁移实施方案

## 一、目标架构

### 当前架构（多入口 SPA + Django 模板混合）

```
用户访问 → Django URL 路由
  ├── /dashboard/              → dashboard.html        → mount dashboard SPA
  ├── /test-cases-vue/#/tc     → test_manager_vue.html → mount test-manager SPA
  ├── /test-suites-vue/#/ts    → test_manager_vue.html → mount test-manager SPA
  ├── /api-asset-manager/      → api_asset_manager_vue.html → mount api-asset SPA
  ├── /projects/               → project_list.html     → Django 模板渲染
  ├── /reports/                → test_report_list.html → Django 模板渲染
  ├── /scheduled-tasks/        → scheduled_task_list.html → Django 模板渲染
  ├── /task-monitor/           → task_monitor.html     → Django 模板渲染
  ├── /performance/            → performance_test.html → mount root SPA
  ├── /ai-xxx/                 → ai_*_vue.html         → mount 各 AI SPA
  └── /profile/ /login/        → auth/*.html           → Django 模板渲染
```

**问题**：每次路径切换都整页刷新，即使两个页面都是 Vue SPA。

### 目标架构（单一 SPA Shell）

```
用户访问
  ├── 登录/注册页             → auth_shell.html       → 轻量 SPA（或保留 Django）
  └── 应用主入口 /app/         → app_shell.html        → mount 统一 SPA
        #!/dashboard           → Dashboard 组件          ← 无刷新
        #!/projects            → ProjectList 组件        ← 无刷新
        #!/test-cases          → TestCaseList 组件       ← 无刷新
        #!/test-suites         → TestSuiteList 组件      ← 无刷新
        #!/reports             → TestReportList 组件      ← 无刷新
        #!/scheduled-tasks     → ScheduledTaskList 组件   ← 无刷新
        #!/environments        → EnvironmentList 组件     ← 无刷新
        #!/api-assets          → ApiAssetManager 组件     ← 无刷新
        #!/mock-data           → MockData 组件            ← 无刷新
        #!/ai/*                → AI 系列组件               ← 无刷新
        #!/task-monitor        → TaskMonitor 组件          ← 无刷新
        #!/performance/*       → Performance 组件          ← 无刷新
        #!/settings            → Settings 组件             ← 无刷新
```

Django 只做两件事：**提供 SPA Shell 页面** + **提供 REST API**。

---

## 二、目录结构设计

### 新建 unified SPA 目录

```
frontend/scene-orchestrator/
├── src/
│   ├── app-shell/                    ← 新建：统一 SPA 入口
│   │   ├── main.js                   ← createApp + Pinia + ElementPlus + Router
│   │   ├── App.vue                   ← 布局框架（侧边栏 + 内容区 + <router-view>）
│   │   ├── router.js                 ← 统一路由表（合并所有 SPA 路由）
│   │   ├── layouts/
│   │   │   ├── MainLayout.vue        ← 侧边栏 + 顶栏 + 内容区
│   │   │   └── AuthLayout.vue        ← 登录/注册独立布局（无侧边栏）
│   │   └── views/                    ← 各页面组件（逐步迁移）
│   │       ├── dashboard/
│   │       │   └── DashboardPage.vue    ← 从 src/dashboard/ 迁移
│   │       ├── projects/
│   │       │   ├── ProjectList.vue      ← 新建（原 Django 模板）
│   │       │   ├── ProjectForm.vue      ← 新建
│   │       │   └── ProjectDetail.vue    ← 新建
│   │       ├── test-manager/            ← 从 src/test-manager/ 迁移
│   │       ├── api-asset-manager/       ← 从 src/api-asset-manager/ 迁移
│   │       ├── environments/            ← 从 src/environment/entries 迁移
│   │       ├── reports/                 ← 新建（原 Django 模板）
│   │       ├── scheduled-tasks/         ← 新建
│   │       ├── ai/                      ← 从各 AI SPA 合并
│   │       └── settings/               ← 新建
│   ├── sidebar/                     ← 保留，作为 layout 组件引入
│   ├── stores/                      ← 统一 Pinia stores
│   └── composables/                 ← 共享 composables
├── vite.config.js                   ← 精简：只保留 app-shell 入口
└── SPA-MERGE-PLAN.md
```

### 模板目录

```
templates/
├── app_shell.html                   ← 新建：统一 SPA Shell
├── auth_shell.html                  ← 新建：登录/注册 Shell（可选）
└── base.html                        ← 保留，过渡期兼容
```

---

## 三、实施步骤

### Phase 1：创建统一 SPA Shell（预计 2-3 天）

#### 1.1 新建 `src/app-shell/main.js`

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router.js'

const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
```

#### 1.2 新建 `src/app-shell/App.vue`

```vue
<template>
  <router-view />
</template>
```

#### 1.3 新建 `src/app-shell/layouts/MainLayout.vue`

集成当前 `base.html` 的布局结构：
- 顶栏（Bootstrap navbar，可考虑用 Element Plus 重构）
- 侧边栏（引入 `src/sidebar/App.vue` 组件）
- 内容区 `<router-view />`
- 深色模式 CSS 变量切换

#### 1.4 新建 `src/app-shell/router.js`

先整合**现有的 Vue SPA 路由**，再逐步添加新页面路由：

```javascript
import { createRouter, createWebHashHistory } from 'vue-router'

// ===== 第一阶段：已存在的 SPA 路由直接合并 =====
// 从 test-manager/router.js 搬过来
import TestCaseList from '../test-manager/views/TestCaseList.vue'
// ... 其他组件

// 从 src/router/index.js 搬过来
import SceneListPage from '../pages/SceneListPage.vue'
// ... 其他组件

const routes = [
  // ---- 仪表盘 ----
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: () => import('./views/dashboard/DashboardPage.vue') },

  // ---- 项目 ----
  { path: '/projects', name: 'projectList', component: () => import('./views/projects/ProjectList.vue') },

  // ---- 测试管理（从 test-manager 合并）----
  { path: '/test-cases', ... },
  { path: '/test-suites', ... },
  { path: '/test-runs', ... },
  { path: '/scene-executions', ... },

  // ---- API 资产管理（从 api-asset-manager 合并）----
  { path: '/api-assets', ... },

  // ---- 环境管理（从 environment 合并）----
  { path: '/environments', ... },

  // ---- 场景编排 + 性能测试（从 root router 合并）----
  { path: '/scenes', ... },
  { path: '/performance', ... },

  // ---- AI 系列（从各 AI SPA 合并）----
  { path: '/ai/draft-box', ... },
  { path: '/ai/records', ... },
  { path: '/ai/rules', ... },

  // ---- Mock 数据 ----
  { path: '/mock-data', ... },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
```

#### 1.5 更新 `vite.config.js`

```javascript
rollupOptions: {
  input: {
    'app-shell': path.resolve(__dirname, 'src/app-shell/main.js'),
    // 过渡期保留旧的入口，逐步移除
    // sidebar: path.resolve(__dirname, 'src/sidebar/main.js'),
  },
  // ...
}
```

#### 1.6 新建 `templates/app_shell.html`

```django
{% load static %}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EasyTesting</title>
  <link rel="stylesheet" href="{% static 'scene-orchestrator/assets/element-plus.css' %}?v={{ asset_version }}">
  <link rel="stylesheet" href="{% static 'scene-orchestrator/assets/app-shell.css' %}?v={{ asset_version }}">
</head>
<body>
  <div id="app"></div>
  <script>
    window.__INITIAL_STATE__ = {
      userAuthenticated: {{ user.is_authenticated|yesno:'true,false' }},
      userName: '{{ user.username|escapejs }}',
      csrfToken: '{{ csrf_token }}',
    }
  </script>
  <script type="module" src="{% static 'scene-orchestrator/assets/app-shell.js' %}?v={{ asset_version }}"></script>
</body>
</html>
```

#### 1.7 新增 Django URL 路由

```python
# urls.py
path('app/', TemplateView.as_view(template_name='app_shell.html'), name='app-shell'),
```

#### 1.8 更新侧边栏 `menuData.js`

将所有菜单项的 `href` 改为 `#/xxx` hash 路由格式：

```javascript
{ type: 'link', label: '仪表盘', icon: 'Speedometer',
  href: '/app/#/dashboard',
  matchHashes: ['/dashboard'] },

{ type: 'link', label: '测试用例', icon: 'BriefcaseFilled',
  href: '/app/#/test-cases',
  matchHashes: ['/test-cases'] },
```

> **关键改动**：侧边栏从独立的 Vue 实例变为 Layout 组件的一部分，与主 SPA 共享同一个 Vue Router。这样可以直接用 `router-link` 替代 `<a>`，完全避免页面刷新。

---

### Phase 2：逐模块迁移 Django 模板页面（预计 2-3 周）

迁移优先级按**使用频率 × 复杂度**排列：

#### 第一批：高频率、低复杂度（推荐最先迁移）

| 页面 | 当前模板 | Vue 组件方案 | 预估 |
|------|---------|-------------|------|
| 项目管理列表 | `project_list.html` | El-Table + 搜索/分页 | 0.5天 |
| 项目表单 | `project_form.html` | El-Form + 验证 | 0.5天 |
| 项目详情 | `project_detail.html` | 描述性展示页面 | 0.5天 |
| 测试报告列表 | `test_report_list.html` | El-Table + 筛选 | 0.5天 |
| 测试报告详情 | `test_report_detail.html` | 报告展示组件 | 0.5天 |
| API 分组管理 | `api_group_*.html` | El-Tree + CRUD | 0.5天 |

**累计：3 天**

#### 第二批：中频率、中等复杂度

| 页面 | 当前模板 | Vue 组件方案 | 预估 |
|------|---------|-------------|------|
| 定时任务列表 | `scheduled_task_list.html` | El-Table + CRUD | 0.5天 |
| 定时任务表单 | `scheduled_task_form.html` | El-Form + cron 表达式 | 0.5天 |
| 定时任务详情 | `scheduled_task_detail.html` | 详情展示 | 0.5天 |
| 执行日志列表 | `task_execution_logs.html` | El-Table + 搜索 | 0.5天 |
| 执行日志详情 | `task_execution_log_detail.html` | 日志详情组件 | 0.5天 |
| 任务监控 | `task_monitor.html` | 监控面板 | 0.5天 |
| 参数配置 | `parameter_config_*.html` | El-Form + KV 列表 | 0.5天 |
| 邮件配置 | `email_config_*.html` | El-Form + 测试发送 | 0.5天 |

**累计：4 天**

#### 第三批：低频率、高安全要求

| 页面 | 当前模板 | Vue 组件方案 | 预估 |
|------|---------|-------------|------|
| 登录页 | `login.html` | 独立 Auth Layout | 1天 |
| 注册页 | `register.html` | 独立 Auth Layout | 0.5天 |
| 个人资料 | `profile.html` / `edit_profile.html` | El-Form | 0.5天 |
| 修改密码 | `password_change_form.html` | El-Form | 0.5天 |
| 密码重置 | `password_reset_*.html` | 多步表单 | 0.5天 |

> **注意**：认证页建议保留独立 Django 模板或使用单独的轻量 SPA，因为它们不需要侧边栏和导航，且涉及安全 Cookie、CSRF 等敏感操作。

**累计：3 天**

---

### Phase 3：清理与收尾（预计 2-3 天）

1. **移除旧构建入口**
   - 从 `vite.config.js` 移除所有旧的 SPA 入口，只保留 `app-shell`
   - 删除 `index.html`（开发用根入口）、各子 SPA 的 `index.html`

2. **更新 Django URL 路由**
   - 将指向旧 Vue SPA 模板的 URL 重定向到 `/app/#!/xxx`
   - 保留 REST API 路由不变
   - Django 模板路由逐步删除

3. **删除旧的 Django 模板**
   - 删除不再使用的 `test_manager/*.html` 模板
   - 只保留 `app_shell.html` 和认证相关模板

4. **更新 base.html**
   - 如果不再需要，删除 `base.html` 或降级为认证页专用

5. **优化构建产物**
   - 利用 `manualChunks` 拆分 vendor chunk
   - 配置 `lazy-load` 路由，按需加载页面组件

---

## 四、关键技术决策

### 4.1 路由模式：Hash 模式

当前所有 SPA 都使用 `createWebHashHistory()`，统一 SPA 继续使用 hash 模式：
- ✅ 无需 Nginx 配置 fallback
- ✅ Django URL 路由不改，`/app/` 一个入口即可
- ✅ 侧边栏直接使用 `router-link`

### 4.2 状态管理：统一 Pinia

合并后需要处理各 SPA 的独立 Pinia store：

```javascript
// src/stores/index.js — 统一导出所有 stores
export { useProjectStore } from '../test-manager/stores/project.js'
export { useTestCaseStore } from '../test-manager/stores/testCase.js'
export { useApiAssetStore } from '../api-asset-manager/stores/apiAsset.js'
// ...
```

各模块的 store 文件保留在原目录，通过统一 index 导出。

### 4.3 组件共享

已有共享组件/工具：
```
src/components/          ← 已有（主 SPA 的场景编排组件）
src/composables/         ← 可新建
src/styles.css           ← 合并所有 SPA 的全局样式
```

对于各 SPA 特有的组件（如 `dashboard/components/StatCards.vue`），保留在原目录，通过相对路径引入。

### 4.4 侧边栏改造

侧边栏从**独立 Vue 实例**变为**Layout 组件的一部分**：

```vue
<!-- src/app-shell/layouts/MainLayout.vue -->
<template>
  <div class="app-layout">
    <!-- 侧边栏现在是 layout 的子组件 -->
    <Sidebar />
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import Sidebar from '../../sidebar/App.vue'
</script>
```

这意味着侧边栏可以：
- ✅ 直接使用 `router-link` 和 `useRouter()`
- ✅ 通过 `route.path` 判断激活状态（比 `isActive()` hack 更可靠）
- ✅ 共享 Vue Router 实例，导航 100% 无刷新

### 4.5 认证页独立处理

登录/注册建议有两种方案：

**方案 A：独立 Django 模板（推荐）**
- 保留 `login.html`、`register.html` 为纯 Django 模板
- 不引入 Vue，保持最轻量加载
- 安全相关逻辑（CSRF、Session）直接由 Django 处理

**方案 B：独立 Auth SPA**
- 使用单独的 `auth_shell.html` + 轻量 Auth Vue App
- 共用 Element Plus，但不包含侧边栏
- 通过 Token 或 Session 与主 SPA 通信

> 推荐方案 A：认证页通常只被访问 1-2 次/会话，不值得引入 Vue。

---

## 五、路由表设计（完整）

```javascript
// src/app-shell/router.js
const routes = [
  // ===== 根重定向 =====
  { path: '/', redirect: '/dashboard' },

  // ===== 仪表盘 =====
  { path: '/dashboard',
    component: () => import('./views/dashboard/DashboardPage.vue') },

  // ===== 项目管理 =====
  { path: '/projects',
    component: () => import('./views/projects/ProjectList.vue') },
  { path: '/projects/create',
    component: () => import('./views/projects/ProjectForm.vue') },
  { path: '/projects/:id',
    component: () => import('./views/projects/ProjectDetail.vue'),
    props: true },
  { path: '/projects/:id/edit',
    component: () => import('./views/projects/ProjectForm.vue'),
    props: true },

  // ===== 环境管理 =====
  { path: '/environments',
    component: () => import('../environment/entries/EnvironmentListPage.vue') },
  { path: '/environments/create',
    component: () => import('../environment/entries/EnvironmentFormPage.vue') },
  { path: '/environments/:id',
    component: () => import('../environment/entries/EnvironmentDetailPage.vue'),
    props: true },

  // ===== 测试管理（从 test-manager 迁移）=====
  { path: '/test-case-groups',
    component: () => import('../test-manager/views/TestCaseGroupList.vue') },
  { path: '/test-cases',
    component: () => import('../test-manager/views/TestCaseList.vue') },
  { path: '/test-cases/create',
    component: () => import('../test-manager/views/TestCaseForm.vue') },
  { path: '/test-cases/:id',
    component: () => import('../test-manager/views/TestCaseDetail.vue'),
    props: true },
  // ... 其余 test-manager 路由

  // ===== 测试套件 =====
  { path: '/test-suite-groups',
    component: () => import('../test-manager/views/TestSuiteGroupList.vue') },
  { path: '/test-suites',
    component: () => import('../test-manager/views/TestSuiteList.vue') },
  // ... 其余套件路由

  // ===== 测试运行 =====
  { path: '/test-runs',
    component: () => import('../test-manager/views/TestRunList.vue') },
  { path: '/test-runs/:id',
    component: () => import('../test-manager/views/TestRunDetail.vue'),
    props: true },

  // ===== 场景执行 =====
  { path: '/scene-executions',
    component: () => import('../test-manager/views/SceneExecutionList.vue') },
  { path: '/scene-executions/:id',
    component: () => import('../test-manager/views/SceneExecutionDetail.vue'),
    props: true },

  // ===== API 资产管理 =====
  { path: '/api-assets',
    component: () => import('../api-asset-manager/App.vue') },

  // ===== 场景编排 + 性能测试 =====
  { path: '/scenes',
    component: () => import('../pages/SceneListPage.vue') },
  { path: '/scenes/:id/designer',
    component: () => import('../pages/SceneDesignerPage.vue'),
    props: true },
  { path: '/performance',
    component: () => import('../views/performance/PerformanceTaskList.vue') },
  // ... performance 子路由

  // ===== Mock 数据 =====
  { path: '/mock-data',
    component: () => import('../mock-data/App.vue') },

  // ===== 测试报告 =====
  { path: '/reports',
    component: () => import('./views/reports/TestReportList.vue') },
  { path: '/reports/:id',
    component: () => import('./views/reports/TestReportDetail.vue'),
    props: true },
  { path: '/reports/generate',
    component: () => import('./views/reports/GenerateReport.vue') },

  // ===== 定时任务 =====
  { path: '/scheduled-tasks',
    component: () => import('./views/scheduled-tasks/ScheduledTaskList.vue') },
  { path: '/scheduled-tasks/create',
    component: () => import('./views/scheduled-tasks/ScheduledTaskForm.vue') },
  { path: '/scheduled-tasks/:id',
    component: () => import('./views/scheduled-tasks/ScheduledTaskDetail.vue'),
    props: true },

  // ===== 任务监控 =====
  { path: '/task-monitor',
    component: () => import('./views/scheduled-tasks/TaskMonitor.vue') },

  // ===== AI 系列 =====
  { path: '/ai/draft-box',
    component: () => import('../draft-box/App.vue') },
  { path: '/ai/records',
    component: () => import('../ai-gen-record/App.vue') },
  { path: '/ai/rules',
    component: () => import('../rule-manager/App.vue') },
  { path: '/ai/prompt-templates',
    component: () => import('../prompt-template-manager/App.vue') },
  { path: '/ai/model-providers',
    component: () => import('../model-provider-manager/App.vue') },
  { path: '/ai/document-import',
    component: () => import('../document-import/App.vue') },

  // ===== 系统设置 =====
  { path: '/settings/profile',
    component: () => import('./views/settings/UserProfile.vue') },
  { path: '/settings/password',
    component: () => import('./views/settings/ChangePassword.vue') },
  { path: '/settings/email',
    component: () => import('./views/settings/EmailConfig.vue') },
  { path: '/settings/parameters',
    component: () => import('./views/settings/ParameterConfig.vue') },
]
```

---

## 六、Django 后端适配

前端迁移同时，Django 视图需要做配套改造：

### 6.1 新增统一入口路由

```python
# urls.py
from django.views.generic import TemplateView

urlpatterns = [
    # 统一 SPA Shell
    path('app/', TemplateView.as_view(template_name='app_shell.html'), name='app-shell'),
    # 保留认证页为 Django 模板
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    # REST API 路由保持不变...
]
```

### 6.2 Django 模板页面 → REST API

**迁移前**（Django 模板渲染）：
```python
def project_list(request):
    projects = Project.objects.all()
    return render(request, 'test_manager/project_list.html', {'projects': projects})
```

**迁移后**（Vue 通过 API 获取）：
```python
@api_view(['GET'])
def project_list_api(request):
    projects = Project.objects.all()
    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)
```

### 6.3 配置管理

```python
# settings.py
# 生产环境使用静态文件
APP_SHELL_VERSION = '20260601'  # 用于模板静态文件缓存失效
```

---

## 七、迁移风险与注意事项

### 7.1 路由冲突

旧 SPA 的路由可能相互冲突（例如 test-manager 和 root 应用都有 `/scenes` 路径）。**解决**：统一路由表时以功能线划分前缀。

### 7.2 Pinia Store 命名冲突

各 SPA 的 store 使用 `defineStore('project', ...)`，合并后全局唯一 ID 可能冲突。

**解决**：统一 store ID 前缀：
```javascript
// 旧: defineStore('project', ...)
// 新: defineStore('test-manager:project', ...)
```

### 7.3 Element Plus 全局样式

各 SPA 已经共用 Element Plus，合并后样式不会冲突。但要注意：
- 全局 CSS 变量覆盖（`--primary-color` 等）需保持统一
- scoped style 天然隔离

### 7.4 深色模式

当前 base.html 管理 CSS 变量 `dark-mode` class。迁移后由 Vue Layout 统一管理：
- App.vue 在 mount 时读取 localStorage 设置 class
- Element Plus 主题跟随 CSS 变量变化

### 7.5 过渡期兼容

Phase 1 期间，新旧 SPA 共存：
- 旧入口（dashboard.js, testManager.js 等）继续构建，保持可用
- 旧 Django 模板继续由 Django 路由提供
- 新 `/app/#!/xxx` 路由开始提供服务
- 侧边栏同时更新新旧两种 href

**用户完全无感**，从旧 URL 访问仍正常，从 `/app/` 访问获得无刷新体验。

---

## 八、工作量汇总

| 阶段 | 内容 | 预估算 |
|------|------|--------|
| Phase 1 | 统一 SPA Shell + 路由整合 + 构建配置 | 2-3 天 |
| Phase 2-1 | 高频率页面迁移（项目/报告/API 分组） | 3 天 |
| Phase 2-2 | 中频率页面迁移（定时任务/日志/监控/配置） | 4 天 |
| Phase 2-3 | 认证/个人设置迁移 | 3 天 |
| Phase 3 | 清理旧入口 + 重定向 + 模板清理 | 2-3 天 |
| **总计** | | **14-16 个工作日** |

### 并行建议

1. **Phase 1** + **Phase 2-1 的 Django API 改造** 可同步进行
2. **Phase 2-1 的 Vue 页面开发** 可在 Phase 1 的 Shell 完成后立即开始
3. **Phase 2-3 的认证页** 可最后做，不影响主流程
