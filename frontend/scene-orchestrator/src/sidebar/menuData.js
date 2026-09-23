/**
 * 左侧菜单栏数据结构
 *
 * 分类原则：一级分组 = 测试类型（接口 / 性能 / UI / APP），
 * 组内按「设计 → 执行 → 报告」工作流排序；跨类型的公共能力
 * （数据支撑、AI 辅助、调度与监控、系统配置）独立成组。
 *
 * @property {string}   type           - 'group' | 'link' | 'section'
 * @property {string}   id             - 唯一标识
 * @property {string}   label          - 显示文本
 * @property {string}   icon           - 图标标识（映射到 App.vue 中的 SVG 路径）
 * @property {string}   href           - 导航 URL
 * @property {boolean}  [external]     - 是否在新标签页打开
 * @property {boolean}  [authRequired] - 是否需要登录才能看到
 * @property {string[]} [matchPaths]   - Django URL 路径匹配模式
 * @property {string[]} [matchBases]   - Vue SPA 基础路径
 * @property {string[]} [matchHashes]  - Vue SPA hash 路由匹配模式
 */

/**
 * 获取完整的菜单树
 * @param {Object} opts
 * @param {boolean} opts.isAuthenticated - 用户是否已登录
 * @returns {Array} 过滤后的菜单组列表
 */
