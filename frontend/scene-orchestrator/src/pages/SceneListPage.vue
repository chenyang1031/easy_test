<template>
  <div class="scene-list-page">
    <!-- ====== 页面标题 ====== -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">测试场景编排</h2>
        <span class="page-subtitle">管理和编排测试场景，支持节点配置、执行和日志查看</span>
      </div>
      <div class="page-header-right">
        <el-button type="primary" size="default" :disabled="projects.length === 0" @click="createNewScene">
          <el-icon><Plus /></el-icon> 新增场景
        </el-button>
      </div>
    </div>

    <div class="panel-card">
      <div v-if="projectsLoading" class="alert alert-light border py-2 mb-2 d-flex align-items-center gap-2">
        <span class="spinner-border spinner-border-sm text-primary" role="status" aria-hidden="true" />
        <span class="text-muted small">正在加载项目与环境、场景列表…</span>
      </div>
      <div class="alert alert-warning py-2 mb-2" v-else-if="projects.length === 0">
        未拉取到可用项目，请先在"项目管理"创建项目，或检查当前账号权限。
      </div>

      <!-- 顶部区域：筛选区 + 操作按钮 -->
      <div class="top-bar">
      <div class="filter-area">
        <div class="filter-row">
          <div class="filter-item">
            <label class="filter-label">当前项目</label>
            <el-select
              v-model="selectedPlatformProjectId"
              placeholder="选择项目"
              size="small"
              class="filter-control"
              @change="reloadByProject"
            >
              <el-option label="选择项目" value="" />
              <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="String(project.id)" />
            </el-select>
          </div>
          <div class="filter-item">
            <label class="filter-label">运行环境</label>
            <el-select
              v-model="selectedEnvironmentId"
              placeholder="请选择运行环境"
              size="small"
              class="filter-control"
              :disabled="!selectedPlatformProjectId"
              @change="onEnvironmentChange"
            >
              <el-option label="请选择运行环境" value="" />
              <el-option
                v-for="env in environments"
                :key="env.id"
                :label="env.name"
                :value="String(env.id)"
              >
                <div class="env-option">
                  <span>{{ env.name }}</span>
                  <el-tooltip placement="left" :show-after="200">
                    <template #content>
                      <div class="env-tooltip">
                        <div><strong>域名：</strong>{{ env.base_url || '-' }}</div>
                        <div v-if="envVariablesPreview(env)"><strong>变量：</strong>{{ envVariablesPreview(env) }}</div>
                      </div>
                    </template>
                    <span class="env-option-hint text-muted ms-1">ⓘ</span>
                  </el-tooltip>
                </div>
              </el-option>
            </el-select>
            <div v-if="selectedPlatformProjectId && !environments.length && !envLoading" class="env-empty-hint">
              <span class="text-muted small">请先在</span>
              <a :href="envListUrl" target="_blank" class="small">「环境」页面</a>
              <span class="text-muted small">创建环境配置</span>
            </div>
          </div>
          <div class="filter-item filter-item--search">
            <label class="filter-label filter-label--short">搜索</label>
            <input v-model="keyword" class="form-control form-control-sm filter-control" placeholder="搜索场景名称" @input="queryScenes" />
          </div>
          <div class="filter-item">
            <label class="filter-label filter-label--short">状态</label>
            <el-select
              v-model="activeFilter"
              placeholder="全部状态"
              size="small"
              class="filter-control"
              @change="queryScenes"
            >
              <el-option label="全部状态" value="" />
              <el-option label="启用" value="1" />
              <el-option label="禁用" value="0" />
            </el-select>
          </div>
          <div class="filter-item">
            <label class="filter-label filter-label--short">分组</label>
            <el-select
              v-model="groupFilter"
              placeholder="全部场景"
              size="small"
              class="filter-control"
              clearable
              filterable
              :disabled="!selectedApiProjectId"
              @change="queryScenes"
            >
              <el-option label="全部场景" value="" />
              <el-option
                v-for="g in sceneGroupOptions"
                :key="g.id"
                :label="g.pathLabel"
                :value="String(g.id)"
              >
                <span class="group-path-option">
                  <i class="bi bi-folder me-1 text-primary"></i>
                  <span v-html="g.pathHtml"></span>
                </span>
              </el-option>
            </el-select>
          </div>
          <div class="filter-item">
            <label class="filter-label filter-label--short">分类</label>
            <el-select v-model="categoryFilter" placeholder="全部分类" size="small" class="filter-control" clearable @change="queryScenes">
              <el-option label="全部分类" value="" />
              <el-option label="留痕版" value="traced" />
              <el-option label="不留痕版" value="untraced" />
            </el-select>
          </div>
          <div class="filter-item">
            <label class="filter-label">执行状态</label>
            <el-select v-model="execStatusFilter" placeholder="全部状态" size="small" class="filter-control" clearable @change="queryScenes">
              <el-option label="全部状态" value="" />
              <el-option label="执行中" value="running" />
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
              <el-option label="部分成功" value="partial_success" />
              <el-option label="从未执行" value="never" />
            </el-select>
          </div>
        </div>
      </div>
      <div class="toolbar-actions">
        <el-tooltip :content="batchExecuteTooltip" placement="top" :disabled="!batchExecuteTooltip">
          <span class="d-inline-block">
            <button
              class="btn btn-sm btn-primary"
              :disabled="!canBatchExecute"
              @click="openBatchExecuteConfirm"
            >
              {{ selectedIds.length ? `批量执行 (${selectedIds.length})` : "批量执行" }}
            </button>
          </span>
        </el-tooltip>
        <button
          class="btn btn-sm btn-outline-danger"
          :disabled="!selectedIds.length || batchDeleteLoading"
          @click="openBatchDeleteConfirm"
        >
          {{ batchDeleteLoading ? "删除中..." : selectedIds.length ? `批量删除 (${selectedIds.length})` : "批量删除" }}
        </button>
        <button class="btn btn-sm btn-outline-secondary me-1" :disabled="!selectedApiProjectId" @click="replayImportVisible = true">
          回放导入
        </button>
        <button class="btn btn-sm btn-outline-secondary me-1" :disabled="!selectedApiProjectId" @click="sceneExportImportVisible = true">
          导出/导入
        </button>
        <span v-if="batchRunning" class="batch-progress ms-2">
          <span class="spinner-border spinner-border-sm text-primary me-1" role="status" />
          {{ batchProgress.completed }}/{{ batchProgress.total }}
        </span>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-responsive mt-3">
      <table class="table table-hover">
        <thead>
          <tr>
            <th style="width: 40px">
              <input
                type="checkbox"
                :checked="isAllSelected"
                :indeterminate="isIndeterminate"
                @change="toggleSelectAll"
              />
            </th>
            <th>名称</th>
            <th>分类</th>
            <th>分组</th>
            <th>描述</th>
            <th>节点数</th>
            <th>最近执行状态</th>
            <th>更新时间</th>
            <th class="text-end">操作</th>
          </tr>
        </thead>
        <tbody>
          <!-- 空状态 -->
          <tr v-if="!sceneRows.length && !loading">
            <td colspan="9" class="empty-state-cell">
              <div class="empty-state">
                <p class="text-muted mb-2">暂无测试场景，点击右上角「新增场景」开始创建</p>
                <button class="btn btn-sm btn-primary" :disabled="projects.length === 0" @click="createNewScene">
                  新增场景
                </button>
              </div>
            </td>
          </tr>
          <tr
            v-for="item in sceneRows"
            :key="item.id"
            :class="{ 'table-secondary': rowRunningMap.has(item.id) }"
          >
            <td>
              <input
                type="checkbox"
                :checked="selectedIds.includes(item.id)"
                :disabled="rowRunningMap.has(item.id)"
                @change="toggleSelect(item.id)"
              />
            </td>
            <td>
              <span v-if="rowRunningMap.has(item.id)" class="spinner-border spinner-border-sm text-primary me-1" role="status" />
              <el-tooltip :content="item.name || ''" placement="top" :show-after="150" :disabled="!(item.name && item.name.length > 20)">
                <span class="text-truncate-20">{{ item.name || '' }}</span>
              </el-tooltip>
              <el-tag v-if="item.api_updated" type="warning" size="small" class="ms-1 api-updated-tag">
                关联API已更新{{ (item.api_updated_node_count ?? 0) > 0 ? `(${item.api_updated_node_count})` : '' }}
              </el-tag>
            </td>
            <td>
              <el-tag v-if="item.category === 'traced'" type="primary" size="small">留痕版</el-tag>
              <el-tag v-else-if="item.category === 'untraced'" type="info" size="small">不留痕版</el-tag>
              <span v-else class="text-muted">-</span>
            </td>
            <td>
              <span v-if="item.group_name" class="group-tag">
                <i class="bi bi-folder2 me-1"></i>{{ item.group_name }}
              </span>
              <span v-else class="text-muted">-</span>
            </td>
            <td class="desc">
              <el-tooltip :content="item.description || '-'" placement="top" :show-after="150" :disabled="!(item.description && item.description.length > 20)">
                <span class="text-truncate-20">{{ item.description || "-" }}</span>
              </el-tooltip>
            </td>
            <td>
              <template v-if="item.node_count">
                <el-popover placement="bottom-start" :width="280" trigger="click">
                  <template #reference>
                    <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none node-count-btn" @click="openNodePopover(item)">
                      {{ item.node_count }}
                    </button>
                  </template>
                  <div v-if="nodePopoverSceneId === item.id" class="node-popover-content">
                    <div v-if="nodePopoverLoading" class="text-center py-2">
                      <span class="spinner-border spinner-border-sm text-primary" role="status" />
                      <span class="ms-1">加载中...</span>
                    </div>
                    <div v-else-if="!nodePopoverNodes.length" class="text-muted small">暂无节点</div>
                    <ul v-else class="node-popover-list list-unstyled mb-0">
                      <li v-for="(n, idx) in nodePopoverNodes" :key="n.id || idx" class="node-popover-item">
                        {{ n.name || n.api_asset_name || `节点 ${idx + 1}` }}
                      </li>
                    </ul>
                  </div>
                </el-popover>
              </template>
              <span v-else class="text-muted">0</span>
            </td>
            <td>
              <el-tooltip :content="getExecutionStatusTooltip(item)" placement="top" :show-after="200">
                <span :class="['exec-status', getExecutionStatusClass(item)]">
                  {{ getExecutionStatusText(item) }}
                </span>
              </el-tooltip>
            </td>
            <td>{{ formatTime(item.updated_at) }}</td>
            <td class="text-end">
              <div class="action-btns">
                <el-tooltip :content="getExecuteTooltip(item)" placement="top" :disabled="!getExecuteTooltip(item)">
                  <span class="d-inline-block">
                    <button
                      class="btn btn-sm btn-primary me-1"
                      :disabled="isExecuteDisabled(item)"
                      @click="runScene(item.id)"
                    >
                      执行
                    </button>
                  </span>
                </el-tooltip>
                <button
                  class="btn btn-sm btn-outline-secondary me-1"
                  :disabled="rowRunningMap.has(item.id)"
                  @click="goDesigner(item.id)"
                >
                  编辑
                </button>
                <button
                  class="btn btn-sm btn-outline-secondary me-1"
                  :disabled="rowRunningMap.has(item.id)"
                  @click="openLogDrawer(item)"
                >
                  日志
                </button>
                <el-dropdown trigger="click" @command="(cmd) => handleMoreCommand(cmd, item)">
                  <button
                    class="btn btn-sm btn-outline-secondary"
                    :disabled="rowRunningMap.has(item.id)"
                  >
                    更多 ▼
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="copy">复制</el-dropdown-item>
                      <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="queryScenes"
        @size-change="page = 1; queryScenes()"
      />
    </div>

    <!-- 批量删除确认框 -->
    <el-dialog
      v-model="batchDeleteVisible"
      title="确认批量删除"
      width="420px"
      :close-on-click-modal="false"
    >
      <div class="mb-3">
        确定要删除以下 <strong>{{ selectedIds.length }}</strong> 个场景吗？此操作不可恢复。
      </div>
      <ul class="batch-scene-list mb-3">
        <li v-for="id in selectedIds" :key="id">{{ getSceneNameById(id) }}</li>
      </ul>
      <template #footer>
        <button class="btn btn-sm btn-outline-secondary" @click="batchDeleteVisible = false">取消</button>
        <button class="btn btn-sm btn-danger" :disabled="batchDeleteLoading" @click="confirmBatchDelete">确认删除</button>
      </template>
    </el-dialog>

    <!-- 批量执行确认框 -->
    <el-dialog
      v-model="batchConfirmVisible"
      title="确认批量执行"
      width="480px"
      :close-on-click-modal="false"
    >
      <div class="mb-3">
        您将执行以下 <strong>{{ selectedIds.length }}</strong> 个场景：
      </div>
      <ul class="batch-scene-list mb-3">
        <li v-for="id in selectedIds" :key="id">{{ getSceneNameById(id) }}</li>
      </ul>
      <div class="mb-3">
        <label class="small text-muted d-block mb-1">执行方式</label>
        <el-radio-group v-model="batchRunMode">
          <el-radio value="serial">串行执行</el-radio>
          <el-radio value="parallel">并发执行</el-radio>
        </el-radio-group>
      </div>
      <template #footer>
        <button class="btn btn-sm btn-outline-secondary" @click="batchConfirmVisible = false">取消</button>
        <button class="btn btn-sm btn-primary" @click="confirmBatchExecute">确认执行</button>
      </template>
    </el-dialog>

    <!-- 回放导入弹窗 -->
    <ReplayImportDialog
      v-model="replayImportVisible"
      :default-platform-project-id="selectedPlatformProjectId"
      @success="onReplayImportSuccess"
    />

    <!-- 场景编排导出/导入弹窗 -->
    <SceneImportExportDialog
      v-model="sceneExportImportVisible"
      :default-platform-project-id="selectedPlatformProjectId"
      :selected-scene-ids="selectedIds"
      @success="onSceneImportSuccess"
    />

    <!-- 执行日志抽屉 -->
    <el-drawer
      v-model="logDrawerVisible"
      :title="`执行日志 - ${logDrawerScene?.name || ''}`"
      direction="rtl"
      size="520px"
      :z-index="9999"
      :append-to-body="true"
      :lock-scroll="false"
      modal-class="log-drawer-modal"
    >
      <div v-if="logDrawerLoading" class="text-center py-4">
        <span class="spinner-border spinner-border-sm text-primary me-2" />
        加载中...
      </div>
      <div v-else-if="!logDrawerExecutions.length" class="text-muted py-4 text-center">暂无执行记录</div>
      <div v-else class="log-drawer-content">
        <div class="execution-history-list">
          <div
            v-for="row in logDrawerExecutions"
            :key="row.id"
            class="execution-history-item"
            :class="{ 'execution-history-item--active': selectedLogId === row.id }"
            @click="selectLogDetail(row)"
          >
            <div class="d-flex justify-content-between align-items-center">
              <span
                :class="[
                  'badge',
                  row.status === 'success'
                    ? 'bg-success'
                    : row.status === 'partial_success'
                      ? 'bg-warning text-dark'
                      : row.status === 'failed'
                        ? 'bg-danger'
                        : 'bg-secondary'
                ]"
              >
                {{
                  row.status === "success"
                    ? "成功"
                    : row.status === "partial_success"
                      ? "部分成功"
                      : row.status === "failed"
                        ? "失败"
                        : row.status === "running"
                          ? "执行中"
                          : row.status
                }}
              </span>
              <small class="text-muted">{{ formatTime(row.started_at) }}</small>
            </div>
            <div class="small text-muted mt-1">
              成功 {{ row.passed_nodes }}/{{ row.total_nodes }} · 耗时 {{ row.duration_ms || 0 }} ms
            </div>
            <div v-if="row.summary?.environment" class="small text-muted mt-1">
              运行环境：{{ row.summary.environment.name }}
            </div>
          </div>
        </div>
        <div v-if="selectedLogDetail" class="log-detail-section">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>执行详情</strong>
            <span class="text-muted small">查看详情</span>
          </div>
          <ExecutionLogPanel
            :logs="selectedLogDetail.node_results || []"
            :environment="selectedLogDetail.summary?.environment"
          />
        </div>
      </div>
    </el-drawer>
    </div>
  </div>
