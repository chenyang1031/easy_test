<template>
  <div class="log-query-page">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">日志查询</h2>
        <span class="page-subtitle">实时查看服务器日志与执行命令</span>
      </div>
    </div>

    <el-tabs v-model="activeTab" type="border-card" class="log-tabs">
      <!-- ========== 日志查看器 ========== -->
      <el-tab-pane label="日志查看" name="log">
        <div class="log-toolbar">
          <div class="toolbar-left">
            <el-select v-model="selectedFile" size="default" style="width: 180px" @change="onFileChange">
              <el-option v-for="f in logFiles" :key="f.name" :label="f.name" :value="f.name">
                <span>{{ f.name }}</span>
                <span style="color: #909399; font-size: 12px; margin-left: 6px">({{ formatSize(f.size) }})</span>
              </el-option>
            </el-select>
            <el-button type="primary" @click="loadHistory" :loading="loadingHistory">
              <el-icon><Refresh /></el-icon> 加载历史
            </el-button>
            <el-button :type="streaming ? 'danger' : 'success'" @click="toggleStream">
              <el-icon><VideoPlay v-if="!streaming" /><VideoPause v-else /></el-icon>
              {{ streaming ? '停止日志' : '实时日志' }}
            </el-button>
            <el-button @click="clearLog">
              <el-icon><Delete /></el-icon> 清空
            </el-button>
          </div>
          <div class="toolbar-right">
            <el-checkbox v-model="autoScroll" label="自动滚动" />
            <span class="log-status" :class="{ 'is-streaming': streaming }">
              {{ streaming ? '● 接收中' : '○ 未连接' }}
            </span>
          </div>
        </div>
        <div class="log-container" ref="logContainer">
          <pre class="log-content"><span v-for="(line, i) in logLines" :key="i" :class="lineClass(line)">{{ line }}
</span></pre>
          <div v-if="logLines.length === 0 && !loadingHistory" class="log-empty">
            暂无日志，请选择文件后点击"加载历史"或"实时日志"
          </div>
        </div>
        <div class="log-footer">共 {{ logLines.length }} 行<span v-if="selectedFile"> | {{ selectedFile }}</span></div>
      </el-tab-pane>

      <!-- ========== 命令终端 ========== -->
      <el-tab-pane label="命令终端" name="terminal">
        <div class="terminal-toolbar">
          <el-tag type="warning" size="large">
            <el-icon><WarningFilled /></el-icon> 仅管理员可用 — 命令在服务端执行
          </el-tag>
          <el-button @click="clearTerminal" size="small">清空输出</el-button>
        </div>
        <div class="terminal-container" ref="terminalContainer">
          <div v-for="(entry, i) in terminalHistory" :key="i" class="terminal-entry">
            <div class="terminal-input-line">
              <span class="prompt">$</span>
              <span class="cmd">{{ entry.command }}</span>
            </div>
            <pre v-if="entry.stdout" class="terminal-output">{{ entry.stdout }}</pre>
            <pre v-if="entry.stderr" class="terminal-error">{{ entry.stderr }}</pre>
            <div class="terminal-exit" :class="entry.returncode === 0 ? 'success' : 'fail'">
              [exit: {{ entry.returncode }}]
            </div>
          </div>
          <div v-if="commandRunning" class="terminal-running">
            <span class="prompt">$</span> {{ currentCommand }}
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
        </div>
        <div class="terminal-input-area">
          <el-input
            v-model="commandInput"
            placeholder="输入命令后按 Enter 执行..."
            @keyup.enter="runCommand"
            :disabled="commandRunning"
            size="large"
            class="terminal-input"
          >
            <template #prepend>$</template>
            <template #append>
              <el-button type="primary" @click="runCommand" :loading="commandRunning" :disabled="!commandInput.trim()">
                执行
              </el-button>
            </template>
          </el-input>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import { logApi } from "../../api/log";
import { ElMessage } from "element-plus";
import { Refresh, Delete, VideoPlay, VideoPause, Loading, WarningFilled } from "@element-plus/icons-vue";

const activeTab = ref("log");

// ========== 日志查看 ==========
const logFiles = ref([]);
const selectedFile = ref("django.log");
const logLines = ref([]);
const streaming = ref(false);
const autoScroll = ref(true);
const loadingHistory = ref(false);
const logContainer = ref(null);
let eventSource = null;

async function fetchLogFiles() {
  try {
    const data = await logApi.listFiles();
    logFiles.value = Array.isArray(data) ? data : [];
    if (logFiles.value.length && !logFiles.value.find(f => f.name === selectedFile.value)) {
      selectedFile.value = logFiles.value[0].name;
    }
  } catch {
    ElMessage.error("获取日志文件列表失败");
  }
}

async function loadHistory() {
  if (!selectedFile.value) return;
  loadingHistory.value = true;
  try {
    const data = await logApi.read(selectedFile.value, 500);
    const content = data.content || "";
    logLines.value = content.split("\n").filter(l => l.length > 0);
    await nextTick();
    scrollBottom();
  } catch {
    ElMessage.error("读取日志失败");
  } finally {
    loadingHistory.value = false;
  }
}

function toggleStream() {
  streaming.value ? stopStream() : startStream();
}