export function getMenuData({ isAuthenticated = false } = {}) {
  const groups = [
    // ========== 总览 ==========
    {
      type: 'group',
      id: 'overview',
      label: '总览',
      icon: 'Speedometer',
      defaultExpanded: true,
      children: [
        { type: 'link', label: '仪表盘', icon: 'Speedometer',
          href: '/app/#/dashboard',
          matchPaths: ['/dashboard/'], matchBases: ['/app/'], matchHashes: ['/dashboard'] },
      ],
    },
    // ========== 接口测试 ==========
    {
      type: 'group',
      id: 'api-testing',
      label: '接口测试',
      icon: 'Connection',
      defaultExpanded: false,
      children: [
        { type: 'link', label: 'API资产管理', icon: 'Connection',
          href: '/app/#/api-assets',
          matchPaths: ['/api-asset-manager/', '/api-assets/'], matchBases: ['/app/', '/api-asset-manager/'], matchHashes: ['/api-assets'] },
        { type: 'link', label: '文档导入资产', icon: 'FileEarmarkArrowUpFilled',
          href: '/app/#/ai/document-import',
          matchPaths: ['/ai-document-import/'], matchBases: ['/app/'], matchHashes: ['/ai/document-import'] },
        { type: 'link', label: '测试用例', icon: 'BriefcaseFilled',
          href: '/app/#/test-cases',
          matchPaths: ['/test-cases/'], matchBases: ['/app/', '/test-cases-vue/'], matchHashes: ['/test-cases'] },
        { type: 'link', label: '测试套件', icon: 'Collection',
          href: '/app/#/test-suites',
          matchPaths: ['/test-suites/'], matchBases: ['/app/', '/test-suites-vue/'], matchHashes: ['/test-suites'] },
        { type: 'link', label: '测试场景编排', icon: 'Share',
          href: '/app/#/scenes',
          matchPaths: ['/test-scene-orchestrator/'], matchBases: ['/app/'], matchHashes: ['/scenes'] },
        { type: 'link', label: '场景执行', icon: 'ClipboardData',
          href: '/app/#/scene-executions',
          matchBases: ['/app/', '/test-suites-vue/'], matchHashes: ['/scene-executions'] },
        { type: 'link', label: '用例运行', icon: 'PlayCircleFilled',
          href: '/app/#/test-runs',
          matchBases: ['/app/', '/test-suites-vue/'], matchHashes: ['/test-runs'] },
        { type: 'link', label: '测试报告', icon: 'ReplyAllFilled',
          href: '/app/#/reports',
          matchPaths: ['/reports/'], matchBases: ['/app/'], matchHashes: ['/reports'] },
      ],
    },
    // ========== 性能测试 ==========
    {
      type: 'group',
      id: 'performance',
      label: '性能测试',
      icon: 'LightningChargeFilled',
      defaultExpanded: false,
      children: [
        { type: 'link', label: '压测任务', icon: 'LightningChargeFilled',
          href: '/app/#/performance',
          matchPaths: ['/performance/'], matchBases: ['/app/'], matchHashes: ['/performance/tasks', '/performance/tasks/'] },
      ],
    },
    // ========== UI自动化 ==========
    {
      type: 'group',
      id: 'ui-automation',
      label: 'UI自动化',
      icon: 'WindowStack',
      defaultExpanded: false,
      children: [
        { type: 'link', label: '自动化工作台', icon: 'LayoutSidebarInset',
          href: '/app/#/ui-automation',
          matchBases: ['/app/'], matchHashes: ['/ui-automation'] },
        { type: 'link', label: 'AI智能用例', icon: 'Robot',
          href: '/app/#/ui-ai',
          matchBases: ['/app/'], matchHashes: ['/ui-ai'] },
        { type: 'link', label: '定时任务', icon: 'Alarm',
          href: '/app/#/ui-scheduled',
          matchBases: ['/app/'], matchHashes: ['/ui-scheduled'] },
      ],
    },
    // ========== APP自动化 ==========
    {
      type: 'group',
      id: 'app-automation',
      label: 'APP自动化',
      icon: 'Phone',
      defaultExpanded: false,
      children: [
        { type: 'link', label: 'Dashboard', icon: 'Odometer',
          href: '/app/#/app-automation/dashboard',
          matchBases: ['/app/'], matchHashes: ['/app-automation/dashboard'] },
        { type: 'section', label: '资产管理' },
        { type: 'link', label: '项目管理', icon: 'FolderOpened',
          href: '/app/#/app-automation/projects',
          matchBases: ['/app/'], matchHashes: ['/app-automation/projects'] },
        { type: 'link', label: '设备管理', icon: 'Cpu',
          href: '/app/#/app-automation/devices',
          matchBases: ['/app/'], matchHashes: ['/app-automation/devices'] },
        { type: 'link', label: '包名管理', icon: 'Collection',
          href: '/app/#/app-automation/packages',
          matchBases: ['/app/'], matchHashes: ['/app-automation/packages'] },
        { type: 'link', label: '元素管理', icon: 'Aim',
          href: '/app/#/app-automation/elements',
          matchBases: ['/app/'], matchHashes: ['/app-automation/elements'] },
        { type: 'section', label: '用例与套件' },
        { type: 'link', label: '用例编排', icon: 'Connection',
          href: '/app/#/app-automation/scene-builder',
          matchBases: ['/app/'], matchHashes: ['/app-automation/scene-builder'] },
        { type: 'link', label: '测试用例', icon: 'Document',
          href: '/app/#/app-automation/test-cases',
          matchBases: ['/app/'], matchHashes: ['/app-automation/test-cases'] },
        { type: 'link', label: '测试套件', icon: 'Files',
          href: '/app/#/app-automation/test-suites',
          matchBases: ['/app/'], matchHashes: ['/app-automation/test-suites'] },
        { type: 'section', label: '执行与报告' },
        { type: 'link', label: '执行记录', icon: 'VideoPlay',
          href: '/app/#/app-automation/executions',
          matchBases: ['/app/'], matchHashes: ['/app-automation/executions'] },
        { type: 'link', label: '测试报告', icon: 'DataAnalysis',
          href: '/app/#/app-automation/reports',
          matchBases: ['/app/'], matchHashes: ['/app-automation/reports'] },
        { type: 'section', label: '调度与通知' },
        { type: 'link', label: '定时任务', icon: 'AlarmClock',
          href: '/app/#/app-automation/scheduled-tasks',
          matchBases: ['/app/'], matchHashes: ['/app-automation/scheduled-tasks'] },
        { type: 'link', label: '通知日志', icon: 'Bell',
          href: '/app/#/app-automation/notification-logs',
          matchBases: ['/app/'], matchHashes: ['/app-automation/notification-logs'] },
        { type: 'link', label: '设置', icon: 'Setting',
          href: '/app/#/app-automation/settings',
          matchBases: ['/app/'], matchHashes: ['/app-automation/settings'] },
      ],
    },
    // ========== 数据支撑 ==========
    {
      type: 'group',
      id: 'data-support',
      label: '数据支撑',
      icon: 'DataLine',
      defaultExpanded: false,
      children: [
        { type: 'link', label: 'Mock数据', icon: 'ClipboardData',
          href: '/app/#/mock-data',
          matchPaths: ['/mock-data/'], matchBases: ['/app/'], matchHashes: ['/mock-data'] },
        { type: 'link', label: '数据工厂', icon: 'DataLine',
          href: '/app/#/data-factory',
          matchBases: ['/app/'], matchHashes: ['/data-factory'] },
      ],
    },
    // ========== AI 辅助 ==========
    {
      type: 'group',
      id: 'ai-assist',
      label: 'AI辅助',
      icon: 'Robot',
      defaultExpanded: false,
      children: [
        { type: 'link', label: 'AI草稿箱', icon: 'InboxFilled',
          href: '/app/#/ai/draft-box',
          matchPaths: ['/ai-case-draft-box/'], matchBases: ['/app/'], matchHashes: ['/ai/draft-box'] },
        { type: 'link', label: 'AI生成记录', icon: 'ClockHistory',
          href: '/app/#/ai/records',
          matchPaths: ['/ai-generation-records/'], matchBases: ['/app/'], matchHashes: ['/ai/records'] },
        { type: 'link', label: 'AI规则管理', icon: 'Rulers',
          href: '/app/#/ai/rules',
          matchPaths: ['/ai-rule-management/'], matchBases: ['/app/'], matchHashes: ['/ai/rules'] },
        { type: 'link', label: 'AI提示词管理', icon: 'ChatLeftTextFilled',
          href: '/app/#/ai/prompt-templates',
          matchPaths: ['/ai-prompt-template-management/'], matchBases: ['/app/'], matchHashes: ['/ai/prompt-templates'] },
        { type: 'link', label: 'AI大模型管理', icon: 'CpuFilled',
          href: '/app/#/ai/model-providers',
          matchPaths: ['/ai-model-providers/'], matchBases: ['/app/'], matchHashes: ['/ai/model-providers'] },
      ],
    },
    // ========== 调度与监控 ==========
    {
      type: 'group',
      id: 'scheduler-monitor',
      label: '调度与监控',
      icon: 'ClockFilled',
      defaultExpanded: false,
      children: [
        { type: 'link', label: '定时任务', icon: 'ClockFilled',
          href: '/app/#/scheduled-tasks', matchBases: ['/app/'], matchHashes: ['/scheduled-tasks'] },
        { type: 'link', label: '定时任务监控', icon: 'ClockHistory',
          href: '/app/#/task-monitor', matchBases: ['/app/'], matchHashes: ['/task-monitor'] },
        { type: 'link', label: '执行日志', icon: 'ClipboardData',
          href: '/app/#/task-execution-logs', matchBases: ['/app/'], matchHashes: ['/task-execution-logs'] },
        { type: 'link', label: '平台日志查询', icon: 'Terminal',
          href: '/app/#/log-query', matchBases: ['/app/'], matchHashes: ['/log-query'] },
      ],
    },
    // ========== 用户&设置 ==========
    {
      type: 'group',
      id: 'user-settings',
      label: '用户&设置',
      icon: 'Sliders',
      defaultExpanded: false,
      authRequired: true,
      children: [
        { type: 'link', label: '个人资料', icon: 'UserFilled',
          href: '/app/#/settings/profile',
          matchPaths: ['/profile/'], matchHashes: ['/settings/profile'] },
        { type: 'link', label: '修改密码', icon: 'Lock',
          href: '/app/#/settings/password',
          matchPaths: ['/password-change/'], matchHashes: ['/settings/password'] },
        { type: 'link', label: '邮件配置', icon: 'Message',
          href: '/app/#/email-config', matchBases: ['/app/'], matchHashes: ['/email-config'] },
        { type: 'link', label: '参数配置', icon: 'Operation',
          href: '/app/#/parameter-config', matchBases: ['/app/'], matchHashes: ['/parameter-config'] },
      ],
    },
    // ========== 管理后台 ==========
    {
      type: 'group',
      id: 'admin',
      label: '管理后台',
      icon: 'Monitor',
      defaultExpanded: false,
      authRequired: true,
      children: [
        { type: 'link', label: '管理后台', icon: 'Laptop',
          href: '/admin/', external: true, matchPaths: ['/admin/'] },
      ],
    },
  ]

  return groups.filter(g => !g.authRequired || isAuthenticated)
}