</template>

<script setup>
import { computed, onActivated, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import ExecutionLogPanel from "../components/ExecutionLogPanel.vue";
import ReplayImportDialog from "../components/ReplayImportDialog.vue";
import SceneImportExportDialog from "../components/SceneImportExportDialog.vue";
import {
  copyScene,
  createScene,
  deleteScene,
  executeScene,
  markSceneExecutionTimeout,
  fetchEnvironments,
  fetchProjects,
  fetchSceneExecutions,
  fetchScenes,
  fetchSceneNodes,
  resolveApiProjectId
} from "../api/scene";
import { fetchApiGroups } from "../api/apiAsset";

const router = useRouter();
const route = useRoute();
const projects = ref([]);
/** 避免首屏 projects 为空时误显「无项目」提示（待 fetchProjects 完成后再判断） */
const projectsLoading = ref(true);
const selectedPlatformProjectId = ref("");
const selectedApiProjectId = ref("");
const environments = ref([]);
const selectedEnvironmentId = ref("");
const envLoading = ref(false);
const keyword = ref("");
const activeFilter = ref("");
const sceneRows = ref([]);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

const selectedIds = ref([]);
const batchRunning = ref(false);
const rowRunningMap = ref(new Set());
const batchConfirmVisible = ref(false);
const batchRunMode = ref("serial");
const batchProgress = ref({ total: 0, completed: 0, succeeded: 0, failed: 0, details: [] });
const batchDeleteVisible = ref(false);
const batchDeleteLoading = ref(false);

const logDrawerVisible = ref(false);
const logDrawerScene = ref(null);
const logDrawerLoading = ref(false);
const logDrawerExecutions = ref([]);
const selectedLogId = ref(null);

const nodePopoverSceneId = ref(null);
const nodePopoverNodes = ref([]);
const nodePopoverLoading = ref(false);

const groupFilter = ref("");
const categoryFilter = ref("");
const execStatusFilter = ref("");
const sceneGroups = ref([]);

/** 将扁平分组列表转换为带完整路径的选项列表 */
const sceneGroupOptions = computed(() => {
  const flat = sceneGroups.value || [];
  if (!flat.length) return [];
  // 构建 id → item 映射
  const byId = {};
  flat.forEach(g => { byId[g.id] = { ...g }; });
  // 计算每个分组的完整路径名称
  function getPath(group) {
    const parts = [];
    let current = group;
    while (current) {
      parts.unshift(current.name);
      current = current.parent ? byId[current.parent] : null;
    }
    return parts;
  }
  return flat.map(g => {
    const path = getPath(g);
    const pathLabel = path.join(' / ');
    const pathHtml = path.length > 1
      ? `<span class="text-muted">${path.slice(0, -1).join(' / ')} / </span><span class="group-name-highlight">${g.name}</span>`
      : `<span class="group-name-highlight">${g.name}</span>`;
    return { id: g.id, name: g.name, pathLabel, pathHtml };
  });
});

const replayImportVisible = ref(false);
const sceneExportImportVisible = ref(false);

const envListUrl = "/environments/";

const totalPages = computed(() => {
  if (!total.value) return 1;
  return Math.ceil(total.value / pageSize.value);
});

const isAllSelected = computed(() => {
  if (!sceneRows.value.length) return false;
  return sceneRows.value.every((r) => selectedIds.value.includes(r.id));
});

const isIndeterminate = computed(() => {
  const n = selectedIds.value.length;
  return n > 0 && n < sceneRows.value.length;
});

const selectedLogDetail = computed(() => {
  if (!selectedLogId.value) return null;
  return logDrawerExecutions.value.find((e) => e.id === selectedLogId.value) || null;
});

const canBatchExecute = computed(() => {
  return !!selectedEnvironmentId.value && selectedIds.value.length > 0 && !batchRunning.value;
});

const batchExecuteTooltip = computed(() => {
  if (!selectedEnvironmentId.value) return "请先选择运行环境";
  if (!selectedIds.value.length) return "请选择要执行的场景";
  return "";
});

function getExecuteTooltip(item) {
  if (rowRunningMap.value.has(item.id)) return "";
  if (!selectedEnvironmentId.value) return "请先选择运行环境";
  const nodeCount = item.node_count || 0;
  if (nodeCount === 0) return "场景无有效节点，无法执行";
  return "";
}

function isExecuteDisabled(item) {
  if (rowRunningMap.value.has(item.id)) return true;
  if (!selectedEnvironmentId.value) return true;
  if ((item.node_count || 0) === 0) return true;
  return false;
}

function getExecutionStatusText(item) {
  if (rowRunningMap.value.has(item.id)) return "⏳ 执行中";
  const status = item.latest_execution_status;
  if (status === "success") return "✅ 成功";
  if (status === "partial_success") return "⚠️ 部分成功";
  if (status === "failed") return "❌ 失败";
  if (status === "running") return "⏳ 执行中";
  // 后端新增状态或静态资源未更新时，避免误显「从未执行」
  if (status) return `⚠️ ${String(status).replace(/_/g, " ")}`;
  return "从未执行";
}

function getExecutionStatusTooltip(item) {
  if (rowRunningMap.value.has(item.id)) return "⏳ 执行中";
  const status = item.latest_execution_status;
  if (status === "success") {
    const time = formatTime(item.latest_execution_started_at);
    const duration = item.latest_execution_duration_ms;
    const durationStr = duration != null ? (duration >= 1000 ? `${(duration / 1000).toFixed(1)}s` : `${duration}ms`) : "-";
    return `✅ 成功 | 执行时间: ${time} | 耗时: ${durationStr}`;
  }
  if (status === "partial_success") {
    const time = formatTime(item.latest_execution_started_at);
    const duration = item.latest_execution_duration_ms;
    const durationStr = duration != null ? (duration >= 1000 ? `${(duration / 1000).toFixed(1)}s` : `${duration}ms`) : "-";
    const hint = (item.latest_execution_error_message || "存在失败继续类断言未通过").slice(0, 80);
    return `⚠️ 部分成功 | 执行时间: ${time} | 耗时: ${durationStr} | ${hint}`;
  }
  if (status === "failed") {
    const time = formatTime(item.latest_execution_started_at);
    const reason = (item.latest_execution_error_message || "未知原因").slice(0, 80);
    return `❌ 失败 | 执行时间: ${time} | 失败原因: ${reason}`;
  }
  if (status === "running") return "⏳ 执行中";
  if (status) {
    const time = formatTime(item.latest_execution_started_at);
    const duration = item.latest_execution_duration_ms;
    const durationStr = duration != null ? (duration >= 1000 ? `${(duration / 1000).toFixed(1)}s` : `${duration}ms`) : "-";
    return `${status} | 执行时间: ${time} | 耗时: ${durationStr}`;
  }
  return "从未执行";
}

function getExecutionStatusClass(item) {
  if (rowRunningMap.value.has(item.id)) return "exec-status-running";
  const status = item.latest_execution_status;
  if (status === "success") return "exec-status-success";
  if (status === "partial_success") return "exec-status-partial";
  if (status === "failed") return "exec-status-failed";
  if (status === "running") return "exec-status-running";
  if (status) return "exec-status-partial";
  return "exec-status-never";
}

function getSceneNameById(id) {
  return sceneRows.value.find((r) => r.id === id)?.name || `场景 #${id}`;
}

function formatTime(raw) {
  return raw ? new Date(raw).toLocaleString() : "-";
}

function envVariablesPreview(env) {
  const vars = env?.variables;
  if (!vars || typeof vars !== "object") return "";
  /** 与后端 env_variables_compat 一致：说明元数据不参与预览 */
  const entries = Object.entries(vars)
    .filter(([k]) => k !== "__var_descriptions__")
    .slice(0, 5);
  return entries.map(([k, v]) => `${k}=${String(v).slice(0, 20)}`).join("; ");
}

function onEnvironmentChange() {
  const projectId = selectedPlatformProjectId.value;
  if (projectId && selectedEnvironmentId.value) {
    try {
      localStorage.setItem(`scene_env_${projectId}`, selectedEnvironmentId.value);
    } catch (_) {}
  }
}

function toggleSelect(id) {
  const idx = selectedIds.value.indexOf(id);
  if (idx >= 0) {
    selectedIds.value = selectedIds.value.filter((x) => x !== id);
  } else {
    selectedIds.value = [...selectedIds.value, id];
  }
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = [];
  } else {
    selectedIds.value = sceneRows.value.map((r) => r.id);
  }
}

