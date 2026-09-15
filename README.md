# EasyTesting - 综合测试管理平台

一个基于 Django + Vue3 的全功能测试管理平台，支持 API 测试、场景编排、UI 自动化、性能压测等多种测试类型。

## 项目简介

EasyTesting 是一个功能全面的自动化测试平台，提供了从测试设计、执行到报告生成的完整闭环。平台采用前后端分离架构，后端基于 Django REST Framework 提供 RESTful API，前端使用 Vue3 + Element Plus 构建现代化用户界面（多标签页工作台，操作习惯类似浏览器标签）。

### 核心特性

- **API 测试**: 支持 HTTP/HTTPS 接口测试，可视化定义请求参数和断言规则
- **场景编排**: 可视化编排多步骤测试场景，节点级变量提取与断言，支持批量执行（串行/并发）、场景健康检查、失败自动重试、Token 探活
- **UI 自动化**: 基于 Playwright 的浏览器自动化测试
- **APP 自动化**: APP 自动化模块（持续完善中）
- **性能压测**: 集成 Locust 进行压力测试
- **数据工厂**: 智能生成测试数据，支持 Faker 和 Mock 数据
- **API 资产导入**: 支持 Apifox/文档/cURL 导入接口资产
- **定时任务**: 基于 Celery Beat 的定时任务调度系统
- **测试报告**: 自动生成测试报告，支持多种导出格式
- **实时日志**: SSE 实时推送日志流，支持命令终端执行
- **AI 辅助**: 集成 AI 能力辅助生成测试数据和用例（模型供应商可配置）

### 主要功能模块

1. **项目管理**: 创建和管理测试项目，组织测试资源
2. **环境管理**: 灵活配置不同环境（开发/测试/生产）的 URL、请求头预设、变量与 Token 探活地址
3. **API 资产**: 管理接口文档，支持 Apifox / 文档 / cURL 导入与同步
4. **测试场景**: 编排多节点场景，支持单步调试、批量执行、健康检查、失败重试
5. **测试用例/套件**: 组织测试用例与套件批量执行
6. **测试报告**: 执行结果与报告管理，支持历史追溯
7. **Mock 数据**: 灵活的 Mock 数据生成规则
8. **数据工厂 / 草稿箱 / 规则管理 / 提示词模板**: 测试数据生产配套工具
9. **性能测试 / UI 自动化 / APP 自动化**: 多形态测试执行入口
10. **日志查询与定时任务**: 平台运行日志检索与定时调度

## 技术栈

### 后端技术
- **Web 框架**: Django 4.2.x, Django REST Framework 3.15.x
- **异步任务**: Celery 5.3.x + Redis
- **定时任务**: django-celery-beat
- **数据库**: SQLite (轻量级)，支持 MySQL/PostgreSQL
- **UI 管理**: Django SimpleUI
- **HTTP 测试引擎**: HttpRunner 4.3.x（场景执行内核，debugtalk 函数可扩展）
- **性能测试**: Locust 2.15.x
- **UI 自动化**: Playwright 1.40.x
- **Mock 数据**: Faker
- **其他依赖**: pydantic、weasyprint (PDF 报告)、js2py (前置脚本 JS 运行) 等，详见 `requirements.txt`

### 前端技术
- **框架**: Vue 3 (Composition API)
- **UI 组件**: Element Plus
- **路由**: Vue Router 4
- **状态管理**: Pinia
- **构建工具**: Vite 5（多入口构建，SPA Shell + 过渡期旧入口）
- **代码编辑器**: CodeMirror
- **图表**: ECharts
- **国际化**: vue-i18n
- **样式**: Sass + Bootstrap 工具类

## 快速开始

### 环境要求

- Python >= 3.9
- Node.js >= 18.x
- npm >= 9.x
- Redis（Celery 异步任务/定时任务需要）

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/chenyang1031/easy_test.git
cd easy_test
```

#### 2. 配置虚拟环境并安装 Python 依赖

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. 安装前端依赖

```powershell
cd frontend/scene-orchestrator
npm install
```

#### 4. 数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

#### 5. 创建管理员账户

```bash
python manage.py createsuperuser
```

按照提示输入用户名、邮箱和密码。

#### 6. 启动服务

```powershell
# 终端 1: 启动 Django 后端服务器
python manage.py runserver 0.0.0.0:8000

# 终端 2: 启动 Celery Worker (Windows 需添加 -P solo 参数)
celery -A EasyTesting worker -l info -P solo
# Linux/Mac: celery -A EasyTesting worker -l info

# 终端 3: 启动 Celery Beat (定时任务调度器)
celery -A EasyTesting beat -l info

