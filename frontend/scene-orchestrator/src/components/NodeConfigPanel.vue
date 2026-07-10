<template>
  <div class="card p-3 h-100 overflow-auto">
    <template v-if="node">
      <div class="mb-2">
        <strong>节点配置</strong>
      </div>

      <el-tabs v-model="activeTab" type="card" class="node-config-tabs">
        <el-tab-pane label="节点信息" name="info">
          <div class="tab-content">
            <div class="mb-2">
              <label class="form-label form-label-sm">节点名称</label>
              <input v-model="localNode.name" class="form-control form-control-sm" />
            </div>
            <div class="mb-2">
              <label class="form-label form-label-sm">节点描述</label>
              <input v-model="localNode.description" class="form-control form-control-sm" />
            </div>
            <div class="mb-2">
              <label class="form-label form-label-sm">失败策略</label>
              <el-select v-model="localNode.on_failed" size="small" popper-class="scene-select-popper" style="width: 100%">
                <el-option label="失败终止" value="stop" />
                <el-option label="失败继续" value="continue" />
              </el-select>
            </div>
            <div class="mb-2">
              <label class="form-label form-label-sm">节点启用</label>
              <el-select v-model="localNode.is_enabled" size="small" popper-class="scene-select-popper" style="width: 100%">
                <el-option label="启用" :value="true" />
                <el-option label="禁用" :value="false" />
              </el-select>
            </div>
            <div class="mb-2">
              <label class="form-label form-label-sm">超时时间(秒)</label>
              <input v-model.number="localNode.timeout" type="number" class="form-control form-control-sm" placeholder="30" />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="参数配置" name="params">
          <div class="tab-content">
            <div class="mb-2">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <label class="form-label form-label-sm m-0">接口 URL</label>
                <button class="btn btn-sm btn-outline-secondary" @click="openVariablePicker('url')">插入变量</button>
              </div>
              <input
                v-model="localNode.request_url"
                class="form-control form-control-sm"
                :placeholder="node?.api_asset_url || '接口地址'"
              />
              <p v-if="node?.api_asset_url && !localNode.request_url" class="text-muted small mt-1 mb-0">使用资产原始 URL：{{ node.api_asset_url }}</p>
              <p v-if="localNode.request_url && node?.api_asset_url && localNode.request_url !== node.api_asset_url" class="text-info small mt-1 mb-0">已覆盖资产 URL，原始地址：{{ node.api_asset_url }}</p>
            </div>
            <div class="mb-2">
              <label class="form-label form-label-sm">接口专属环境</label>
              <el-select v-model="localNode.environment_id" placeholder="继承场景" size="small" popper-class="scene-select-popper" style="width: 100%" @change="markDirty">
                <el-option label="继承场景" :value="''" />
                <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
              </el-select>
            </div>
            <div class="mb-2">
              <label class="form-label form-label-sm">自定义域名</label>
              <input
                v-model="localNode.custom_base_url"
                class="form-control form-control-sm"
                placeholder="如 https://api.example.com，留空则使用环境拼接"
                @input="markDirty"
              />
              <p class="text-muted small mt-1 mb-0">直接输入外部地址时优先于环境选择</p>
            </div>
            <div class="mb-2">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <label class="form-label form-label-sm m-0">请求头</label>
                <div class="d-flex gap-1">
                  <button class="btn btn-sm btn-outline-secondary" @click="openVariablePicker('headers')">插入变量</button>
                </div>
              </div>
              <KvTableEditor v-model="headersKvRows" variant="simple" row-key="h" add-label="+ 新增请求头" @row-focus="setHeaderCursor" />
            </div>
            <!-- ========== 合并后的"请求配置"区域 ========== -->
            <div class="mb-2">
              <!-- 标题行 -->
              <div class="d-flex justify-content-between align-items-center mb-2">
                <label class="form-label form-label-sm m-0">请求配置</label>
                <button class="btn btn-sm btn-outline-secondary" @click="openVariablePicker(requestField)">插入变量</button>
              </div>
              
              <!-- 单选：请求参数 / 请求体 -->
              <div class="request-type-selector mb-2">
                <el-radio-group v-model="requestType" size="small" @change="onRequestTypeUserChange">
                  <el-radio-button label="params">请求参数</el-radio-button>
                  <el-radio-button label="body">请求体</el-radio-button>
                </el-radio-group>
              </div>
              
              <!-- 格式切换：JSON / 键值对 -->
              <div class="request-format-selector mb-2">
                <el-radio-group v-model="requestFormat" size="small">
                  <el-radio-button label="json">JSON</el-radio-button>
                  <el-radio-button label="kv">键值对</el-radio-button>
                </el-radio-group>
              </div>
              
              <!-- 请求参数 - JSON 格式 -->
              <div v-if="requestType === 'params' && requestFormat === 'json'" class="json-editor-wrapper">
                <textarea
                  ref="paramsTextareaRef"
                  v-model="paramsText"
                  class="form-control form-control-sm code-area"
                />
                <button class="btn btn-sm btn-outline-secondary json-expand-btn" title="全屏编辑" @click="openJsonDialog('params')">
                  <i class="bi bi-arrows-angle-expand"></i>
                </button>
              </div>
              
              <!-- 请求参数 - 键值对格式 -->
              <KvTableEditor v-else-if="requestType === 'params' && requestFormat === 'kv'" v-model="paramsKvRows" variant="typed" row-key="p" add-label="+ 新增参数" @row-focus="(idx) => setKvCursor('params', idx)" />
              
              <!-- 请求体 - JSON 格式 -->
              <div v-else-if="requestType === 'body' && requestFormat === 'json'" class="json-editor-wrapper">
                <textarea
                  ref="bodyTextareaRef"
                  v-model="bodyText"
                  class="form-control form-control-sm code-area"
                />
                <button class="btn btn-sm btn-outline-secondary json-expand-btn" title="全屏编辑" @click="openJsonDialog('body')">
                  <i class="bi bi-arrows-angle-expand"></i>
                </button>
              </div>
              
              <!-- 请求体 - 键值对格式 -->
              <KvTableEditor v-else-if="requestType === 'body' && requestFormat === 'kv'" v-model="bodyKvRows" variant="typed" row-key="b" add-label="+ 新增字段" @row-focus="(idx) => setKvCursor('body', idx)" />
            </div>
            <VariablePicker
              v-model:visible="showVariablePicker"
              :model-value="activeVariablePreview"
              :options="variableOptions"
              :scene-id="sceneId"
              :current-node-id="currentNodeId"
              :environment-id="environmentId"
              @pick="insertVariableAtCursor"
              @close="onPickerClose"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="响应配置" name="response">
          <div class="tab-content response-config-layout">
            <div class="response-preview-section" :style="{ flex: `0 0 ${responseSplitRatio * 100}%` }">
              <div class="section-label">响应预览</div>
              <div v-if="!nodeResponsePreview" class="response-preview-empty">暂无响应数据</div>
              <div v-else class="response-preview-body">
                <div class="response-json-rows">
                  <div
                    v-for="(row, idx) in responsePreviewRows"
                    :key="idx"
                    class="response-json-row"
                    :class="{ 'response-json-row--selected': selectedRowIndex === idx }"
                    @click="selectResponseRow(idx)"
                  >
                    {{ row.line }}
                  </div>
                </div>
                <div class="response-preview-actions">
                  <el-tooltip :content="selectedRowPath ? '复制选中字段路径' : '请先选中JSON字段行'" placement="top">
                    <span class="copy-path-wrapper">
                      <button
                        class="btn btn-sm btn-outline-secondary"
                        :disabled="!selectedRowPath"
                        @click="copyResponsePath"
                      >
                        复制路径
                      </button>
                    </span>
                  </el-tooltip>
                </div>
              </div>
            </div>
            <div class="response-divider" @mousedown="startResize">
              <div class="response-divider-handle" />
            </div>
            <div class="response-extract-section" :style="{ flex: `1` }">
              <div class="mb-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label form-label-sm m-0">提取规则</label>
                  <button class="btn btn-sm btn-outline-primary" @click="addExtractRow">新增提取</button>
                </div>
                <div class="extract-editor kv-editor">
                  <div v-for="(row, idx) in extractRows" :key="`e-${idx}`" class="kv-row">
                    <input v-model="row.name" class="form-control form-control-sm" placeholder="变量名" />
                    <input v-model="row.path" class="form-control form-control-sm" placeholder="路径，如 $.response.data.token（响应体在 response 下）" />
                    <button class="btn btn-sm btn-outline-danger" @click="removeExtractRow(idx)">删</button>
                  </div>
                  <p class="text-muted small mt-1 mb-0">从响应中提取字段到变量池，供后续节点使用</p>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="断言规则" name="assert">
          <div class="tab-content">
            <AssertionEditor v-model="localNode.assert_rules" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="前置脚本" name="script">
          <div class="tab-content">
            <!-- 继承提示 -->
            <div v-if="!localNode.pre_request_script && effectiveEnvScript" class="script-inherit-info mb-2">
              <span class="badge bg-secondary me-1">继承环境脚本</span>
              <span class="text-muted small">当前节点未配置，使用环境前置脚本</span>
            </div>

            <!-- 超时配置 + 操作栏 -->
            <div class="d-flex justify-content-between align-items-center mb-2">
              <div class="d-flex align-items-center gap-2">
                <label class="form-label form-label-sm mb-0">超时 (ms)</label>
                <input v-model.number="localNode.script_timeout" type="number"
                       min="0" max="30000" step="100"
                       class="form-control form-control-sm"
                       style="width: 100px"
                       placeholder="1000" />
              </div>
              <div class="d-flex gap-1">
                <el-select v-model="scriptSnippet" placeholder="插入片段" size="small"
                           style="width: 130px" @change="onScriptSnippetChange">
                  <el-option label="插入片段" value="" disabled />
                  <el-option label="Token 刷新" value="token_refresh" />
                  <el-option label="签名生成" value="signature" />
                  <el-option label="请求头添加" value="request_header" />
                  <el-option label="时间戳" value="timestamp" />
                </el-select>
                <el-button size="small" type="primary" plain
                           :loading="testingScript"
                           @click="testNodeScript">
                  <i class="bi bi-play-circle"></i> 测试
                </el-button>
              </div>
            </div>

            <!-- ES6 语法警告 -->
            <div v-if="es6Warnings.length" class="es6-warning mb-2">
              <span class="text-danger">⚠ ES6 语法检测：</span>
              <span>{{ es6Warnings.join("、") }} — 请改用 ES5.1 兼容写法</span>
            </div>

            <!-- 编辑器 -->
            <textarea
              id="node-pre-request-script-editor"
              v-model="localNode.pre_request_script"
              class="form-control form-control-sm code-area font-monospace"
              rows="10"
              placeholder="// 节点级前置脚本，会在环境脚本之后执行&#10;// 使用 pm.environment / pm.request / pm.variables 预处理请求&#10;// 当前仅支持 ES5.1 语法（禁止 const/let/箭头函数/async-await 等 ES6+）&#10;&#10;var token = pm.environment.get('token');&#10;if (token) { pm.request.headers.add({ key: 'Authorization', value: 'Bearer ' + token }); }"
            />

            <!-- 测试结果 -->
            <div v-if="scriptTestResult" class="script-test-result mt-2">
              <div class="small text-muted mb-1">测试结果：</div>
              <pre class="small mb-0 p-2 bg-light border rounded">{{ scriptTestResult }}</pre>
            </div>

            <div class="form-text mt-1">
              <span class="text-danger">⚠ ES5.1 限制</span>：禁止 const/let/箭头函数/class/解构/for...of/async-await 等 ES6+ 语法。
              建议用 AI 工具将 ES6 代码转为 ES5.1。
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
    <div v-else class="text-muted">请选择/添加接口配置</div>
  </div>

  <!-- JSON 全屏编辑覆盖层：Teleport to body + v-show 隔离组件树 -->
  <Teleport to="body">
    <div v-show="jsonDialogVisible" ref="jsonDialogOverlayRef" tabindex="-1" class="json-fullscreen-overlay" @click.self="onJsonDialogCancel" @keydown.escape="onJsonDialogCancel" @keydown.enter.prevent="onJsonDialogConfirm">
      <div class="json-fullscreen-card">
        <div class="json-fullscreen-header">
          <span>{{ jsonDialogTitle }}</span>
          <div class="json-fullscreen-header-actions">
            <button class="btn btn-sm btn-outline-secondary" @click="onJsonDialogCancel">取消</button>
            <button class="btn btn-sm btn-primary" @click="onJsonDialogConfirm">确定</button>
          </div>
        </div>
        <textarea
          ref="jsonDialogTextareaRef"
          v-model="jsonDialogText"
          class="form-control code-area font-monospace json-fullscreen-textarea"
        />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { computed, nextTick, onUnmounted, ref, watch } from "vue";
