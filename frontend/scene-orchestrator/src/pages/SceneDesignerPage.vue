<template>
  <div class="designer-page">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <button class="btn btn-outline-secondary" @click="goList"><i class="bi bi-arrow-left"></i> 返回列表</button>
      <div class="d-flex align-items-center gap-2">
        <span v-if="lastSavedAt && !store.dirty && !nodeConfigDirty" class="save-status text-muted small">
          <i class="bi bi-check-circle text-success"></i> 已保存于 {{ lastSavedAt }}
        </span>
        <span v-else-if="store.dirty || nodeConfigDirty" class="save-status text-warning small">
          <i class="bi bi-dot-circle"></i> 有未保存的修改
        </span>
        <button
          class="btn btn-primary px-4"
          :disabled="store.saving || initLoading"
          @click="saveNow"
        >
          <span v-if="store.saving" class="spinner-border spinner-border-sm me-2" role="status" />
          <i class="bi bi-check-lg"></i> {{ store.saving ? "保存中..." : "保存" }}
        </button>
      </div>
    </div>
    <div class="designer-toolbar card p-2 mb-2">
      <div class="d-flex gap-2 align-items-center flex-wrap">
        <span class="text-muted small">场景信息</span>
        <input v-model="store.scene.name" class="form-control form-control-sm scene-name-input" @input="store.markDirty()" />
        <input v-model="store.scene.description" class="form-control form-control-sm scene-desc-input" placeholder="场景描述" @input="store.markDirty()" />
        <div class="d-flex align-items-center gap-1">
          <label class="text-muted small mb-0">分组</label>
          <el-select
            v-model="sceneGroupId"
            placeholder="无分组"
            size="small"
            clearable
            filterable
            class="scene-env-select"
            popper-class="scene-select-popper"
            style="min-width: 140px"
            @change="store.markDirty()"
          >
            <el-option label="无分组" :value="''" />
            <el-option
              v-for="g in groupOptions"
              :key="g.id"
              :label="g.pathLabel"
              :value="g.id"
            >
              <span class="group-option-item">
                <i class="bi bi-folder me-1 text-primary"></i>
                <span v-html="g.pathHtml"></span>
              </span>
            </el-option>
          </el-select>
        </div>
        <div class="d-flex align-items-center gap-1">
          <label class="text-muted small mb-0">场景专属环境</label>
          <el-select
            v-model="sceneEnvironmentId"
            placeholder="继承全局"
            size="small"
            class="scene-env-select"
            popper-class="scene-select-popper"
            style="min-width: 140px"
          >
            <el-option label="继承全局" :value="''" />
            <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </div>
        <button class="btn btn-sm btn-outline-primary" @click="openAddDialog" :disabled="initLoading">添加接口</button>
        <button class="btn btn-sm btn-outline-info" @click="openSceneVarsDialog">场景变量</button>
      </div>
    </div>

    <!-- 场景变量编辑弹窗 -->
    <el-dialog v-model="sceneVarsDialogVisible" title="场景变量" width="620px" top="10vh" append-to-body>
      <div>
        <p class="text-muted small mb-2">
          场景变量在执行启动时预渲染一次，同一场景内所有节点共享。支持 <code v-pre>{{func()}}</code> 函数调用和 <code v-pre>{{var}}</code> 变量引用语法。
        </p>
        <div class="kv-editor">
          <div v-for="(row, idx) in sceneVarRows" :key="idx" class="kv-row mb-2">
            <input v-model="row.key" class="form-control form-control-sm" placeholder="变量名" style="width:180px" />
            <input v-model="row.value" class="form-control form-control-sm" placeholder='变量值，使用模板语法，如 debugtalk.timestamp()' />
            <button class="btn btn-sm btn-outline-secondary" @click="openSceneVarPicker(idx)">变量</button>
            <button class="btn btn-sm btn-outline-danger" @click="removeSceneVarRow(idx)">删</button>
          </div>
        </div>
        <button class="btn btn-sm btn-outline-primary mt-1" @click="addSceneVarRow">新增变量</button>
      </div>
      <template #footer>
        <button class="btn btn-sm btn-outline-secondary" @click="sceneVarsDialogVisible = false">取消</button>
        <button class="btn btn-sm btn-primary" @click="saveSceneVars">保存</button>
      </template>
      <VariablePicker
        v-model:visible="sceneVarsPickerVisible"
        :options="variableOptions"
        :scene-id="store.currentSceneId"
        :current-node-id="store.selectedNodeId"
        :environment-id="sceneEnvironmentId || ''"
        @pick="insertSceneVarVariable"
        @close="sceneVarsPickerVisible = false"
      />
    </el-dialog>

    <div v-if="initLoading" class="card p-3">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else-if="initError" class="card p-3 text-center">
      <div class="text-danger mb-2">{{ initError }}</div>
      <button class="btn btn-sm btn-outline-primary" @click="loadDesignerData">重试</button>
    </div>

    <div v-else class="designer-grid">
      <section class="center-panel card p-2">
        <el-table
          ref="nodeTableRef"
          :data="pagedNodes"
          row-key="id"
          height="100%"
          highlight-current-row
          :current-row-key="store.selectedNodeId"
          @row-click="onRowClick"
        >
          <el-table-column width="36" align="center" class-name="drag-handle-cell">
            <template #default>
              <i class="bi bi-grip-vertical text-muted node-drag-handle" title="拖动调整顺序" />
            </template>
          </el-table-column>
          <el-table-column label="Method" width="110">
            <template #default="{ row }">
              <span :class="`badge method-badge method-${(row.method || '').toLowerCase()}`">{{ row.method || "API" }}</span>
            </template>
          </el-table-column>
          <el-table-column label="接口名称" min-width="240">
            <template #default="{ row }">
              <span>{{ row.name }}</span>
              <span v-if="row.id === store.selectedNodeId && nodeConfigDirty" class="node-unsaved-mark">*</span>
            </template>
          </el-table-column>
          <el-table-column label="启用状态" width="120">
            <template #default="{ row }">
              <el-switch
                :model-value="row.isEnabled"
                :loading="nodeLoadingMap.get(row.id) === 'toggle'"
                @change="(val) => toggleNodeEnabled(row.id, val)"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <div class="d-flex gap-2">
                <button class="btn btn-sm btn-outline-primary" @click="selectNode(row.id)" :disabled="nodeLoadingMap.has(row.id)">编辑</button>
                <button class="btn btn-sm btn-outline-danger" @click="deleteNode(row.id)" :disabled="nodeLoadingMap.get(row.id) === 'delete'">
                  {{ nodeLoadingMap.get(row.id) === "delete" ? "删除中..." : "删除" }}
                </button>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!tableState.list.length" class="text-center text-muted py-4">暂无节点，点击“添加接口”创建</div>
        <div class="d-flex justify-content-end mt-2" v-if="tableState.list.length > pageSize">
          <el-pagination
            layout="prev, pager, next"
            :total="tableState.list.length"
            :page-size="pageSize"
            :current-page="pageNum"
            @current-change="(v) => (pageNum = v)"
          />
        </div>
      </section>

      <section class="right-panel">
        <div v-if="configPanelLoading" class="config-panel-loading">
          <el-skeleton :rows="4" animated />
        </div>
        <NodeConfigPanel
          v-else
          ref="configPanelRef"
          :key="store.selectedNodeId ?? 'none'"
          :node="store.selectedNode"
          :nodes="store.nodeList"
          :variable-options="variableOptions"
          :scene-id="store.currentSceneId"
          :current-node-id="store.selectedNodeId"
          :environment-id="sceneEnvironmentId || ''"
          :node-response-preview="nodeResponsePreview"
          :environments="environments"
          :saving="savingNodeConfig"
          @save="saveNodeConfig"
          @update:dirty="nodeConfigDirty = $event"
        />
      </section>
    </div>

    <!-- 关联API已更新 - 差异提示弹窗 -->
    <el-dialog
      v-model="apiDiffDialogVisible"
      title="关联接口已更新 - 请选择同步方式"
      width="560px"
      :close-on-click-modal="false"
      append-to-body
      @close="onApiDiffDialogClose"
    >
      <div v-if="apiDiffLoading" class="text-center py-4">
        <span class="spinner-border spinner-border-sm text-primary me-2" />
        加载差异中...
      </div>
      <div v-else class="api-diff-dialog-content">
        <!-- 汇总摘要 -->
        <div class="api-diff-summary mb-3">
          共 <strong>{{ apiDiffSummary.total }}</strong> 个节点需要同步：
          <span v-if="apiDiffSummary.urlChanges">URL 变更 {{ apiDiffSummary.urlChanges }} 处；</span>
          <span v-if="apiDiffSummary.methodChanges">Method 变更 {{ apiDiffSummary.methodChanges }} 处；</span>
          <span v-if="apiDiffSummary.paramsAdded">新增参数 {{ apiDiffSummary.paramsAdded }} 个；</span>
          <span v-if="apiDiffSummary.paramsRemoved">删除参数 {{ apiDiffSummary.paramsRemoved }} 个；</span>
          <span v-if="apiDiffSummary.headersAdded">新增请求头 {{ apiDiffSummary.headersAdded }} 个；</span>
          <span v-if="apiDiffSummary.headersRemoved">删除请求头 {{ apiDiffSummary.headersRemoved }} 个；</span>
          <span v-if="apiDiffSummary.responseFieldsAdded">新增响应字段 {{ apiDiffSummary.responseFieldsAdded }} 个；</span>
          <span v-if="apiDiffSummary.responseFieldsRemoved">删除响应字段 {{ apiDiffSummary.responseFieldsRemoved }} 个</span>
        </div>
        <!-- 全部一键同步 -->
        <div v-if="hasAnySyncBasic" class="mb-2">
          <button
            class="btn btn-sm btn-primary"
            :disabled="apiDiffSyncingMap.size > 0"
            @click="doSyncAll"
          >
            全部一键同步
          </button>
        </div>
        <!-- 折叠面板 -->
        <el-collapse v-model="apiDiffActiveNames">
          <el-collapse-item
            v-for="diffItem in apiDiffItems"
            :key="diffItem.node_id"
            :name="String(diffItem.node_id)"
          >
            <template #title>
              <div class="api-diff-collapse-title">
                <strong>{{ diffItem.api_asset_name || ('节点 #' + diffItem.node_id) }}</strong>
                <span class="api-diff-collapse-summary text-muted small ms-2">{{ apiDiffNodeSummary(diffItem) }}</span>
              </div>
            </template>
            <div class="api-diff-node-block">
              <div v-if="diffItem.diffs?.basic?.url?.changed" class="mb-1 small">
                <span class="text-muted">URL: </span>
                <span class="text-decoration-line-through api-diff-highlight">{{ diffItem.diffs.basic.url.old }}</span>
                <span class="mx-1">→</span>
                <span class="api-diff-highlight">{{ diffItem.diffs.basic.url.new }}</span>
                <button
                  v-if="diffItem.sync_status?.can_sync_basic"
                  class="btn btn-sm btn-outline-primary ms-2"
                  :disabled="apiDiffSyncingMap.has(diffItem.node_id)"
                  @click="doSyncBasic(diffItem.node_id)"
                >{{ apiDiffSyncingMap.has(diffItem.node_id) ? "同步中..." : "一键同步" }}</button>
              </div>
              <div v-if="diffItem.diffs?.basic?.method?.changed" class="mb-1 small">
                <span class="text-muted">Method: </span>
                <span class="api-diff-highlight">{{ diffItem.diffs.basic.method.old }}</span>
                <span class="mx-1">→</span>
                <span class="api-diff-highlight">{{ diffItem.diffs.basic.method.new }}</span>
                <button
                  v-if="diffItem.sync_status?.can_sync_basic"
                  class="btn btn-sm btn-outline-primary ms-2"
                  :disabled="apiDiffSyncingMap.has(diffItem.node_id)"
                  @click="doSyncBasic(diffItem.node_id)"
                >{{ apiDiffSyncingMap.has(diffItem.node_id) ? "同步中..." : "一键同步" }}</button>
              </div>
              <div v-if="(diffItem.diffs?.request?.params_removed?.length || 0) > 0" class="mb-1 small d-flex align-items-center flex-wrap gap-1">
                <span class="text-muted">删除参数: </span>
                <span><template v-for="(p, i) in (diffItem.diffs.request.params_removed || [])" :key="p"><span v-if="i">, </span><span class="api-diff-highlight">{{ p }}</span></template></span>
                <button
                  v-if="diffItem.sync_status?.can_sync_params"
                  class="btn btn-sm btn-outline-primary ms-1"
                  :disabled="apiDiffSyncingMap.has(`params-full-${diffItem.node_id}`)"
                  @click="doSyncParams(diffItem.node_id)"
                >{{ apiDiffSyncingMap.has(`params-full-${diffItem.node_id}`) ? "同步中..." : "同步参数" }}</button>
              </div>
              <div v-if="(diffItem.diffs?.request?.params_added?.length || 0) > 0" class="mb-1 small d-flex align-items-center flex-wrap gap-1">
                <span class="text-muted">新增参数: </span>
                <span><template v-for="(p, i) in (diffItem.diffs.request.params_added || [])" :key="p"><span v-if="i">, </span><span class="api-diff-highlight">{{ p }}</span></template></span>
                <button
                  v-if="diffItem.sync_status?.can_add_params"
                  class="btn btn-sm btn-outline-primary ms-1"
                  :disabled="apiDiffSyncingMap.has(`params-${diffItem.node_id}`)"
                  @click="doSyncAddParams(diffItem.node_id, diffItem.diffs.request.params_added || [], 'request_params')"
                >{{ apiDiffSyncingMap.has(`params-${diffItem.node_id}`) ? "同步中..." : "新增空参数到节点" }}</button>
                <button
                  v-if="diffItem.sync_status?.can_sync_params"
                  class="btn btn-sm btn-outline-primary ms-1"
                  :disabled="apiDiffSyncingMap.has(`params-full-${diffItem.node_id}`)"
                  @click="doSyncParams(diffItem.node_id)"
                >{{ apiDiffSyncingMap.has(`params-full-${diffItem.node_id}`) ? "同步中..." : "同步参数" }}</button>
              </div>
              <div v-if="(diffItem.diffs?.request?.headers_added?.length || 0) > 0" class="mb-1 small d-flex align-items-center flex-wrap gap-1">
                <span class="text-muted">新增请求头: </span>
                <span><template v-for="(h, i) in (diffItem.diffs.request.headers_added || [])" :key="h"><span v-if="i">, </span><span class="api-diff-highlight">{{ h }}</span></template></span>
                <button
                  v-if="diffItem.sync_status?.can_add_params"
                  class="btn btn-sm btn-outline-primary ms-1"
                  :disabled="apiDiffSyncingMap.has(`headers-${diffItem.node_id}`)"
                  @click="doSyncAddParams(diffItem.node_id, diffItem.diffs.request.headers_added || [], 'request_headers')"
                >{{ apiDiffSyncingMap.has(`headers-${diffItem.node_id}`) ? "同步中..." : "新增空请求头到节点" }}</button>
              </div>
              <div v-if="(diffItem.diffs?.request?.headers_value_changed?.length || 0) > 0" class="mb-1 small d-flex align-items-start flex-wrap gap-1">
                <span class="text-muted">请求头值变更: </span>
                <span>
                  <template v-for="(h, i) in (diffItem.diffs.request.headers_value_changed || [])" :key="h.key">
                    <span v-if="i">；</span>
                    <span class="api-diff-highlight">{{ h.key }}</span>
                    <span>: {{ h.old || '(空)' }} → {{ h.new || '(空)' }}</span>
                  </template>
                </span>
              </div>
              <div v-if="(diffItem.diffs?.request?.headers_removed?.length || 0) > 0" class="mb-1 small d-flex align-items-center flex-wrap gap-1">
                <span class="text-muted">删除请求头: </span>
                <span><template v-for="(h, i) in (diffItem.diffs.request.headers_removed || [])" :key="h"><span v-if="i">, </span><span class="api-diff-highlight">{{ h }}</span></template></span>
              </div>
              <div v-if="diffItem.diffs?.request?.body_format_changed" class="mb-1 small">
                <span class="text-muted">请求体格式已变更</span>
              </div>
              <div v-if="diffItem.sync_status?.can_sync_headers" class="mb-1 small">
                <button
                  class="btn btn-sm btn-outline-primary"
                  :disabled="apiDiffSyncingMap.has(`headers-full-${diffItem.node_id}`)"
                  @click="doSyncHeaders(diffItem.node_id)"
                >{{ apiDiffSyncingMap.has(`headers-full-${diffItem.node_id}`) ? "同步中..." : "同步请求头" }}</button>
              </div>
              <div v-if="(diffItem.diffs?.response?.fields_removed?.length || 0) > 0" class="mb-1 small d-flex align-items-center flex-wrap gap-1">
                <span class="text-muted">删除响应字段: </span>
                <span>{{ (diffItem.diffs.response.fields_removed || []).slice(0, 5).join(", ") }}</span>
                <span v-if="(diffItem.diffs.response.fields_removed || []).length > 5">...</span>
              </div>
              <div v-if="(diffItem.diffs?.response?.fields_added?.length || 0) > 0" class="mb-1 small d-flex align-items-center flex-wrap gap-1">
                <span class="text-muted">新增响应字段: </span>
                <span>{{ (diffItem.diffs.response.fields_added || []).slice(0, 5).join(", ") }}</span>
                <span v-if="(diffItem.diffs.response.fields_added || []).length > 5">...</span>
                <button class="btn btn-sm btn-outline-primary ms-1" @click="goToNodeConfig(diffItem.node_id)">去配置断言/提取规则</button>
              </div>
              <div v-if="(diffItem.diffs?.response?.warnings?.length || 0) > 0" class="mb-1 small text-warning">
                ⚠️ {{ (diffItem.diffs.response.warnings || [])[0] }}
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
      <template #footer>
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <el-checkbox v-model="apiDiffDontShowAgain" class="mb-0">本次不再提示</el-checkbox>
            <el-checkbox v-model="apiDiffDismiss7d" class="mb-0">7天内不再提示该接口变更</el-checkbox>
          </div>
          <button class="btn btn-sm btn-outline-secondary" @click="apiDiffDialogVisible = false">暂不同步</button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="addDialogVisible" title="选择API资产" width="520px" top="8vh" append-to-body>
      <div class="mb-2">
        <input
          v-model="assetSearchInput"
          class="form-control form-control-sm"
          placeholder="搜索接口名称..."
        />
      </div>
      <div class="asset-dialog-scroll">
        <el-tree
          v-if="assetTreeData.length"
          ref="assetTreeRef"
          class="asset-dialog-tree"
          :data="assetTreeData"
          node-key="key"
          :default-expanded-keys="assetDefaultExpandedKeys"
          highlight-current
          :props="{ label: 'label', children: 'children' }"
          @node-click="onAssetTreeNodeClick"
        />
        <div v-else class="text-center text-muted py-4">
          {{ assetSearchKeyword ? '未找到匹配的接口' : '暂无可用接口' }}
        </div>
      </div>
      <template #footer>
        <button class="btn btn-sm btn-outline-secondary" @click="addDialogVisible = false">取消</button>
        <button class="btn btn-sm btn-primary" :disabled="!pendingApiId || addingNode" @click="confirmAddApi">
          {{ addingNode ? "添加中..." : "确认添加" }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import Sortable from "sortablejs";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, nextTick, onMounted, onUnmounted, ref, shallowReactive, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import NodeConfigPanel from "../components/NodeConfigPanel.vue";
import VariablePicker from "../components/VariablePicker.vue";
import {
  createSceneNode,
  deleteSceneNode,
  fetchSceneDesignerInit,
  fetchSceneExecutions,
  fetchNodeApiDiff,
  syncNodeBasic,
  syncNodeAddParams,
  syncNodeHeaders,
  syncNodeParams,
  syncAllSceneNodes,
  reorderSceneNodes,
  updateSceneNode
} from "../api/scene";
import { fetchApiGroups } from "../api/apiAsset";
import { useSceneStore } from "../stores/sceneStore";
import { cloneJson } from "../utils/cloneJson";

const route = useRoute();
const router = useRouter();
const store = useSceneStore();

const groups = ref([]);
const assets = ref([]);
const environments = ref([]);
const addDialogVisible = ref(false);
const sceneVarsDialogVisible = ref(false);
const sceneVarRows = ref([]);
const sceneVarsPickerVisible = ref(false);
const activeSceneVarRowIdx = ref(-1);
const pendingApiId = ref(null);
const addingNode = ref(false);
const initLoading = ref(true);
const initError = ref("");
const pageNum = ref(1);
const pageSize = 50;
const assetTreeRef = ref(null);
const nodeLoadingMap = ref(new Map());
const creatingNodePromiseCache = new Map();
const savingNodeConfig = ref(false);
const nodeConfigDirty = ref(false);
const lastSavedAt = ref("");
const configPanelLoading = ref(false);
const configPanelRef = ref(null);
const nodeTableRef = ref(null);
let sortableInstance = null;
const assetSearchInput = ref("");
const assetSearchKeyword = ref("");
let assetSearchTimer = null;
const lastExecutionNodeResults = ref({});
const debugtalkFunctions = ref([]);
const apiDiffDialogVisible = ref(false);
const apiDiffLoading = ref(false);
const apiDiffItems = ref([]);
const apiDiffSyncingMap = ref(new Set());
const apiDiffDontShowAgain = ref(false);
const apiDiffDismiss7d = ref(false);
const apiDiffActiveNames = ref([]);

const API_DIFF_DISMISS_7D_KEY = "api_diff_dismissed_7d";
const DISMISS_7D_MS = 7 * 24 * 60 * 60 * 1000;

function getApiDiffDismissed7dMap() {
  try {
    const raw = localStorage.getItem(API_DIFF_DISMISS_7D_KEY);
    if (!raw) return {};
    const obj = JSON.parse(raw);
    return typeof obj === "object" ? obj : {};
  } catch {
    return {};
  }
}

function isApiAssetDismissed7d(assetId) {
  if (!assetId) return false;
  const map = getApiDiffDismissed7dMap();
  const until = map[String(assetId)];
  if (!until) return false;
  return Date.now() < until;
}

function dismissApiAssets7d(assetIds) {
  if (!assetIds?.length) return;
  const map = getApiDiffDismissed7dMap();
  const until = Date.now() + DISMISS_7D_MS;
  assetIds.forEach((id) => {
    if (id) map[String(id)] = until;
  });
  try {
    localStorage.setItem(API_DIFF_DISMISS_7D_KEY, JSON.stringify(map));
  } catch (e) {
    console.warn("保存7天不再提示失败", e);
  }
}

// --- 场景变量编辑 ---
function openSceneVarsDialog() {
  const vars = store.scene?.variables || {};
  sceneVarRows.value = Object.entries(vars).map(([k, v]) => ({ key: k, value: String(v ?? "") }));
  if (sceneVarRows.value.length === 0) {
    sceneVarRows.value = [{ key: "", value: "" }];
  }
  sceneVarsDialogVisible.value = true;
}

function addSceneVarRow() {
  sceneVarRows.value.push({ key: "", value: "" });
}

function removeSceneVarRow(idx) {
  sceneVarRows.value.splice(idx, 1);
}

async function saveSceneVars() {
  const vars = {};
  sceneVarRows.value.forEach((row) => {
    const k = String(row.key || "").trim();
    if (k) {
      vars[k] = row.value;
    }
  });
  if (!store.scene) return;
  store.scene = { ...store.scene, variables: vars };
  store.markDirty();
  sceneVarsDialogVisible.value = false;
  // 立即持久化到后端，避免用户后续执行时 DB 中还是旧变量
  try {
    await store.flushSave();
  } catch (err) {
    console.error("场景变量保存失败:", err);
  }
}

function openSceneVarPicker(idx) {
  activeSceneVarRowIdx.value = idx;
  sceneVarsPickerVisible.value = true;
}

function insertSceneVarVariable(variable) {
  const idx = activeSceneVarRowIdx.value;
  if (idx >= 0 && idx < sceneVarRows.value.length) {
    sceneVarRows.value[idx].value = `${sceneVarRows.value[idx].value || ""}${variable}`;
  }
  sceneVarsPickerVisible.value = false;
}
// --- end 场景变量编辑 ---

const tableState = shallowReactive({ list: [] });

const hasAnySyncBasic = computed(() =>
  apiDiffItems.value.some((d) => d.sync_status?.can_sync_basic)
);

const apiDiffSummary = computed(() => {
  const items = apiDiffItems.value;
  let urlChanges = 0;
  let methodChanges = 0;
  let paramsAdded = 0;
  let paramsRemoved = 0;
  let headersAdded = 0;
  let headersRemoved = 0;
  let responseFieldsAdded = 0;
  let responseFieldsRemoved = 0;
  items.forEach((d) => {
    const diffs = d.diffs || {};
    if (diffs.basic?.url?.changed) urlChanges++;
    if (diffs.basic?.method?.changed) methodChanges++;
    if (diffs.request?.params_added?.length) paramsAdded += diffs.request.params_added.length;
    if (diffs.request?.params_removed?.length) paramsRemoved += diffs.request.params_removed.length;
    if (diffs.request?.headers_added?.length) headersAdded += diffs.request.headers_added.length;
    if (diffs.request?.headers_removed?.length) headersRemoved += diffs.request.headers_removed.length;
    if (diffs.response?.fields_added?.length) responseFieldsAdded += diffs.response.fields_added.length;
    if (diffs.response?.fields_removed?.length) responseFieldsRemoved += diffs.response.fields_removed.length;
  });
  return {
    total: items.length,
    urlChanges, methodChanges, paramsAdded, paramsRemoved,
    headersAdded, headersRemoved, responseFieldsAdded, responseFieldsRemoved
  };
});

function apiDiffNodeSummary(diffItem) {
  const parts = [];
  const diffs = diffItem.diffs || {};
  if (diffs.basic?.url?.changed) parts.push("URL 变更");
  if (diffs.basic?.method?.changed) parts.push("Method 变更");
  if ((diffs.request?.params_added?.length || 0) > 0) parts.push(`新增 ${diffs.request.params_added.length} 个参数`);
  if ((diffs.request?.params_removed?.length || 0) > 0) parts.push(`删除 ${diffs.request.params_removed.length} 个参数`);
  if ((diffs.request?.headers_added?.length || 0) > 0) parts.push(`新增 ${diffs.request.headers_added.length} 个请求头`);
  if ((diffs.request?.headers_removed?.length || 0) > 0) parts.push(`删除 ${diffs.request.headers_removed.length} 个请求头`);
  if ((diffs.response?.fields_added?.length || 0) > 0) parts.push(`新增 ${diffs.response.fields_added.length} 个响应字段`);
  if ((diffs.response?.fields_removed?.length || 0) > 0) parts.push(`删除 ${diffs.response.fields_removed.length} 个响应字段`);
  return parts.join("、") || "配置差异";
}

const sceneEnvironmentId = computed({
  get: () => {
    const rc = store.scene?.runtime_config || {};
    const id = rc.environment_id;
    return id != null ? String(id) : "";
  },
  set: (val) => {
    if (!store.scene) return;
    const rc = { ...(store.scene.runtime_config || {}) };
    rc.environment_id = val ? Number(val) : null;
    store.scene = { ...store.scene, runtime_config: rc };
    store.markDirty();
  }
});

/** 将层级分组树扁平化为带缩进的选项列表 */
const groupOptions = computed(() => {
  /** 递归展平树节点 */
  function flatten(tree, depth = 0) {
    const result = [];
    (tree || []).forEach((g) => {
      const indent = '　'.repeat(depth);
      const label = indent + g.name;
      result.push({
        id: g.id,
        name: g.name,
        label,
        pathLabel: label,
        pathHtml: `<span class="text-muted">${indent}</span><span class="group-name-highlight">${g.name}</span>`
      });
      if (g.children?.length) {
        result.push(...flatten(g.children, depth + 1));
      }
    });
    return result;
  }
  return flatten(groups.value);
});

const sceneGroupId = computed({
  get: () => store.scene?.group ?? '',
  set: (val) => {
    if (!store.scene) return;
    store.scene = { ...store.scene, group: val ? Number(val) : null };
    store.markDirty();
  }
});


const variableOptions = computed(() => {
  const options = [];
  // debugtalk 函数（可在参数/请求体/请求头中使用 {{func()}}）
  (debugtalkFunctions.value || []).forEach((f) =>
    options.push({
      label: `${f.name}()${f.doc ? ` - ${f.doc}` : ""}`,
      value: `{{${f.name}()}}`,
      kindText: "debugtalk 函数"
    })
  );
  // 环境中定义的变量：选中场景专属环境时用该环境；继承全局时合并当前项目下各环境的键（便于插入 {{env.xxx}}）
  const envList = environments.value || [];
  const selectedEnv = sceneEnvironmentId.value
    ? envList.find((e) => String(e.id) === String(sceneEnvironmentId.value))
    : null;
  const envKeys = new Set();
  if (selectedEnv?.variables && typeof selectedEnv.variables === "object") {
    Object.keys(selectedEnv.variables).forEach((k) => envKeys.add(k));
  } else if (!sceneEnvironmentId.value && envList.length) {
    envList.forEach((e) => {
      if (e?.variables && typeof e.variables === "object") {
        Object.keys(e.variables).forEach((k) => envKeys.add(k));
      }
    });
  }
  envKeys.forEach((key) => {
    if (key === "__var_descriptions__") return;
    options.push({ label: `env.${key}`, value: `{{env.${key}}}`, kindText: "环境变量" });
  });
  // 场景变量（运行时在变量池顶层，直接 {{key}} 引用）
  const sceneVars = store.scene?.variables || {};
  Object.keys(sceneVars).forEach((key) =>
    options.push({ label: key, value: `{{${key}}}`, kindText: "场景变量" })
  );
  // 前置节点提取的变量
  const current = store.selectedNode;
  const currentSort = current ? Number(current.sort ?? 0) : Infinity;
  const pool = store.sceneVariablePool || {};
  const nodes = store.nodeList || [];
  nodes
    .filter((n) => Number(n.sort ?? 0) < currentSort)
    .forEach((n) => {
      const key = n.node_key || `node_${n.id}`;
      const vars = pool[key] || {};
      const nodeName = n.name || key;
      Object.keys(vars).forEach((varName) =>
        options.push({
          label: `[${nodeName}] ${varName}`,
          value: `{{${varName}}}`,
          kindText: "前置变量"
        })
      );
    });
  return options.slice(0, 300);
});

const nodeResponsePreview = computed(() => {
  const node = store.selectedNode;
  if (!node) return null;
  const r = lastExecutionNodeResults.value[node.id];
  if (r?.response?.body != null) return r.response.body;
  const schema = node.api_asset_response_schema;
  if (schema && typeof schema === "object" && Object.keys(schema).length > 0) {
    return schemaToExample(schema);
  }
  // 资产无 response_schema 时，回退到节点上存储的预期响应体（来自 HAR 导入或手动配置）
  if (node.expected_response_body) {
    return node.expected_response_body;
  }
  return null;
});

function schemaToExample(schema) {
  if (!schema || typeof schema !== "object") return null;
  if (schema.example !== undefined) return schema.example;
  if (Array.isArray(schema.examples) && schema.examples.length > 0) return schema.examples[0];
  const props = schema.properties;
  if (props && typeof props === "object") {
    const out = {};
    for (const [k, v] of Object.entries(props)) {
      if (v && typeof v === "object") {
        if (v.example !== undefined) out[k] = v.example;
        else if (Array.isArray(v.examples) && v.examples.length > 0) out[k] = v.examples[0];
        else if (v.properties && typeof v.properties === "object") out[k] = schemaToExample(v);
        else if (v.type === "array") out[k] = v.items ? [schemaToExample(v.items)] : [];
        else out[k] = defaultForType(v.type);
      }
    }
    return out;
  }
  return schema;
}

function defaultForType(t) {
  if (t === "string") return "";
  if (t === "integer" || t === "number") return 0;
  if (t === "boolean") return false;
  if (t === "array") return [];
  if (t === "object") return {};
  if (t === "null") return null;
  return null;
}

/** 扁平分组列表 → 树（与 /api/api-groups/ list 扁平响应一致） */
function buildGroupTreeFromFlat(flat) {
  const list = Array.isArray(flat) ? flat : [];
  const byId = {};
  list.forEach((g) => {
    if (!g || g.id == null) return;
    byId[g.id] = { ...g, children: [] };
  });
  const roots = [];
  list.forEach((g) => {
    if (!g || g.id == null) return;
    const node = byId[g.id];
    const pid = g.parent;
    if (pid == null || pid === undefined || pid === "") {
      roots.push(node);
    } else {
      const p = byId[pid];
      if (p) p.children.push(node);
      else roots.push(node);
    }
  });
  function sortRec(nodes) {
    nodes.sort(
      (a, b) =>
        (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0) || Number(a.id) - Number(b.id)
    );
    nodes.forEach((n) => n.children && n.children.length && sortRec(n.children));
  }
  sortRec(roots);
  return roots;
}

const pagedNodes = computed(() => {
  const start = (pageNum.value - 1) * pageSize;
  return tableState.list.slice(start, start + pageSize);
});

const assetTreeData = computed(() => {
  const kw = assetSearchKeyword.value.toLowerCase().trim();
  const filteredAssets = (assets.value || []).filter(
    (a) => !kw || (a.name || "").toLowerCase().includes(kw)
  );

  function buildGroupNode(group) {
    const groupAssets = filteredAssets.filter((a) => a.group === group.id);
    const apiNodes = groupAssets.map((a) => ({
      key: `a-${a.id}`,
      label: a.name,
      isApi: true,
      apiId: a.id
    }));
    const childGroups = (group.children || []).map((child) => buildGroupNode(child)).filter((node) => node != null);
    const allChildren = [...childGroups, ...apiNodes];
    // 搜索时去掉不含匹配接口的分支，只保留通向命中接口的分组路径
    if (kw && allChildren.length === 0) {
      return null;
    }
    return {
      key: `g-${group.id}`,
      label: group.name,
      children: allChildren
    };
  }

  const groupTrees = (groups.value || []).map((g) => buildGroupNode(g)).filter((node) => node != null);
  const root = {
    key: "root",
    label: "未分组",
    children: filteredAssets
      .filter((a) => !a.group)
      .map((a) => ({ key: `a-${a.id}`, label: a.name, isApi: true, apiId: a.id }))
  };
  return [...groupTrees, root].filter((item) => item.children.length > 0);
});

const assetDefaultExpandedKeys = computed(() => {
  const kw = assetSearchKeyword.value.toLowerCase().trim();
  const data = assetTreeData.value;
  if (!data.length) return [];
  if (!kw) {
    // 无搜索：仅展开第一层分组节点
    return data.map((n) => n.key).filter(Boolean);
  }
  // 有搜索：展开所有包含匹配接口的分支
  const keys = [];
  function collectAncestors(nodes, ancestors) {
    nodes.forEach((n) => {
      const hasMatch = n.isApi
        ? (n.label || "").toLowerCase().includes(kw)
        : n.children?.some((c) => subtreeHasMatch(c, kw));
      if (hasMatch && ancestors.length) {
        ancestors.forEach((a) => keys.push(a));
      }
      const nextAncestors = [...ancestors, n.key];
      if (n.children?.length) collectAncestors(n.children, nextAncestors);
    });
  }
  function subtreeHasMatch(node, kw) {
    if (node.isApi) return (node.label || "").toLowerCase().includes(kw);
    return node.children?.some((c) => subtreeHasMatch(c, kw)) || false;
  }
  collectAncestors(data, []);
  return [...new Set(keys)];
});

watch(
  () => store.nodeList,
  (list) => {
    try {
      const arr = list || [];
      tableState.list = arr.map((node) => ({
        id: node.id,
        sort: Number(node.sort || 0),
        method: node.method || node.api_asset_method || "API",
        name: node.name || "",
        isEnabled: node.is_enabled !== false
      }));
      if ((pageNum.value - 1) * pageSize >= tableState.list.length) {
        pageNum.value = 1;
      }
      nextTick(() => initTableSortable());
    } catch (err) {
      console.error("nodeList watch error:", err);
    }
  },
  { immediate: true, deep: true }
);

watch(assetSearchInput, (val) => {
  clearTimeout(assetSearchTimer);
  assetSearchTimer = setTimeout(() => {
    assetSearchKeyword.value = val;
  }, 300);
});
function buildNodePayload(node) {
  try {
    const apiAssetId =
      node.api_asset != null && typeof node.api_asset === "object" && "id" in node.api_asset
        ? node.api_asset.id
        : node.api_asset;
    const envId = node.environment_id ?? (node.environment?.id ?? node.environment ?? null);
    const environmentId = envId === "" || envId == null ? null : Number(envId);
    return {
      scene: store.currentSceneId,
      api_asset: apiAssetId,
      node_key: node.node_key,
      name: node.name || "",
      description: node.description || "",
      request_headers: cloneJson(node.request_headers, {}),
      request_params: cloneJson(node.request_params, {}),
      request_body: cloneJson(node.request_body, {}),
      param_type: node.param_type || "json",
      body_type: node.body_type || "json",
      assert_rules: cloneJson(node.assert_rules, []),
      extract_rules: cloneJson(node.extract_rules, []),
      expected_status_code: Number(node.expected_status_code || 200),
      timeout: Number(node.timeout || 30),
      on_failed: node.on_failed || "continue",
      sort: Number(node.sort ?? 0),
      is_enabled: node.is_enabled !== false,
      environment_id: isNaN(environmentId) ? null : environmentId,
      custom_base_url: node.custom_base_url || "",
      request_url: node.request_url || "",
      pre_request_script: node.pre_request_script || "",
      script_timeout: node.script_timeout ?? 1000
    };
  } catch (err) {
    console.error("buildNodePayload error:", err);
    throw err;
  }
}

function markNodeLoading(nodeId, type) {
  const next = new Map(nodeLoadingMap.value);
  next.set(nodeId, type);
  nodeLoadingMap.value = next;
}

function clearNodeLoading(nodeId) {
  const next = new Map(nodeLoadingMap.value);
  next.delete(nodeId);
  nodeLoadingMap.value = next;
}

async function loadDesignerData() {
  initLoading.value = true;
  initError.value = "";
  let payload = null;
  try {
    payload = await fetchSceneDesignerInit(route.params.id);
    store.currentSceneId = Number(payload?.scene?.id || route.params.id);
    store.scene = payload?.scene || {};
    store.setNodeList(payload?.nodes || []);
    store.setSelectedNodeId((payload?.nodes || [])[0]?.id || null);
    store.buildVariableTree();
    assets.value = payload?.api_assets || [];
    environments.value = payload?.environments || [];
    debugtalkFunctions.value = payload?.debugtalk_functions || [];
    // 分组信息与 API 资产管理使用相同接口，保证层级一致
    // fetchApiGroups 与 fetchSceneExecutions 无依赖，并行请求
    const projectId = payload?.scene?.project;
    if (projectId) {
      await Promise.all([
        fetchApiGroups(projectId).then(groupsData => {
          const rawGroups = groupsData?.results ?? groupsData ?? [];
          const flat = Array.isArray(rawGroups) ? rawGroups : [];
          groups.value = buildGroupTreeFromFlat(flat);
        }).catch(e => {
          console.warn("加载分组失败，使用空分组", e);
          groups.value = [];
        }),
        fetchSceneExecutions(store.currentSceneId, {page_size: 1}).then(execs => {
          const latest = Array.isArray(execs) ? execs[0] : execs?.results?.[0];
          const results = latest?.node_results || [];
          const map = {};
          results.forEach((r) => {
            if (r?.node_id != null) map[r.node_id] = r;
          });
          lastExecutionNodeResults.value = map;
        }).catch(() => {
          lastExecutionNodeResults.value = {};
        })
      ]);
    } else {
      groups.value = [];
      try {
        const execs = await fetchSceneExecutions(store.currentSceneId);
        const latest = Array.isArray(execs) ? execs[0] : execs?.results?.[0];
        const results = latest?.node_results || [];
        const map = {};
        results.forEach((r) => {
          if (r?.node_id != null) map[r.node_id] = r;
        });
        lastExecutionNodeResults.value = map;
      } catch {
        lastExecutionNodeResults.value = {};
      }
    }
  } catch (error) {
    initError.value = error?.message || "初始化失败";
  } finally {
    initLoading.value = false;
  }
  // 优先用 scene.api_updated_node_ids（与列表页一致），否则用 nodes 中的 api_updated
  const sceneApiUpdated = payload?.scene?.api_updated;
  const nodeIdsFromScene = payload?.scene?.api_updated_node_ids || [];
  let apiUpdatedNodes = (payload?.nodes || []).filter((n) => n.api_updated);
  if (apiUpdatedNodes.length === 0 && nodeIdsFromScene.length > 0) {
    apiUpdatedNodes = nodeIdsFromScene
      .map((id) => (payload?.nodes || []).find((n) => n.id === id))
      .filter(Boolean);
  }
  // 过滤 7 天内已选择「不再提示」的接口
  apiUpdatedNodes = apiUpdatedNodes.filter((n) => {
    const assetId = n.api_asset ?? n.api ?? n.api_asset_id;
    return !isApiAssetDismissed7d(assetId);
  });
  if ((sceneApiUpdated || apiUpdatedNodes.length > 0) && !apiDiffDontShowAgain.value && apiUpdatedNodes.length > 0) {
    openApiDiffDialog(apiUpdatedNodes);
  }
}

function hasVisibleDiffContent(diffItem) {
  const d = diffItem?.diffs;
  if (!d) return false;
  const basic = d.basic;
  const req = d.request;
  const res = d.response;
  return (
    (basic?.url?.changed) ||
    (basic?.method?.changed) ||
    (req?.params_added?.length > 0) ||
    (req?.params_removed?.length > 0) ||
    (req?.headers_added?.length > 0) ||
    (req?.headers_removed?.length > 0) ||
    (req?.headers_value_changed?.length > 0) ||
    (req?.body_format_changed) ||
    (res?.fields_added?.length > 0) ||
    (res?.fields_removed?.length > 0) ||
    (res?.warnings?.length > 0) ||
    (diffItem.sync_status?.can_sync_params) ||
    (diffItem.sync_status?.can_sync_headers)
  );
}

async function openApiDiffDialog(apiUpdatedNodes) {
  apiDiffLoading.value = true;
  apiDiffItems.value = [];
  try {
    const results = await Promise.all(
      apiUpdatedNodes.map((n) =>
        fetchNodeApiDiff(n.id).then((d) => ({ ...d, node_id: n.id })).catch(() => null)
      )
    );
    // 仅展示有实际差异的节点（has_diff 为 true 或未返回）；无差异（has_diff 明确为 false）时不弹窗
    const withDiff = results.filter(Boolean).filter((r) => r.has_diff !== false);
    // 过滤出有可展示内容的节点，避免空弹窗
    apiDiffItems.value = withDiff.filter((r) => hasVisibleDiffContent(r));
    if (apiDiffItems.value.length > 0) {
      apiDiffActiveNames.value = [String(apiDiffItems.value[0].node_id)];
      apiDiffDialogVisible.value = true;
    }
  } catch (e) {
    console.warn("加载API差异失败", e);
  } finally {
    apiDiffLoading.value = false;
  }
}

async function doSyncBasic(nodeId) {
  apiDiffSyncingMap.value = new Set([...apiDiffSyncingMap.value, nodeId]);
  try {
    await syncNodeBasic(nodeId);
    ElMessage.success("基础信息已同步");
    const idx = apiDiffItems.value.findIndex((d) => d.node_id === nodeId);
    if (idx >= 0) {
      const updated = await fetchNodeApiDiff(nodeId);
      apiDiffItems.value = [...apiDiffItems.value];
      apiDiffItems.value[idx] = { ...updated, node_id: nodeId };
    }
    store.upsertNode(
      { ...store.nodeList.find((n) => n.id === nodeId), api_synced_at: new Date().toISOString() },
      false
    );
  } catch (e) {
    ElMessage.error(e?.message || "同步失败");
  } finally {
    const next = new Set(apiDiffSyncingMap.value);
    next.delete(nodeId);
    apiDiffSyncingMap.value = next;
  }
}

async function doSyncHeaders(nodeId) {
  const key = `headers-full-${nodeId}`;
  apiDiffSyncingMap.value = new Set([...apiDiffSyncingMap.value, key]);
  try {
    const res = await syncNodeHeaders(nodeId);
    const resNodeId = res?.node_id ?? nodeId;
    if (resNodeId !== nodeId) return;
    ElMessage.success("请求头已同步");
    const idx = apiDiffItems.value.findIndex((d) => d.node_id === nodeId);
    if (idx >= 0) {
      const updated = await fetchNodeApiDiff(nodeId);
      apiDiffItems.value = [...apiDiffItems.value];
      apiDiffItems.value[idx] = { ...updated, node_id: nodeId };
    }
    if (res?.request_headers != null) {
      store.updateNodeLocal(nodeId, {
        request_headers: res.request_headers,
        api_synced_at: new Date().toISOString()
      }, false);
    }
  } catch (e) {
    ElMessage.error(e?.message || "同步失败");
  } finally {
    const next = new Set(apiDiffSyncingMap.value);
    next.delete(key);
    apiDiffSyncingMap.value = next;
  }
}

async function doSyncParams(nodeId) {
  const key = `params-full-${nodeId}`;
  apiDiffSyncingMap.value = new Set([...apiDiffSyncingMap.value, key]);
  try {
    const res = await syncNodeParams(nodeId);
    const resNodeId = res?.node_id ?? nodeId;
    if (resNodeId !== nodeId) return;
    ElMessage.success("请求参数已同步");
    const idx = apiDiffItems.value.findIndex((d) => d.node_id === nodeId);
    if (idx >= 0) {
      const updated = await fetchNodeApiDiff(nodeId);
      apiDiffItems.value = [...apiDiffItems.value];
      apiDiffItems.value[idx] = { ...updated, node_id: nodeId };
    }
    if (res?.request_params != null) {
      store.updateNodeLocal(nodeId, {
        request_params: res.request_params,
        api_synced_at: new Date().toISOString()
      }, false);
    }
  } catch (e) {
    ElMessage.error(e?.message || "同步失败");
  } finally {
    const next = new Set(apiDiffSyncingMap.value);
    next.delete(key);
    apiDiffSyncingMap.value = next;
  }
}

async function doSyncAddParams(nodeId, paramKeys, scope) {
  if (!paramKeys?.length) return;
  const key = `${scope.replace("request_", "")}-${nodeId}`;
  apiDiffSyncingMap.value = new Set([...apiDiffSyncingMap.value, key]);
  try {
    const res = await syncNodeAddParams(nodeId, { param_keys: paramKeys, scope });
    const resNodeId = res?.node_id ?? nodeId;
    if (resNodeId !== nodeId) return;
    ElMessage.success("已新增空参数到节点");
    const idx = apiDiffItems.value.findIndex((d) => d.node_id === nodeId);
    if (idx >= 0) {
      const updated = await fetchNodeApiDiff(nodeId);
      apiDiffItems.value = [...apiDiffItems.value];
      apiDiffItems.value[idx] = { ...updated, node_id: nodeId };
    }
    const patch = {};
    if (res?.request_params != null) patch.request_params = res.request_params;
    if (res?.request_headers != null) patch.request_headers = res.request_headers;
    if (res?.request_body != null) patch.request_body = res.request_body;
    if (Object.keys(patch).length > 0) {
      store.updateNodeLocal(nodeId, patch, false);
    }
  } catch (e) {
    ElMessage.error(e?.message || "同步失败");
  } finally {
    const next = new Set(apiDiffSyncingMap.value);
    next.delete(key);
    apiDiffSyncingMap.value = next;
  }
}

function goToNodeConfig(nodeId) {
  apiDiffDialogVisible.value = false;
  selectNode(nodeId);
}

function onApiDiffDialogClose() {
  if (apiDiffDismiss7d.value && apiDiffItems.value.length > 0) {
    const assetIds = apiDiffItems.value.map((d) => d.api_asset_id).filter(Boolean);
    dismissApiAssets7d(assetIds);
  }
  apiDiffDismiss7d.value = false;
}

async function doSyncAll() {
  const toSync = apiDiffItems.value.filter((d) => d.sync_status?.can_sync_basic);
  if (!toSync.length) return;
  apiDiffSyncingMap.value = new Set(['__all__']);
  try {
    const res = await syncAllSceneNodes(sceneId.value);
    const count = res?.synced_count ?? 0;
    ElMessage.success(`已同步 ${count} 个节点`);
    // 刷新所有 diff 项
    const refreshed = await Promise.all(
      apiDiffItems.value.map((d) => fetchNodeApiDiff(d.node_id).catch(() => null))
    );
    apiDiffItems.value = apiDiffItems.value
      .map((item, i) => {
        if (refreshed[i]) return { ...refreshed[i], node_id: item.node_id };
        return item;
      })
      .filter((d) => hasVisibleDiffContent(d));
    // 更新 store 中所有已同步节点的 api_synced_at
    if (res?.nodes) {
      for (const nr of res.nodes) {
        store.upsertNode(
          { ...store.nodeList.find((n) => n.id === nr.node_id), api_synced_at: new Date().toISOString() },
          false
        );
      }
    }
    // 全部同步完成则关闭弹窗
    if (apiDiffItems.value.length === 0) {
      apiDiffDialogVisible.value = false;
    }
  } catch (e) {
    ElMessage.error(e?.message || "批量同步失败");
  } finally {
    apiDiffSyncingMap.value = new Set();
  }
}

function goList() {
  const query = { _refresh: Date.now() };
  if (route.query.env_id) query.env_id = route.query.env_id;
  if (route.query.project_id) query.project_id = route.query.project_id;
  router.push({ name: "scene-list", query });
}

async function saveNow() {
  try {
    // 先保存当前节点配置（如果有未保存的修改）
    if (nodeConfigDirty.value && configPanelRef.value?.getPayload) {
      const payload = configPanelRef.value.getPayload();
      if (!payload) {
        ElMessage.error("节点配置存在格式错误，请检查后重试");
        return;
      }
      const ok = await saveNodeConfig(payload);
      if (ok) {
        nodeConfigDirty.value = false;
      }
    }
    await store.flushSave();
    lastSavedAt.value = new Date().toLocaleTimeString();
    ElMessage.success("保存成功");
  } catch (error) {
    console.error("保存失败:", error);
    ElMessage.error(error?.message || "保存失败");
  }
}

function onRowClick({ row }) {
  if (row?.id) {
    selectNode(row.id);
  }
}

async function selectNode(nodeId) {
  if (nodeId === store.selectedNodeId) {
    return;
  }
  if (nodeConfigDirty.value) {
    try {
      await ElMessageBox.confirm("当前配置未保存，是否保存后切换？", "提示", {
        confirmButtonText: "保存",
        cancelButtonText: "不保存",
        distinguishCancelAndClose: true,
        type: "warning"
      });
    } catch (action) {
      if (action === "cancel") {
        nodeConfigDirty.value = false;
        doSwitchNode(nodeId);
        return;
      }
      return;
    }
    const payload = configPanelRef.value?.getPayload?.();
    if (!payload) {
      ElMessage.error("配置无效，无法保存");
      return;
    }
    configPanelLoading.value = true;
    try {
      const ok = await saveNodeConfig(payload);
      if (!ok) {
        ElMessage.error("保存失败，终止切换");
        return;
      }
      nodeConfigDirty.value = false;
      doSwitchNode(nodeId);
    } finally {
      configPanelLoading.value = false;
    }
    return;
  }
  doSwitchNode(nodeId);
}

function doSwitchNode(nodeId) {
  configPanelLoading.value = true;
  store.setSelectedNodeId(nodeId);
  nextTick(() => {
    configPanelLoading.value = false;
  });
}

function openAddDialog() {
  pendingApiId.value = null;
  assetSearchInput.value = "";
  assetSearchKeyword.value = "";
  addDialogVisible.value = true;
}

function onAssetTreeNodeClick(node) {
  pendingApiId.value = node?.isApi ? Number(node.apiId) : null;
}

async function confirmAddApi() {
  if (!pendingApiId.value || addingNode.value) {
    return;
  }
  const cacheKey = `${store.currentSceneId}:${pendingApiId.value}`;
  if (creatingNodePromiseCache.has(cacheKey)) {
    return;
  }
  addingNode.value = true;
  const beforeNodes = [...store.nodeList];
  const createPromise = createSceneNode({
    scene: store.currentSceneId,
    api_asset: pendingApiId.value
  });
  creatingNodePromiseCache.set(cacheKey, createPromise);
  try {
    const created = await createPromise;
    store.upsertNode(created, false);
    addDialogVisible.value = false;
    ElMessage.success("节点添加成功");
    await selectNode(created.id);
  } catch (error) {
    // 创建失败时保持本地状态不变，避免脏状态。
    store.setNodeList(beforeNodes);
    console.error("添加节点失败:", error);
    ElMessage.error(error?.message || "添加接口失败");
  } finally {
    creatingNodePromiseCache.delete(cacheKey);
    addingNode.value = false;
  }
}

async function deleteNode(nodeId) {
  markNodeLoading(nodeId, "delete");
  try {
    await deleteSceneNode(nodeId);
    store.removeNode(nodeId, false);
    ElMessage.success("节点已删除");
  } catch (error) {
    console.error("删除节点失败:", error);
    ElMessage.error(error?.message || "删除节点失败");
  } finally {
    clearNodeLoading(nodeId);
  }
}

async function toggleNodeEnabled(nodeId, enabled) {
  if (nodeLoadingMap.value.has(nodeId)) {
    return;
  }
  const node = store.nodeList.find((item) => item.id === nodeId);
  if (!node) {
    return;
  }
  const boolEnabled = Boolean(enabled);
  const oldEnabled = node.is_enabled !== false;
  markNodeLoading(nodeId, "toggle");
  store.updateNodeLocal(nodeId, { is_enabled: boolEnabled }, false);
  try {
    const saved = await updateSceneNode(node.id, { ...buildNodePayload(node), is_enabled: boolEnabled });
    store.upsertNode(saved, false);
    ElMessage.success(boolEnabled ? "节点已启用" : "节点已禁用");
  } catch (error) {
    store.updateNodeLocal(nodeId, { is_enabled: oldEnabled }, false);
    console.error("更新启用状态失败:", error);
    ElMessage.error(error?.message || "更新失败");
  } finally {
    clearNodeLoading(nodeId);
  }
}

async function saveNodeConfig(node) {
  if (savingNodeConfig.value) {
    return false;
  }
  if (!node?.id) {
    ElMessage.error("节点 ID 无效，请先保存场景或刷新页面后重试");
    return false;
  }
  savingNodeConfig.value = true;
  try {
    const payload = buildNodePayload(node);
    if (payload.assert_rules && !Array.isArray(payload.assert_rules)) {
      ElMessage.error("断言规则格式错误");
      return false;
    }
    const saved = await updateSceneNode(node.id, payload);
    if (saved?.id) {
      store.upsertNode(saved, false);
      ElMessage.success("节点保存成功");
      return true;
    }
    return false;
  } catch (error) {
    console.error("保存节点配置失败:", error);
    ElMessage.error(error?.message || "节点保存失败");
    return false;
  } finally {
    savingNodeConfig.value = false;
  }
}

function initTableSortable() {
  if (sortableInstance) {
    sortableInstance.destroy();
    sortableInstance = null;
  }
  nextTick(() => {
    const tableEl = nodeTableRef.value?.$el;
    const tbody = tableEl?.querySelector(".el-table__body-wrapper tbody");
    if (!tbody || !tableState.list.length) return;
    sortableInstance = Sortable.create(tbody, {
      handle: ".node-drag-handle",
      animation: 150,
      ghostClass: "sortable-ghost",
      onEnd: handleDragEnd
    });
  });
}

async function handleDragEnd(evt) {
  const { oldIndex, newIndex } = evt;
  if (oldIndex === newIndex) return;
  const start = (pageNum.value - 1) * pageSize;
  const fullList = [...store.nodeList];
  const pageStart = start;
  const pageEnd = Math.min(start + pageSize, fullList.length);
  const pageNodes = fullList.slice(pageStart, pageEnd);
  const [moved] = pageNodes.splice(oldIndex, 1);
  pageNodes.splice(newIndex, 0, moved);
  const newFullList = [...fullList.slice(0, pageStart), ...pageNodes, ...fullList.slice(pageEnd)];
  // 创建新对象（不原地修改），确保 Vue 响应式触发 watch 更新 localNode.sort
  const updatedList = newFullList.map((node, idx) => ({ ...node, sort: idx }));
  const orderedIds = updatedList.map((n) => n.id);
  const beforeList = [...store.nodeList];
  store.setNodeList(updatedList);
  try {
    await reorderSceneNodes(store.currentSceneId, orderedIds);
    ElMessage.success("顺序已更新");
  } catch (err) {
    store.setNodeList(beforeList);
    console.error("排序更新失败:", err);
    ElMessage.error(err?.message || "排序更新失败");
  }
}

function handleKeydown(e) {
  // 不在输入框/文本域/可编辑元素中触发快捷键
  const tag = (e.target?.tagName || "").toLowerCase();
  const isEditable = tag === "input" || tag === "textarea" || tag === "select" || e.target?.isContentEditable;
  if (isEditable) return;

  // Ctrl+S / Cmd+S：保存
  if ((e.ctrlKey || e.metaKey) && e.key === "s") {
    e.preventDefault();
    saveNow();
    return;
  }
  // Ctrl+N / Cmd+N：添加接口
  if ((e.ctrlKey || e.metaKey) && e.key === "n") {
    e.preventDefault();
    openAddDialog();
    return;
  }

  const nodeIds = (store.nodeList || []).map((n) => n.id);
  const currentIdx = nodeIds.indexOf(store.selectedNodeId);

  // 上箭头：选择上一个节点
  if (e.key === "ArrowUp") {
    e.preventDefault();
    if (currentIdx > 0) selectNode(nodeIds[currentIdx - 1]);
    return;
  }
  // 下箭头：选择下一个节点
  if (e.key === "ArrowDown") {
    e.preventDefault();
    if (currentIdx < nodeIds.length - 1) selectNode(nodeIds[currentIdx + 1]);
    return;
  }
  // Delete：删除选中节点
  if (e.key === "Delete" && store.selectedNodeId != null) {
    e.preventDefault();
    ElMessageBox.confirm("确定删除该节点？", "删除节点", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning"
    }).then(() => {
      deleteNode(store.selectedNodeId);
    }).catch(() => {});
    return;
  }
}

