<template>
  <div class="perf-editor-page">
    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <button type="button" class="btn btn-outline-secondary" @click="goBack">
        <i class="bi bi-arrow-left" aria-hidden="true" /> 返回列表
      </button>
      <button
        type="button"
        class="btn btn-primary px-4"
        :disabled="submitLoading"
        @click="beforeSubmit"
      >
        <span v-if="submitLoading" class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
        {{ submitLoading ? "保存中…" : "保存" }}
      </button>
    </div>

    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" class="card p-3 perf-form" status-icon>
      <!-- 基础信息 -->
      <el-collapse v-model="activeNames">
        <el-collapse-item title="基础信息" name="base">
          <el-form-item label="任务名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入任务名称" maxlength="255" show-word-limit />
          </el-form-item>
          <el-form-item label="所属项目" prop="project">
            <el-select v-model="form.project" placeholder="选择项目" style="width: 100%" @change="onProjectChange">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="测试环境" prop="environment">
            <el-select v-model="form.environment" placeholder="选择环境" style="width: 100%" :disabled="!form.project">
              <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联接口" prop="interface">
            <el-select v-model="form.interface" placeholder="选择接口" style="width: 100%" :disabled="!form.project">
              <el-option v-for="a in apiAssets" :key="a.id" :label="`${a.method} ${a.name}`" :value="a.id" />
            </el-select>
          </el-form-item>
        </el-collapse-item>

        <!-- 负载策略 -->
        <el-collapse-item title="负载策略配置" name="load">
          <el-form-item label="模式">
            <el-radio-group v-model="loadMode">
              <el-radio-button label="fixed">固定并发</el-radio-button>
              <el-radio-button label="staged">阶梯式负载</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <template v-if="loadMode === 'fixed'">
            <el-form-item label="总用户数" prop="total_users">
              <el-input-number v-model="form.total_users" :min="1" :max="10000" />
            </el-form-item>
            <el-form-item label="加压速率" prop="spawn_rate">
              <el-input-number v-model="form.spawn_rate" :min="1" :max="1000" />
              <span class="unit-hint">用户/秒</span>
            </el-form-item>
            <el-form-item label="压测时长" prop="run_time">
              <el-input-number v-model="form.run_time" :min="1" :max="7200" />
              <span class="unit-hint">秒</span>
            </el-form-item>
          </template>

          <template v-else>
            <p class="block-hint">各阶段时长之和必须等于下方「总时长（秒）」；保存时将自动写入「压测时长」字段。</p>
            <el-form-item label="阶段列表">
              <!-- vue-draggable-next 2.x 仅渲染默认插槽，勿用 #item（否则列表不显示） -->
              <VueDraggableNext v-model="stages" handle=".drag-handle" class="stage-list">
                <div
                  v-for="(element, index) in stages"
                  :key="element._id"
                  class="stage-row"
                >
                  <div class="drag-handle" title="拖动排序">⋮⋮</div>
                  <div class="stage-fields">
                    <span>阶段 {{ index + 1 }}</span>
                    <el-input-number v-model="element.duration_sec" :min="1" :max="99999" size="small" />
                    <span class="mini">秒</span>
                    <el-input-number v-model="element.users" :min="1" :max="10000" size="small" />
                    <span class="mini">用户</span>
                    <el-input-number v-model="element.spawn_rate" :min="1" :max="1000" size="small" />
                    <span class="mini">用户/秒</span>
                    <el-button type="danger" link size="small" @click="removeStage(index)">删除</el-button>
                  </div>
                </div>
              </VueDraggableNext>
              <el-button type="primary" link native-type="button" @click.prevent="addStage">+ 添加阶段</el-button>
            </el-form-item>
            <el-form-item label="总时长(秒)">
              <el-input-number :model-value="stagedTotalSeconds" disabled />
              <span class="unit-hint">= 各阶段时长之和</span>
            </el-form-item>
          </template>

          <el-form-item label="目标 RPS" prop="target_rps">
            <el-input-number
              v-model="form.target_rps"
              :min="0.1"
              :max="100000"
              :precision="2"
              :step="10"
              controls-position="right"
              clearable
            />
            <span class="unit-hint">留空不限制；填写后按当前活跃用户数节流，近似全局 RPS（在响应时间之后、思考时间之前）</span>
          </el-form-item>

          <el-form-item label="超时(秒)">
            <el-input-number v-model="form.timeout" :min="1" :max="300" />
          </el-form-item>
        </el-collapse-item>

        <!-- 思考时间 -->
        <el-collapse-item title="思考时间(Think Time)" name="think">
          <el-form-item label="思考时间">
            <el-input-number v-model="form.think_time_ms" :min="0" :max="600000" />
            <span class="unit-hint">毫秒；每次请求完成后休眠，默认 0</span>
          </el-form-item>
        </el-collapse-item>

        <!-- 业务断言 -->
        <el-collapse-item title="业务断言配置" name="assert">
          <p class="block-hint">
            无断言时仅按 HTTP 状态码判定失败（与后端默认一致）。断言规则：JSONPath 指向响应 JSON 字段；操作符 eq/ne/gt/ge/lt/le 需填期望值；not_null
            仅检查路径存在且非 null；contains 为字符串包含。
          </p>
          <VueDraggableNext v-model="assertions" handle=".drag-handle" class="assert-list">
            <div
              v-for="(element, index) in assertions"
              :key="element._id"
              class="assert-row"
            >
              <div class="drag-handle" title="拖动排序">⋮⋮</div>
              <el-input v-model="element.jsonpath" placeholder="JSONPath，如 $.code" class="w-jsonpath" />
              <el-select v-model="element.op" placeholder="操作符" style="width: 130px" @change="onOpChange(element)">
                <el-option v-for="op in opOptions" :key="op.value" :label="op.label" :value="op.value" />
              </el-select>
              <el-input
                v-if="element.op !== 'not_null'"
                v-model="element.expectRaw"
                placeholder="期望值（数字或字符串）"
                class="w-expect"
              />
              <span v-else class="w-expect text-muted">—</span>
              <el-button type="danger" link @click="removeAssertion(index)">删除</el-button>
            </div>
          </VueDraggableNext>
          <el-button type="primary" link native-type="button" @click.prevent="addAssertion">+ 添加断言</el-button>
        </el-collapse-item>

        <!-- CSV -->
        <el-collapse-item title="参数化(CSV)" name="csv">
          <el-form-item label="读取策略">
            <el-radio-group v-model="form.csv_read_strategy">
              <el-radio label="per_iteration">每迭代一行</el-radio>
              <el-radio label="per_user">每用户一行</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="CSV 文件">
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept=".csv"
              :on-change="onCsvFileChange"
            >
              <el-button type="primary">选择文件</el-button>
              <template #tip>
                <div class="el-upload__tip">仅 .csv，≤10MB；{{ existingCsvName ? `当前：${existingCsvName}` : "未上传" }}</div>
              </template>
            </el-upload>
            <div v-if="csvFileName" class="csv-file-name">新文件：{{ csvFileName }}</div>
          </el-form-item>
          <el-form-item v-if="csvPreview.headers.length" label="内容预览">
            <el-table :data="csvPreviewRows" border size="small" max-height="240">
              <el-table-column
                v-for="(h, i) in csvPreview.headers"
                :key="i"
                :prop="`c${i}`"
                :label="h"
                min-width="100"
              />
            </el-table>
            <p class="preview-hint">表头 + 前 5 行</p>
          </el-form-item>
        </el-collapse-item>
      </el-collapse>
    </el-form>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VueDraggableNext } from "vue-draggable-next";