import AssertionEditor from "./AssertionEditor.vue";
import VariablePicker from "./VariablePicker.vue";
import KvTableEditor from "./KvTableEditor.vue";
import { cloneJson } from "../utils/cloneJson";

const KV_TYPE_OPTIONS = [
  { value: "string", label: "string" },
  { value: "number", label: "number" },
  { value: "boolean", label: "boolean" },
  { value: "file", label: "file" },
  { value: "array", label: "array" },
  { value: "object", label: "object" }
];

const props = defineProps({
  node: {
    type: Object,
    default: null
  },
  nodes: {
    type: Array,
    default: () => []
  },
  variableOptions: {
    type: Array,
    default: () => []
  },
  sceneId: {
    type: [Number, String],
    default: null
  },
  currentNodeId: {
    type: [Number, String],
    default: null
  },
  nodeResponsePreview: {
    type: [Object, Array, String, Number],
    default: null
  },
  environments: {
    type: Array,
    default: () => []
  },
  environmentId: {
    type: [Number, String],
    default: null
  },
  saving: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(["save", "update:dirty"]);

const activeTab = ref("info");
const localNode = ref(null);
const headersKvRows = ref([{ key: "", value: "" }]);
const extractRows = ref([{ name: "", path: "" }]);
const paramsText = ref("{}");
const bodyText = ref("{}");
const showVariablePicker = ref(false);
const activeField = ref("");
// 合并后的请求配置状态
const requestType = ref("body");    // "params" | "body"
const requestFormat = ref("json"); // "json" | "kv"
const userChangedRequestType = ref(false); // 用户手动切换过 requestType 时置 true，阻止 watch 覆盖
// 计算属性：获取当前激活的 field 类型（用于变量选择器）
const requestField = computed(() => requestType.value);
// 兼容旧代码：paramsMode 和 bodyMode（保持向后兼容，内部不再使用）
const paramsMode = computed(() => requestFormat.value);
const bodyMode = computed(() => requestFormat.value);
const paramsTextareaRef = ref(null);
const bodyTextareaRef = ref(null);
const paramsKvRows = ref([]);
const bodyKvRows = ref([]);
const activeKvCursor = ref(null);
const activeHeaderCursor = ref(0);
const activeVariablePreview = ref("");
// JSON 全屏编辑对话框
const jsonDialogVisible = ref(false);
const jsonDialogType = ref("body");
const jsonDialogText = ref("");
const jsonDialogTextareaRef = ref(null);
const jsonDialogOverlayRef = ref(null);
const jsonDialogTitle = computed(() => {
  return jsonDialogType.value === "body" ? "编辑请求体 (JSON)" : "编辑请求参数 (JSON)";
});

const isInternalUpdate = ref(false);
const isDirty = ref(false);
let markDirtyTimer = null;
const MARK_DIRTY_DEBOUNCE_MS = 80;
const lastLoadedNodeId = ref(null);

// 节点前置脚本相关
const scriptSnippet = ref("");
const testingScript = ref(false);
const scriptTestResult = ref("");

const ES6_PATTERNS = [
  { pattern: /\bconst\s+\w/g, label: "const 声明" },
  { pattern: /\blet\s+\w/g, label: "let 声明" },
  { pattern: /=>/g, label: "箭头函数" },
  { pattern: /\bclass\s+\w/g, label: "class 声明" },
  { pattern: /\bimport\s+/g, label: "import 语句" },
  { pattern: /\bexport\s+/g, label: "export 语句" },
  { pattern: /for\s*\([^)]*\b(of)\b/g, label: "for...of 循环" },
  { pattern: /\basync\s+function|\basync\s+\(|\basync\s+\w+\s*=>/g, label: "async 函数" },
  { pattern: /\bawait\s+/g, label: "await 表达式" },
  { pattern: /`[^`]*\$\{[^}]*\}[^`]*`/g, label: "模板字符串" },
  { pattern: /const\s*\{[^}]*\}\s*=/g, label: "解构赋值" },
  { pattern: /const\s*\[[^\]]*\]\s*=/g, label: "数组解构" },
];

