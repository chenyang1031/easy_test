<template>
  <el-dialog
    v-model="visible"
    :title="activeTab === 'export' ? '导出测试用例' : '导入测试用例'"
    width="760px"
    :close-on-click-modal="false"
    :append-to-body="true"
    modal-class="tc-import-export-dialog-modal"
    destroy-on-close
    @close="handleClose"
  >
    <!-- Tab -->
    <div class="tab-bar mb-3">
      <button class="btn btn-sm" :class="activeTab === 'export' ? 'btn-primary' : 'btn-outline-secondary'" @click="activeTab = 'export'">导出</button>
      <button class="btn btn-sm" :class="activeTab === 'import' ? 'btn-primary' : 'btn-outline-secondary'" @click="activeTab = 'import'">导入</button>
    </div>

    <!-- ==================== 导出 Tab ==================== -->
    <div v-if="activeTab === 'export'" class="export-section">
      <div class="mb-3">
        <label class="form-label">导出格式</label>
        <div class="d-flex gap-3">
          <label class="form-check-label-radio"><input type="radio" v-model="exportFormat" value="json" /> JSON</label>
          <label class="form-check-label-radio"><input type="radio" v-model="exportFormat" value="yaml" /> YAML</label>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label">导出范围</label>
        <div class="text-muted small">
          <template v-if="selectedCaseIds.length">已选中 <strong>{{ selectedCaseIds.length }}</strong> 个用例</template>
          <template v-else>将导出当前项目下所有用例</template>
        </div>
      </div>
      <div v-if="exportError" class="alert alert-danger py-2 small">{{ exportError }}</div>
    </div>

    <!-- ==================== 导入 Tab ==================== -->
    <div v-if="activeTab === 'import'">
      <!-- Step 1 -->
      <div v-if="!importPreviewData" class="import-step1">
        <div class="mb-3">
          <label class="form-label">上传导出文件</label>
          <el-upload ref="uploadRef" :auto-upload="false" :limit="1" :on-change="onFileChange" :on-exceed="onExceed" accept=".json,.yaml,.yml" drag>
            <div class="upload-area">
              <el-icon class="upload-icon"><Upload /></el-icon>
              <div class="upload-text">支持 JSON / YAML 格式的测试用例导出文件，拖到此处或点击上传</div>
            </div>
          </el-upload>
        </div>
        <div v-if="importError" class="alert alert-danger py-2 small">{{ importError }}</div>
      </div>

      <!-- Step 2 -->
      <div v-else class="import-step2">
        <div class="preview-summary mb-3">
          <div class="mb-2"><span>来源项目：<strong>{{ importPreviewData.source_project }}</strong></span></div>
          <div class="d-flex gap-3 flex-wrap">
            <span>用例分组 <strong>{{ importPreviewData.summary.test_case_groups }}</strong> 个</span>
            <span>测试用例 <strong>{{ importPreviewData.summary.test_cases }}</strong> 个</span>
          </div>
        </div>

        <!-- 冲突列表 -->
        <div v-if="hasConflicts" class="conflicts-section mb-3">
          <div class="fw-bold mb-2">
            <el-icon class="text-warning"><WarningFilled /></el-icon>
            发现 {{ totalConflicts }} 项冲突
          </div>
          <div class="table-responsive" style="max-height: 200px; overflow-y: auto">
            <table class="table table-sm table-hover">
              <thead><tr><th>类型</th><th>名称</th><th>原因</th></tr></thead>
              <tbody>
                <tr v-for="(c, i) in allConflicts" :key="i">
                  <td><el-tag size="small" :type="c.tagType">{{ c.typeName }}</el-tag></td>
                  <td>{{ c.name }}</td>
                  <td class="text-muted">{{ c.reason }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="mb-3">
          <label class="form-label">冲突处理策略</label>
          <el-select v-model="conflictStrategy" size="default" class="w-100">
            <el-option label="跳过已存在的数据" value="skip" />
            <el-option label="覆盖已存在的数据" value="overwrite" />
            <el-option label="保留两者（重命名导入）" value="keep_both" />
          </el-select>
        </div>

        <div v-if="importResult" class="alert alert-success py-2 small mb-0">
          导入完成！
          分组：创建 {{ importResult.test_case_groups.created }}，跳过 {{ importResult.test_case_groups.skipped }}；
          用例：创建 {{ importResult.test_cases.created }}，更新 {{ importResult.test_cases.updated }}，跳过 {{ importResult.test_cases.skipped }}
        </div>
      </div>
    </div>

    <!-- ==================== Footer ==================== -->
    <template #footer>
      <div class="d-flex justify-content-between w-100">
        <div>
          <el-button v-if="activeTab === 'import' && importPreviewData && !importResult" type="default" @click="backToStep1">返回</el-button>
        </div>
        <div class="d-flex gap-2">
          <el-button @click="visible = false">{{ importResult ? '关闭' : '取消' }}</el-button>
          <el-button v-if="activeTab === 'export'" type="primary" :loading="exportLoading" :disabled="!projectId" @click="doExport">导出</el-button>
          <el-button v-if="activeTab === 'import' && !importPreviewData" type="primary" :loading="previewLoading" :disabled="!selectedFile" @click="doPreview">解析预览</el-button>
          <el-button v-if="activeTab === 'import' && importPreviewData && !importResult" type="primary" :loading="confirmLoading" @click="doConfirm">确认导入</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { Upload, WarningFilled } from "@element-plus/icons-vue";
import { testCaseImportExportApi } from "../../api/index.js";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projectId: { type: [String, Number], default: "" },
  selectedCaseIds: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue", "success"]);

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const activeTab = ref("export");
const exportFormat = ref("json");
const exportLoading = ref(false);
const exportError = ref("");

const uploadRef = ref(null);
const selectedFile = ref(null);
const previewLoading = ref(false);
const confirmLoading = ref(false);
const importPreviewData = ref(null);
const importError = ref("");
const importResult = ref(null);
const conflictStrategy = ref("skip");

const hasConflicts = computed(() => totalConflicts.value > 0);
const totalConflicts = computed(() => {
  if (!importPreviewData.value?.conflicts) return 0;
  const c = importPreviewData.value.conflicts;
  return (c.test_case_groups?.length || 0) + (c.test_cases?.length || 0);
});

const allConflicts = computed(() => {
  if (!importPreviewData.value?.conflicts) return [];
  const c = importPreviewData.value.conflicts;
  const list = [];
  (c.test_case_groups || []).forEach((g) => list.push({ typeName: "分组", tagType: "warning", name: g.name, reason: g.reason }));
  (c.test_cases || []).forEach((tc) => list.push({ typeName: "用例", tagType: "info", name: tc.name, reason: tc.reason }));
  return list;
});

watch(() => props.modelValue, (v) => {
  if (v) {
    activeTab.value = "export";
    exportFormat.value = "json";
    exportError.value = "";
    exportLoading.value = false;
    selectedFile.value = null;
    previewLoading.value = false;
    confirmLoading.value = false;
    importPreviewData.value = null;
    importError.value = "";
    importResult.value = null;
    conflictStrategy.value = "skip";
    if (uploadRef.value) uploadRef.value.clearFiles();
  }
});

async function doExport() {
  if (!props.projectId) return;
  exportLoading.value = true;
  exportError.value = "";
  try {
    const caseIds = props.selectedCaseIds.length ? props.selectedCaseIds : null;
    const res = await testCaseImportExportApi.export(props.projectId, caseIds, exportFormat.value);
    const content = exportFormat.value === "json" ? JSON.stringify(res.content, null, 2) : res.content;
    const blob = new Blob([content], { type: exportFormat.value === "json" ? "application/json" : "application/x-yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = res.filename || `test_cases.${exportFormat.value}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    ElMessage.success("导出成功");
    visible.value = false;
  } catch (e) {
    exportError.value = e?.message || "导出失败";
  } finally {
    exportLoading.value = false;
  }
}

function onFileChange(file) {
  selectedFile.value = file?.raw || null;
  importError.value = "";
}

function onExceed() {
  ElMessage.warning("仅支持上传一个文件");
}

async function doPreview() {
  if (!selectedFile.value || !props.projectId) return;
  previewLoading.value = true;
  importError.value = "";
  try {
    const data = await testCaseImportExportApi.previewImport(selectedFile.value, props.projectId);
    importPreviewData.value = data;
  } catch (e) {
    importError.value = e?.message || "解析失败";
  } finally {
    previewLoading.value = false;
  }
}

function backToStep1() {
  importPreviewData.value = null;
  importResult.value = null;
  selectedFile.value = null;
  if (uploadRef.value) uploadRef.value.clearFiles();
}

async function doConfirm() {
  if (!importPreviewData.value || !props.projectId) return;
  confirmLoading.value = true;
  try {
    const res = await testCaseImportExportApi.confirmImport({
      project_id: props.projectId,
      data: importPreviewData.value.data,
      default_conflict_strategy: conflictStrategy.value,
    });
    importResult.value = res;
    ElMessage.success("导入完成");
    emit("success", res);
  } catch (e) {
    ElMessage.error(e?.message || "导入失败");
  } finally {
    confirmLoading.value = false;
  }
}

function handleClose() {
  importPreviewData.value = null;
  importResult.value = null;
  selectedFile.value = null;
}
</script>

<style scoped>
.tab-bar { display: flex; gap: 8px; }
.export-section .form-label, .import-step1 .form-label, .import-step2 .form-label { font-weight: 500; margin-bottom: 6px; display: block; }
.form-check-label-radio { display: inline-flex; align-items: center; gap: 4px; cursor: pointer; }
.upload-area { padding: 24px; text-align: center; }
.upload-icon { font-size: 48px; color: var(--el-color-primary); margin-bottom: 8px; }
.upload-text { color: var(--el-text-color-regular); font-size: 14px; }
.preview-summary { font-size: 14px; }
.conflicts-section .fw-bold { display: flex; align-items: center; gap: 4px; }
.w-100 { width: 100%; }
.small { font-size: 13px; }
</style>

<style>
.tc-import-export-dialog-modal { z-index: 9999 !important; isolation: isolate; }
</style>