import { msgError, msgSuccess } from "../../utils/uiMessage.js";
import {
  createPerformanceTask,
  updatePerformanceTask,
  fetchPerformanceTaskDetail
} from "../../api/performance";
import { fetchProjects, fetchEnvironments, resolveApiProjectId } from "../../api/scene";
import { fetchApiAssets } from "../../api/apiAsset";
import { nextLocalId, parseCsvPreview } from "./performanceUtils.js";

const route = useRoute();
const router = useRouter();

const isEdit = computed(() => !!route.params.id && route.params.id !== "new");
const taskId = computed(() => (isEdit.value ? route.params.id : null));

const formRef = ref(null);
const submitLoading = ref(false);
const activeNames = ref(["base", "load", "think", "assert", "csv"]);

const projects = ref([]);
const environments = ref([]);
const apiAssets = ref([]);

const loadMode = ref("fixed");
const form = ref({
  name: "",
  project: null,
  environment: null,
  interface: null,
  total_users: 10,
  spawn_rate: 5,
  run_time: 60,
  target_rps: null,
  timeout: 30,
  think_time_ms: 0,
  csv_read_strategy: "per_iteration"
});

const stages = ref([]);
const assertions = ref([]);

const csvFile = ref(null);
const csvFileName = ref("");
const csvPreview = ref({ headers: [], rows: [] });
const existingCsvName = ref("");