const es6Warnings = computed(() => {
  const script = localNode.value?.pre_request_script || "";
  if (!script.trim()) return [];
  return ES6_PATTERNS
    .filter(({ pattern }) => {
      const p = new RegExp(pattern.source, pattern.flags);
      return p.test(script);
    })
    .map(({ label }) => label);
});

// 响应预览与提取规则区的分割比例（0.2 ~ 0.7）
const responseSplitRatio = ref(0.4);
const selectedRowIndex = ref(-1);
let resizeRaf = null;

function startResize(e) {
  e.preventDefault();
  const container = e.target.closest(".response-config-layout");
  if (!container) return;
  const startY = e.clientY;
  const startTopHeight = container.querySelector(".response-preview-section")?.offsetHeight || 0;
  const containerHeight = container.offsetHeight;
  const startRatio = containerHeight > 0 ? startTopHeight / containerHeight : 0.4;

  function onMove(ev) {
    if (resizeRaf) return;
    resizeRaf = requestAnimationFrame(() => {
      resizeRaf = null;
      const dy = ev.clientY - startY;
      const newRatio = Math.min(0.7, Math.max(0.2, startRatio + dy / containerHeight));
      responseSplitRatio.value = newRatio;
    });
  }

  function onUp() {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }

  document.body.style.cursor = "row-resize";
  document.body.style.userSelect = "none";
  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

// 响应预览行数据：{ line, path }，path 为 JSONPath（如 $.response.data.token），与提取规则语法一致
const responsePreviewRows = computed(() => {
  const data = props.nodeResponsePreview;
  if (data == null) return [];
  try {
    const obj = typeof data === "string" ? JSON.parse(data) : data;
    const rows = [];
    const PREFIX = "$.response";

    function pathSeg(k) {
      return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(String(k)) ? `.${k}` : `["${String(k).replace(/"/g, '\\"')}"]`;
    }
    function formatValue(v) {
      if (v === null) return "null";
      if (typeof v === "string") return JSON.stringify(v);
      if (typeof v === "number" || typeof v === "boolean") return String(v);
      return "null";
    }
    function walkObject(val, basePath, indent) {
      const pad = "  ".repeat(indent);
      const keys = Object.keys(val);
      keys.forEach((k, i) => {
        const isLast = i === keys.length - 1;
        const path = basePath + pathSeg(k);
        const v = val[k];
        if (v !== null && typeof v === "object" && !Array.isArray(v)) {
          rows.push({ line: `${pad}"${k}": {`, path });
          walkObject(v, path, indent + 1);
          rows.push({ line: `${pad}}${isLast ? "" : ","}`, path: null });
        } else if (Array.isArray(v)) {
          rows.push({ line: `${pad}"${k}": [`, path });
          v.forEach((item, idx) => {
            const elemPath = `${path}[${idx}]`;
            if (item !== null && typeof item === "object" && !Array.isArray(item)) {
              rows.push({ line: `${pad}  {`, path: elemPath });
              walkObject(item, elemPath, indent + 2);
              rows.push({ line: `${pad}  }${idx === v.length - 1 ? "" : ","}`, path: null });
            } else {
              rows.push({ line: `${pad}  ${formatValue(item)}${idx === v.length - 1 ? "" : ","}`, path: elemPath });
            }
          });
          rows.push({ line: `${pad}]${isLast ? "" : ","}`, path: null });
        } else {
          rows.push({ line: `${pad}"${k}": ${formatValue(v)}${isLast ? "" : ","}`, path });
        }
      });
    }
    if (Array.isArray(obj)) {
      rows.push({ line: "[", path: null });
      obj.forEach((item, idx) => {
        const path = `${PREFIX}[${idx}]`;
        if (item !== null && typeof item === "object" && !Array.isArray(item)) {
          rows.push({ line: "  {", path });
          walkObject(item, path, 1);
          rows.push({ line: `  }${idx === obj.length - 1 ? "" : ","}`, path: null });
        } else {
          rows.push({ line: `  ${formatValue(item)}${idx === obj.length - 1 ? "" : ","}`, path });
        }
      });
      rows.push({ line: "]", path: null });
    } else if (obj !== null && typeof obj === "object") {
      rows.push({ line: "{", path: null });
      walkObject(obj, PREFIX, 1);
      rows.push({ line: "}", path: null });
    }
    return rows.slice(0, 2000);
  } catch {
    return [{ line: String(data), path: null }];
  }
});

// 当前选中行的路径，未选中时为 null
const selectedRowPath = computed(() => {
  if (selectedRowIndex.value < 0) return null;
  const row = responsePreviewRows.value[selectedRowIndex.value];
  return row?.path ?? null;
});

// 单选逻辑：点击行时取消其他行选中，仅保留当前行
function selectResponseRow(idx) {
  const row = responsePreviewRows.value[idx];
  if (row?.path != null) {
    selectedRowIndex.value = idx;
  } else {
    selectedRowIndex.value = -1;
  }
}

function copyResponsePath() {
  const path = selectedRowPath.value;
  if (!path) return;
  copyToClipboard(path).then(
    () => ElMessage.success(`已复制路径：${path}`),
    () => ElMessage.error("复制失败")
  );
}

/** 剪贴板写入，兼容非安全上下文（HTTP）降级到 document.execCommand */
function copyToClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  }
  // fallback for HTTP / older browsers
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    return Promise.resolve();
  } catch {
    return Promise.reject(new Error("copy failed"));
  }
}