function startStream() {
  if (!selectedFile.value) return;
  stopStream();
  eventSource = new EventSource(logApi.streamUrl(selectedFile.value));
  streaming.value = true;

  eventSource.onmessage = (e) => {
    logLines.value.push(e.data);
    if (logLines.value.length > 10000) {
      logLines.value = logLines.value.slice(-8000);
    }
    if (autoScroll.value) nextTick(scrollBottom);
  };

  eventSource.onerror = () => {
    stopStream();
    ElMessage.warning("日志流连接断开");
  };
}

function stopStream() {
  if (eventSource) { eventSource.close(); eventSource = null; }
  streaming.value = false;
}

function clearLog() { logLines.value = []; }
function onFileChange() { stopStream(); logLines.value = []; }
function scrollBottom() {
  if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight;
}

function lineClass(line) {
  if (/ERROR/i.test(line)) return "log-error";
  if (/WARNING/i.test(line)) return "log-warning";
  if (/DEBUG/i.test(line)) return "log-debug";
  return "";
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// ========== 命令终端 ==========
const commandInput = ref("");
const terminalHistory = ref([]);
const commandRunning = ref(false);
const currentCommand = ref("");
const terminalContainer = ref(null);

async function runCommand() {
  const cmd = commandInput.value.trim();
  if (!cmd || commandRunning.value) return;
  commandRunning.value = true;
  currentCommand.value = cmd;
  commandInput.value = "";

  try {
    const data = await logApi.execute(cmd);
    terminalHistory.value.push({
      command: cmd,
      stdout: data.stdout,
      stderr: data.stderr,
      returncode: data.returncode,
    });
  } catch (err) {
    terminalHistory.value.push({
      command: cmd, stdout: "", stderr: err.message || "执行失败", returncode: -1,
    });
  } finally {
    commandRunning.value = false;
    currentCommand.value = "";
    await nextTick();
    scrollTerminal();
  }
}

function clearTerminal() { terminalHistory.value = []; }
function scrollTerminal() {
  if (terminalContainer.value) terminalContainer.value.scrollTop = terminalContainer.value.scrollHeight;
}

// ========== 生命周期 ==========
onMounted(fetchLogFiles);
onUnmounted(stopStream);
</script>

<style scoped>
.log-query-page { display: flex; flex-direction: column; gap: 12px; }

.log-tabs :deep(.el-tabs__content) { padding: 0; overflow: hidden; }
.log-tabs :deep(.el-tab-pane) { display: flex; flex-direction: column; }

/* ========== 日志工具栏 ========== */
.log-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 14px; background: #fff; border-bottom: 1px solid #ebeef5;
}
.toolbar-left { display: flex; align-items: center; gap: 8px; }
.toolbar-right { display: flex; align-items: center; gap: 12px; }
.log-status { font-size: 13px; color: #909399; }
.log-status.is-streaming { color: #67c23a; font-weight: 600; }

/* ========== 日志容器 ========== */
.log-container {
  flex: 1; overflow-y: auto; min-height: 420px; max-height: 65vh;
  background: #1e1e1e; padding: 10px;
  font-family: Consolas, Monaco, 'Courier New', monospace; font-size: 13px; line-height: 1.55;
}
.log-content {
  margin: 0; white-space: pre-wrap; word-break: break-all; color: #d4d4d4;
}
.log-content .log-error { color: #f56c6c; }
.log-content .log-warning { color: #e6a23c; }
.log-content .log-debug { color: #909399; }
.log-empty { color: #909399; text-align: center; padding: 60px 0; font-size: 14px; }
.log-footer {
  padding: 6px 14px; background: #f5f7fa; border-top: 1px solid #ebeef5;
  font-size: 12px; color: #909399;
}

/* ========== 命令终端 ========== */
.terminal-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 14px; background: #fff; border-bottom: 1px solid #ebeef5;
}
.terminal-container {
  flex: 1; overflow-y: auto; min-height: 400px; max-height: 60vh;
  background: #1e1e1e; padding: 10px;
  font-family: Consolas, Monaco, 'Courier New', monospace; font-size: 13px; line-height: 1.55;
}
.terminal-entry { margin-bottom: 10px; }
.terminal-input-line { display: flex; gap: 8px; }
.prompt { color: #67c23a; user-select: none; }
.cmd { color: #d4d4d4; font-weight: 600; }
.terminal-output { margin: 4px 0 0 16px; color: #b0b0b0; white-space: pre-wrap; word-break: break-all; }
.terminal-error { margin: 4px 0 0 16px; color: #f56c6c; white-space: pre-wrap; word-break: break-all; }
.terminal-exit { margin-left: 16px; font-size: 11px; }
.terminal-exit.success { color: #67c23a; }
.terminal-exit.fail { color: #f56c6c; }
.terminal-running { color: #d4d4d4; }
.terminal-input-area {
  padding: 10px 14px; background: #2d2d2d; border-top: 1px solid #404040;
}
.terminal-input :deep(.el-input-group__prepend) {
  background: #3c3c3c; color: #67c23a; border-color: #555;
  font-family: Consolas, monospace; font-weight: 700;
}
.terminal-input :deep(.el-input__wrapper) {
  background: #3c3c3c; box-shadow: none; border: 1px solid #555;
}
.terminal-input :deep(.el-input__inner) {
  color: #d4d4d4; font-family: Consolas, monospace;
}
.terminal-input :deep(.el-input-group__append) {
  background: #3c3c3c; border-color: #555; padding: 0;
}
</style>