const opOptions = [
  { value: "eq", label: "eq 等于" },
  { value: "ne", label: "ne 不等于" },
  { value: "gt", label: "gt 大于" },
  { value: "ge", label: "ge 大于等于" },
  { value: "lt", label: "lt 小于" },
  { value: "le", label: "le 小于等于" },
  { value: "not_null", label: "not_null" },
  { value: "contains", label: "contains 包含" }
];

const rules = computed(() => {
  const r = {
    name: [{ required: true, message: "请输入任务名称", trigger: "blur" }],
    project: [{ required: true, message: "请选择项目", trigger: "change" }],
    environment: [{ required: true, message: "请选择环境", trigger: "change" }],
    interface: [{ required: true, message: "请选择接口", trigger: "change" }]
  };
  if (loadMode.value === "fixed") {
    r.total_users = [{ required: true, type: "number", min: 1, message: "≥1", trigger: "blur" }];
    r.spawn_rate = [{ required: true, type: "number", min: 1, message: "≥1", trigger: "blur" }];
    r.run_time = [{ required: true, type: "number", min: 1, message: "≥1", trigger: "blur" }];
  }
  r.target_rps = [
    {
      validator: (_rule, val, cb) => {
        if (val === null || val === undefined || val === "") return cb();
        const n = Number(val);
        if (Number.isNaN(n) || n <= 0) return cb(new Error("须大于 0 或留空"));
        return cb();
      },
      trigger: "change"
    }
  ];
  return r;
});

const stagedTotalSeconds = computed(() => stages.value.reduce((s, x) => s + (Number(x.duration_sec) || 0), 0));

const csvPreviewRows = computed(() => {
  const headers = csvPreview.value.headers;
  return csvPreview.value.rows.map((cells) => {
    const row = {};
    cells.forEach((c, i) => {
      row[`c${i}`] = c;
    });
    return row;
  });
});

function goBack() {
  router.push({ name: "perf-list" });
}

function addStage() {
  stages.value.push({
    _id: nextLocalId(),
    duration_sec: 60,
    users: 10,
    spawn_rate: 2
  });
}
function removeStage(i) {
  stages.value.splice(i, 1);
}

function addAssertion() {
  assertions.value.push({
    _id: nextLocalId(),
    jsonpath: "$.code",
    op: "eq",
    expectRaw: "200"
  });
}
function removeAssertion(i) {
  assertions.value.splice(i, 1);
}
function onOpChange(el) {
  if (el.op === "not_null") {
    el.expectRaw = "";
  }
}

/** 与 test_manager.utils.performance_config.validate_assertions_config 对齐的前端校验 */
function validateAssertionRows() {
  for (let i = 0; i < assertions.value.length; i++) {
    const a = assertions.value[i];
    const jp = (a.jsonpath || "").trim();
    if (!jp) {
      msgError(`第 ${i + 1} 条断言：请填写 JSONPath`);
      return false;
    }
    if (a.op !== "not_null") {
      const raw = a.expectRaw;
      if (raw === "" || raw === null || raw === undefined) {
        msgError(`第 ${i + 1} 条断言：操作符「${a.op}」需要填写期望值`);
        return false;
      }
    }
  }
  return true;
}

