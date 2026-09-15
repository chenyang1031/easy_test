# EasyTesting - 综合测试管理平台

一个基于 Django + Vue3 的全功能测试管理平台，支持 API 测试、UI 自动化测试、性能压测、场景编排等多种测试类型。

## 项目简介

EasyTesting 是一个功能全面的自动化测试平台，提供了从测试设计、执行到报告生成的完整闭环。平台采用前后端分离架构，后端基于 Django REST Framework 提供 RESTful API，前端使用 Vue3 + Element Plus 构建现代化用户界面。

### 核心特性

- **API 测试**: 支持 HTTP/HTTPS 接口测试，可视化定义请求参数和断言规则
- **UI 自动化**: 基于 Playwright 的浏览器自动化测试，支持 Chrome/Firefox/Safari
- **性能压测**: 集成 Locust 进行分布式压力测试，支持分布式部署
- **场景编排**: 可视化编排多步骤测试场景，支持复杂业务逻辑模拟
- **数据工厂**: 智能生成测试数据，支持 Faker 和 Mock 数据
- **定时任务**: 基于 Celery Beat 的定时任务调度系统
- **测试报告**: 自动生成美观的测试报告，支持多种导出格式
- **实时日志**: SSE 实时推送日志流，支持命令终端执行

### 主要功能模块

1. **项目管理**: 创建和管理测试项目，组织测试资源
2. **环境变量**: 灵活配置不同环境（开发/测试/生产）的变量
3. **API 资产**: 管理 API 接口文档和测试用例
4. **测试套件**: 将多个测试用例组织成套件批量执行
5. **测试结果**: 详细记录每次测试结果，支持历史追溯
6. **AI 辅助**: 集成 AI 能力辅助生成测试数据和用例
7. **Mock 服务**: 灵活的 Mock 数据生成规则
8. **邮件通知**: 测试结果自动发送到指定邮箱

## 技术栈

### 后端技术
- **Web 框架**: Django 4.2.x, Django REST Framework 3.15.x
- **异步任务**: Celery 5.3.x + Redis 5.0.x
- **定时任务**: django-celery-beat 2.5.x
- **数据库**: SQLite (轻量级)，支持 MySQL/PostgreSQL
- **UI 管理**: Django SimpleUI
- **HTTP 测试引擎**: HttpRunner 4.3.x
- **性能测试**: Locust 2.15.x
- **UI 自动化**: Playwright 1.40.x + browser-use
- **Mock 数据**: Faker 37.x, fakerx
- **其他依赖**: 
  - pydantic 1.8.2 (数据校验)
  - weasyprint 60.x (PDF 报告生成)
  - mammoth 1.6.x (文档解析)
  - js2py 0.74+ (JavaScript 运行)

### 前端技术
- **框架**: Vue 3.4.x (Composition API)
- **UI 组件**: Element Plus (latest)
- **路由**: Vue Router 4.6.x
- **状态管理**: Pinia 2.1.x
- **构建工具**: Vite 5.3.x
- **代码编辑器**: CodeMirror 5.65.x
- **图表**: ECharts 5.4.3
- **国际化**: vue-i18n 11.x
- **样式预处理器**: Sass

## 快速开始

### 环境要求

- Python >= 3.9
- Node.js >= 18.x
- npm >= 9.x 或 yarn
- Redis (可选，用于异步任务)
- SQLite3 (默认，无需额外安装)

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://gitee.com/joyamon/easy-testing.git
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

或者使用 yarn:
```powershell
yarn install
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

**方式一：单独启动各个服务**

```powershell
# 终端 1: 启动 Django 后端服务器
python manage.py runserver

# 终端 2: 启动 Celery Worker (Windows 需添加 -P solo 参数)
celery -A EasyTesting worker -l info -P solo
# Linux/Mac: celery -A EasyTesting worker -l info

# 终端 3: 启动 Celery Beat (定时任务调度器)
celery -A EasyTesting beat -l info

