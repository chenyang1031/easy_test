# doc/md 文档转 API 资产 — 完整方案

## 需求回顾

1. 使用 mammoth + python-docx 实现 docx 转 md
2. 在【AI提示词管理】增加分类 "API生成" 和 "用例生成"
3. 本地存储转换后的 md 文档，数据库记录路径，支持"重新生成"跳过转换
4. 新增独立页面：上传文档 → 自定义任务名 → 展示生成记录 → 提供"重新生成""查看""导入API资产"按钮

## 格式说明

- mammoth 仅支持 `.docx`（Office 2007+），不支持旧版 `.doc` 二进制格式
- 方案支持 `.docx` + `.md`，旧 `.doc` 后续可通过 LibreOffice 扩展
- 需确认：上传文件后缀限定为 `.docx` 和 `.md`

---

## 一、数据模型

### 1.1 PromptTemplate 增加分类字段

**文件**: `test_manager/models/prompt_template.py`

新增字段：
```python
CATEGORY_API_GEN = "api_gen"         # API生成
CATEGORY_TEST_CASE_GEN = "test_case_gen"  # 用例生成
CATEGORY_CHOICES = [
    (CATEGORY_API_GEN, "API生成"),
    (CATEGORY_TEST_CASE_GEN, "用例生成"),
]
category = CharField(max_length=20, choices=CATEGORY_CHOICES, default="test_case_gen")
```

现有模板全部默认为"用例生成"，向后兼容。

### 1.2 新增 DocumentGenRecord 模型

**文件**: `test_manager/_models_flat.py`（或独立 `test_manager/models/document_gen_record.py`）

```python
class DocumentGenRecord(models.Model):
    """文档AI生成记录 — 上传文档→转md→调用大模型→提取API定义"""
    
    STATUS_CHOICES = [
        ("uploading",   "上传中"),
        ("converting",  "转换中"),
        ("generating",  "AI生成中"),
        ("success",     "生成成功"),
        ("failed",      "生成失败"),
    ]
    IMPORT_STATUS_CHOICES = [
        ("pending",          "待导入"),
        ("partial_imported", "部分导入"),
        ("imported",         "全部导入"),
    ]
    
    task_name           = CharField(max_length=200)              # 用户自定义任务名
    project             = ForeignKey(ApiProject, on_delete=CASCADE)
    original_file       = FileField(upload_to="document_gen/original/%Y/%m/")  # 上传的原始文件
    original_filename   = CharField(max_length=500)              # 原始文件名
    file_type           = CharField(max_length=10)               # "docx" / "md"
    converted_md_path   = CharField(max_length=500, blank=True)  # 转换后md文件路径（相对media）
    md_content          = TextField(blank=True)                  # md文本内容（方便直接读取，避免频繁IO）
    model_provider      = ForeignKey(AIModelProvider, on_delete=SET_NULL, null=True)
    prompt_template     = ForeignKey(PromptTemplate, on_delete=SET_NULL, null=True)
    prompt_full_text    = TextField(blank=True)                  # 实际发送给AI的完整prompt快照
    status              = CharField(max_length=20, default="uploading")
    extracted_apis      = JSONField(default=list)                # AI提取的API列表
    response_raw        = TextField(blank=True)                  # AI原始响应
    error_message       = TextField(blank=True)
    duration_ms         = IntegerField(null=True, blank=True)
    api_count           = IntegerField(default=0)                # 提取到的API数量
    import_status       = CharField(max_length=20, default="pending")
    imported_asset_ids  = JSONField(default=list)                # 已导入的ApiAsset ID列表
    created_by          = ForeignKey(User, on_delete=CASCADE)
    created_at          = DateTimeField(auto_now_add=True)
    updated_at          = DateTimeField(auto_now=True)
```