function onCsvFileChange(uploadFile) {
  const raw = uploadFile.raw;
  if (!raw) return;
  if (raw.size > 10 * 1024 * 1024) {
    msgError("文件不能超过 10MB");
    return;
  }
  csvFile.value = raw;
  csvFileName.value = raw.name;
  const reader = new FileReader();
  reader.onload = () => {
    const text = reader.result;
    const p = parseCsvPreview(text, 5);
    csvPreview.value = { headers: p.headers, rows: p.rows };
  };
  reader.readAsText(raw, "UTF-8");
}

async function onProjectChange(projectId) {
  form.value.environment = null;
  form.value.interface = null;
  environments.value = [];
  apiAssets.value = [];
  if (!projectId) return;
  try {
    const [envRes, apiProjRes] = await Promise.all([
      fetchEnvironments(projectId),
      resolveApiProjectId(projectId)
    ]);
    environments.value = envRes.results || envRes.data || envRes || [];
    if (Array.isArray(envRes)) environments.value = envRes;
    const apiProjectId = apiProjRes?.api_project_id;
    if (apiProjectId) {
      const assetRes = await fetchApiAssets(apiProjectId);
      apiAssets.value = assetRes.results || assetRes.data || assetRes || [];
      if (Array.isArray(assetRes)) apiAssets.value = assetRes;
    }
  } catch (e) {
    msgError(e?.message || "加载环境/接口失败");
  }
}

function buildExtraConfig() {
  const ec = {
    timeout: form.value.timeout,
    think_time_ms: form.value.think_time_ms,
    csv_read_strategy: form.value.csv_read_strategy
  };
  const ass = assertions.value
    .filter((a) => (a.jsonpath || "").trim())
    .map((a) => {
      const row = { jsonpath: a.jsonpath.trim(), op: a.op };
      if (a.op !== "not_null") {
        let ex = a.expectRaw;
        if (ex === "" || ex === null || ex === undefined) {
          ex = null;
        } else if (!Number.isNaN(Number(ex)) && String(ex).trim() !== "" && /^-?\d+(\.\d+)?$/.test(String(ex).trim())) {
          ex = Number(ex);
        }
        row.expect = ex;
      }
      return row;
    });
  if (ass.length) ec.assertions = ass;

  if (loadMode.value === "staged" && stages.value.length) {
    ec.stages = stages.value.map((s) => ({
      duration_sec: Number(s.duration_sec),
      users: Number(s.users),
      spawn_rate: Number(s.spawn_rate)
    }));
  }
  return ec;
}

async function beforeSubmit() {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
  } catch {
    return;
  }
  if (assertions.value.length && !validateAssertionRows()) {
    return;
  }
  if (loadMode.value === "staged") {
    if (!stages.value.length) {
      msgError("请至少添加一个负载阶段");
      return;
    }
    const sum = stagedTotalSeconds.value;
    if (sum <= 0) {
      msgError("阶段时长无效");
      return;
    }
  }
  await doSubmit();
}

async function doSubmit() {
  const ec = buildExtraConfig();
  let runTime = form.value.run_time;
  let totalUsers = form.value.total_users;
  let spawnRate = form.value.spawn_rate;

  if (loadMode.value === "staged") {
    runTime = stagedTotalSeconds.value;
    totalUsers = Math.max(...stages.value.map((s) => Number(s.users) || 0));
    spawnRate = Number(stages.value[0]?.spawn_rate) || 1;
  }

  const payload = {
    name: form.value.name,
    project: form.value.project,
    environment: form.value.environment,
    interface: form.value.interface,
    total_users: totalUsers,
    spawn_rate: spawnRate,
    run_time: runTime,
    target_rps: form.value.target_rps ?? null,
    extra_config: ec
  };

  submitLoading.value = true;
  try {
    if (isEdit.value) {
      await updatePerformanceTask(taskId.value, payload, csvFile.value);
      msgSuccess("更新成功");
    } else {
      await createPerformanceTask(payload, csvFile.value);
      msgSuccess("创建成功");
    }
    router.push({ name: "perf-list" });
  } catch (e) {
    msgError(e?.message || "保存失败");
  } finally {
    submitLoading.value = false;
  }
}