# 终端 4: 启动前端开发服务器
cd frontend/scene-orchestrator
npm run dev
```

> 一键拉起全部服务的启动脚本未包含在仓库中，可按上述命令自行封装（注意 Windows 下 Celery 需要 `-P solo`）。

### 访问应用

- **主应用**: http://127.0.0.1:8000/ （自动跳转到 `/app/` 工作台）
- **后台管理**: http://localhost:8000/admin/
- **前端开发服务器**: http://localhost:5178/static/scene-orchestrator/ （开发时使用，`/api` 已代理到 8000 后端）

> 说明：8000 端口直接使用 `npm run build` 的构建产物（`static/scene-orchestrator/`）；5178 是 Vite 开发服务器，改前端源码实时热更新。仅跑后端接口测试时不依赖 Node。

## 使用说明

### 基础操作

1. **登录系统**: 使用创建的管理员账户登录
2. **创建项目**: 点击"新建项目"按钮，填写项目名称和描述
3. **配置环境**: 在环境管理中设置不同环境的 base_url、请求头预设（如 Authorization）与变量；可配置"Token 探活 URL"供批量执行前校验登录态
4. **导入 API 资产**: 通过 Apifox / 文档 / cURL 导入接口，或手工创建
5. **编排测试场景**: 在场景编排器中添加节点、配置断言与提取规则，支持单步调试
6. **执行与查看结果**: 单次执行或批量执行，在执行记录中查看节点级请求/响应/断言明细

### 场景编排要点

场景 = 变量池 + 有序节点。每个节点可覆盖方法/URL/请求头/参数/请求体，执行顺序自上而下，前序节点的提取结果供后续节点引用。

#### 变量提取与关联

```json
// 提取规则（JSON）：从响应中提取字段写入变量池
[
  { "name": "token", "path": "$.response.data.token" },
  // 列表可能为空时，勾选"可选"并给默认值，未命中不报错
  { "name": "itemId", "path": "$.response.data.list[0].id", "required": false, "default_value": "" }
]

// 后续节点引用
{ "url": "/user/{{token}}/profile" }
```

内置变量：`{{runId}}`（本次执行唯一标识）、`{{timestamp}}`（毫秒时间戳），可直接用于规避唯一约束，也支持 `{{debugtalk函数()}}`。

#### 场景健康检查

场景编辑页提供"健康检查"按钮，保存时也会自动静默检查，静态识别四类常见配置缺陷（不发起任何请求）：

| 检查项 | 说明 | 级别 |
|---|---|---|
| 未定义变量 | `{{var}}` 引用了不存在的变量/函数 | 错误 |
| URL 占位符 | 生效 URL 含 `{id}` 字面量占位符，会被原样发出 | 错误 |
| 跨模块覆盖 | 节点 URL 覆盖指向了其他模块的接口（配错链） | 警告 |
| 请求体格式 | 资产要求 form-data 而节点按 JSON 提交，字段会被忽略 | 警告 |

#### 失败自动重试

节点可配置"失败自动重试次数"（0-3 次）与"重试匹配文本"（失败原因或服务端 msg 包含该文本才重试，留空则全部重试），适用于"转写中"等竞态类瞬态失败。

#### 批量执行与 Token 探活

支持将多个场景按串行/并发模式批量执行，批次维度聚合成功/失败/部分成功统计，批次展开行支持"只看失败"过滤。若环境配置了"Token 探活 URL"，开跑前会先校验登录态，Token 过期时整批直接跳过并显著提示，避免整批场景白白失败。

#### Mock 数据生成

使用 Faker 规则生成模拟数据：

```python
{
  "username": "mock:string,length=10",  # 随机字符串
  "age": "mock:integer,min=18,max=60",  # 随机整数
  "email": "mock:email",                # 随机邮箱
  "is_active": "mock:bool"              # 随机布尔值
}
```

#### 定时任务配置

在定时任务页面配置 Cron 表达式，可设置：
- 定期执行测试用例
- 自定义触发时间
- 失败时发送邮件通知

## 项目结构

```
easy_test/
├── EasyTesting/                  # Django 项目配置（settings/urls/wsgi/celery）
├── test_manager/                 # 核心业务模块
│   ├── api/                      # DRF 接口层
│   │   ├── scene_engine.py       #   场景执行引擎（变量池/断言/提取/重试）
│   │   ├── scene_validators.py   #   场景静态校验器（健康检查）
│   │   ├── scene_views.py        #   场景/节点 CRUD 与执行
│   │   ├── scene_batch_views.py  #   批量执行与统一执行列表
│   │   ├── api_asset_views.py    #   API 资产
│   │   ├── log_views.py          #   日志查询（SSE）
│   │   ├── performance_views.py  #   性能测试
│   │   └── ...
│   ├── models/                   # 数据模型（场景/节点/资产/环境/批次等）
│   ├── utils/
│   │   └── scene_batch_schedule.py  # 批量执行调度（含 Token 探活）
│   ├── ai_adapters/              # AI 能力适配
│   ├── app_automation/           # APP 自动化模块
│   ├── ui_automation/            # UI 自动化模块
│   ├── data_factory/             # 数据工厂
│   ├── report/                   # 报告模块
│   ├── httprunner_executor.py    # HttpRunner 执行器封装
│   ├── scheduler.py / tasks.py   # 调度与 Celery 任务
│   └── pre_request_script*.py    # 节点前置脚本（ES5.1 JS）运行时
├── frontend/scene-orchestrator/  # Vue3 SPA（Vite 多入口）
│   ├── src/app-shell/            # 工作台外壳（多标签页/布局/路由守卫）
│   ├── src/pages/                # 场景编排器/场景列表
│   ├── src/components/           # 通用组件（节点配置面板/变量选择器等）
│   ├── src/test-manager/         # 用例/套件/执行记录视图
│   ├── src/api/                  # 后端 API 封装
│   └── vite.config.js            # 端口 5178，/api 代理到 8000
├── static/                       # 构建产物与静态资源（collectstatic 输出）
├── media/                        # 上传文件存储
├── logs/                         # 日志文件
├── templates/                    # Django 模板（SPA Shell 页面）
├── sql/ docs/                    # SQL 脚本与文档
├── manage.py
└── requirements.txt
```

## 部署指南

### 生产环境部署

#### 1. 配置环境变量

创建 `settings_local.py` 或设置以下环境变量：

```bash
export DJANGO_SECRET_KEY="你的安全密钥"
export DJANGO_DEBUG="False"
export DJANGO_ALLOWED_HOSTS="your-domain.com,www.your-domain.com"
```

#### 2. 收集静态文件

```bash
python manage.py collectstatic --noinput
```

#### 3. 前端构建

```bash
cd frontend/scene-orchestrator
npm run build
```

构建后的文件会输出到 `static/scene-orchestrator/`

#### 4. 使用 Gunicorn + Nginx

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务
gunicorn --bind 0.0.0.0:8000 EasyTesting.wsgi
```