`extracted_apis` JSON 结构（每个元素与 ApiAsset 字段对齐）：
```json
[{
  "name": "接口名称",
  "method": "GET",
  "url": "/api/xxx",
  "interface_desc": "描述",
  "request_headers": {},
  "request_params": [],
  "request_body_format": "json",
  "request_body": {},
  "response_schema": {},
  "error_code": [],
  "auth_config": {},
  "_imported": false,
  "_imported_asset_id": null
}]
```

---

## 二、文档转换层

### 2.1 新建 `test_manager/utils/document_converter.py`

| 函数 | 说明 |
|------|------|
| `convert_docx_to_md(file_path) -> str` | 使用 mammoth 将 .docx 转为 markdown |
| `convert_to_md(file_path, file_type) -> str` | 统一入口：docx 调 mammoth，md 直接读取 |
| `save_converted_md(md_content, record_id) -> str` | 将 md 内容写入 `media/document_gen/converted/{record_id}.md`，返回相对路径 |

### 2.2 依赖

添加到 `requirements.txt`：
```
mammoth>=1.6.0
python-docx>=1.1.0
```

---

## 三、大模型调用层

### 3.1 扩展 BaseAdapter

**文件**: `test_manager/ai_adapters/base.py`

新增方法 `extract_apis_from_document(self, md_content: str, prompt_template=None) -> dict`：

1. 构建提示词上下文：`{"document_content": md_content}`
2. 如果有 prompt_template，调用 `prompt_template.to_rendered_prompt(context)`
3. 否则使用内置默认提示词（指令：从文档中提取 API 定义，输出 JSON 数组）
4. 调用 `self._call_llm(prompt)` 发送请求
5. 使用 `_extract_json()` 解析响应
6. 返回 `{"success": bool, "apis": list, "error": str|None}`

> 抽取 `_call_llm(prompt)` 私有方法，复用现有的 `build_request` + HTTP 调用逻辑，但使用专用的 API 提取 system prompt。

---

## 四、API 接口层

### 4.1 新建 `test_manager/api/document_gen_views.py`

**DocumentGenRecordViewSet** 注册在 `/api/ai/document-gen-records/`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 列表（分页，按 project_id/user 筛选） |
| `/` | POST | 创建记录（仅元数据，不含文件） |
| `/{id}/` | GET | 详情 |
| `/{id}/` | DELETE | 删除记录及关联文件 |
| `/{id}/upload/` | POST | 上传文件 + 转换 + 调 AI（multipart，含 task_name/file/model_provider_id/prompt_template_id/project_id） |

上传流程（`upload` action）：

1. 接收文件 + 参数
2. 创建 DocumentGenRecord（status="uploading"）
3. 保存原始文件 → status="converting"
4. 调用 `convert_to_md()` → 保存转换结果 → 存储 md_content + converted_md_path
5. status="generating"，通过 `get_adapter(provider)` 获取适配器
6. 调用 `adapter.extract_apis_from_document(md_content, prompt_template_obj)`
7. 成功：保存 extracted_apis、response_raw、prompt_full_text、duration_ms、api_count，status="success"
8. 失败：status="failed"，记录 error_message
9. 考虑到 LLM 调用耗时 10-30 秒，整个 upload 接口保持同步（前端显示加载进度即可），或使用 Celery 异步

| 端点 | 方法 | 说明 |
|------|------|------|
| `/{id}/regenerate/` | POST | 重新生成：从 converted_md_path 读取 md 内容，重新调用 AI（跳过转换），替换 extracted_apis |
| `/{id}/apis/` | GET | 获取提取的 API 列表详情（供"查看"页面使用） |
| `/{id}/preview-import/` | POST | 导入预览：接收要导入的 api index 列表，检测冲突，返回冲突信息 |
| `/{id}/confirm-import/` | POST | 确认导入：创建 ApiAsset 记录（source="ai_document"），更新 import_status 和 imported_asset_ids |

### 4.2 regenerate 流程