function hydrateFromTask(task) {
  form.value = {
    name: task.name,
    project: task.project,
    environment: task.environment,
    interface: task.interface,
    total_users: task.total_users,
    spawn_rate: task.spawn_rate,
    run_time: task.run_time,
    target_rps: task.target_rps ?? null,
    timeout: task.extra_config?.timeout ?? 30,
    think_time_ms: task.extra_config?.think_time_ms ?? 0,
    csv_read_strategy: task.extra_config?.csv_read_strategy ?? "per_iteration"
  };
  const ex = task.extra_config || {};
  if (Array.isArray(ex.stages) && ex.stages.length) {
    loadMode.value = "staged";
    stages.value = ex.stages.map((s) => ({
      _id: nextLocalId(),
      duration_sec: s.duration_sec,
      users: s.users,
      spawn_rate: s.spawn_rate
    }));
  } else {
    loadMode.value = "fixed";
    stages.value = [];
  }
  if (Array.isArray(ex.assertions)) {
    assertions.value = ex.assertions.map((a) => ({
      _id: nextLocalId(),
      jsonpath: a.jsonpath,
      op: a.op,
      expectRaw: a.op === "not_null" ? "" : a.expect !== undefined && a.expect !== null ? String(a.expect) : ""
    }));
  } else {
    assertions.value = [];
  }
  if (task.csv_file) {
    const p = String(task.csv_file);
    existingCsvName.value = p.split("/").pop() || p;
  }
}

async function loadTask() {
  if (!isEdit.value) {
    if (route.query.copy === "1") {
      try {
        const raw = sessionStorage.getItem("perfTaskCopy");
        if (raw) {
          const t = JSON.parse(raw);
          hydrateFromTask(t);
          form.value.name = `${t.name || "任务"}（副本）`;
          sessionStorage.removeItem("perfTaskCopy");
          if (form.value.project) {
            await onProjectChange(form.value.project);
            form.value.environment = t.environment;
            form.value.interface = t.interface;
          }
        }
      } catch {
        /* ignore */
      }
    }
    return;
  }
  try {
    const task = await fetchPerformanceTaskDetail(taskId.value);
    await onProjectChange(task.project);
    hydrateFromTask(task);
  } catch (e) {
    msgError(e?.message || "加载任务失败");
  }
}

watch(loadMode, (m) => {
  if (m === "staged" && !stages.value.length) {
    addStage();
  }
});

onMounted(async () => {
  try {
    const res = await fetchProjects();
    projects.value = res.results || res.data || res || [];
    if (Array.isArray(res)) projects.value = res;
  } catch (e) {
    msgError(e?.message || "加载项目失败");
  }
  await loadTask();
});
</script>

<style scoped>
.perf-editor-page {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.perf-form {
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}
.unit-hint {
  margin-left: 8px;
  color: #909399;
  font-size: 13px;
}
.block-hint {
  font-size: 13px;
  color: #606266;
  margin: 0 0 12px;
}
.stage-list {
  width: 100%;
}
.stage-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
  padding: 8px;
  background: #f8fafc;
  border-radius: 6px;
}
.drag-handle {
  cursor: grab;
  padding: 4px 8px 0 0;
  color: #94a3b8;
  user-select: none;
}
.stage-fields {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.mini {
  font-size: 12px;
  color: #64748b;
}
.assert-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
padding: 8px;
  background: #f8fafc;
  border-radius: 6px;
}
.w-jsonpath {
  flex: 1;
  min-width: 180px;
}
.w-expect {
  width: 160px;
}
.text-muted {
  color: #94a3b8;
}
.csv-file-name {
  margin-top: 8px;
  font-size: 13px;
  color: #409eff;
}
.preview-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
</style>