async function reloadByProject() {
  const projectId = selectedPlatformProjectId.value;
  if (!projectId) {
    selectedApiProjectId.value = "";
    environments.value = [];
    selectedEnvironmentId.value = "";
    sceneRows.value = [];
    selectedIds.value = [];
    groupFilter.value = "";
    categoryFilter.value = "";
    execStatusFilter.value = "";
    sceneGroups.value = [];
    return;
  }

  // resolveApiProjectId 与 fetchEnvironments 无依赖，并行请求
  envLoading.value = true;
  const [mapped, envData] = await Promise.all([
    resolveApiProjectId(Number(projectId)).catch(() => null),
    fetchEnvironments(projectId).then(d => d.results || d || []).catch(() => [])
  ]);
  envLoading.value = false;

  if (!mapped) {
    // resolve 失败，清空场景列表
    selectedApiProjectId.value = "";
    selectedEnvironmentId.value = "";
    sceneRows.value = [];
    selectedIds.value = [];
    groupFilter.value = "";
    categoryFilter.value = "";
    execStatusFilter.value = "";
    sceneGroups.value = [];
    environments.value = envData;
    return;
  }

  selectedApiProjectId.value = mapped.api_project_id;
  page.value = 1;
  environments.value = envData;

  // 加载 API 分组（场景复用 API 资产的分组体系）
  fetchApiGroups(mapped.api_project_id).then(data => {
    sceneGroups.value = data.results || data || [];
  }).catch(() => {
    sceneGroups.value = [];
  });

  const envFromRoute = route.query.env_id;
  const lastEnv = localStorage.getItem(`scene_env_${projectId}`);
  if (envFromRoute && environments.value.some((e) => String(e.id) === String(envFromRoute))) {
    selectedEnvironmentId.value = String(envFromRoute);
  } else if (lastEnv && environments.value.some((e) => String(e.id) === lastEnv)) {
    selectedEnvironmentId.value = lastEnv;
  } else {
    selectedEnvironmentId.value = "";
  }

  await queryScenes();
}

