# 测试场景编排前端

## 目录说明

- `src/pages/SceneListPage.vue` 场景列表页（搜索/筛选/分页/CRUD/复制/执行）
- `src/pages/SceneDesignerPage.vue` 场景可视化编排页（左树中画布右配置）
- `src/pages/SceneExecutionPage.vue` 执行结果页（节点执行日志、历史记录）
- `src/components/*` 变量选择器、断言编辑器、节点卡片、执行日志、节点配置等组件
- `src/stores/sceneStore.js` Pinia 全局状态（场景ID、节点列表、变量池、草稿自动保存）
- `src/api/*` 接口封装（复用现有 `/api/api-assets` 与新建 `/api/test-scenes`）

## 挂载到 Django

页面入口：`/test-scene-orchestrator/`

- 开发态调试（Vite 热更新）：`/test-scene-orchestrator/?vite=1`
- 生产态静态资源：`/static/scene-orchestrator/assets/main.js` 与 `main.css`

## 本地运行方式

请先安装 Node.js（建议 18+）后执行：

```bash
npm install
npm run dev
```

## 构建产物接入

构建命令（**场景编排与环境模块共用这一次构建**）：

```bash
npm run build
```

`vite.config.js` 已配置将产物直接输出到 Django 静态目录：

- 输出目录：`static/scene-orchestrator`
- 场景编排：`assets/main.js`、`assets/main.css`
- 环境管理（Django 模板挂载，多入口）：`assets/environmentList.js`、`environmentForm.js`、`environmentDetail.js` 及对应 CSS；公共样式 `assets/element-plus.css`；共享 chunk 如 `assets/element-plus-*.js`

环境相关源码位于 `src/environment/`（组件、入口 `entries/`、`utils/environmentPayload.js`）。

## 接口兼容

前端已按现有后端接口实现，包含：

- 项目映射：`/api/api-projects/resolve-platform-project/`
- API资产：`/api/api-groups/`、`/api/api-assets/`
- 场景编排：`/api/test-scenes/`、`/api/test-scene-nodes/`、`/api/test-scenes/{id}/execute/`