// 切换节点时清空选中态，避免跨节点残留
watch(
  () => props.node?.id,
  () => {
    selectedRowIndex.value = -1;
  }
);

function onRequestTypeUserChange() {
  userChangedRequestType.value = true;
}

function markDirty() {
  if (isInternalUpdate.value) return;
  clearTimeout(markDirtyTimer);
  markDirtyTimer = setTimeout(() => {
    markDirtyTimer = null;
    if (!isDirty.value) {
      isDirty.value = true;
      emit("update:dirty", true);
    }
  }, MARK_DIRTY_DEBOUNCE_MS);
}

watch(
  () => props.node,
  (value) => {
    isInternalUpdate.value = true;
    try {
      if (!value) {
        localNode.value = null;
        lastLoadedNodeId.value = null;
        return;
      }
      const nodeIdChanged = String(value.id) !== String(lastLoadedNodeId.value);
      localNode.value = toEditableNode(value);
      if (!nodeIdChanged) {
        // 同一节点数据刷新（如保存后 store.upsertNode 触发），保持用户正在编辑的表单状态不变
        return;
      }
      lastLoadedNodeId.value = value.id;
      // 切换到不同节点时重置用户手动标记，让 watch 按节点数据设置初始值
      userChangedRequestType.value = false;
      // 使用节点保存的配置作为显示来源，不再与 API 默认值合并，避免用户清空后保存时被 API 默认参数覆盖
      const nodeHeaders = value.request_headers || {};
      headersKvRows.value = objectToKvRows(nodeHeaders);
      activeHeaderCursor.value = 0;

      const nodeParams = value.request_params || {};
      // 兼容 list 格式（旧节点可能存储了数组格式的 request_params）
      const nodeParamsObj = Array.isArray(nodeParams)
        ? nodeParams.reduce((acc, item) => {
            if (item && item.key) acc[item.key] = item.value || ''
            return acc
          }, {})
        : nodeParams
      const apiParams = value.api_asset_request_params || {};
      paramsText.value = JSON.stringify(nodeParamsObj, null, 2);

      const nodeBody = value.request_body || {};
      bodyText.value = JSON.stringify(nodeBody, null, 2);

      // 新的回显逻辑：根据哪个字段有值来决定 requestType
      // 但如果用户已手动切换过 requestType，则优先保留用户选择
      const hasParams = nodeParamsObj && typeof nodeParamsObj === 'object' && !Array.isArray(nodeParamsObj) && Object.keys(nodeParamsObj).length > 0;
      const hasBody = nodeBody && Object.keys(nodeBody).length > 0;

      if (!userChangedRequestType.value) {
        if (hasParams) {
          // request_params 有值 -> 显示请求参数
          requestType.value = "params";
          requestFormat.value = (value.param_type || (Object.keys(apiParams).length ? "form-data" : "json")) === "form-data" ? "kv" : "json";
        } else if (hasBody) {
          // request_body 有值 -> 显示请求体
          requestType.value = "body";
          const apiBodyFormat = value.api_asset_request_body_format || "json";
          requestFormat.value = (value.body_type || apiBodyFormat) === "form-data" ? "kv" : "json";
        } else {
          // 两者都没有 -> 默认显示请求体
          requestType.value = "body";
          requestFormat.value = "json";
        }
      }

      // 兼容旧代码：仍需更新 paramsMode 和 bodyMode
      paramsKvRows.value = requestFormat.value === "kv"
        ? objectToKvRowsWithType(nodeParams)
        : [{ key: "", value: "", type: "string" }];
      bodyKvRows.value = requestFormat.value === "kv"
        ? objectToKvRowsWithType(nodeBody)
        : [{ key: "", value: "", type: "string" }];
      extractRows.value = extractRulesToRows(localNode.value.extract_rules);
    } catch (err) {
      console.error("NodeConfigPanel node watch error:", err);
    } finally {
      nextTick(() => {
        isInternalUpdate.value = false;
        isDirty.value = false;
        emit("update:dirty", false);
      });
    }
  },
  { immediate: true }
);