async function queryScenes() {
  if (!selectedApiProjectId.value) return;
  loading.value = true;
  try {
    const params = {
      project: selectedApiProjectId.value,
      q: keyword.value,
      is_active: activeFilter.value,
      group: groupFilter.value,
      category: categoryFilter.value,
      latest_execution_status: execStatusFilter.value,
      page: page.value,
      page_size: pageSize.value
    };
    if (route.query._refresh) {
      params._t = Date.now();
    }
    const data = await fetchScenes(params);
    sceneRows.value = data.results || [];
    total.value = data.count || 0;
  } finally {
    loading.value = false;
  }
}

async function createNewScene() {
  if (!selectedApiProjectId.value) {
    if (projects.value.length > 0) {
      selectedPlatformProjectId.value = String(projects.value[0].id);
      await reloadByProject();
    }
  }
  if (!selectedApiProjectId.value) {
    ElMessage.warning("当前无可用项目，请先在项目管理中创建项目");
    return;
  }

  // 弹窗选择场景分类
  let selectedCategory = "traced";
  try {
    await ElMessageBox.confirm(
      `<div style="margin: 12px 0;">
        <label style="display: block; margin-bottom: 12px; cursor: pointer;">
          <input type="radio" name="scene-category" value="traced" checked style="margin-right: 6px;"> 留痕版
        </label>
        <label style="display: block; cursor: pointer;">
          <input type="radio" name="scene-category" value="untraced" style="margin-right: 6px;"> 不留痕版
        </label>
      </div>`,
      "选择场景分类",
      {
        dangerouslyUseHTMLString: true,
        confirmButtonText: "确认创建",
        cancelButtonText: "取消",
        type: "info",
      }
    );
    const checked = document.querySelector('input[name="scene-category"]:checked');
    if (checked) {
      selectedCategory = checked.value;
    }
  } catch {
    return;
  }

  const scene = await createScene({
    project: Number(selectedApiProjectId.value),
    name: `新场景-${Date.now()}`,
    category: selectedCategory,
    description: "",
    variables: {},
    runtime_config: {},
    is_active: true
  });
  router.push({ name: "scene-designer", params: { id: scene.id } });
}

