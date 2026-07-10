# API 资产修改后场景节点同步优化设计文档

## 1. 概述

### 1.1 核心目标

仅自动同步 URL/Method，请求/响应仅提示差异，支持手动选择性同步，避免节点配置失效。

### 1.2 背景与价值

| 问题 | 说明 |
|------|------|
| **配置失效风险** | API 资产修改后，场景节点若全量覆盖同步，会丢失用户已填写的参数值、变量引用、file 类型配置 |
| **变更感知滞后** | 用户难以知晓哪些场景引用了已修改的接口，导致执行失败后才发现问题 |
| **同步粒度粗** | 缺乏「可同步/不建议同步」的区分，易误操作 |

| 价值点 | 说明 |
|--------|------|
| **安全同步** | 基础信息（URL/Method）一键同步，请求/响应仅提示差异，不自动覆盖 |
| **可追溯** | 所有同步操作记录日志，支持 72 小时回滚 |
| **可视化差异** | 清晰区分「已同步/可同步/不建议同步」内容 |

---

## 2. 变更检测

### 2.1 监听时机

- 监听 **API 资产修改事件**（`ApiAsset.update` / `perform_update`）
- 修改后触发「变更检测」流程，检测该接口被哪些场景节点引用

### 2.2 检测维度

仅检测以下变更类型：

| 维度 | 说明 | 对应字段 |
|------|------|----------|
| **URL/Method** | 请求路径、请求方法 | `url`, `method` |
| **请求参数（增删）** | Query/Header 参数新增或删除 | `request_params`, `request_headers` |
| **请求体格式** | JSON / Form Data 切换 | `request_body_format`, `request_body` 结构 |
| **响应结构（增删字段）** | 响应 Schema 字段变化 | `response_schema` |
| **响应码** | 错误码定义变化 | `error_code` |

### 2.3 引用关系查询

```python
# 伪代码：获取引用某 API 资产的场景节点
def get_scene_nodes_referencing_asset(api_asset_id):
    return TestSceneNode.objects.filter(
        api_asset_id=api_asset_id,
        is_deleted=False,
        scene__is_deleted=False,
    ).select_related("scene", "api_asset")
```

### 2.4 变更记录模型（新增）

为支持「关联 API 已更新」标记与差异计算，需新增变更记录表：

```python
# test_manager/models.py 或 _models_flat.py

class ApiAssetChangeRecord(models.Model):
    """API 资产变更记录，用于场景节点同步提示。"""
    asset = models.ForeignKey(
        ApiAsset,
        on_delete=models.CASCADE,
        related_name="change_records",
        verbose_name="接口资产",
    )
    change_type = models.CharField(
        max_length=30,
        choices=[
            ("url_method", "URL/Method"),
            ("request_params", "请求参数"),
            ("request_body", "请求体"),
            ("response_schema", "响应结构"),
            ("error_code", "响应码"),
        ],
        verbose_name="变更类型",
    )
    before_snapshot = models.JSONField(default=dict, verbose_name="变更前快照")
    after_snapshot = models.JSONField(default=dict, verbose_name="变更后快照")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="api_asset_changes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["asset", "created_at"], name="api_asset_change_asset_time_idx"),
        ]
```

---

## 3. 提示触发

### 3.1 场景列表页

- 引用该接口的场景，在列表中标注 **「关联API已更新」** 标签
- 实现方式：场景列表接口返回 `api_updated: true` 或 `api_updated_node_count: N`

**接口扩展**：`GET /api/test-scenes/` 响应中，每个场景增加：

```json
{
  "id": 1,
  "name": "登录流程",
  "api_updated": true,
  "api_updated_node_ids": [10, 12],
  "api_updated_node_count": 2
}
```

**计算逻辑**：遍历场景节点，若 `api_asset.updated_at > node.api_synced_at`（或存在未读变更记录），则标记 `api_updated`。

### 3.2 场景设计器

- 打开场景时，若存在「关联 API 已更新」的节点，**弹出差异提示弹窗**
- 弹窗内容按维度分组展示：**基础信息 / 请求 / 响应**

**弹窗结构示意**：

