<template>
  <div class="execution-log-panel">
    <div v-if="environment" class="log-env-bar">
      <strong>运行环境：</strong>{{ environment.name }} ({{ environment.base_url }})
    </div>
    <div v-if="!logs.length" class="text-muted py-2">暂无日志</div>
    <div v-else class="log-cards">
      <div
        v-for="(log, idx) in logs"
        :key="log.node_id || log.node_key || idx"
        class="log-card"
        :class="{
          'log-card--failed': log.status === 'failed',
          'log-card--skipped': log.status === 'skipped',
          'log-card--collapsed': !isCardExpanded(idx)
        }"
      >
        <!-- 卡片头部：可点击收放 -->
        <div class="log-card-header" @click="toggleCard(idx)">
          <span class="log-card-toggle" :class="{ 'log-card-toggle--collapsed': !isCardExpanded(idx) }">
            <span class="log-card-chevron"></span>
          </span>
          <span class="log-card-title">{{ log.node_name || log.node_key || `节点 ${idx + 1}` }}</span>
          <span :class="['log-status-badge', `log-status-badge--${log.status}`]">
            {{ log.status === "passed" ? "passed" : log.status === "failed" ? "failed" : log.status }}
          </span>
        </div>

        <!-- 卡片内容：可收放 -->
        <div v-show="isCardExpanded(idx)" class="log-card-body">
        <!-- 断言失败 / 错误原因 - 顶部醒目展示 -->
        <div v-if="log.status === 'failed' && getFailedAssert(log)" class="log-alert log-alert--assert">
          <strong>断言规则：</strong>{{ formatAssertRule(getFailedAssert(log)) }} - 失败
          <div class="log-alert-detail">
            期望：{{ stringifyValue(getFailedAssert(log).expected) }} · 实际：{{ stringifyValue(getFailedAssert(log).actual) }}
          </div>
        </div>
        <div v-else-if="log.status === 'failed' && log.reason" class="log-alert log-alert--error">
          <strong>错误原因：</strong>{{ log.reason }}
        </div>

        <!-- 核心信息区：请求方法、URL、状态码、响应时间 -->
        <div v-if="log.request" class="log-summary">
          <div v-if="log.request.method" class="log-summary-row">
            <span class="log-summary-label">请求方法：</span>
            <span class="log-summary-value log-summary-value--method">{{ log.request.method }}</span>
          </div>
          <div v-if="log.request.url" class="log-summary-row">
            <span class="log-summary-label">请求 URL：</span>
            <span class="log-summary-value log-summary-value--url">{{ log.request.url }}</span>
          </div>
          <div v-if="log.response != null" class="log-summary-row">
            <span class="log-summary-label">响应状态码：</span>
            <span class="log-summary-value" :class="getStatusClass(log.response.status_code)">{{ log.response.status_code ?? '-' }}</span>
          </div>
          <div v-if="log.response?.duration_ms != null" class="log-summary-row">
            <span class="log-summary-label">响应时间：</span>
            <span class="log-summary-value log-summary-value--highlight">{{ formatDuration(log.response.duration_ms) }} 毫秒</span>
          </div>
        </div>

        <!-- 跳过节点：仅显示原因 -->
        <div v-else-if="log.status === 'skipped' && log.reason" class="log-skip-reason">
          {{ log.reason }}
        </div>

        <!-- 核心信息模块：请求头、请求参数、请求体、响应头、响应体（可折叠） -->
        <div class="log-sections">
          <details v-if="hasRequestHeaders(log)" class="collapsible-section">
            <summary class="collapsible-header">请求头 (Request Headers)</summary>
            <pre class="collapsible-pre">{{ formatHeaders(log.request.headers) }}</pre>
          </details>
          <details v-if="hasRequestParams(log)" class="collapsible-section">
            <summary class="collapsible-header">请求参数 (Request Params)</summary>
            <pre class="collapsible-pre">{{ formatParamsOrBody(log.request.params) }}</pre>
          </details>
          <details v-if="hasRequestBody(log)" class="collapsible-section">
            <summary class="collapsible-header">请求体 (Request Body)</summary>
            <pre class="collapsible-pre">{{ formatParamsOrBody(log.request.body) }}</pre>
          </details>
          <details v-if="hasResponseHeaders(log)" class="collapsible-section">
            <summary class="collapsible-header">响应头 (Response Headers)</summary>
            <pre class="collapsible-pre">{{ formatHeaders(log.response.headers) }}</pre>
          </details>
          <details v-if="hasResponseBody(log)" class="collapsible-section">
            <summary class="collapsible-header">响应体 (Response Body)</summary>
            <pre class="collapsible-pre">{{ formatBody(log.response.body) }}</pre>
          </details>
        </div>

        <!-- 断言详情（全部断言） -->
        <div v-if="Array.isArray(log.assert_results) && log.assert_results.length" class="log-assert-section">
          <div class="log-assert-header">断言结果</div>
          <div
            v-for="(ar, ai) in log.assert_results"
            :key="ai"
            :class="['log-assert-item', ar.passed ? 'pass' : 'fail']"
          >
            <span class="log-assert-rule">{{ ar.path }} ({{ ar.comparator }})</span>
            <span :class="['log-assert-status', ar.passed ? 'text-success' : 'text-danger']">
              {{ ar.passed ? '通过' : '失败' }}
            </span>
            <span v-if="!ar.passed" class="log-assert-detail">
              期望: {{ stringifyValue(ar.expected) }} · 实际: {{ stringifyValue(ar.actual) }}
            </span>
          </div>
        </div>

        <!-- 前置脚本 console：msg 为原始字符串，避免「原始数据」整段 JSON 序列化时对内层引号加 \ 造成误解 -->
        <details v-if="hasScriptLogs(log)" class="collapsible-section log-script-logs-block">
          <summary class="collapsible-header">前置脚本日志 (Script logs)</summary>
          <div class="script-logs">
            <div
              v-for="(sl, si) in log.script_logs"
              :key="si"
              class="script-log-item"
            >
              <div class="script-log-meta">
                <span class="script-log-level">{{ sl.level || "log" }}</span>
              </div>
              <pre class="script-log-msg">{{ sl.msg }}</pre>
            </div>
          </div>
        </details>

        <!-- 原始 JSON 调试入口（折叠，含完整错误信息） -->
        <details class="log-raw-details">
          <summary class="log-raw-summary">原始数据</summary>
          <p class="log-raw-hint">
            提示：前置脚本里打印的字符串在下方 JSON 中会按 JSON 规则转义（如
            <code>\"</code>）。与 HMAC 输入逐字节一致的内容请以「前置脚本日志」中对应行的纯文本为准。
          </p>
          <pre class="log-raw-content">{{ JSON.stringify(log, null, 2) }}</pre>
        </details>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