function goDesigner(id) {
  router.push({ name: "scene-designer", params: { id } });
}

async function runScene(id) {
  if (!selectedEnvironmentId.value) {
    ElMessage.warning("请先选择运行环境");
    return;
  }
  const item = sceneRows.value.find((r) => r.id === id);
  if (item && (item.node_count || 0) === 0) {
    ElMessage.warning("场景无有效节点，无法执行");
    return;
  }
  rowRunningMap.value = new Set([...rowRunningMap.value, id]);
  try {
    const execData = await executeScene(id, { run_mode: "all", environment_id: Number(selectedEnvironmentId.value) });
    if (execData?.status === "partial_success") {
      ElMessage.warning(execData?.error_message || "执行结束：部分成功（存在失败继续类断言未通过）");
    } else {
      ElMessage.success("执行完成");
    }
    router.push({ name: "scene-execution", params: { id } });
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || "执行失败";
    ElMessage.error(msg);
    // 请求超时时，通知后端将卡住的执行标记为失败，避免状态一直显示「执行中」
    if (msg && String(msg).includes("请求超时")) {
      try {
        await markSceneExecutionTimeout(id);
      } catch (_) {
        // 忽略标记失败，继续刷新列表
      }
    }
    // 超时或失败后刷新列表，获取后端最新执行状态
    await queryScenes();
  } finally {
    const next = new Set(rowRunningMap.value);
    next.delete(id);
    rowRunningMap.value = next;
  }
}

