# GoReplay 回放导入与 EasyTesting 集成设计文档

## 1. 概述

### 1.1 目标

在 EasyTesting 平台的「测试场景编排」模块中增加「回放导入」功能，将 GoReplay 录制的 `.gor` 流量文件解析后：
1. 存储为测试场景（TestScene + TestSceneNode）
2. 将回放中的接口与「API资产管理」中的接口进行匹配
3. 未匹配的接口触发新增接口机制，自动创建 ApiAsset 并关联到场景节点

### 1.2 价值

| 价值点 | 说明 |
|--------|------|
| **快速建场景** | 从真实流量一键生成测试场景，无需手工编排 |
| **资产自动补齐** | 回放中的新接口自动入库，保持 API 资产与场景同步 |
| **真实流量覆盖** | 基于生产/测试环境真实请求，提高测试覆盖度 |
| **回归验证** | 导入后可立即执行，验证目标环境行为 |

---

## 2. GoReplay 文件格式说明

### 2.1 文件结构

`.gor` 文件为纯文本格式，HTTP 请求按以下结构存储：

```
1 <request_id> <timestamp>\n
<HTTP Request Raw>\r\n
\r\n
[<Request Body>]

\n🐵🙈🙉\n

1 <request_id2> <timestamp2>\n
...
```

- **元信息行**：`payload_type request_id timestamp`
  - `payload_type`：1=请求，2=响应，3=回放响应
  - `request_id`：请求唯一标识（请求与响应共用）
  - `timestamp`：Unix 时间戳
- **分隔符**：`\n🐵🙈🙉\n` 用于分隔多条记录
- **支持压缩**：`.gor.gz` 扩展名表示 GZIP 压缩

### 2.2 解析要点

- 解析 `payload_type=1` 的请求记录
- 解析 `payload_type=2`（响应）和 `payload_type=3`（回放响应），通过 `request_id` 与请求关联
- 从 HTTP 首行解析 Method 和 URL（含 query）
- 从 Headers 解析 Content-Type、Cookie 等
- 从 Body 解析请求体（JSON / form-data）
- **响应数据**：解析 HTTP 状态码、响应头、响应体（JSON 优先），与对应请求一并导入

---

## 3. 功能设计

### 3.1 入口位置

| 位置 | 说明 |
|------|------|
| **测试场景编排 → 场景列表页** | 在「新增场景」旁增加「回放导入」按钮 |
| **测试场景编排 → 场景设计器** | 在「添加接口」旁增加「从回放导入」入口 |

### 3.2 交互流程

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 用户点击「回放导入」                                          │
│     → 弹出导入弹窗                                                │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 上传 .gor / .gor.gz 文件                                      │
│     → 选择目标项目、目标分组（用于未匹配接口的归属）                │
│     → 可选：场景名称、场景描述                                    │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 后端解析文件 → 预览阶段                                       │
│     → 展示解析出的请求列表（Method、URL、匹配状态、是否有响应）   │
│     → 匹配状态：已匹配 / 待新增                                  │
│     → 支持勾选/取消勾选要导入的请求（可过滤噪音）                 │
│     → 含响应的请求将一并导入响应数据（状态码、头、体）            │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 用户确认导入                                                  │
│     → 未匹配接口：自动创建 ApiAsset（source=goreplay）            │
│     → 创建 TestScene，按请求顺序创建 TestSceneNode                │
│     → 节点关联 ApiAsset（新建或已有）                             │
│     → 若有响应数据：写入 expected_status_code、expected_response_headers、expected_response_body │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. 跳转至场景设计器，可继续编辑断言、提取规则等                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 接口匹配规则

与现有 API 资产导入逻辑保持一致，以 **Method + URL Path** 作为唯一标识：

| 匹配维度 | 说明 |
|----------|------|
| **Method** | GET / POST / PUT / DELETE / PATCH，需大小写归一化 |
| **URL Path** | 去除域名、协议，仅保留 path + query 的「路径部分」 |