```
┌─────────────────────────────────────────────────────────────┐
│  关联接口已更新 - 请选择同步方式                              │
├─────────────────────────────────────────────────────────────┤
│  节点：登录接口 (node_1)                                       │
│                                                              │
│  【基础信息】                                                  │
│  • URL: /api/v1/login → /api/v2/auth/login   [一键同步]        │
│  • Method: 无变化                                             │
│                                                              │
│  【请求】                                                      │
│  • 新增参数: client_id   [新增空参数到节点]                    │
│  • 删除参数: (无)                                              │
│  • 请求体格式: 无变化                                          │
│                                                              │
│  【响应】                                                      │
│  • 新增字段: data.session_token   [生成新断言/提取规则]         │
│  • 删除字段: data.old_token  ⚠️ 可能影响现有断言               │
│                                                              │
│  [暂不同步]  [仅同步基础信息]  [查看详情]                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 同步规则

### 4.1 基础信息（URL/Method）

| 规则 | 说明 |
|------|------|
| **支持一键自动同步** | 用户点击「一键同步」后，将 API 资产的 `url`、`method` 写入节点（节点本身不存 url/method，来自 api_asset，需确认：若节点有 url 覆盖则需更新） |
| **同步后标记** | 记录 `api_synced_at` 或 `last_sync_record_id`，用于后续「已同步」判断 |

**说明**：当前 `TestSceneNode` 的 URL/Method 来自 `api_asset`，节点无独立存储。因此「同步」实质为：更新节点与资产的关联快照时间，并记录同步日志。若未来节点支持 URL 覆盖，则同步时更新节点的 `url_override` 等字段。

### 4.2 请求参数 / 请求体

| 规则 | 说明 |
|------|------|
| **仅展示差异** | 不自动覆盖节点的 `request_params`、`request_headers`、`request_body` |
| **新增空参数到节点** | 提供「新增空参数到节点」选项，将 API 资产中新增的参数以**空值**追加到节点，**不覆盖**节点已有参数值 |
| **不覆盖** | 节点内已填写的参数值、变量引用（如 `{{token}}`）、file 类型配置一律保留 |

### 4.3 响应结构 / Schema

| 规则 | 说明 |
|------|------|
| **仅展示差异** | 不自动修改节点的 `assert_rules`、`extract_rules` |
| **快捷入口** | 提供「生成新断言/提取规则」入口，根据新 Schema 生成建议规则，用户确认后再写入 |
| **不同步原有规则** | 已有断言、提取规则保持不变，对可能失效的规则标注警告 |

### 4.4 防护机制

| 机制 | 说明 |
|------|------|
| **72 小时回滚** | 同步后保留 72 小时回滚能力，支持恢复到同步前的节点配置 |
| **断言/提取规则警告** | 对可能失效的断言、提取规则（如路径已删除）标注 ⚠️，不自动修改 |

---

## 5. 数据模型与字段扩展

### 5.1 TestSceneNode 扩展

```python
# 新增字段（需 migration）

class TestSceneNode(models.Model):
    # ... 现有字段 ...

    # 同步相关
    api_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="API 最后同步时间",
        help_text="上次从 API 资产同步基础信息的时间",
    )
    api_sync_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="同步时 API 快照",
        help_text="用于回滚时恢复",
    )
```

### 5.2 节点同步日志模型（新增）

```python
class TestSceneNodeSyncLog(models.Model):
    """场景节点同步日志，用于追溯与回滚。"""
    node = models.ForeignKey(
        TestSceneNode,
        on_delete=models.CASCADE,
        related_name="sync_logs",
        verbose_name="场景节点",
    )
    sync_type = models.CharField(
        max_length=30,
        choices=[
            ("basic", "基础信息"),
            ("params_add", "新增参数"),
            ("rollback", "回滚"),
        ],
        verbose_name="同步类型",
    )
    before_snapshot = models.JSONField(default=dict, verbose_name="同步前节点快照")
    after_snapshot = models.JSONField(default=dict, verbose_name="同步后节点快照")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="node_sync_logs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["node", "created_at"], name="node_sync_log_node_time_idx"),
        ]
```

---

## 6. API 设计

### 6.1 获取场景节点的 API 变更差异

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/test-scene-nodes/{id}/api-diff/` | 获取节点与关联 API 资产的差异详情 |

**响应示例**：

```json
{
  "node_id": 10,
  "api_asset_id": 5,
  "api_asset_name": "登录接口",
  "api_updated_at": "2025-03-13T10:00:00Z",
  "diffs": {
    "basic": {
      "url": {"changed": true, "old": "/api/v1/login", "new": "/api/v2/auth/login"},
      "method": {"changed": false}
    },
    "request": {
      "params_added": ["client_id"],
      "params_removed": [],
      "body_format_changed": false
    },
    "response": {
      "fields_added": ["data.session_token"],
      "fields_removed": ["data.old_token"],
      "warnings": ["断言路径 $.data.old_token 可能已失效"]
    }
  },
  "sync_status": {
    "basic_synced": false,
    "can_sync_basic": true,
    "can_add_params": true
  }
}
```

