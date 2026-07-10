# EasyTesting 项目 Review 优化建议

> **Review 日期**：2026 年 6 月 3 日  
> **Review 范围**：全栈代码、架构、安全性、性能、可维护性

---

## 一、紧急修复项（安全风险）

### 1.1 硬编码密钥和密码 ⚠️ 严重

**问题**：`EasyTesting/settings.py` 中硬编码了：
- `SECRET_KEY`（第 26 行）
- `EMAIL_HOST_PASSWORD`（第 167 行）— SMTP 密码明文
- 数据库密码（SQLite 无密码，但若将来切换需注意）

**建议**：
```python
# 使用环境变量
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-default")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
```

**优先级**：🔴 紧急 — 代码一旦泄露，密钥和密码直接暴露

### 1.2 DEBUG=True 在生产配置中 ⚠️ 严重

**问题**：`settings.py:29` — `DEBUG = True` 且 `ALLOWED_HOSTS` 包含 `172.168.0.123`（显然是内网生产地址）

**建议**：
```python
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")
```

**优先级**：🔴 紧急 — DEBUG 模式在生产环境会泄露完整错误堆栈和敏感信息

---

## 二、架构优化

### 2.1 数据库升级

**问题**：使用 SQLite，不适合并发写入和多用户场景。

**建议**：
- 生产环境迁移到 PostgreSQL（Django ORM 零代码改动）
- 利用 PostgreSQL 的 JSONB 字段增强 JSON 查询性能
- 利用连接池提高并发能力

**优先级**：🟡 中 — SQLite 在单用户开发场景可用，但多用户部署需升级

### 2.2 模型文件拆分

**问题**：`test_manager/_models_flat.py` 超过 1900 行，包含所有模型定义，难以维护。

**现状**：性能测试和 AI 相关模型已拆分为独立文件（`models/performance.py`, `models/ai_model_provider.py` 等），但大量模型仍集中在 `_models_flat.py`。

**建议**：
```
test_manager/models/
    __init__.py       # 统一导出
    project.py        # Project, ApiProject
    api_asset.py      # ApiAsset, ApiGroup, ApiHistory, ApiAssetChangeRecord, ApiPreset, ApiAssetDraft
    test_case.py      # TestCase, TestCaseGroup, TestSuite, TestSuiteGroup, TestSuiteCase, TestRun, TestResult, TestSuiteRun
    scene.py          # TestScene, TestSceneNode, TestSceneNodeSyncLog, TestSceneExecution
    environment.py    # Environment
    ai_draft.py       # AICaseDraftGroup, AICaseDraft, AICaseDraftRuleUsage
    scheduled.py      # ScheduledTask, TaskExecutionLog
    report.py         # TestReport
    email_config.py   # EmailConfig
    mock_data.py      # MockData
    document_gen.py   # DocumentGenRecord, AIGenerationRecord
    parameter.py      # ParameterConfig
```

**优先级**：🟡 中 — 不影响功能，但随着模型增多维护成本递增

### 2.3 API 版本化

**问题**：API 路由无版本号前缀（如 `/api/projects/`），Report API 使用了 `v1/` 但不统一。

**建议**：
```python
urlpatterns = [
    path('api/v1/', include('test_manager.api.urls')),
    path('api/v1/', include('test_manager.report.api_urls')),
]
```

**优先级**：🟡 中 — 在 API 发生 Breaking Change 前引入版本化

### 2.4 前端多 SPA 架构优化

**问题**：当前 10 个前端子应用各自独立入口（`main.js`），导致：
- `useCsrf.js` 在 8 个模块中重复复制
- API 封装（`http.js`, `api/index.js`）在各模块中重复
- 公共组件（如 `KvTableEditor`, `JsonEditor`）引用路径复杂

**建议**：
1. 提取公共代码到 `@/shared/` 目录：
   ```
   frontend/scene-orchestrator/src/shared/
       composables/useCsrf.js      # 统一 CSRF
       api/http.js                 # 统一 HTTP 客户端
       components/                 # 公共组件
   ```
2. 考虑升级为 monorepo 结构（pnpm workspace），或使用 Vue 3 的 Module Federation 实现微前端

**优先级**：🟢 低 — 当前可工作，但随模块增多重复代码会膨胀

### 2.5 前端 TypeScript 迁移

**问题**：前端全部为 JavaScript，缺少类型检查，接口数据结构的变更容易引入运行时错误。