> 注意：开发机为 Windows 时 Gunicorn 不可用，可使用 waitress（`waitress-serve --port=8000 EasyTesting.wsgi:application`）。批量并发场景建议控制并发数或引入任务队列排队。

#### 5. 启用 HTTPS

使用 Let's Encrypt 配置免费 SSL 证书：

```bash
certbot --nginx -d your-domain.com
```

### Docker 部署 (规划中)

项目暂不支持 Docker，但计划在未来版本中添加 Docker Compose 配置文件。

## 常见问题

### Q: Celery Worker 无法启动

**A**: Windows 系统需要添加 `-P solo` 参数：
```bash
celery -A EasyTesting worker -l info -P solo
```

### Q: 端口被占用

**A**: 命令行指定其他端口即可：
```bash
python manage.py runserver 8001
```

### Q: 前端无法访问

**A**: 检查 CORS 配置，确保 `ALLOWED_HOSTS` 包含正确域名。

### Q: 日志显示异常

**A**: 检查 `logs/` 目录下的权限问题，确保应用有写入权限。

### Q: 批量执行整批显示失败并提示 Token 探活未通过

**A**: 这是预期行为——环境配置了"Token 探活 URL"且登录态失效时，批次会直接跳过。到环境管理中刷新 Token 后重新发起批量执行即可。

## 更新日志

### v1.1.0 (2026-09)
- 场景健康检查：未定义变量/URL 占位符/跨模块覆盖/form 格式四类静态检查，保存时自动触发
- 节点失败自动重试（次数 + 错误文本匹配），新增内置变量 `{{runId}}`/`{{timestamp}}`
- 批量执行 Token 探活：Token 过期整批跳过；批次列表"只看失败"过滤与批次 ID 展示
- 修复：场景/节点复制丢失 URL 覆盖等字段；断言失败原因带期望/实际值与服务端 msg
- 提取规则支持"可选 + 默认值"；多标签页登录/登出自动清空；节点详情深链

### v1.0.0
- 完成 API 测试基础功能
- 集成 Playwright UI 自动化
- 支持 Locust 性能测试
- 实现场景编排功能
- 优化前端 UI 体验
- 新增 AI 辅助测试功能

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 致谢

感谢以下开源项目的支持和贡献：

- [Django](https://www.djangoproject.com/)
- [Vue.js](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [HttpRunner](https://www.httprunner.com/)
- [Playwright](https://playwright.dev/)
- [Locust](https://locust.io/)

---

**注意**: 本项目仍在积极开发中，部分功能可能还在完善中。使用前请阅读完整文档。