async function openNodePopover(item) {
  if (!(item.node_count || 0)) return;
  nodePopoverSceneId.value = item.id;
  nodePopoverNodes.value = [];
  nodePopoverLoading.value = true;
  try {
    const data = await fetchSceneNodes(item.id);
    const list = data.results || data || [];
    nodePopoverNodes.value = Array.isArray(list) ? list : [];
  } catch (e) {
    nodePopoverNodes.value = [];
  } finally {
    nodePopoverLoading.value = false;
  }
}

function openBatchExecuteConfirm() {
  if (!selectedIds.value.length) return;
  if (!selectedEnvironmentId.value) {
    ElMessage.warning("请先选择运行环境");
    return;
  }
  batchConfirmVisible.value = true;
}

function openBatchDeleteConfirm() {
  if (!selectedIds.value.length) return;
  batchDeleteVisible.value = true;
}

async function confirmBatchDelete() {
  const ids = [...selectedIds.value];
  batchDeleteVisible.value = false;
  batchDeleteLoading.value = true;
  let success = 0;
  let fail = 0;
  for (const id of ids) {
    try {
      await deleteScene(id);
      success++;
      selectedIds.value = selectedIds.value.filter((x) => x !== id);
    } catch (e) {
      fail++;
      ElMessage.error(`删除场景 #${id} 失败: ${e?.message || "未知错误"}`);
    }
  }
  batchDeleteLoading.value = false;
  if (success) {
    ElMessage.success(`成功删除 ${success} 个场景${fail ? `，${fail} 个失败` : ""}`);
    await queryScenes();
  }
}