**建议**：
- 新模块使用 TypeScript
- 核心类型定义（API 响应结构、Pinia Store 类型）优先迁移
- 使用 `vue-tsc` 进行类型检查

**优先级**：🟢 低 — 长期优化项

---

## 三、代码质量

### 3.1 迁移文件冲突

**问题**：`migrations/0014` 出现两次（`0014_alter_mockdata_aim.py` 和 `0014_scheduledtask_alter_mockdata_aim_taskexecutionlog.py`），加了 merge migration `0015_merge`。

**建议**：清理历史迁移（Squash），避免迁移链混乱。

**优先级**：🟢 低 — 当前合并已处理，但新开发者可能困惑

### 3.2 重复代码

**发现的多处重复**：
- 分页类 `StandardResultsSetPagination` 在 `views.py` 和 `document_gen_views.py` 中重复定义
- `_normalize_kv_payload` 在 `api_asset_views.py` 和 `document_gen_views.py` 重复引用
- 前端每个子应用的 `App.vue` 结构高度相似

**建议**：提取公共分页类到 `test_manager/api/pagination.py`，提取公共前端布局组件

**优先级**：🟢 低

### 3.3 异常处理

**问题**：多处使用 `except Exception as e` 捕获过于宽泛，且日志级别不一致。

**建议**：
- 区分 `except` 的具体异常类型
- 统一错误响应的格式（当前部分返回 `{"detail": "..."}`, 部分返回 `{"error": "..."}`)
- 添加全局异常处理器（DRF `EXCEPTION_HANDLER`）

**优先级**：🟡 中

### 3.4 测试覆盖

**问题**：项目测试非常少，仅发现：
- `test_manager/tests.py` — 基础测试
- `test_manager/tests_dashboard.py`
- `test_manager/tests_performance_stage2.py`
- `test_manager/tests_performance_stop.py`
- `test_manager/tests_apifox_environment_import.py`
- `test_manager/test_har_parser.py`
- `test_manager/test_scene_execution_report.py`
- `test_manager/report/tests.py`

**缺少测试的模块**：
- ❌ AI 生成流程
- ❌ 文档导入 API 生成
- ❌ 场景编排引擎
- ❌ 前置脚本引擎
- ❌ 定时任务调度
- ❌ 用户认证流程

**建议**：
- 核心业务逻辑（场景引擎、AI 适配器、前置脚本）至少达到 70% 覆盖率
- API ViewSet 添加集成测试
- 定时任务添加单元测试
- 使用 `pytest-django` + `pytest-cov`

**优先级**：🔴 高 — 缺少测试是最大的质量风险

---

## 四、安全加固

### 4.1 频率限制

**问题**：目前仅 AI 生成接口有频率限制（`ai_generate: 10/hour`），登录接口、上传接口、API 导入接口无限制。