defineProps({
  logs: {
    type: Array,
    default: () => []
  },
  environment: {
    type: Object,
    default: null
  }
});

const expandedCards = ref({});

function isCardExpanded(idx) {
  return expandedCards.value[idx] !== false;
}

function toggleCard(idx) {
  expandedCards.value = { ...expandedCards.value, [idx]: !isCardExpanded(idx) };
}

function getFailedAssert(log) {
  const arr = log.assert_results;
  if (!Array.isArray(arr)) return null;
  return arr.find((a) => !a.passed) || null;
}

function formatAssertRule(ar) {
  if (!ar) return "";
  return `${ar.path} (${ar.comparator})`;
}

function stringifyValue(value) {
  if (value === undefined || value === null) return "-";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function formatDuration(ms) {
  if (ms == null || ms === "") return "-";
  const n = Number(ms);
  return Number.isFinite(n) ? n.toFixed(2) : "-";
}

function getStatusClass(code) {
  if (code == null) return "";
  const c = Number(code);
  if (c >= 200 && c < 300) return "log-status-2xx";
  if (c >= 400 && c < 500) return "log-status-4xx";
  if (c >= 500) return "log-status-5xx";
  return "";
}

function hasRequestHeaders(log) {
  const h = log?.request?.headers;
  return h && typeof h === "object" && Object.keys(h).length > 0;
}

function hasRequestParams(log) {
  const p = log?.request?.params;
  return p !== undefined && p !== null && (typeof p === "object" || typeof p === "string");
}

function hasRequestBody(log) {
  const b = log?.request?.body;
  return b !== undefined && b !== null && (typeof b === "object" || typeof b === "string");
}

/** 将对象中的 File 类型转为可读展示，用于请求参数/请求体 */
function formatParamsOrBody(val) {
  if (val === undefined || val === null) return "";
  if (typeof val === "string") return val;
  const sanitized = _replaceFilePlaceholders(val);
  try {
    return JSON.stringify(sanitized, null, 2);
  } catch {
    return String(sanitized);
  }
}

/** 判断是否为 file 类型参数对象（与 NodeConfigPanel / 后端存储格式一致） */
function _isFileParam(v) {
  if (!v || typeof v !== "object") return false;
  return v.type === "File" || v.type === "file";
}

function _replaceFilePlaceholders(obj) {
  if (obj === null || obj === undefined) return obj;
  if (typeof obj !== "object") return obj;
  if (Array.isArray(obj)) {
    return obj.map((item) => _replaceFilePlaceholders(item));
  }
  const out = {};
  for (const [k, v] of Object.entries(obj)) {
    if (_isFileParam(v)) {
      const path = v.file_path || v.file_url || v.value || "";
      const name = v.file_name || (path ? path.split(/[/\\]/).pop() : "") || "file";
      out[k] = `[File] ${name} (${path || "—"})`;
    } else {
      out[k] = _replaceFilePlaceholders(v);
    }
  }
  return out;
}

function hasResponseHeaders(log) {
  const h = log?.response?.headers;
  return h && typeof h === "object" && Object.keys(h).length > 0;
}

function hasResponseBody(log) {
  const b = log?.response?.body;
  return b !== undefined && b !== null;
}

function hasScriptLogs(log) {
  return Array.isArray(log?.script_logs) && log.script_logs.length > 0;
}

function formatHeaders(obj) {
  if (!obj || typeof obj !== "object") return "{}";
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

function formatBody(val) {
  if (val === undefined || val === null) return "";
  if (typeof val === "string") return val;
  try {
    return JSON.stringify(val, null, 2);
  } catch {
    return String(val);
  }
}
</script>

<style scoped>
.execution-log-panel {
  font-size: var(--el-font-size-small);
}

.log-env-bar {
  padding: 8px 12px;
  margin-bottom: 12px;
  background-color: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.log-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.log-card {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.log-card--failed {
  border-color: #f56c6c;
  background-color: #fef0f0;
}

.log-card--skipped {
  border-color: #e4e7ed;
  background-color: #fafafa;
}

.log-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  cursor: pointer;
  user-select: none;
  text-align: left;
}

.log-card--collapsed .log-card-header {
  border-bottom: none;
}

.log-card-header:hover {
  background-color: #f0f2f5;
}

.log-card-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  margin-right: 8px;
  flex-shrink: 0;
}

.log-card-chevron {
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid #606266;
  transition: transform 0.2s;
}

.log-card-toggle--collapsed .log-card-chevron {
  border-left: 6px solid #606266;
  border-right: 0 solid transparent;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  margin-left: 2px;
}

.log-card-title {
  font-weight: 600;
  color: #303133;
  text-align: left;
}

.log-status-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: var(--el-font-size-extra-small);
  font-weight: 600;
  border-radius: 4px;
}

.log-status-badge--passed {
  background-color: rgba(103, 194, 58, 0.15);
  color: #67c23a;
}

.log-status-badge--failed {
  background-color: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.log-status-badge--skipped {
  background-color: rgba(144, 147, 153, 0.15);
  color: #909399;
}

.log-alert {
  margin: 12px 16px;
  padding: 10px 12px;
  border-radius: 6px;
}

.log-alert--assert {
  background-color: #fef0f0;
  border: 1px solid #f56c6c;
  color: #c45656;
}

.log-alert--error {
  background-color: #fdf6ec;
  border: 1px solid #e6a23c;
  color: #b88230;
}

.log-alert-detail {
  margin-top: 6px;
  font-size: var(--el-font-size-extra-small);
}

.log-summary {
  padding: 12px 16px;
  background-color: #fff;
  border-bottom: 1px solid #e9ecef;
  text-align: left;
}

.log-summary-row {
  margin-bottom: 8px;
  display: flex;
  align-items: baseline;
  text-align: left;
}

.log-summary-row:last-child {
  margin-bottom: 0;
}

.log-summary-label {
  color: #606266;
  min-width: 100px;
  flex-shrink: 0;
}

.log-summary-value {
  color: #303133;
  word-break: break-all;
}

.log-summary-value--method {
  font-weight: 600;
  color: #409eff;
}

.log-summary-value--url {
  font-weight: 600;
  color: #303133;
}

.log-summary-value--highlight {
  font-weight: 600;
  color: #67c23a;
}

.log-status-2xx {
  color: #67c23a;
  font-weight: 600;
}

.log-status-4xx {
  color: #e6a23c;
  font-weight: 600;
}

.log-status-5xx {
  color: #f56c6c;
  font-weight: 600;
}

.log-skip-reason {
  padding: 12px 16px;
  color: #909399;
}

.log-sections {
  padding: 0 16px 12px;
  text-align: left;
}

.collapsible-section {
  margin-top: 12px;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  overflow: hidden;
}

.collapsible-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: #f8f9fa;
  cursor: pointer;
  user-select: none;
  list-style: none;
  text-align: left;
}

.collapsible-header::-webkit-details-marker {
  display: none;
}

.collapsible-header::before {
  content: "▶";
  margin-right: 8px;
  font-size: var(--fs-micro);
  color: #909399;
}

.collapsible-section[open] .collapsible-header::before {
  content: "▼";
}

.collapsible-header:hover {
  background-color: #f0f2f5;
}

.collapsible-pre {
  margin: 0;
  padding: 12px;
  background-color: #f8f9fa;
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: var(--el-font-size-extra-small);
  color: #303133;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
  border-top: 1px solid #e9ecef;
  text-align: left;
}

.log-assert-section {
  margin: 12px 16px;
  padding: 12px;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  background-color: #fff;
}

.log-assert-header {
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}

.log-assert-item {
  padding: 6px 0;
  border-bottom: 1px solid #ebeef5;
  font-size: var(--el-font-size-extra-small);
}

.log-assert-item:last-child {
  border-bottom: none;
}

.log-assert-rule {
  color: #303133;
}

.log-assert-status {
  margin-left: 8px;
}

.log-assert-detail {
  display: block;
  margin-top: 4px;
  color: #909399;
}

.text-success {
  color: #67c23a;
}

.text-danger {
  color: #f56c6c;
}

.log-script-logs-block {
  margin: 12px 16px 0;
}

.script-logs {
  margin: 0;
  padding: 10px 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 6px;
  font-size: var(--el-font-size-extra-small);
  max-height: 360px;
  overflow: auto;
}

.script-log-item {
  margin-bottom: 10px;
}

.script-log-item:last-child {
  margin-bottom: 0;
}

.script-log-meta {
  margin-bottom: 4px;
}

.script-log-level {
  display: inline-block;
  padding: 0 6px;
  border-radius: 4px;
  font-size: var(--fs-tiny);
  color: #b5cea8;
  background: rgba(255, 255, 255, 0.08);
}

.script-log-msg {
  margin: 0;
  padding: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: ui-monospace, "Cascadia Code", "Consolas", monospace;
  background: transparent;
  color: #ce9178;
}

.log-raw-hint {
  margin: 0 0 8px;
  padding: 8px 10px;
  font-size: var(--el-font-size-extra-small);
  color: #606266;
  background: #f0f9ff;
  border: 1px solid #b3d8ff;
  border-radius: 6px;
  line-height: 1.5;
}

.log-raw-details {
  margin: 12px 16px;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  overflow: hidden;
}

.log-raw-summary {
  padding: 8px 12px;
  background-color: #f8f9fa;
  cursor: pointer;
  font-size: var(--el-font-size-extra-small);
  color: #606266;
  list-style: none;
}

.log-raw-summary::-webkit-details-marker {
  display: none;
}

.log-raw-content {
  margin: 0;
  padding: 12px;
  background-color: #fff;
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: var(--fs-tiny);
  color: #606266;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}
</style>