watch(
  [
    () => localNode.value?.environment_id,
    () => localNode.value?.custom_base_url,
    () => localNode.value,
    () => headersKvRows.value,
    () => paramsText.value,
    () => bodyText.value,
    () => paramsKvRows.value,
    () => bodyKvRows.value,
    () => paramsMode.value,
    () => bodyMode.value,
    () => extractRows.value
  ],
  () => markDirty(),
  { deep: true, flush: "post" }
);

watch(paramsMode, (mode) => {
  if (mode !== "kv" || !localNode.value) return;
  const nodeParams = localNode.value.request_params || {};
  paramsKvRows.value = objectToKvRowsWithType(nodeParams);
});

watch(bodyMode, (mode) => {
  if (mode !== "kv" || !localNode.value) return;
  const nodeBody = localNode.value.request_body || {};
  bodyKvRows.value = objectToKvRowsWithType(nodeBody);
});

function toEditableNode(node) {
  return {
    id: node.id,
    scene: node.scene,
    api_asset: node.api_asset,
    node_key: node.node_key,
    name: node.name || "",
    description: node.description || "",
    request_headers: asPlainObject(node.request_headers),
    request_params: asPlainObject(node.request_params),
    request_body: asPlainObject(node.request_body),
    assert_rules: cloneJson(node.assert_rules, []),
    extract_rules: cloneJson(node.extract_rules, []),
    expected_status_code: Number(node.expected_status_code || 200),
    timeout: Number(node.timeout || 30),
    on_failed: node.on_failed || "continue",
    sort: Number(node.sort || 0),
    is_enabled: node.is_enabled !== false,
    param_type: node.param_type || "json",
    body_type: node.body_type || "json",
    environment_id: node.environment_id ?? (typeof node.environment === "object" && node.environment?.id) ?? (typeof node.environment === "number" ? node.environment : null) ?? "",
    custom_base_url: node.custom_base_url || "",
    request_url: node.request_url || "",
    pre_request_script: node.pre_request_script || "",
    script_timeout: node.script_timeout ?? 1000
  };
}

function asPlainObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return value;
}
function openVariablePicker(field) {
  activeField.value = field;
  activeVariablePreview.value = "";
  showVariablePicker.value = true;
}

function insertVariableAtCursor(variable) {
  const field = activeField.value;
  if (!field) {
    return;
  }
  if (field === "params") {
    if (paramsMode.value === "json") {
      paramsText.value = insertTextAtCursor(paramsTextareaRef.value, paramsText.value, variable);
    } else if (activeKvCursor.value?.target === "params") {
      const row = paramsKvRows.value[activeKvCursor.value.index];
      if (row) {
        row.value = `${row.value || ""}${variable}`;
      }
    }
  } else if (field === "body") {
    if (bodyMode.value === "json") {
      bodyText.value = insertTextAtCursor(bodyTextareaRef.value, bodyText.value, variable);
    } else if (activeKvCursor.value?.target === "body") {
      const row = bodyKvRows.value[activeKvCursor.value.index];
      if (row) {
        row.value = `${row.value || ""}${variable}`;
      }
    }
  } else if (field === "headers") {
    const idx = Math.max(0, Math.min(activeHeaderCursor.value, headersKvRows.value.length - 1));
    const row = headersKvRows.value[idx];
    if (row) {
      row.value = `${row.value || ""}${variable}`;
    }
  } else if (field === "url") {
    if (localNode.value) {
      localNode.value.request_url = `${localNode.value.request_url || ""}${variable}`;
    }
  }
  activeVariablePreview.value = variable;
  showVariablePicker.value = false;
}

function onPickerClose() {
  showVariablePicker.value = false;
}

function openJsonDialog(type) {
  jsonDialogType.value = type;
  jsonDialogText.value = type === "body" ? bodyText.value : paramsText.value;
  jsonDialogVisible.value = true;
  nextTick(() => {
    if (jsonDialogOverlayRef.value) {
      jsonDialogOverlayRef.value.focus();
    }
    if (jsonDialogTextareaRef.value) {
      jsonDialogTextareaRef.value.focus();
    }
  });
}

function onJsonDialogConfirm() {
  if (jsonDialogType.value === "body") {
    bodyText.value = jsonDialogText.value;
  } else {
    paramsText.value = jsonDialogText.value;
  }
  markDirty();
  jsonDialogVisible.value = false;
}

function onJsonDialogCancel() {
  jsonDialogVisible.value = false;
}

function insertTextAtCursor(textareaEl, source, insertText) {
  const text = String(source || "");
  if (!textareaEl) {
    return text + insertText;
  }
  const start = textareaEl.selectionStart || 0;
  const end = textareaEl.selectionEnd || 0;
  // 插入时使用 {{func()}} 不带引号形式，保存时 parseJsonStrict 会自动补引号
  const wrapped = insertText;
  const next = `${text.slice(0, start)}${wrapped}${text.slice(end)}`;
  requestAnimationFrame(() => {
    const pos = start + wrapped.length;
    textareaEl.selectionStart = pos;
    textareaEl.selectionEnd = pos;
    textareaEl.focus();
  });
  return next;
}

function parseJsonStrict(raw, label) {
  // 允许用户在编辑区写注释，保存前去掉 // 行注释
  let clean = String(raw)
    .split("\n")
    .filter((line) => !line.trim().startsWith("//"))
    .join("\n");
  try {
    // 先尝试直接解析：若已是合法 JSON（如首次保存后再次保存，此时 {{func()}} 已被引号包裹），直接返回，避免正则误改
    const parsed = JSON.parse(clean || "{}");
    return parsed;
  } catch {
    // 解析失败时，遍历字符串，只给不在 JSON 字符串内的 {{...}} 加引号，
    // 避免误伤 "user{{time}}" 这种已在引号内的变量引用。
    let inString = false;
    let result = "";
    let i = 0;
    while (i < clean.length) {
      // 转义符：跳过下一个字符
      if (clean[i] === "\\" && i + 1 < clean.length) {
        result += clean[i] + clean[i + 1];
        i += 2;
        continue;
      }
      // 引号切换字符串状态
      if (clean[i] === '"') {
        inString = !inString;
        result += '"';
        i++;
        continue;
      }
      // 不在字符串内时，检测裸 {{...}}（如 [{{roleid}}]、{"key": {{val}}}），为其加引号
      if (!inString && clean[i] === "{" && i + 1 < clean.length && clean[i + 1] === "{") {
        const end = clean.indexOf("}}", i + 2);
        if (end !== -1) {
          const expr = clean.slice(i, end + 2);
          // 转义模板表达式内的引号，防止 {{func("arg")}} 被引号包裹时破坏 JSON 结构
          const escaped = expr.replace(/"/g, '\\"');
          result += `"${escaped}"`;
          i = end + 2;
          continue;
        }
      }
      result += clean[i];
      i++;
    }
    try {
      return JSON.parse(result || "{}");
    } catch (error) {
      throw new Error(`${label} 不是合法JSON`);
    }
  }
}

/**
 * 将对象转为键值对行，兼容两种格式：
 * - 简单格式：{ key: "value" }
 * - API 资产格式：{ key: { value: "xxx", required, type, ... } }
 */
function objectToKvRows(obj) {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
    return [{ key: "", value: "" }];
  }
  const rows = Object.keys(obj).map((key) => ({
    key,
    value: normalizeKvValue(obj[key])
  }));
  return rows.length ? rows : [{ key: "", value: "" }];
}