onMounted(async () => {
  store.attachBeforeUnloadGuard();
  await loadDesignerData();
  initTableSortable();
  document.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  if (sortableInstance) {
    sortableInstance.destroy();
    sortableInstance = null;
  }
  store.detachBeforeUnloadGuard();
  creatingNodePromiseCache.clear();
  clearTimeout(assetSearchTimer);
  document.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.designer-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.designer-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(420px, 44%) minmax(0, 1fr);
  gap: 12px;
  align-items: stretch;
}

.center-panel,
.right-panel {
  min-height: 0;
}

.center-panel {
  display: flex;
  flex-direction: column;
}

.right-panel {
  width: auto;
  max-width: none;
}

@media (max-width: 1360px) {
  .designer-grid {
    grid-template-columns: minmax(360px, 48%) minmax(0, 1fr);
  }
}

@media (max-width: 1100px) {
  .designer-grid {
    grid-template-columns: 1fr;
  }
}

.asset-dialog-scroll {
  max-height: 56vh;
  overflow-y: auto;
}

.asset-dialog-tree {
  min-height: 220px;
}

.config-panel-loading {
  padding: 16px;
  min-height: 200px;
}

:deep(.el-table__row) {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

:deep(.el-table__row:hover) {
  background-color: #e8f0fe !important;
}

:deep(.el-table__row.current-row) {
  background-color: #f0f7ff !important;
}

:deep(.el-table__row.current-row td:first-child) {
  border-left: 4px solid #409eff;
}

:deep(.el-table__row.current-row:hover) {
  background-color: #e6f0ff !important;
}

.node-unsaved-mark {
  color: #e6a23c;
  font-weight: bold;
  margin-left: 4px;
}

.scene-env-select {
  min-width: 140px;
}

.node-drag-handle {
  cursor: grab;
  font-size: 14px;
}

.node-drag-handle:active {
  cursor: grabbing;
}

:deep(.sortable-ghost) {
  opacity: 0.5;
  background-color: #f0f7ff;
}

:deep(.drag-handle-cell) {
  padding: 8px 4px !important;
}

.api-diff-dialog-content {
  max-height: 460px;
  overflow-y: auto;
}

.api-diff-summary {
  padding: 10px 12px;
  background: var(--el-color-info-light-9);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
}

.api-diff-collapse-title {
  display: flex;
  align-items: center;
  width: 100%;
}

.api-diff-collapse-summary {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.api-diff-node-block {
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.api-diff-highlight {
  color: var(--el-color-danger);
  font-weight: 500;
}

.group-option-item {
  font-size: 13px;
}
.group-option-item .group-name-highlight {
  font-weight: 500;
  color: #303133;
}
.method-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  letter-spacing: 0.3px;
}
.method-get { background: #e8f5e9; color: #2e7d32; }
.method-post { background: #e3f2fd; color: #1565c0; }
.method-put { background: #fff3e0; color: #e65100; }
.method-delete { background: #fce4ec; color: #c62828; }
.method-patch { background: #e0f7fa; color: #00695c; }
.method-head { background: #f3e5f5; color: #7b1fa2; }
.method-options { background: #efebe9; color: #4e342e; }
</style>