1. 校验记录 status 不是 "generating"
2. 从 converted_md_path 读取 md 内容（或直接用 md_content 字段）
3. 重建 prompt（使用 prompt_full_text 快照或重新渲染）
4. 调用 adapter.extract_apis_from_document(md_content)
5. 覆盖 extracted_apis、response_raw、duration_ms
6. 重置 import_status 为 "pending"（因为提取结果可能变化）

### 4.3 confirm-import 流程

1. 接收 body: `{api_indices: [0, 2, 5], conflict_strategy: "skip/overwrite/keep_both"}`
2. 从 record.extracted_apis 按索引取出要导入的 API
3. 对每个 API 调用 `_normalize_item()` 格式化数据
4. 调用 `_find_conflict_assets()` 检测冲突
5. 根据策略：skip/overwrite/keep_both
6. 创建 ApiAsset（source="ai_document"），调用 `resolve_group()` 处理分组
7. 更新 record.imported_asset_ids 和 import_status
8. 更新 record.extracted_apis 中对应项的 `_imported` 标记

### 4.4 URL 注册

**文件**: `test_manager/api/urls.py`

```python
router.register(r'ai/document-gen-records', DocumentGenRecordViewSet, basename='ai-document-gen-records')
```

---

## 五、前端页面

### 5.1 目录结构

```
frontend/scene-orchestrator/src/document-import/
├── main.js                          # Vue 应用入口
├── App.vue                          # 主布局
├── components/
│   ├── DocumentGenList.vue          # 生成记录列表（主页面）
│   ├── UploadDialog.vue             # 上传文档对话框
│   ├── ApiDetailView.vue            # "查看"页面 — 提取的API详情
│   └── ImportDialog.vue             # 导入确认对话框
├── stores/
│   └── documentImport.js            # Pinia store
└── api/
    └── index.js                     # API 请求封装
```

### 5.2 主页面 DocumentGenList

- 顶部："上传文档"按钮 + 项目筛选下拉
- 表格列：任务名、文件名、状态（标签）、API 数量、导入状态、创建时间、操作
- 操作列按钮：
  - **重新生成**：图标刷新，loading 状态，disabled 当 status="generating"
  - **查看**：跳转到 ApiDetailView 页面
  - **导入API资产**：打开 ImportDialog
  - **删除**：确认后删除

### 5.3 UploadDialog

表单字段：
- 任务名称（文本输入，必填）
- 文件上传（拖拽区域，限制 .docx/.md，必填）
- AI 模型（下拉，从 `store.aiModelProviders` 加载）
- 提示词模板（下拉，筛选 category="api_gen"）
- 项目（下拉，选择 ApiProject）

点击"开始生成"：
- 调用 `POST /api/ai/document-gen-records/{id}/upload/`
- 显示进度文字："正在上传文档…" → "正在转换格式…" → "正在调用AI提取接口…"
- 成功后关闭弹窗，刷新列表

### 5.4 ApiDetailView（"查看"页面）

- 顶部：任务名、原始文件名、生成时间
- 折叠面板：原始 markdown 文档内容（只读）
- API 列表（表格）：名称、方法、URL、描述
- 点击某个 API → 展开显示完整详情（类似 API 资产详情页）：
  - 请求头、请求参数、请求体、响应 schema、错误码、认证配置
- 支持勾选 API → "导入选中"按钮

### 5.5 ImportDialog

复用草稿箱的导入模式：

1. 显示待导入的 API 列表（已勾选或全选）
2. 点击"检测冲突" → 调 `/preview-import/`
3. 显示冲突信息（哪些 API 与现有资产冲突）
4. 选择冲突策略：跳过 / 覆盖 / 保留两者
5. 点击"确认导入" → 调 `/confirm-import/`
6. 显示导入结果：created_count / updated_count / skipped_count

### 5.6 路由和入口

**文件**: `frontend/scene-orchestrator/vite.config.js` — 新增多页入口 `document-import`

---

## 六、提示词管理改造

### 6.1 后端

