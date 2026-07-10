<template>
  <div class="apifox-env-import-panel">
    <div class="d-flex align-items-center gap-2 mb-2 flex-wrap">
      <span class="fw-semibold text-body">环境变量（Apifox）</span>
      <el-tag v-if="hasEnvironments" type="info" size="small">{{ environmentCount }} 个环境</el-tag>
      <el-tag v-if="hasEnvironments" type="success" size="small">{{ enabledVarTotal }} 个启用变量</el-tag>
    </div>

    <div v-if="loading" class="text-muted small py-2">
      <el-icon class="is-loading me-1"><Loading /></el-icon>
      正在比对平台已有环境...</div>

    <div v-else-if="!hasEnvironments" class="text-muted small border rounded px-3 py-2 bg-light">
      当前文件未包含可导入的环境定义（<code>environments</code> 为空），将仅导入接口。</div>

    <template v-else>
      <el-steps :active="step" finish-status="success" align-center class="apifox-env-steps mb-3">
        <el-step title="解析预览" description="新建 / 覆盖 / 新增" />
        <el-step title="确认导入" description="核对后执行" />
      </el-steps>

      <!-- Step 0 -->
      <div v-show="step === 0" class="apifox-env-step-body">
        <el-alert type="info" :closable="false" show-icon class="mb-3">
          <template #title>与平台「环境」模块比对结果</template>
          仅展示<strong>启用</strong>的变量；禁用项不会写入平台。</el-alert>

        <div v-if="summary.createEnvNames.length" class="mb-3">
          <div class="subsection-title">
            <el-tag type="success" effect="plain" size="small">新建环境</el-tag>
            <span class="text-muted small ms-2">导入后将自动创建</span>
          </div>
          <div class="d-flex flex-wrap gap-1 mt-2">
            <el-tag v-for="n in summary.createEnvNames" :key="'new-' + n" type="success">{{ n }}</el-tag>
          </div>
        </div>

        <div v-if="summary.reuseEnvNames.length" class="mb-2">
          <div class="subsection-title">
            <el-tag type="warning" effect="plain" size="small">已有环境</el-tag>
            <span class="text-muted small ms-2">将合并变量（同名覆盖、新名追加）</span>
          </div>
        </div>

        <el-collapse v-model="activeNames" class="apifox-env-collapse">
          <el-collapse-item
            v-for="block in perEnvDiff"
            :key="block.name"
            :name="block.name"
          >
            <template #title>
              <span class="collapse-title-text">{{ block.name }}</span>
              <el-tag v-if="block.isNew" type="success" size="small" class="ms-2">将创建</el-tag>
              <el-tag v-else type="warning" size="small" class="ms-2">已存在</el-tag>
            </template>

            <div v-if="block.overwriteRows.length" class="mb-3">
              <div class="subsection-title">
                <el-tag type="danger" effect="light" size="small">即将覆盖</el-tag>
                <span class="text-muted small ms-2">{{ block.overwriteRows.length }} 项</span>
              </div>
              <el-table :data="block.overwriteRows" size="small" border stripe class="mt-2">
                <el-table-column prop="name" label="变量名" min-width="120" />
                <el-table-column prop="oldValue" label="当前值（平台）" min-width="160" show-overflow-tooltip />
                <el-table-column prop="newValue" label="导入值（Apifox）" min-width="160" show-overflow-tooltip />
                <el-table-column prop="description" label="说明" min-width="100" show-overflow-tooltip />
              </el-table>
            </div>

            <div v-if="block.newRows.length">
              <div class="subsection-title">
                <el-tag type="primary" effect="light" size="small">即将新增</el-tag>
                <span class="text-muted small ms-2">{{ block.newRows.length }} 项</span>
              </div>
              <el-table :data="block.newRows" size="small" border stripe class="mt-2">
                <el-table-column prop="name" label="变量名" min-width="120" />
                <el-table-column prop="value" label="值" min-width="160" show-overflow-tooltip />
                <el-table-column prop="description" label="说明" min-width="100" show-overflow-tooltip />
              </el-table>
            </div>

            <div
              v-if="!block.overwriteRows.length && !block.newRows.length"
              class="text-muted small"
            >
              无启用变量需要合并（或全部跳过）。</div>
          </el-collapse-item>
        </el-collapse>

        <div class="d-flex justify-content-end gap-2 mt-3">
          <el-button type="primary" @click="goNext">下一步：确认导入</el-button>
        </div>
      </div>

      <!-- Step 1 -->
      <div v-show="step === 1" class="apifox-env-step-body">
        <el-alert type="warning" :closable="false" show-icon class="mb-3">
          <template #title>请确认后执行</template>
          将同时提交<strong>接口列表</strong>、<strong>环境变量</strong>导入；与下方「确认导入」按钮为同一次请求。</el-alert>
        <el-descriptions :column="1" border size="small" class="mb-3">
          <el-descriptions-item label="新建环境">
            {{ summary.createEnvNames.length ? summary.createEnvNames.join('、') : '无' }}
          </el-descriptions-item>
          <el-descriptions-item label="合并变量（启用）">
            覆盖合计 {{ summary.totalOverwrite }} 项，新增合计 {{ summary.totalNew }} 。</el-descriptions-item>
        </el-descriptions>
        <div class="d-flex justify-content-between gap-2 flex-wrap">
          <el-button @click="step = 0">上一步</el-button>
          <span class="text-muted small align-self-center">
            完成后请点击下方「确认导入」</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Loading } from "@element-plus/icons-vue";
import { http } from "../../api/http";

const META_DESC = "__var_descriptions__";