/**
 * 将对象转为带类型的键值对行，用于请求参数/请求体。
 * 支持 API 资产格式 { key: { value, type, ... } } 及 file 类型 { type: "File", file_path, file_name }。
 */
function objectToKvRowsWithType(obj) {
  if (!obj || typeof obj !== "object") {
    return [{ key: "", value: "", type: "string" }];
  }
  // form-data 数组格式：[{ key, type, value, ... }, ...] → 直接映射为行
  if (Array.isArray(obj)) {
    if (obj.length === 0) return [{ key: "", value: "", type: "string" }];
    const rows = obj.map((item) => ({
      key: item.key || "",
      value: normalizeKvValue(item.value),
      type: item.type || (item.value && typeof item.value === "object" && item.value.type === "File" ? "file" : "string"),
      fileName: item.fileName || item.file_name || ""
    }));
    return rows.length ? rows : [{ key: "", value: "", type: "string" }];
  }
  const rows = Object.keys(obj).map((key) => {
    const raw = obj[key];
    let value = "";
    let type = "string";
    let fileName = "";
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      if (raw.type === "File" || (raw.type === "file" && (raw.file_path || raw.file_url))) {
        type = "file";
        value = raw.file_path || raw.file_url || raw.value || "";
        fileName = raw.file_name || "";
      } else if (Object.prototype.hasOwnProperty.call(raw, "value")) {
        value = normalizeKvValue(raw.value);
        type = String(raw.type || "string");
        if (!KV_TYPE_OPTIONS.some((o) => o.value === type)) type = "string";
      } else {
        value = normalizeKvValue(raw);
      }
    } else {
      value = normalizeKvValue(raw);
    }
    return { key, value, type, fileName };
  });
  return rows.length ? rows : [{ key: "", value: "", type: "string" }];
}

/**
 * 规范化键值对中的 value 显示，兼容 API 资产格式。
 */
