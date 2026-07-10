<template>
  <el-dialog
    v-model="visible"
    title="回放导入"
    width="720px"
    :close-on-click-modal="false"
    :append-to-body="true"
    modal-class="replay-import-dialog-modal"
    destroy-on-close
    @close="handleClose"
  >
    <div v-if="!previewData" class="replay-import-step1">
      <div class="mb-3">
        <label class="form-label">上传文件</label>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          :on-change="onFileChange"
          :on-exceed="onExceed"
          accept=".gor,.gor.gz,.har"
          drag
        >
          <div class="upload-area">
            <el-icon class="upload-icon"><Upload /></el-icon>
            <div class="upload-text">
              支持上传 GoReplay（.gor/.gor.gz）或 Fiddler 导出的 HAR（.har）文件，拖到此处或点击上传
            </div>
          </div>
        </el-upload>
      </div>
      <div class="mb-3">
        <label class="form-label">目标项目</label>
        <el-select v-model="projectId" placeholder="选择项目" size="default" class="w-100" disabled>
          <el-option v-for="p in projects" :key="p.id" :label="p.name || `项目 #${p.id}`" :value="String(p.id)" />
        </el-select>
      </div>
      <div class="mb-3">
        <label class="form-label">目标分组（未匹配接口将归属到此分组）</label>
        <el-select
          v-model="groupId"
          placeholder="可选，不选则归入根分组"
          clearable
          size="default"
          class="w-100"
          :teleported="true"
          popper-class="replay-import-select-popper"
        >
          <el-option label="不指定分组" :value="null" />
          <el-option v-for="g in flatGroups" :key="g.id" :label="g.label" :value="g.id" />
        </el-select>
      </div>
      <div class="mb-3">
        <label class="form-label">场景名称</label>
        <el-input v-model="sceneName" placeholder="导入后自动生成" size="default" />
      </div>
      <div class="mb-3">
        <label class="form-label">场景描述</label>
        <el-input v-model="sceneDescription" type="textarea" :rows="2" placeholder="可选" size="default" />
      </div>
    </div>

    <div v-else class="replay-import-preview">
      <div class="preview-summary mb-3">
        <span>共 {{ previewData.total_requests }} 条请求，</span>
        <span class="text-success">已匹配 {{ previewData.matched_count }} 条，</span>
        <span class="text-warning">待新增 {{ previewData.unmatched_count }} 条</span>
      </div>
      <div class="table-responsive" style="max-height: 320px; overflow-y: auto">
        <table class="table table-sm table-hover">
          <thead>
            <tr>
              <th style="width: 40px">
                <input type="checkbox" :checked="isAllChecked" :indeterminate="isIndeterminate" @change="toggleAll" />
              </th>
              <th>序号</th>
              <th>Method</th>
              <th>URL</th>
              <th>匹配状态</th>
              <th>关联接口</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="req in previewData.requests" :key="req.index">
              <td>
                <input type="checkbox" :checked="selectedIndices.includes(req.index)" @change="toggleItem(req.index)" />
              </td>
              <td>{{ req.index }}</td>
              <td><span class="badge bg-secondary">{{ req.method }}</span></td>
              <td class="url-cell" :title="req.url_full">{{ req.url }}</td>
              <td>
                <el-tag v-if="req.match_status === 'matched'" type="success" size="small">已匹配</el-tag>
                <el-tag v-else type="warning" size="small">待新增</el-tag>
              </td>
              <td class="asset-cell">
                {{ req.match_status === "matched" ? req.api_asset_name : "将新建" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <template #footer>
      <div class="d-flex justify-content-between w-100">
        <div>
          <el-button v-if="previewData" type="default" @click="backToStep1">返回</el-button>
        </div>
        <div class="d-flex gap-2">
          <el-button @click="visible = false">取消</el-button>
          <el-button v-if="!previewData" type="primary" :disabled="!canPreview" :loading="previewLoading" @click="doPreview">
            解析预览
          </el-button>
          <el-button v-else type="primary" :disabled="!canConfirm" :loading="confirmLoading" @click="doConfirm">
            确认导入
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { Upload } from "@element-plus/icons-vue";
import { fetchApiGroups } from "../api/apiAsset";
import { fetchProjects, resolveApiProjectId, replayImportPreview, replayImportConfirm } from "../api/scene";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  /** 默认选中的平台项目 ID（用于展示项目名称） */
  defaultPlatformProjectId: { type: [String, Number], default: "" }
});

const emit = defineEmits(["update:modelValue", "success"]);

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v)
});

const uploadRef = ref(null);
const projects = ref([]);
const projectId = ref("");
const groupId = ref(null);
const sceneName = ref("");
const sceneDescription = ref("");
const selectedFile = ref(null);
const previewData = ref(null);
const previewLoading = ref(false);
const confirmLoading = ref(false);
const apiGroups = ref([]);