const props = defineProps({
  /** 与后端 preview 返回的 apifox_environment_import 一致 */
  environmentImport: {
    type: Object,
    default: () => ({ environments: [] })
  },
  /** 平台项目 ID（用于拉取已有 Environment）*/
  platformProjectId: {
    type: Number,
    default: null
  },
  /** 通知父页面更新「确认导入」按钮可用状态 */
  onGateChange: {
    type: Function,
    default: null
  }
});

const loading = ref(true);
const serverEnvironments = ref([]);
const step = ref(0);
const activeNames = ref([]);

function variablesForRuntime(vars) {
  if (!vars || typeof vars !== "object" || Array.isArray(vars)) return {};
  const out = { ...vars };
  delete out[META_DESC];
  return out;
}

function formatVal(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function isRowEnabled(row) {
  if (Object.prototype.hasOwnProperty.call(row, "enabled")) return !!row.enabled;
  if (Object.prototype.hasOwnProperty.call(row, "enable")) return !!row.enable;
  return true;
}

const environments = computed(() => {
  const raw = props.environmentImport?.environments;
  return Array.isArray(raw) ? raw : [];
});

const hasEnvironments = computed(() => environments.value.length > 0);

const environmentCount = computed(() => environments.value.length);

const enabledVarTotal = computed(() => {
  let n = 0;
  for (const env of environments.value) {
    const vars = Array.isArray(env.variables) ? env.variables : [];
    for (const row of vars) {
      if (isRowEnabled(row)) n += 1;
    }
  }
  return n;
});

const perEnvDiff = computed(() => {
  const list = [];
  const byName = new Map(serverEnvironments.value.map((e) => [e.name, e]));

  for (const block of environments.value) {
    const name = String(block.name || "").trim();
    if (!name) continue;

    const existing = byName.get(name);
    const isNew = !existing;
    const runtime = existing ? variablesForRuntime(existing.variables) : {};

    const overwriteRows = [];
    const newRows = [];
    const vars = Array.isArray(block.variables) ? block.variables : [];

    for (const row of vars) {
      if (!isRowEnabled(row)) continue;
      const key = String(row.name || "").trim();
      if (!key || key === META_DESC) continue;
      const newVal = row.value;
      const desc = String(row.description || "").trim();
      if (Object.prototype.hasOwnProperty.call(runtime, key)) {
        overwriteRows.push({
          name: key,
          oldValue: formatVal(runtime[key]),
          newValue: formatVal(newVal),
          description: desc
        });
      } else {
        newRows.push({
          name: key,
          value: formatVal(newVal),
          description: desc
        });
      }
    }

    list.push({
      name,
      isNew,
      overwriteRows,
      newRows
    });
  }

  return list;
});

const summary = computed(() => {
  const createEnvNames = [];
  const reuseEnvNames = [];
  let totalOverwrite = 0;
  let totalNew = 0;

  for (const block of perEnvDiff.value) {
    if (block.isNew) createEnvNames.push(block.name);
    else reuseEnvNames.push(block.name);
    totalOverwrite += block.overwriteRows.length;
    totalNew += block.newRows.length;
  }

  return {
    createEnvNames,
    reuseEnvNames,
    totalOverwrite,
    totalNew
  };
});

function syncConfirmGate() {
  if (!hasEnvironments.value) {
    window.__apifoxEnvImportStep2Done = true;
  } else {
    window.__apifoxEnvImportStep2Done = step.value >= 1;
  }
  if (typeof props.onGateChange === "function") props.onGateChange();
}

watch(loading, (v) => {
  window.__apifoxEnvImportLoading = !!v;
  if (typeof props.onGateChange === "function") props.onGateChange();
});

function goNext() {
  step.value = 1;
  syncConfirmGate();
}

watch(step, () => syncConfirmGate());
watch(
  () => props.environmentImport,
  () => {
    step.value = 0;
    syncConfirmGate();
  },
  { deep: true }
);

watch(hasEnvironments, () => syncConfirmGate());

async function loadServerEnvironments() {
  loading.value = true;
  serverEnvironments.value = [];
  const pid = props.platformProjectId;
  if (!pid) {
    loading.value = false;
    syncConfirmGate();
    return;
  }
  try {
    const acc = [];
    let page = 1;
    const pageSize = 100;
    while (true) {
      const url = `/api/v1/environments/?project=${encodeURIComponent(pid)}&page_size=${pageSize}&page=${page}`;
      const data = await http.get(url);
      const results = Array.isArray(data) ? data : data?.results || [];
      acc.push(...results);
      const hasNext = data?.next && results.length === pageSize;
      if (!hasNext) break;
      page += 1;
      if (page > 50) break;
    }
    serverEnvironments.value = acc;
  } catch {
    serverEnvironments.value = [];
  } finally {
    loading.value = false;
    activeNames.value = perEnvDiff.value.map((b) => b.name);
    syncConfirmGate();
  }
}

onMounted(() => {
  loadServerEnvironments();
});

watch(
  () => props.platformProjectId,
  () => loadServerEnvironments()
);
</script>

<style scoped>
.apifox-env-import-panel {
  border: 1px solid #dbeafe;
  background: #f8fbff;
  border-radius: 10px;
  padding: 12px 14px;
}

.subsection-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-weight: 600;
  color: #334155;
  font-size: 13px;
}

.collapse-title-text {
  font-weight: 600;
  color: #0f172a;
}

.apifox-env-collapse {
  --el-collapse-border-color: #e2e8f0;
}

.apifox-env-steps :deep(.el-step__title) {
  font-size: 13px;
}

.apifox-env-steps :deep(.el-step__description) {
  font-size: 12px;
}
</style>