async function confirmBatchExecute() {
  batchConfirmVisible.value = false;
  const ids = [...selectedIds.value];
  batchRunning.value = true;
  batchProgress.value = { total: ids.length, completed: 0, succeeded: 0, failed: 0, details: [] };
  rowRunningMap.value = new Set([...rowRunningMap.value, ...ids]);

  const envId = Number(selectedEnvironmentId.value);
  const results = [];

  const runOne = async (sceneId) => {
    const name = getSceneNameById(sceneId);
    try {
      await executeScene(sceneId, { run_mode: "all", environment_id: envId });
      results.push({ id: sceneId, name, ok: true });
      batchProgress.value.succeeded++;
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message;
      if (msg && String(msg).includes("请求超时")) {
        try {
          await markSceneExecutionTimeout(sceneId);
        } catch (_) {}
      }
      results.push({ id: sceneId, name, ok: false, err: msg || "未知错误" });
      batchProgress.value.failed++;
    } finally {
      batchProgress.value.completed++;
      const next = new Set(rowRunningMap.value);
      next.delete(sceneId);
      rowRunningMap.value = next;
    }
  };

  try {
    if (batchRunMode.value === "serial") {
      for (const id of ids) {
        await runOne(id);
      }
    } else {
      await Promise.all(ids.map((id) => runOne(id)));
    }

    // P1：执行结果汇总弹窗
    const successCount = batchProgress.value.succeeded;
    const failCount = batchProgress.value.failed;
    const failList = results.filter((r) => !r.ok);

    const summaryLines = [`成功: ${successCount}，失败: ${failCount}`];
    if (failList.length > 0) {
      summaryLines.push("", "失败详情：");
      failList.forEach((r) => {
        summaryLines.push(`• ${r.name}：${r.err}`);
      });
    }

    await ElMessageBox.alert(summaryLines.join("\n"), "批量执行结果", {
      confirmButtonText: "确定",
      type: failCount > 0 ? "warning" : "success",
      dangerouslyUseHTMLString: false,
    });

    selectedIds.value = [];
    await queryScenes();
  } catch (e) {
    ElMessage.error(e?.message || "批量执行异常");
  } finally {
    batchRunning.value = false;
    rowRunningMap.value = new Set();
  }
}

async function openLogDrawer(item) {
  logDrawerScene.value = item;
  logDrawerVisible.value = true;
  selectedLogId.value = null;
  logDrawerLoading.value = true;
  logDrawerExecutions.value = [];
  try {
    const data = await fetchSceneExecutions(item.id, {page_size: 20});
    logDrawerExecutions.value = Array.isArray(data) ? data : data.results || [];
    if (logDrawerExecutions.value.length) {
      selectedLogId.value = logDrawerExecutions.value[0].id;
    }
  } catch (e) {
    ElMessage.error(e?.message || "加载执行记录失败");
  } finally {
    logDrawerLoading.value = false;
  }
}

function selectLogDetail(row) {
  selectedLogId.value = row.id;
}

function onReplayImportSuccess(data) {
  if (data?.scene_id) {
    queryScenes();
    router.push({ name: "scene-designer", params: { id: data.scene_id } });
  }
}

function onSceneImportSuccess() {
  queryScenes();
}

async function handleMoreCommand(cmd, item) {
  if (cmd === "copy") {
    await copyScene(item.id, `${item.name}-副本`);
    ElMessage.success("复制成功");
    await queryScenes();
  } else if (cmd === "delete") {
    if (!window.confirm("确认删除该场景？")) return;
    await deleteScene(item.id);
    ElMessage.success("删除成功");
    await queryScenes();
  }
}

onMounted(async () => {
  projectsLoading.value = true;
  try {
    const projectResp = await fetchProjects();
    projects.value = projectResp.results || projectResp || [];
    if (projects.value.length > 0) {
      const queryProject = route.query.project_id;
      const projectId = queryProject && projects.value.some((p) => String(p.id) === String(queryProject))
        ? String(queryProject)
        : String(projects.value[0].id);
      selectedPlatformProjectId.value = projectId;
      await reloadByProject();
      if (route.query._refresh) {
        const q = { ...route.query };
        delete q._refresh;
        router.replace({ path: route.path, query: Object.keys(q).length ? q : {} });
      }
    }
  } catch (e) {
    projects.value = [];
    ElMessage.error(e?.message || "加载项目列表失败，请稍后重试");
  } finally {
    projectsLoading.value = false;
  }
});

onActivated(() => {
  if (selectedApiProjectId.value) {
    queryScenes();
  }
});
</script>