### 6.2 同步基础信息

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/test-scene-nodes/{id}/sync-basic/` | 一键同步 URL/Method 到节点 |

**请求**：无 body 或 `{}`

**响应**：

```json
{
  "success": true,
  "node_id": 10,
  "synced_fields": ["url", "method"],
  "sync_log_id": 123,
  "rollback_until": "2025-03-16T10:00:00Z"
}
```

### 6.3 新增空参数到节点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/test-scene-nodes/{id}/sync-add-params/` | 将 API 新增的参数以空值追加到节点 |

**请求**：

```json
{
  "param_keys": ["client_id", "scope"],
  "scope": "request_params"
}
```

**说明**：`scope` 可为 `request_params`、`request_headers`、`request_body`（form-data 时）。

### 6.4 回滚节点配置

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/test-scene-nodes/{id}/sync-rollback/` | 回滚到指定同步前的配置 |

**请求**：

```json
{
  "sync_log_id": 123
}
```

**校验**：仅当 `sync_log.created_at` 在 72 小时内允许回滚。

### 6.5 场景列表扩展

在 `GET /api/test-scenes/` 的序列化中，为每个场景增加：

- `api_updated`: 是否存在关联 API 已更新且未同步的节点
- `api_updated_node_count`: 此类节点数量
- `api_updated_node_ids`: 节点 ID 列表（可选，用于跳转定位）

---

## 7. 前端交互设计

### 7.1 场景列表页

| 区域 | 内容 |
|------|------|
| 场景行 | 若 `api_updated` 为 true，显示橙色/黄色「关联API已更新」标签 |
| 标签点击 | 可筛选仅显示有更新的场景 |

### 7.2 场景设计器 - 差异弹窗

| 区域 | 内容 |
|------|------|
| 触发时机 | 进入设计器且存在 `api_updated` 节点时，自动弹出（可配置「不再提示」） |
| 维度分组 | 基础信息 / 请求 / 响应，每类下展示具体差异 |
| 操作按钮 | 暂不同步、仅同步基础信息、新增空参数、生成新断言/提取规则 |
| 状态标识 | 已同步（绿色）、可同步（蓝色）、不建议同步（灰色/警告） |

### 7.3 节点配置面板

| 区域 | 内容 |
|------|------|
| 关联接口区 | 若 API 已更新，显示「接口已更新」提示 + 「查看差异」按钮 |
| 断言/提取规则 | 对可能失效的规则显示 ⚠️ 图标，悬停展示原因 |

---

## 8. 交付要求（约束）

### 8.1 同步操作不改变

- 节点内已填写的参数值
- 变量引用（如 `{{token}}`、`[节点名] 变量名`）
- file 类型配置

### 8.2 差异展示可视化

- 清晰区分「已同步 / 可同步 / 不建议同步」
- 使用颜色或图标：绿色=已同步，蓝色=可同步，橙色=警告/不建议

### 8.3 日志记录

- 所有同步操作记录：同步人、时间、同步内容（before/after）
- 存储于 `TestSceneNodeSyncLog`，便于追溯

---

## 9. 实施计划建议

| 阶段 | 内容 |
|------|------|
| **Phase 1** | 数据模型：`ApiAssetChangeRecord`、`TestSceneNodeSyncLog`，`TestSceneNode` 扩展字段；API 资产更新时写入变更记录 |
| **Phase 2** | 后端 API：`api-diff`、`sync-basic`、`sync-add-params`、`sync-rollback`；场景列表 `api_updated` 计算 |
| **Phase 3** | 前端：场景列表「关联API已更新」标签；设计器打开时差异弹窗 |
| **Phase 4** | 前端：节点配置面板内差异提示、断言/提取规则警告；回滚入口 |

---

## 10. 附录：与现有逻辑的关系

| 现有能力 | 与本方案关系 |
|----------|--------------|
| `ApiHistory` | 记录 API 资产修改历史，本方案可复用其快照做差异计算，或使用 `ApiAssetChangeRecord` 做轻量记录 |
| `TestSceneNode.api_asset` | 节点关联 API 资产，URL/Method 当前从资产实时读取，若需「节点级覆盖」可后续扩展 |
| 场景执行引擎 | 执行时使用节点的 `request_headers`、`request_params`、`request_body` 等，同步不覆盖已有值，不影响执行逻辑 |

---

*文档版本：1.0 | 基于 EasyTesting 代码库与需求整理*