| 文件 | 改动 |
|------|------|
| `test_manager/models/prompt_template.py` | 新增 `category` 字段 |
| `test_manager/api/serializers.py` | `PromptTemplateSerializer` 新增 `category` |
| `test_manager/api/views.py` | `PromptTemplateManagementViewSet` 列表接口支持 `?category=api_gen` 筛选 |

### 6.2 前端

| 文件 | 改动 |
|------|------|
| `components/PromptTemplateModal.vue` | 表单新增"分类"下拉（API生成 / 用例生成） |
| `components/PromptTemplateList.vue` | 表格新增"分类"列，新增分类筛选 |
| `stores/promptTemplate.js` | formData 新增 category 字段 |

### 6.3 向后兼容

- 迁移文件设置所有现有模板 `category="test_case_gen"`
- AI 生成弹窗（AIGenerateModal）筛选模板时默认只显示"用例生成"分类
- 文档上传弹窗（UploadDialog）筛选模板时只显示"API生成"分类

---

## 七、API 资产 source 扩展

**文件**: `test_manager/_models_flat.py` — `ApiAsset.source` 新增选项 `"ai_document"`

---

## 八、文件清单汇总

### 新建文件
| 文件 | 说明 |
|------|------|
| `test_manager/utils/document_converter.py` | docx→md 转换工具 |
| `test_manager/api/document_gen_views.py` | DocumentGenRecord ViewSet |
| `frontend/scene-orchestrator/src/document-import/main.js` | 前端入口 |
| `frontend/scene-orchestrator/src/document-import/App.vue` | 主组件 |
| `frontend/scene-orchestrator/src/document-import/components/DocumentGenList.vue` | 记录列表 |
| `frontend/scene-orchestrator/src/document-import/components/UploadDialog.vue` | 上传弹窗 |
| `frontend/scene-orchestrator/src/document-import/components/ApiDetailView.vue` | API 详情 |
| `frontend/scene-orchestrator/src/document-import/components/ImportDialog.vue` | 导入弹窗 |
| `frontend/scene-orchestrator/src/document-import/stores/documentImport.js` | Pinia store |
| `frontend/scene-orchestrator/src/document-import/api/index.js` | API 封装 |

### 修改文件
| 文件 | 改动 |
|------|------|
| `test_manager/models/prompt_template.py` | 新增 category 字段 |
| `test_manager/_models_flat.py` | 新增 DocumentGenRecord 模型 + ApiAsset.source 扩展 |
| `test_manager/api/serializers.py` | PromptTemplateSerializer + DocumentGenRecordSerializer |
| `test_manager/api/views.py` | PromptTemplateManagementViewSet 支持 category 筛选 |
| `test_manager/api/urls.py` | 注册 document-gen-records 路由 |
| `test_manager/ai_adapters/base.py` | 新增 extract_apis_from_document + _call_llm 方法 |
| `requirements.txt` | 新增 mammoth、python-docx |
| `frontend/.../prompt-template-manager/components/PromptTemplateModal.vue` | 新增分类字段 |
| `frontend/.../prompt-template-manager/components/PromptTemplateList.vue` | 新增分类列和筛选 |
| `frontend/.../prompt-template-manager/stores/promptTemplate.js` | formData 新增 category |
| `frontend/.../api-asset-manager/components/AIGenerateModal.vue` | 模板列表筛选 category="test_case_gen" |
| `frontend/scene-orchestrator/vite.config.js` | 新增 document-import 入口 |

---

## 九、验证方式

1. 提示词管理：创建/编辑模板时可选择分类，列表可按分类筛选
2. 上传 .docx：转换 → 查看 md 内容 → AI 提取 API → 列表展示
3. 上传 .md：跳过转换直接调 AI
4. 重新生成：查看生成的提取结果变化，验证转换步骤被跳过
5. 查看页面：点击 API 展开详情，各字段正确显示
6. 导入：创建冲突/无冲突场景，验证跳过/覆盖/保留两者策略
7. 错误处理：上传非支持格式、超大文件、AI 返回异常数据