**建议**：
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'ai_generate': '10/hour',
        'login': '5/min',
        'upload': '30/hour',
    },
}
```

**优先级**：🟡 中

### 4.2 CSRF 保护

**问题**：前端每个子应用独立处理 CSRF，存在遗漏风险。未在 DRF 中显式配置 CSRF 策略。

**建议**：
- 统一前端 CSRF 拦截器（见 2.4）
- 确保所有 POST/PUT/DELETE 请求携带 CSRF Token

**优先级**：🟡 中

### 4.3 文件上传安全

**问题**：
- 文件类型验证仅在前端检查扩展名（`.docx`, `.md`），后端依赖 `FileExtensionValidator` 需确认完备性
- 上传文件大小限制 50MB（前端），后端 Django 配置为 10MB（`DATA_UPLOAD_MAX_MEMORY_SIZE`），不一致

**建议**：
- 后端增加文件 MIME 类型验证（不只是扩展名）
- 统一前后端文件大小限制
- 上传文件使用病毒扫描（生产环境）

**优先级**：🟡 中

---

## 五、性能优化

### 5.1 数据库查询优化

**问题**：
- `views.py` 中的 `get_queryset()` 使用了 `.all()` 后再过滤，应先过滤
- JSONField 查询（`extracted_apis`, `node_results`）效率较低

**建议**：
- 使用 `select_related()` / `prefetch_related()` 减少 N+1 查询
- 对频繁查询的 JSONField 路径添加数据库索引（PostgreSQL GIN 索引）
- 添加 Django Debug Toolbar 进行查询分析

**优先级**：🟡 中

### 5.2 前端打包优化

**问题**：多个 SPA 子应用各自打包，共享依赖（Vue、Element Plus、ECharts）重复加载。

**建议**：
- Vite 配置 `build.rollupOptions.output.manualChunks` 提取公共 vendor
- 使用 CDN 加载大型静态资源（ECharts ~1MB）
- Element Plus 按需导入（当前是全量导入 `import ElementPlus from "element-plus"`）

**优先级**：🟢 低

### 5.3 Celery 任务优化

**问题**：
- 性能测试结果每 3 秒写入一次数据库，高频压测时数据库压力大
- 场景执行结果（`node_results`）整存整取，无分页

**建议**：
- 性能测试结果改为批量写入（每 30 秒一批）
- 场景执行节点数 > 100 时分页存储或使用外部存储

**优先级**：🟢 低

---

## 六、可维护性

### 6.1 API 文档

**问题**：REST API 无自动文档（Swagger/OpenAPI）。

**建议**：
```bash
pip install drf-yasg
```
```python
# urls.py
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(title="EasyTesting API", default_version='v1'),
    public=True,
)
urlpatterns += [path('api/docs/', schema_view.with_ui('swagger'))]
```

**优先级**：🟡 中

### 6.2 日志规范

**问题**：
- 部分模块使用 `logger = logging.getLogger(__name__)`，部分用 `print()`
- tasks.py 中混用 `logger.info()` 和 `print()`（开发遗留）

**建议**：
- 统一使用 `logging`
- 清除所有 `print()` 调试输出
- 添加请求 ID 追踪（`django-log-request-id`），便于链路追踪

**优先级**：🟢 低

### 6.3 配置管理

**问题**：所有配置集中在 `settings.py`，无环境区分。

**建议**：
```
EasyTesting/
    settings/
        __init__.py     # 从 base 导入并根据环境覆盖
        base.py         # 基础配置
        dev.py          # 开发环境
        production.py   # 生产环境
```

**优先级**：🟡 中

### 6.4 Docker 容器化

**问题**：项目无 Dockerfile / docker-compose.yml，环境搭建依赖手动操作。

**建议**：
```dockerfile
# Dockerfile (Django)
FROM python:3.10-slim
...

# docker-compose.yml
services:
  web: ...
  redis: ...
  celery_worker: ...
  celery_beat: ...
```

**优先级**：🟡 中 — 对团队协作和生产部署至关重要

---

## 七、功能增强建议

### 7.1 接口测试结果对比

**问题**：同场景多次执行结果无对比功能。

**建议**：在场景执行历史中添加"对比"按钮，选择两次执行记录，展示 diff（通过率变化、响应时间变化、新增失败节点）。

### 7.2 批量导入接口的自动去重

**问题**：当前 Postman/Apifox 导入的冲突检测仅在导入时一次提示，无智能合并。

**建议**：导入时展示三级 diff（新增/冲突/重复），支持按分组自动归类。

### 7.3 测试数据工厂

**问题**：Mock 数据生成器独立使用，未与测试用例/场景集成。

**建议**：在测试用例编辑器中嵌入"生成测试数据"按钮，选择数据类型，自动填充到请求参数/请求体中。

---

## 八、优化优先级总结

| 优先级 | 优化项 | 类型 |
|--------|--------|------|
| 🔴 紧急 | 硬编码密钥迁移到环境变量 | 安全 |
| 🔴 紧急 | DEBUG 改为环境变量控制 | 安全 |
| 🔴 高 | 核心模块测试覆盖 | 质量 |
| 🟡 中 | 数据库升级到 PostgreSQL | 架构 |
| 🟡 中 | API 版本化 | 架构 |
| 🟡 中 | 统一异常处理 | 质量 |
| 🟡 中 | 频率限制完善 | 安全 |
| 🟡 中 | API 自动文档（Swagger） | 可维护性 |
| 🟡 中 | Docker 容器化 | 可维护性 |
| 🟡 中 | 配置文件环境分离 | 可维护性 |
| 🟡 中 | 数据库查询 N+1 优化 | 性能 |
| 🟢 低 | 模型文件拆分 | 架构 |
| 🟢 低 | 前端代码去重 | 架构 |
| 🟢 低 | TypeScript 迁移 | 代码质量 |
| 🟢 低 | 前端打包优化 | 性能 |

---

> **Review 执行人**：AI Code Review  
> **下次 Review 建议时间**：完成紧急项和高优项修复后