# 终端 4: 启动前端开发服务器
cd frontend/scene-orchestrator
npm run dev
```

**方式二：一键启动 (推荐使用)**

可以使用 `start.bat` (Windows) 或 `start.sh` (Linux/Mac) 脚本一键启动所有服务。

### 访问应用

- **主应用**: http://localhost:8000/
- **后台管理**: http://localhost:8000/admin/
- **前端开发服务器**: http://localhost:5178/static/scene-orchestrator/

## 使用说明

### 基础操作

1. **登录系统**: 使用创建的管理员账户登录
2. **创建项目**: 点击"新建项目"按钮，填写项目名称和描述
3. **配置环境**: 在环境变量中设置不同环境的 URL 和参数
4. **创建测试用例**: 在 API 资产中定义接口测试用例
5. **执行测试**: 选择测试用例或测试套件执行测试
6. **查看结果**: 在测试结果中查看详细报告和日志

### 高级功能

#### 参数提取与关联

测试用例之间可以通过响应参数提取实现数据传递：

```yaml
# 提取响应中的 session_id
extract:
  - location: json
    key: $.data.session_id
    name: session_id

# 后续用例使用该参数
headers:
  PHPSESSID: "{{ session_id }}"
```

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
├── EasyTesting/                 # Django 项目配置
│   ├── __init__.py
│   ├── settings.py             # 配置文件
│   ├── urls.py                 # URL 路由
│   └── wsgi.py                 # WSGI 配置
├── test_manager/               # 核心业务模块
│   ├── api/                    # API 接口层
│   │   ├── api_asset_views.py  # API 资产相关接口
│   │   ├── auth_views.py       # 认证授权接口
│   │   ├── log_views.py        # 日志查询接口
│   │   ├── performance_views.py # 性能测试接口
│   │   ├── report_views.py     # 测试报告接口
│   │   └── ...
│   ├── models/                 # 数据模型层
│   ├── views.py                # 传统视图 (部分保留)
│   ├── tasks.py                # Celery 任务
│   ├── httprunner_executor.py  # HttpRunner 执行器
│   ├── scheduler.py            # 任务调度器
│   └── async_executor.py       # 异步任务执行器
├── frontend/                   # 前端项目
│   └── scene-orchestrator/     # Vue3 SPA 应用
│       ├── src/                # 源代码
│       │   ├── api/           # API 调用封装
│       │   ├── components/    # 通用组件
│       │   ├── router/        # 路由配置
│       │   ├── stores/        # Pinia 状态管理
│       │   ├── utils/         # 工具函数
│       │   ├── app-shell/     # 应用 Shell
│       │   └── ...
│       ├── index.html         # 入口 HTML
│       ├── vite.config.js     # Vite 配置
│       └── package.json       # 依赖配置
├── static/                     # 静态资源
├── media/                      # 上传文件存储
├── logs/                       # 日志文件
├── docs/                       # 项目文档
├── sql/                        # SQL 脚本
├── templates/                  # HTML 模板
├── manage.py                   # Django 管理脚本
├── requirements.txt            # Python 依赖
└── README.md                   # 项目说明
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

**A**: 修改 `manage.py` 或命令行指定端口：
```bash
python manage.py runserver 8001
```

### Q: 前端无法访问

**A**: 检查 CORS 配置，确保 `ALLOWED_HOSTS`包含正确域名。

### Q: 日志显示异常

**A**: 检查 `logs/` 目录下的权限问题，确保应用有写入权限。

## 更新日志

### v1.0.0 (当前版本)
- 完成 API 测试基础功能
- 集成 Playwright UI 自动化
- 支持 Locust 性能测试
- 实现场景编排功能
- 优化前端 UI 体验
- 新增 AI 辅助测试功能
- 修复已知 bug

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 联系方式

- 项目主页：https://gitee.com/joyamon/easy-testing
- Email: [contact@email.com]
- QQ 群：[请填写]

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
