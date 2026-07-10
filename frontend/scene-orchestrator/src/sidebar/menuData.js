/**
 * 左侧菜单栏数据结构
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
    // ========== 测试管理 ==========
    {
      type: 'group',
      id: 'management',
      label: '测试管理',
      icon: 'Calendar',
      defaultExpanded: true,
      children: [
        { type: 'link', label: '仪表盘', icon: 'Speedometer',
          href: '/app/#/dashboard',
          matchPaths: ['/dashboard/'], matchBases: ['/app/'], matchHashes: ['/dashboard'] },
        { type: 'section', label: '基础配置' },
        { type: 'link', label: '项目', icon: 'FolderOpened',
          href: '/app/#/projects',
          matchPaths: ['/projects/'], matchBases: ['/app/'], matchHashes: ['/projects'] },
        { type: 'link', label: '环境', icon: 'Setting',
          href: '/app/#/environments',
          matchPaths: ['/environments/'], matchBases: ['/app/'], matchHashes: ['/environments'] },
        { type: 'section', label: '接口与场景' },
        { type: 'link', label: 'API资产管理', icon: 'Connection',
          href: '/app/#/api-assets',
          matchPaths: ['/api-asset-manager/', '/api-assets/'], matchBases: ['/app/', '/api-asset-manager/'], matchHashes: ['/api-assets'] },
        { type: 'link', label: '测试场景编排', icon: 'Share',
          href: '/app/#/scenes',
          matchPaths: ['/test-scene-orchestrator/'], matchBases: ['/app/'], matchHashes: ['/scenes'] },
        { type: 'link', label: '场景执行', icon: 'ClipboardData',
          href: '/app/#/scene-executions',
          matchBases: ['/app/', '/test-suites-vue/'], matchHashes: ['/scene-executions'] },
        { type: 'link', label: 'mock数据', icon: 'ClipboardData',
          href: '/app/#/mock-data',
          matchPaths: ['/mock-data/'], matchBases: ['/app/'], matchHashes: ['/mock-data'] },
        { type: 'section', label: '用例与套件' },
        { type: 'link', label: '测试用例分组', icon: 'FolderFilled',
          href: '/app/#/test-case-groups',
          matchBases: ['/app/', '/test-case-groups-vue/'], matchHashes: ['/test-case-groups'] },
        { type: 'link', label: '测试用例', icon: 'BriefcaseFilled',
          href: '/app/#/test-cases',
          matchPaths: ['/test-cases/'], matchBases: ['/app/', '/test-cases-vue/'], matchHashes: ['/test-cases'] },
        { type: 'link', label: '测试套件分组', icon: 'FolderFilled',
          href: '/app/#/test-suite-groups',
          matchBases: ['/app/', '/test-suite-groups-vue/'], matchHashes: ['/test-suite-groups'] },
        { type: 'link', label: '测试套件', icon: 'Collection',
          href: '/app/#/test-suites',
          matchPaths: ['/test-suites/'], matchBases: ['/app/', '/test-suites-vue/'], matchHashes: ['/test-suites'] },
        { type: 'section', label: '执行与报告' },
        { type: 'link', label: '测试运行', icon: 'PlayCircleFilled',
          href: '/app/#/test-runs',
          matchBases: ['/app/', '/test-suites-vue/'], matchHashes: ['/test-runs'] },
        { type: 'link', label: '测试报告', icon: 'ReplyAllFilled',
          href: '/app/#/reports',
          matchPaths: ['/reports/'], matchBases: ['/app/'], matchHashes: ['/reports'] },
        { type: 'link', label: '性能测试', icon: 'LightningChargeFilled',
          href: '/app/#/performance',
          matchPaths: ['/performance/'], matchBases: ['/app/'], matchHashes: ['/performance'] },
        { type: 'section', label: 'AI辅助' },
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
        { type: 'link', label: '文档导入API资产', icon: 'FileEarmarkArrowUpFilled',
          href: '/app/#/ai/document-import',
          matchPaths: ['/ai-document-import/'], matchBases: ['/app/'], matchHashes: ['/ai/document-import'] },
        { type: 'section', label: '调度与监控' },
        { type: 'link', label: '定时任务', icon: 'ClockFilled',
          href: '/app/#/scheduled-tasks', matchBases: ['/app/'], matchHashes: ['/scheduled-tasks'] },
        { type: 'link', label: '定时任务监控', icon: 'ClockHistory',
          href: '/app/#/task-monitor', matchBases: ['/app/'], matchHashes: ['/task-monitor'] },
        { type: 'link', label: '执行日志', icon: 'ClipboardData',
          href: '/app/#/task-execution-logs', matchBases: ['/app/'], matchHashes: ['/task-execution-logs'] },
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