function normalizeKvValue(value) {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "";
  if (value && typeof value === "object" && !Array.isArray(value) && Object.prototype.hasOwnProperty.call(value, "value")) {
    return normalizeKvValue(value.value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function kvRowsToObject(rows) {
  const output = {};
  (rows || []).forEach((row) => {
    const key = String(row.key || "").trim();
    if (!key) return;
    output[key] = String(row.value || "");
  });
  return output;
}

/**
 * 带类型的键值对行转为对象。
 * - file 类型存储为 { type: "File", file_path, file_name }
 * - number/boolean/array/object 存储为 { value, type } 以保留类型，避免保存后变为 string
 */
function kvRowsToObjectWithType(rows) {
  const output = {};
  (rows || []).forEach((row) => {
    const key = String(row.key || "").trim();
    if (!key) return;
    const type = String(row.type || "string");
    const val = row.value;
    if (type === "file" && val) {
      output[key] = {
        type: "File",
        file_path: val,
        file_name: row.fileName || row.file_name || val.split("/").pop() || val
      };
    } else if (type === "number") {
      const num = val === "" ? 0 : Number(val);
      output[key] = { value: isNaN(num) ? 0 : num, type: "number" };
    } else if (type === "boolean") {
      const b = String(val || "").toLowerCase();
      output[key] = { value: b === "true" || b === "1", type: "boolean" };
    } else if (type === "array" || type === "object") {
      try {
        const parsed = val ? (typeof val === "string" ? JSON.parse(val) : val) : (type === "array" ? [] : {});
        output[key] = { value: parsed, type };
      } catch {
        output[key] = { value: type === "array" ? [] : {}, type };
      }
    } else {
      output[key] = { value: String(val || ""), type: "string" };
    }
  });
  return output;
}

function setKvCursor(target, index) {
  activeKvCursor.value = { target, index };
}

function setHeaderCursor(index) {
  activeHeaderCursor.value = index;
}

function extractRulesToRows(rules) {
  if (!Array.isArray(rules) || rules.length === 0) {
    return [{ name: "", path: "" }];
  }
  return rules.map((r) => ({
    name: r.name || "",
    path: r.path || ""
  }));
}

function extractRowsToRules(rows) {
  return (rows || [])
    .filter((r) => String(r.name || "").trim())
    .map((r) => ({
      name: String(r.name || "").trim(),
      path: String(r.path || "").trim() || "$.response"
    }));
}

function addExtractRow() {
  extractRows.value.push({ name: "", path: "" });
}

function removeExtractRow(index) {
  extractRows.value.splice(index, 1);
  if (!extractRows.value.length) {
    extractRows.value.push({ name: "", path: "" });
  }
}

function validateHeaderRows() {
  const keys = [];
  for (const row of headersKvRows.value) {
    const key = String(row.key || "").trim();
    if (!key) continue;
    if (keys.includes(key.toLowerCase())) {
      throw new Error(`请求头存在重复Key: ${key}`);
    }
    keys.push(key.toLowerCase());
  }
}

function buildPayload() {
  if (!localNode.value) return null;
  try {
    validateHeaderRows();
    
    let requestParams = {};
    let requestBody = {};
    let paramType = "json";
    let bodyType = "json";
    
    // 根据 requestType 和 requestFormat 决定填哪个字段
    if (requestType.value === "params") {
      // 用户选择了"请求参数"
      paramType = requestFormat.value === "kv" ? "form-data" : "json";
      requestParams = requestFormat.value === "json"
        ? parseJsonStrict(paramsText.value, "请求参数")
        : kvRowsToObjectWithType(paramsKvRows.value);
    } else {
      // 用户选择了"请求体"
      bodyType = requestFormat.value === "kv" ? "form-data" : "json";
      requestBody = requestFormat.value === "json"
        ? parseJsonStrict(bodyText.value, "请求体")
        : kvRowsToObjectWithType(bodyKvRows.value);
    }
    
    const envId = localNode.value.environment_id;
    return {
      ...localNode.value,
      environment_id: envId === "" || envId == null ? null : Number(envId),
      custom_base_url: String(localNode.value.custom_base_url || "").trim(),
      request_headers: kvRowsToObject(headersKvRows.value),
      request_params: requestParams,
      request_body: requestBody,
      extract_rules: extractRowsToRules(extractRows.value),
      param_type: paramType,
      body_type: bodyType
    };
  } catch (error) {
    return null;
  }
}

function saveNode() {
  if (!localNode.value || props.saving) {
    return;
  }
  const payload = buildPayload();
  if (!payload) {
    ElMessage.error("节点配置格式错误");
    return;
  }
  emit("save", payload);
}

defineExpose({
  getPayload: buildPayload
});

onUnmounted(() => {
  clearTimeout(markDirtyTimer);
  if (resizeRaf) cancelAnimationFrame(resizeRaf);
});
</script>

<style scoped>
.es6-warning {
  padding: 6px 10px;
  background: #fff3e0;
  border: 1px solid #ffcc80;
  border-radius: 4px;
  font-size: var(--el-font-size-extra-small);
  line-height: 1.5;
}

.node-config-tabs {
  margin-top: 0;
}

.node-config-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.node-config-tabs :deep(.el-tabs__item) {
  padding: 0 16px;
  height: 36px;
  line-height: 36px;
  font-size: var(--el-font-size-small);
}

.node-config-tabs :deep(.el-tabs__content) {
  overflow: visible;
  width: 100%;
}

.node-config-tabs :deep(.el-tab-pane) {
  width: 100%;
}

.tab-content {
  width: 100%;
  padding-top: 4px;
  min-height: 120px;
}

.extract-editor .kv-row {
  display: grid;
  grid-template-columns: 100px 1fr auto;
  gap: 6px;
  margin-bottom: 6px;
  align-items: center;
}

.response-config-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 320px;
}

.response-preview-section {
  flex: 0 0 40%;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.section-label {
  font-size: var(--el-font-size-extra-small);
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin-bottom: 6px;
}

.response-preview-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-placeholder);
  font-size: var(--el-font-size-small);
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.response-preview-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.response-json-rows {
  flex: 1;
  margin: 0;
  padding: 8px 10px;
  font-size: var(--el-font-size-extra-small);
  font-family: ui-monospace, monospace;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
  border: 1px solid var(--el-border-color-lighter);
  max-height: 400px;
  overflow-y: auto;
  overflow-x: auto;
  min-height: 80px;
}

.response-json-row {
  padding: 2px 4px;
  cursor: pointer;
  white-space: pre;
  word-break: break-all;
  border-left: 4px solid transparent;
  transition: background-color 0.15s ease;
}

.response-json-row:hover {
  background-color: rgba(64, 158, 255, 0.06);
}

.response-json-row--selected {
  background-color: #f0f7ff;
  border-left-color: #409eff;
}

.response-preview-actions {
  margin-top: 6px;
}

.copy-path-wrapper {
  display: inline-block;
}

.response-divider {
  height: 8px;
  background: transparent;
  margin: 4px 0;
  flex-shrink: 0;
  cursor: row-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.response-divider:hover {
  background: var(--el-fill-color-light);
}
.response-divider-handle {
  width: 32px;
  height: 4px;
  background: var(--el-border-color-dark);
  border-radius: 2px;
}

.response-extract-section {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

/* JSON 编辑框全屏按钮 */
.json-editor-wrapper {
  position: relative;
}

.json-editor-wrapper .json-expand-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  z-index: 1;
  opacity: 0.5;
  padding: 2px 6px;
  line-height: 1.2;
  font-size: var(--el-font-size-extra-small);
  border-color: var(--el-border-color);
  background-color: var(--el-bg-color);
}

.json-editor-wrapper .json-expand-btn:hover {
  opacity: 1;
  background-color: var(--el-fill-color);
}

/* JSON 全屏编辑覆盖层（fixed 定位，不依赖 Teleport，避免与 el-tabs 交互问题） */
.json-fullscreen-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.json-fullscreen-card {
  width: 80%;
  max-width: 1200px;
  height: 85vh;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.json-fullscreen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  font-weight: 600;
  font-size: var(--el-font-size-base);
  flex-shrink: 0;
}

.json-fullscreen-header-actions {
  display: flex;
  gap: 8px;
}

.json-fullscreen-textarea {
  flex: 1;
  min-height: 0;
  margin: 0;
  border: none;
  border-radius: 0;
  resize: none;
  font-size: var(--el-font-size-small);
  line-height: 1.6;
  padding: 16px;
  font-family: ui-monospace, monospace;
}

.json-fullscreen-textarea:focus {
  box-shadow: none;
  outline: none;
}
</style>