**URL 归一化规则**：
- 从完整 URL 提取：`path + query`（如 `/api/v1/users?id=1`）
- 去除 `Host`、`http://`、`https://` 等
- 若录制时带完整 URL，需解析出 path 部分用于匹配

**匹配逻辑**：
```python
# 伪代码
def match_api_asset(project_id, method, url_path):
    return ApiAsset.objects.filter(
        project_id=project_id,
        method=method.upper(),
        url=url_path,  # 或做 path 归一化后比较
        is_deleted=False
    ).first()
```

### 3.4 未匹配接口 → 新增机制

当 `match_api_asset` 返回 `None` 时，触发新增接口：

| 步骤 | 说明 |
|------|------|
| 1 | 创建 `ApiAsset`，`source=SOURCE_GOREPLAY`（需在模型中新增） |
| 2 | 归属到用户选择的「目标分组」 |
| 3 | 从 HTTP 请求中解析：name、method、url、headers、params、body |
| 4 | `status=active`，`external_id` 可存 request_id 或留空 |
| 5 | 若有响应：`response_schema` 可从响应体推断（JSON），否则为空 |
| 6 | 新建的 ApiAsset 立即用于创建 TestSceneNode |

---

## 4. 数据模型与 API 设计

### 4.1 模型扩展

**ApiAsset 新增来源**：
```python
# test_manager/models 或 _models_flat.py
SOURCE_GOREPLAY = "goreplay"
SOURCE_CHOICES = [
    ...
    (SOURCE_GOREPLAY, "GoReplay"),
]
```

### 4.2 后端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/test-scenes/replay-import/preview` | 上传 .gor 文件，解析并返回预览数据 |
| POST | `/api/test-scenes/replay-import/confirm` | 确认导入，创建场景与节点，未匹配则新建接口 |

#### 4.2.1 预览接口 `replay-import/preview`

**请求**：
- `Content-Type: multipart/form-data`
- `file`: .gor 或 .gor.gz 文件
- `project_id`: 目标项目 ID
- `group_id`: 可选，未匹配接口的目标分组

**响应**：
```json
{
  "total_requests": 15,
  "matched_count": 10,
  "unmatched_count": 5,
  "requests": [
    {
      "index": 1,
      "method": "GET",
      "url": "/api/v1/users",
      "url_full": "http://example.com/api/v1/users",
      "headers": {"Content-Type": "application/json"},
      "params": {},
      "body": null,
      "match_status": "matched",
      "api_asset_id": 123,
      "api_asset_name": "获取用户列表",
      "response": {
        "status_code": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {"code": 0, "data": []}
      }
    },
    {
      "index": 2,
      "method": "POST",
      "url": "/api/v1/orders",
      "match_status": "unmatched",
      "api_asset_id": null,
      "api_asset_name": null
    }
  ]
}
```

#### 4.2.2 确认导入接口 `replay-import/confirm`

**请求**：
```json
{
  "project_id": 1,
  "group_id": 2,
  "scene_name": "从回放导入-20250313",
  "scene_description": "来自 GoReplay 流量",
  "selected_indices": [1, 2, 3, 5, 8],
  "requests": [
    {
      "index": 1,
      "method": "GET",
      "url": "/api/v1/users",
      "match_status": "matched",
      "api_asset_id": 123,
      "headers": {},
      "params": {},
      "body": null
    },
    ...
  ]
}
```

- `selected_indices`：用户勾选要导入的请求索引，为空则全部导入
- `requests`：与预览阶段一致，用于未匹配时创建 ApiAsset

**响应**：
```json
{
  "scene_id": 456,
  "scene_name": "从回放导入-20250313",
  "nodes_created": 5,
  "assets_created": 2,
  "assets_matched": 3
}
```

---

## 5. 核心实现要点

### 5.1 .gor 文件解析器

解析器同时解析 `payload_type=1`（请求）和 `payload_type=2/3`（响应），通过 `request_id` 关联：

