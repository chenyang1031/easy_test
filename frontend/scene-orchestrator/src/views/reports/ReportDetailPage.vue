<template>
  <div class="report-detail-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button size="default" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
        <h2 class="page-title" v-if="report">{{ report.name }}</h2>
        <el-skeleton v-else :rows="1" style="width:200px" />
      </div>
      <div class="page-header-right">
        <el-button size="default" :loading="exporting" @click="handleExport">
          <el-icon><Download /></el-icon> {{ exporting ? '导出中...' : '导出' }}
        </el-button>
        <el-button size="default" type="danger" plain @click="confirmDeleteReport">
          <el-icon><Delete /></el-icon> 删除
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="panel-card" style="text-align:center;padding:60px;">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="loadError" class="panel-card" style="text-align:center;padding:60px;">
      <el-result icon="error" title="加载失败" :sub-title="loadError">
        <template #extra>
          <el-button type="primary" @click="fetchDetail">重新加载</el-button>
          <el-button @click="goBack">返回列表</el-button>
        </template>
      </el-result>
    </div>

    <!-- 主内容 -->
    <template v-else-if="report">
      <!-- 报告信息卡片 -->
      <div class="panel-card info-card">
        <div class="info-card-header">
          <el-icon><InfoFilled /></el-icon>
          <span>报告概要</span>
        </div>
        <el-row :gutter="24" class="info-grid">
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">项目</span>
              <span class="info-value">
                <el-link type="primary" :underline="false" @click="goToProject(report.project)">
                  {{ report.project_name }}
                </el-link>
              </span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">报告类型</span>
              <span class="info-value">
                <el-tag :type="reportTypeTag(report.report_type)" size="small" effect="light" round>
                  {{ report.report_type_display }}
                </el-tag>
              </span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">报告格式</span>
              <span class="info-value">
                <el-tag size="small" effect="plain">{{ report.report_format_display }}</el-tag>
              </span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{ formatTime(report.created_at) }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">更新时间</span>
              <span class="info-value">{{ formatTime(report.updated_at) }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">创建者</span>
              <span class="info-value">{{ report.created_by_name || '-' }}</span>
            </div>
          </el-col>
          <el-col v-if="report.description" :xs="24" :sm="24" :md="24">
            <div class="info-item">
              <span class="info-label">描述</span>
              <span class="info-value">{{ report.description }}</span>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 执行统计卡片 -->
      <div v-if="hasSummary" class="panel-card stats-card">
        <div class="stats-card-header">
          <el-icon><DataAnalysis /></el-icon>
          <span>执行统计</span>
        </div>
        <!-- JSON 格式报告的统计 -->
        <template v-if="!isSceneSource">
          <el-row :gutter="16">
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-total">
                <div class="stat-value">{{ summary.total }}</div>
                <div class="stat-label">总用例数</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-passed">
                <div class="stat-value">{{ summary.passed }}</div>
                <div class="stat-label">成功</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-failed">
                <div class="stat-value">{{ summary.failed }}</div>
                <div class="stat-label">失败</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-error">
                <div class="stat-value">{{ summary.error }}</div>
                <div class="stat-label">错误</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-skipped">
                <div class="stat-value">{{ summary.skipped }}</div>
                <div class="stat-label">跳过</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-rate">
                <div class="stat-value">{{ summary.success_rate }}</div>
                <div class="stat-label">成功率</div>
              </div>
            </el-col>
          </el-row>
        </template>
        <!-- 场景执行报告的统计 -->
        <template v-else>
          <el-row :gutter="16">
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-total">
                <div class="stat-value">{{ summary.total_nodes }}</div>
                <div class="stat-label">总节点数</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-passed">
                <div class="stat-value">{{ passedNodes }}</div>
                <div class="stat-label">成功节点</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-failed">
                <div class="stat-value">{{ summary.failed_nodes }}</div>
                <div class="stat-label">失败节点</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-info">
                <div class="stat-value">
                  <el-tag :type="sceneStatusTag(summary.status)" size="small" effect="dark">
                    {{ summary.status }}
                  </el-tag>
                </div>
                <div class="stat-label">执行状态</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-info">
                <div class="stat-value">{{ formatDuration(summary.duration_sec) }}</div>
                <div class="stat-label">耗时</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8" :md="4">
              <div class="stat-box stat-rate">
                <div class="stat-value">{{ sceneSuccessRate }}</div>
                <div class="stat-label">成功率</div>
              </div>
            </el-col>
          </el-row>
        </template>
      </div>

      <!-- 报告内容 -->
      <div class="panel-card report-content-card">
        <div class="content-toolbar">
          <span class="content-label">报告内容</span>
          <div class="content-actions">
            <el-button size="small" @click="copyContent">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
            <el-button size="small" @click="toggleFullscreen">
              <el-icon><FullScreen /></el-icon> 全屏
            </el-button>
          </div>
        </div>
        <div class="report-content-body" ref="contentBodyRef">
          <!-- HTML 格式 -->
          <div v-if="report.report_format === 'html'" class="report-html-content" v-html="report.content"></div>
          <!-- JSON 格式 -->
          <pre v-else-if="report.report_format === 'json'" class="report-json-content"><code>{{ formattedJson }}</code></pre>
          <!-- 其他格式（文本） -->
          <pre v-else class="report-text-content">{{ report.content }}</pre>
        </div>
      </div>
    </template>

    <!-- 全屏弹窗 -->
    <el-dialog v-model="fullscreenVisible" fullscreen :title="report?.name" @close="fullscreenVisible = false">
      <div v-if="report" class="fullscreen-content">
        <div v-if="report.report_format === 'html'" v-html="report.content"></div>
        <pre v-else-if="report.report_format === 'json'"><code>{{ formattedJson }}</code></pre>
        <pre v-else>{{ report.content }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Download, Delete, CopyDocument, FullScreen, InfoFilled, DataAnalysis } from "@element-plus/icons-vue";
import { fetchReportDetail, deleteReport } from "../../api/report";
import { confirmWarning, msgSuccess, msgError } from "../../utils/uiMessage.js";

const route = useRoute();
const router = useRouter();

const report = ref(null);
const loading = ref(false);
const loadError = ref("");
const fullscreenVisible = ref(false);
const contentBodyRef = ref(null);
const exporting = ref(false);

const formattedJson = computed(() => {
  if (report.value?.report_format !== 'json') return '';
  try {
    const parsed = typeof report.value.content === 'string'
      ? JSON.parse(report.value.content)
      : report.value.content;
    return JSON.stringify(parsed, null, 2);
  } catch {
    return report.value.content;
  }
});

// ---- 执行统计相关 ----
const summary = computed(() => report.value?.summary || {});

const hasSummary = computed(() => {
  const s = summary.value;
  if (!s || Object.keys(s).length === 0) return false;
  // JSON 报告统计
  if (s.total !== undefined) return true;
  // 场景执行统计
  if (s._source === 'scene_execution_report' && s.total_nodes !== undefined) return true;
  return false;
});

const isSceneSource = computed(() => summary.value._source === 'scene_execution_report');

const passedNodes = computed(() => {
  if (!isSceneSource.value) return 0;
  const s = summary.value;
  return (s.total_nodes || 0) - (s.failed_nodes || 0);
});

const sceneSuccessRate = computed(() => {
  if (!isSceneSource.value) return '-';
  const s = summary.value;
  const total = s.total_nodes || 0;
  if (total === 0) return '-';
  const rate = ((total - (s.failed_nodes || 0)) / total * 100).toFixed(1);
  return `${rate}%`;
});

function sceneStatusTag(status) {
  if (!status) return 'info';
  const map = {
    'success': 'success',
    'passed': 'success',
    'completed': 'success',
    'failed': 'danger',
    'failure': 'danger',
    'error': 'danger',
    'running': 'warning',
    'pending': 'info',
    'skipped': 'info',
  };
  return map[status.toLowerCase()] || 'info';
}

function formatDuration(seconds) {
  if (seconds === undefined || seconds === null || seconds === '') return '-';
  const secs = Number(seconds);
  if (isNaN(secs)) return '-';
  if (secs < 1) return `${Math.round(secs * 1000)}ms`;
  if (secs < 60) return `${secs.toFixed(1)}s`;
  const m = Math.floor(secs / 60);
  const s = Math.round(secs % 60);
  return `${m}m${s}s`;
}

function formatTime(raw) {
  if (!raw) return "-";
  const d = new Date(raw);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function reportTypeTag(type) {
  const map = {
    test_run: "primary",
    test_suite_run: "success",
    scene_execution: "info",
    custom: "info",
  };
  return map[type] || "info";
}

function goBack() {
  router.push({ name: "reportList" });
}

function goToProject(projectId) {
  if (router.getRoutes().some(r => r.name === 'projectDetail')) {
    router.push({ name: 'projectDetail', params: { id: projectId } });
  }
}

async function fetchDetail() {
  loading.value = true;
  loadError.value = "";
  try {
    const res = await fetchReportDetail(route.params.id);
    report.value = res;
  } catch (e) {
    loadError.value = e?.message || "加载报告详情失败";
  } finally {
    loading.value = false;
    await nextTick();
    initCollapsible();
  }
}

function initCollapsible(container) {
  container = container || contentBodyRef.value;
  if (!container) return;
  const headers = container.querySelectorAll('.collapsible h4');
  headers.forEach((h4) => {
    if (h4._collapsibleBound) return;
    h4._collapsibleBound = true;

    const pre = h4.nextElementSibling;
    if (pre && pre.tagName === 'PRE') {
      pre.style.display = 'none';
      const icon = document.createElement('span');
      icon.className = 'collapse-icon';
      icon.textContent = ' ▶';
      h4.appendChild(icon);
      h4.style.cursor = 'pointer';
      h4.addEventListener('click', () => {
        const isHidden = pre.style.display === 'none';
        pre.style.display = isHidden ? 'block' : 'none';
        icon.textContent = isHidden ? ' ▼' : ' ▶';
      });
    }
  });
}

watch(fullscreenVisible, (val) => {
  if (val) {
    nextTick(() => {
      const fsContainer = document.querySelector('.fullscreen-content');
      if (fsContainer) initCollapsible(fsContainer);
    });
  }
});

async function copyContent() {
  let text = "";
  if (report.value.report_format === 'json') {
    text = formattedJson.value;
  } else if (report.value.report_format === 'html') {
    const el = contentBodyRef.value?.querySelector('.report-html-content');
    const body = el?.querySelector('.test-report') ||
                 el?.querySelector('.test-report-container') ||
                 el;
    text = body?.textContent?.trim() || report.value.content;
  } else {
    text = report.value.content || "";
  }
  try {
    await navigator.clipboard.writeText(text);
    msgSuccess("内容已复制到剪贴板");
  } catch {
    msgError("复制失败，请手动选择复制");
  }
}

function toggleFullscreen() {
  fullscreenVisible.value = !fullscreenVisible.value;
}

async function handleExport() {
  if (!report.value || report.value.report_format !== 'html') {
    msgError('仅 HTML 格式的报告支持下载');
    return;
  }
  exporting.value = true;
  try {
    const resp = await fetch(`/api/v1/reports/${report.value.id}/download/`);
    if (!resp.ok) {
      let detail = `下载失败 (${resp.status})`;
      try { const data = await resp.json(); detail = data.detail || detail; } catch {}
      throw new Error(detail);
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.value.name.replace(/[\\/:*?"<>|]/g, '_')}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    msgSuccess('导出成功');
  } catch (e) {
    msgError(e?.message || '导出失败');
  } finally {
    exporting.value = false;
  }
}

async function confirmDeleteReport() {
  try {
    await confirmWarning(`确定删除测试报告「${report.value.name}」吗？此操作不可撤销。`);
  } catch {
    return;
  }
  try {
    await deleteReport(report.value.id);
    msgSuccess("已删除");
    goBack();
  } catch (e) {
    msgError(e?.message || "删除失败");
  }
}

onMounted(fetchDetail);
</script>

<style scoped>
.report-detail-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* ---- 页面标题 ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.page-header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* ---- 通用卡片 ---- */
.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
}

/* ---- 报告概要信息卡片 ---- */
.info-card {
  padding: 20px 24px;
}
.info-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}
.info-grid {
  row-gap: 14px;
}
.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.info-label {
  font-size: 13px;
  font-weight: 500;
  color: #909399;
}
.info-value {
  font-size: 14px;
  color: #303133;
  word-break: break-word;
}

/* ---- 执行统计卡片 ---- */
.stats-card {
  padding: 20px 24px;
}
.stats-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}
.stat-box {
  text-align: center;
  padding: 16px 8px;
  border-radius: 8px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  transition: transform 0.15s, box-shadow 0.15s;
}
.stat-box:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 4px;
}
.stat-label {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
.stat-total .stat-value { color: #409eff; }
.stat-passed .stat-value { color: #67c23a; }
.stat-failed .stat-value { color: #f56c6c; }
.stat-error .stat-value { color: #e6a23c; }
.stat-skipped .stat-value { color: #909399; }
.stat-rate .stat-value { color: #7232dd; }
.stat-info .stat-value { color: #303133; }

/* ---- 报告内容卡片 ---- */
.report-content-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.content-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.content-label {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.content-actions {
  display: flex;
  gap: 8px;
}

.report-content-body {
  flex: 1;
  overflow: auto;
  min-height: 200px;
}

/* HTML 报告内容 */
.report-html-content {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
}

.report-html-content :deep(h1),
.report-html-content :deep(h2),
.report-html-content :deep(h3) {
  margin-top: 20px;
  margin-bottom: 10px;
  font-weight: 600;
}

.report-html-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}

.report-html-content :deep(th),
.report-html-content :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 8px 12px;
  text-align: left;
}

.report-html-content :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}

.report-html-content :deep(details) {
  margin: 8px 0;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
}

.report-html-content :deep(details summary) {
  cursor: pointer;
  font-weight: 500;
  color: #409eff;
}

.report-html-content :deep(.collapsible) {
  margin-top: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}

.report-html-content :deep(.collapsible h4) {
  margin: 0;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.report-html-content :deep(.collapsible h4 .collapse-icon) {
  font-size: 10px;
  color: #909399;
  transition: transform 0.15s;
}

.report-html-content :deep(.collapsible pre) {
  margin: 0;
  padding: 12px 16px;
  background: #fafafa;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow-y: auto;
  border: none;
}

/* 全屏弹窗 */
.fullscreen-content :deep(.collapsible) {
  margin-top: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}

.fullscreen-content :deep(.collapsible h4) {
  margin: 0;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.fullscreen-content :deep(.collapsible pre) {
  margin: 0;
  padding: 12px 16px;
  background: #fafafa;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.report-json-content {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 16px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
}

.report-text-content {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
}

.fullscreen-content {
  height: 100%;
  overflow: auto;
  font-size: 14px;
  line-height: 1.6;
}
</style>