<style scoped>
.scene-list-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.page-header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  line-height: 1.3;
}
.page-subtitle {
  font-size: var(--el-font-size-base);
  color: #909399;
}
.page-header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.filter-area {
  flex: 1;
  min-width: 0;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 24px;
  align-items: flex-end;
  justify-content: flex-start;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-item--search {
  gap: 6px;
}

.filter-label {
  font-size: 16px;
  color: #6c757d;
  margin: 0;
  width: 72px;
  flex-shrink: 0;
  text-align: right;
}

.filter-label.filter-label--short {
  width: 48px;
}

.filter-control {
  width: 160px;
  padding: 0;
  border: none;
  box-shadow: none;
  outline: none;
  flex-shrink: 0;
  font-size: 16px;
}

.form-control.filter-control {
  height: 32px;
  padding: 6px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
}

.form-control.filter-control:focus {
  box-shadow: none;
  border-color: #409eff;
}

/* 下拉框：仅内层 el-select__wrapper 保留单层边框 */
.filter-control :deep(.el-select) {
  width: 100%;
  border: none;
  box-shadow: none;
  outline: none;
}

.filter-control :deep(.el-select__wrapper) {
  width: 100%;
  border-radius: 6px;
  min-height: 32px;
  box-shadow: none !important;
  border: 1px solid #dcdfe6;
  padding: 4px 12px;
  background-color: #fff;
}

.filter-control :deep(.el-select__wrapper:hover),
.filter-control :deep(.el-select__wrapper.is-focused) {
  box-shadow: none !important;
  border-color: #c0c4cc;
}

.filter-control :deep(.el-select__wrapper.is-focused) {
  border-color: #409eff;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  align-items: center;
}

.select-hint {
  font-size: 12px;
}

.desc {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.exec-status {
  font-size: 13px;
}

.exec-status-success {
  color: #67c23a;
}

.exec-status-partial {
  color: #e6a23c;
}

.exec-status-failed {
  color: #f56c6c;
}

.exec-status-running {
  color: #909399;
}

.exec-status-never {
  color: #909399;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  margin-top: 16px;
}

.empty-state-cell {
  padding: 48px 16px !important;
}

.empty-state {
  text-align: center;
}

.env-empty-hint {
  margin-top: 4px;
  font-size: 12px;
}

.env-empty-hint a {
  color: #409eff;
}

.batch-scene-list {
  max-height: 180px;
  overflow-y: auto;
  padding-left: 20px;
  margin: 0;
}

.log-drawer-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.execution-history-list {
  max-height: 240px;
  overflow-y: auto;
}

.execution-history-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.execution-history-item:hover {
  background-color: var(--el-fill-color-lighter);
}

.execution-history-item--active {
  background-color: #f0f7ff;
  border-color: #409eff;
}

.log-detail-section {
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.action-btns {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 4px;
}

.node-count-btn {
  color: #409eff;
  cursor: pointer;
  border: none;
  background: none;
  font-size: inherit;
}

.node-count-btn:hover {
  color: #66b1ff;
  text-decoration: underline;
}

.node-popover-content {
  max-height: 200px;
  overflow-y: auto;
}

.node-popover-list {
  padding-left: 0;
}

.node-popover-item {
  padding: 6px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
}

.node-popover-item:last-child {
  border-bottom: none;
}

.api-updated-tag {
  vertical-align: middle;
}

.batch-progress {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  color: #409eff;
  white-space: nowrap;
}

/* 分组标签 */
.group-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  font-size: 12px;
  border-radius: 12px;
  background: #e8f4fd;
  color: #1a6ba0;
  border: 1px solid #b8dff5;
  white-space: nowrap;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.group-tag i {
  font-size: 13px;
}
/* 分组下拉选项 */
.group-path-option {
  font-size: 13px;
}
.group-name-highlight {
  font-weight: 500;
  color: #303133;
}

/* ====== 行高优化：表格单元格紧凑 ====== */
.scene-list-page .table > :not(caption) > * > * {
  padding: 0.35rem 0.45rem;
  vertical-align: middle;
}
.scene-list-page .table thead th {
  font-weight: 600;
  background: #f6f8fa;
  white-space: nowrap;
}
/* 操作列按钮紧凑 */
.scene-list-page .action-btns .btn {
  padding: 0.1rem 0.35rem;
  font-size: 12px;
  line-height: 1.4;
}
.scene-list-page .action-btns .btn-sm {
  padding: 0.1rem 0.35rem;
  font-size: 12px;
}
/* 行内标签与文本垂直居中 */
.scene-list-page .table td {
  line-height: 1.3;
}
/* 批量操作工具栏紧凑 */
.scene-list-page .top-bar {
  margin-bottom: 8px;
}
.scene-list-page .filter-row {
  gap: 10px 16px;
}

/* ====== Font-size 统一 ====== */
/* Bootstrap 组件字体对齐 Element Plus（其他页面使用） */
.scene-list-page .table {
  font-size: 13px;
}
.scene-list-page .table thead th {
  font-size: 13px;
  font-weight: 600;
}
.scene-list-page .form-control {
  font-size: 13px;
}
</style>

<!-- 日志抽屉浮层：非 scoped，因 el-drawer teleport 到 body，固定 z-index 避免层级抖动 -->
<style>
.log-drawer-modal {
  z-index: 9999 !important;
  isolation: isolate;
}
</style>