- 请求：解析 Method、URL、headers、params、body
- 响应：解析 HTTP 状态码、headers、body（JSON 优先）
- 输出：每个请求附带 `response` 字段（若有），含 `status_code`、`headers`、`body`

实现位置：`test_manager/utils/goreplay_parser.py`

### 5.2 URL 归一化与匹配

```python
from urllib.parse import urlparse, urlunparse

def normalize_url_for_match(full_url):
    """
    从完整 URL 提取 path + query，用于与 ApiAsset.url 匹配。
    ApiAsset.url 通常为 /api/xxx 形式。
    """
    parsed = urlparse(full_url)
    path = parsed.path or "/"
    query = "?" + parsed.query if parsed.query else ""
    return path + query
```

### 5.3 场景与节点创建

确认导入时，若有响应数据则写入节点：

- `expected_status_code`：从响应的 HTTP 状态码
- `expected_response_headers`：响应头（JSON）
- `expected_response_body`：响应体（JSON，非 JSON 不存储）

新建 ApiAsset 时，若响应体为 JSON，可推断 `response_schema` 作为接口响应结构基线。

---

## 6. 前端交互设计

### 6.1 回放导入弹窗

| 区域 | 内容 |
|------|------|
| 步骤 1 | 文件上传区（拖拽或点击），支持 .gor / .gor.gz |
| 步骤 2 | 目标项目、目标分组、场景名称、场景描述 |
| 步骤 3 | 解析后展示请求列表表格，支持勾选、筛选 |
| 底部 | 「取消」「预览」（解析）、「确认导入」 |

### 6.2 请求列表表格列

| 列 | 说明 |
|----|------|
| 勾选 | 是否导入该请求 |
| 序号 | 请求在文件中的顺序 |
| Method | GET/POST/... |
| URL | path + query |
| 匹配状态 | 已匹配 / 待新增（徽章样式） |
| 关联接口 | 已匹配时显示接口名称，未匹配显示「将新建」 |
| 响应 | 有/无（表示是否含录制响应，有则一并导入） |

---

## 7. 异常与边界处理

| 场景 | 处理方式 |
|------|----------|
| 文件格式错误 | 提示「无法解析，请确认为 GoReplay .gor 格式」 |
| 解析出 0 条请求 | 提示「未解析到有效 HTTP 请求」 |
| 无响应数据 | 录制时需加 `--input-raw-track-response` 才有响应；无响应时节点仍可创建，仅不写入 expected_response_* |
| 请求数量过多（如 >500） | 限制单次导入数量，或分页预览 |
| 未选择项目 | 禁用「预览」和「确认导入」 |
| 全部取消勾选 | 禁用「确认导入」 |
| 重复 URL+Method | 按顺序保留，或提供「去重」选项 |

---

## 8. 实施计划建议

| 阶段 | 内容 |
|------|------|
| Phase 1 | .gor 解析器、预览 API、确认导入 API（含自动新建接口） |
| Phase 2 | 前端回放导入弹窗、列表展示、勾选与确认 |
| Phase 3 | 场景设计器内「从回放追加」入口（追加节点到已有场景） |
| Phase 4 | 可选：敏感信息脱敏、URL 过滤规则（如只导入 /api/ 开头） |

---

## 9. 附录：与现有导入的对比

| 维度 | API 资产导入（Postman/OpenAPI） | 回放导入（GoReplay） |
|------|--------------------------------|----------------------|
| 输入 | 接口定义（规范） | 真实 HTTP 请求流 |
| 输出 | ApiAsset | TestScene + TestSceneNode + 可选 ApiAsset |
| 匹配 | 以 Method+URL 冲突检测 | 以 Method+URL 匹配已有资产 |
| 未匹配 | 冲突策略（覆盖/跳过/保留两者） | 自动新建 ApiAsset |
| 场景 | 不涉及 | 直接生成场景并关联节点 |

---

*文档版本：1.0 | 基于 EasyTesting 代码库与 GoReplay 文档整理*
