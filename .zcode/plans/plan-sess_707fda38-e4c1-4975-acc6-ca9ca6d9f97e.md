# 场景批量执行合并为一条记录（含每条子执行展示）

## 方案总览

参照项目内已有的 UI 自动化批量模式（UiBatchExecutionRecord + 子记录 FK）和性能批量调度器模式（后台线程 + 统计回写），新增「场景批量执行」实体：批量执行 N 个场景 → 场景执行列表出现**一条**聚合记录，行内展开显示每个场景的执行情况。单次执行行为不变。

## 一、后端（Django）

### 1. 新模型 + 迁移
`test_manager/models/scene.py` 新增 `SceneBatchExecution`（db_table=scene_batch_execution）：
- `name`（如"批量执行 (3 个场景)"）、`project` FK Project(SET_NULL, null)、`environment` FK Environment(SET_NULL, null)
- `execute_mode`（serial/parallel）、`total_scenes / completed_scenes / success_scenes / failed_scenes / partial_scenes`（int, default 0）
- `status`（running/success/partial_success/failed/stopped）、`cancel_requested` bool、`error_message` text
- `started_at / finished_at`（null）、`created_by` FK User、`created_at` auto

`TestSceneExecution` 增加 `batch = FK(SceneBatchExecution, SET_NULL, null, blank, related_name='executions')`。

`makemigrations test_manager && migrate`（SQLite，加列+新表安全）。

### 2. 执行引擎挂批次
`scene_engine.py` 的 `execute_scene(...)` 增加可选参数 `batch=None`，传入 `TestSceneExecution.objects.create(...)`（现有 2 个调用方不受影响）。

### 3. 批量调度器（新文件 `test_manager/utils/scene_batch_schedule.py`，仿 performance_batch_schedule.py）
- `start_scene_batch(batch_id)`：daemon 线程执行 `_run_batch`
- 串行：逐个 `execute_scene(scene, operator, runtime_config_override={environment_id, base_url})`；并发：`ThreadPoolExecutor(max_workers≤5)`（现状前端 Promise.all 并发已验证可承受）
- 每个子执行结束后回写批次计数（completed/success/failed/partial）；每个场景启动前检查 `batch.cancel_requested` / 终态则中断
- 单场景启动异常（执行记录未创建）：计 failed + 记 error_message
- 收尾 `_finalize_batch`：全成→success；有失败/部分→partial_success；全败→failed；写 finished_at
- 每步 `close_old_connections()` 防 SQLite 连接腐化

### 4. API（新文件 `test_manager/api/scene_batch_views.py`，注册路由 `scene-batch-executions`）
- `POST /api/v1/scene-batch-executions/`：body `{scene_ids, environment_id, mode}`；校验（场景存在、环境必填且属于场景项目——复用 execute action 的校验逻辑）→ 建批次(running) → `transaction.on_commit` 启动线程 → 返回批次
- `GET list`：过滤 project/status；轻量序列化器（不含子记录）
- `GET {id}`：详情含嵌套子记录（TestSceneExecutionListSerializer many + 成功率）
- `POST {id}/stop/`：置 batch.cancel_requested + 对 running 子执行置 cancel_requested（复用引擎协作式取消）
- `DELETE {id}`：删子执行 + 批次（仿 UI 模块 perform_destroy）
- 权限：IsAuthenticated + 项目归属过滤（与现有 ViewSet 一致）

### 5. 统一列表接口（合成交付给前端）
`GET /api/v1/scene-executions-unified/`：按 created_at 倒序**合并**批次记录 + 单次执行（`batch__isnull=True`），offset 分页；支持现有筛选参数 project / status / scene_name（批次按名称或子执行场景名模糊匹配）；条目带 `type: 'batch' | 'single'` 与 `key: 'b-{id}' / 'e-{id}'`。

## 二、前端（Vue）

### 6. API 封装
- `src/api/scene.js`：`batchExecuteScenes({scene_ids, environment_id, mode})`
- `src/test-manager/api/index.js`：`unifiedExecutionApi.list(params)`、`sceneBatchApi.get/stop/remove`

### 7. SceneListPage.vue — 批量执行改为服务端驱动
`confirmBatchExecute` 重写：
- 一次 `batchExecuteScenes` 提交（传串行/并发选择）→ 轮询 `sceneBatchApi.get(id)` 每 2s 直到终态
- 进度条/行 running 标记改读批次计数；完成后汇总弹窗改为从批次统计 + 子执行 error_message 生成（成功/部分成功/失败 + 未通过明细）
- 移除逐个 executeScene 循环与超时标记逻辑（单行「执行」按钮的旧流程不动）

### 8. SceneExecutionList.vue — 混合列表 + 行内展开
- 数据源切换为 unified 接口；分页/筛选参数不变
- 批次行：名称「批量执行 (N 个场景)」、聚合状态 tag、`成功x·部分y·失败z` 统计、项目/环境/创建人/时间列复用；展开箭头懒加载批次详情（首次展开时 GET）
- 子表列：场景名（链接跳 `/scene-executions/{id}` 详情）/ 状态 / 耗时 / 开始时间 / 错误摘要
- 单次执行行行为完全不变（行点击/名称链接进详情）
- 删除：批次行走 `sceneBatchApi.remove`（级联子执行），单次走原 `sceneExecutionApi.remove`

## 三、验证

1. `makemigrations + migrate` 通过
2. 浏览器实测：选 2 成功 + 1 失败场景（#51/#48/#41，测试191 环境）批量执行 →
   - 执行中列表出现 1 条 running 批次；完成后聚合状态=部分成功
   - 行内展开 3 条子执行（2✅ 1❌ 带错误信息），子行可进详情页
   - 汇总弹窗数字与 DB 一致
3. 回归：单次执行、场景名搜索、状态筛选不受影响
4. `npm run build + collectstatic`，8000 端口实测；子模型识图复核列表展开效果

## 不做的事（控制范围）
- 不回填昨天已分散的 36 条历史记录
- 定时任务（单场景）链路不动
- 批次不做独立详情路由页（行内展开已覆盖）