const flatGroups = computed(() => {
  // API 返回的是扁平列表，先构建树，再扁平化为带层级前缀的选项
  const flat = apiGroups.value || [];
  // 建树
  const byId = {};
  flat.forEach(g => { if (g?.id != null) byId[g.id] = { ...g, children: [] }; });
  const roots = [];
  flat.forEach(g => {
    if (!g || g.id == null) return;
    const node = byId[g.id];
    if (g.parent == null || g.parent === '' || !byId[g.parent]) {
      roots.push(node);
    } else {
      const p = byId[g.parent];
      if (p) p.children.push(node);
      else roots.push(node);
    }
  });
  // 排序
  const sortRec = (nodes) => {
    nodes.sort((a, b) => (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0) || (Number(a.id) - Number(b.id)));
    nodes.forEach(n => n.children?.length && sortRec(n.children));
  };
  sortRec(roots);
  // 扁平化带前缀
  const result = [];
  const walk = (items, prefix = "") => {
    for (const g of items || []) {
      const label = prefix ? `${prefix} / ${g.name}` : g.name;
      result.push({ id: g.id, label });
      if (g.children?.length) walk(g.children, label);
    }
  };
  walk(roots);
  return result;
});

const selectedIndices = computed(() => {
  if (!previewData.value?.requests) return [];
  return previewData.value.requests.filter((r) => r._checked !== false).map((r) => r.index);
});

const isAllChecked = computed(() => {
  const reqs = previewData.value?.requests || [];
  if (!reqs.length) return false;
  return reqs.every((r) => r._checked !== false);
});

const isIndeterminate = computed(() => {
  const reqs = previewData.value?.requests || [];
  const checked = reqs.filter((r) => r._checked !== false).length;
  return checked > 0 && checked < reqs.length;
});

const canPreview = computed(() => {
  return selectedFile.value && projectId.value;
});

const canConfirm = computed(() => {
  return selectedIndices.value.length > 0;
});

watch(
  () => props.modelValue,
  async (v) => {
    if (v) {
      try {
        const data = await fetchProjects();
        projects.value = data.results || data || [];
      } catch {
        projects.value = [];
      }
      projectId.value = props.defaultPlatformProjectId ? String(props.defaultPlatformProjectId) : "";
      if (projects.value.length && !projectId.value) {
        projectId.value = String(projects.value[0].id);
      }
      groupId.value = null;
      sceneName.value = "";
      sceneDescription.value = "";
      selectedFile.value = null;
      previewData.value = null;
      if (uploadRef.value) uploadRef.value.clearFiles();
      loadGroups();
    }
  }
);

async function loadGroups() {
  if (!projectId.value) return;
  try {
    const { api_project_id } = await resolveApiProjectId(Number(projectId.value));
    const data = await fetchApiGroups(api_project_id);
    apiGroups.value = data.results || data || [];
  } catch {
    apiGroups.value = [];
  }
}

watch(projectId, () => loadGroups());

function onFileChange(file) {
  selectedFile.value = file?.raw || null;
}

function onExceed() {
  ElMessage.warning("仅支持上传一个文件");
}

function toggleAll() {
  if (!previewData.value?.requests) return;
  const next = !isAllChecked.value;
  previewData.value.requests.forEach((r) => (r._checked = next));
}

function toggleItem(index) {
  const req = previewData.value?.requests.find((r) => r.index === index);
  if (req) req._checked = !(req._checked !== false);
}

async function doPreview() {
  if (!selectedFile.value || !projectId.value) return;
  previewLoading.value = true;
  try {
    const { api_project_id } = await resolveApiProjectId(Number(projectId.value));
    const data = await replayImportPreview(selectedFile.value, api_project_id, groupId.value ? Number(groupId.value) : null);
    data.requests = (data.requests || []).map((r) => ({ ...r, _checked: true }));
    previewData.value = data;
  } catch (e) {
    ElMessage.error(e?.message || "解析失败");
  } finally {
    previewLoading.value = false;
  }
}

function backToStep1() {
  previewData.value = null;
}

async function doConfirm() {
  if (!previewData.value || selectedIndices.value.length === 0) return;
  confirmLoading.value = true;
  try {
    const { api_project_id } = await resolveApiProjectId(Number(projectId.value));
    const payload = {
      project_id: api_project_id,
      group_id: groupId.value ? Number(groupId.value) : null,
      scene_name: sceneName.value || undefined,
      scene_description: sceneDescription.value || undefined,
      selected_indices: selectedIndices.value,
      requests: previewData.value.requests
    };
    const data = await replayImportConfirm(payload);
    ElMessage.success(`导入成功，已创建场景「${data.scene_name}」`);
    visible.value = false;
    emit("success", data);
  } catch (e) {
    ElMessage.error(e?.message || "导入失败");
  } finally {
    confirmLoading.value = false;
  }
}

function handleClose() {
  previewData.value = null;
  selectedFile.value = null;
}
</script>

<style scoped>
.replay-import-step1 .form-label {
  font-weight: 500;
  margin-bottom: 6px;
  display: block;
}

.upload-area {
  padding: 24px;
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  color: var(--el-color-primary);
  margin-bottom: 8px;
}

.upload-text {
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.preview-summary {
  font-size: 14px;
}

.url-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-cell {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.w-100 {
  width: 100%;
}
</style>

<!-- 弹窗 teleport 到 body，需非 scoped 样式固定 z-index，避免与菜单层切换 -->
<style>
.replay-import-dialog-modal {
  z-index: 9999 !important;
  isolation: isolate;
}

/* 目标分组下拉选项需高于弹窗，否则会出现在弹窗后面 */
.replay-import-select-popper {
  z-index: 10000 !important;
}
</style>
