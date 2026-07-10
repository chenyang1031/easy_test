<template>
  <div class="perf-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">性能测试</h2>
        <span class="page-subtitle">管理性能测试任务，支持固定并发和阶梯负载模式</span>
      </div>
      <div class="page-header-right">
        <button type="button" class="btn btn-sm btn-primary" :disabled="!projects.length" @click="goNew">
          新建任务
        </button>
      </div>
    </div>

    <div class="panel-card">
      <div class="top-bar">
        <div class="filter-area">
          <div class="filter-row">
            <div class="filter-item">
              <label class="filter-label">项目</label>
              <el-select
              v-model="selectedProjectId"
              placeholder="全部项目"
              clearable
              size="small"
              class="filter-control filter-control--wide"
              popper-class="scene-select-popper"
              @change="loadTasks"
            >
              <el-option label="全部项目" value="" />
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="String(p.id)" />
            </el-select>
          </div>
          <div class="filter-item">
            <label class="filter-label">负载类型</label>
            <el-select
              v-model="filterLoadType"
              placeholder="全部"
              clearable
              size="small"
              class="filter-control"
              popper-class="scene-select-popper"
              @change="applyFilters"
            >
              <el-option label="固定并发" value="fixed" />
              <el-option label="阶梯负载" value="staged" />
            </el-select>
          </div>
          <div class="filter-item">
            <label class="filter-label">业务断言</label>
            <el-select
              v-model="filterAssertion"
              placeholder="全部"
              clearable
              size="small"
              class="filter-control"
              popper-class="scene-select-popper"
              @change="applyFilters"
            >
              <el-option label="已开启" value="yes" />
              <el-option label="未开启" value="no" />
            </el-select>
          </div>
          <div class="filter-item">
            <label class="filter-label">CSV</label>
            <el-select
              v-model="filterCsv"
              placeholder="全部"
              clearable
              size="small"
              class="filter-control"
              popper-class="scene-select-popper"
              @change="applyFilters"
            >
              <el-option label="已使用" value="yes" />
              <el-option label="未使用" value="no" />
            </el-select>
          </div>
          <div class="filter-item">
            <button type="button" class="btn btn-sm btn-outline-secondary" @click="resetFilters">重置筛选</button>
          </div>
        </div>
        <p class="filter-hint text-muted small mb-0 mt-2">
          筛选作用于当前已加载数据；数据量大时可提高分页条数后筛选。
        </p>
      </div>
      <div class="toolbar-actions">
      </div>
    </div>

    <div class="table-wrap mt-3">
      <el-table v-loading="listLoading" :data="displayRows" stripe size="small" class="perf-task-table">
        <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="project_name" label="项目" min-width="100" show-overflow-tooltip />
        <el-table-column prop="interface_name" label="接口" min-width="120" show-overflow-tooltip />
        <el-table-column label="负载类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="taskLoadType(row) === 'staged' ? 'warning' : 'info'">
              {{ taskLoadType(row) === "staged" ? "阶梯" : "固定" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="断言" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="taskHasAssertions(row) ? 'success' : 'info'">
              {{ taskHasAssertions(row) ? "是" : "否" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="参数化" width="88" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="taskHasCsv(row) ? 'success' : 'info'">
              {{ taskHasCsv(row) ? "是" : "否" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_users" label="用户数" width="80" align="center" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="340" fixed="right" align="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button type="primary" link size="small" @click="goReport(row)">查看报告</el-button>
              <el-button type="primary" link size="small" @click="goConsole(row)">实时控制台</el-button>
              <el-button
                link
                size="small"
                type="success"
                :loading="startLoadingMap[row.id]"
                :disabled="row.status === 'running'"
                @click="rerun(row)"
              >
                {{ row.status === "draft" ? "开始运行" : "重新运行" }}
              </el-button>
              <el-button
                v-if="row.status === 'running'"
                link
                size="small"
                type="warning"
                :loading="stopLoadingMap[row.id]"
                :disabled="stopLoadingMap[row.id]"
                @click="confirmStop(row)"
              >
                停止
              </el-button>
              <el-button link size="small" @click="goEdit(row)">编辑</el-button>
              <el-button link size="small" type="danger" @click="confirmDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <span v-if="filterActive" class="page-filter-note">本页筛选后 {{ displayRows.length }} 条</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  fetchPerformanceTasks,
  deletePerformanceTask,
  startPerformanceTest,
  stopPerformanceTest
} from "../../api/performance";
import { fetchProjects } from "../../api/scene";
import { confirmWarning, msgError, msgSuccess, msgWarning } from "../../utils/uiMessage.js";
import { taskLoadType, taskHasAssertions, taskHasCsv } from "./performanceUtils.js";

const router = useRouter();

const listLoading = ref(false);
const startLoadingMap = ref({});
const stopLoadingMap = ref({});
const projects = ref([]);
const selectedProjectId = ref("");
const rawRows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);

const filterLoadType = ref("");
const filterAssertion = ref("");
const filterCsv = ref("");

const filterActive = computed(
  () => !!(filterLoadType.value || filterAssertion.value || filterCsv.value)
);

const displayRows = computed(() => {
  let rows = rawRows.value;
  if (filterLoadType.value) {
    rows = rows.filter((r) => taskLoadType(r) === filterLoadType.value);
  }
  if (filterAssertion.value === "yes") {
    rows = rows.filter((r) => taskHasAssertions(r));
  } else if (filterAssertion.value === "no") {
    rows = rows.filter((r) => !taskHasAssertions(r));
  }
  if (filterCsv.value === "yes") {
    rows = rows.filter((r) => taskHasCsv(r));
  } else if (filterCsv.value === "no") {
    rows = rows.filter((r) => !taskHasCsv(r));
  }
  return rows;
});

function statusLabel(s) {
  const map = {
    draft: "草稿",
    running: "执行中",
    stopped: "已停止",
    completed: "已完成",
    finished: "已完成",
    failed: "失败"
  };
  return map[s] || s;
}
function statusTagType(s) {
  const map = {
    draft: "info",
    running: "warning",
    stopped: "info",
    completed: "success",
    finished: "success",
    failed: "danger"
  };
  return map[s] || "info";
}

function applyFilters() {
  /* 计算属性自动刷新 */
}

function resetFilters() {
  filterLoadType.value = "";
  filterAssertion.value = "";
  filterCsv.value = "";
}

async function loadProjects() {
  try {
    const res = await fetchProjects();
    projects.value = res.results || res.data || res || [];
    if (Array.isArray(res)) projects.value = res;
  } catch (e) {
    msgError(e?.message || "加载项目失败");
  }
}

async function loadTasks() {
  listLoading.value = true;
  try {
    const params = { page: page.value, page_size: pageSize.value };
    if (selectedProjectId.value) params.project = selectedProjectId.value;
    const res = await fetchPerformanceTasks(params);
    rawRows.value = res.results || [];
    total.value = res.count ?? rawRows.value.length;
  } catch (e) {
    msgError(e?.message || "加载任务列表失败");
  } finally {
    listLoading.value = false;
  }
}

async function confirmStop(row) {
  try {
    await confirmWarning("确定要停止该性能测试任务吗？");
  } catch {
    return;
  }
  stopLoadingMap.value = { ...stopLoadingMap.value, [row.id]: true };
  try {
    const res = await stopPerformanceTest(row.id, { reason: "用户手动停止" });
    msgSuccess(res?.message || "已停止");
    const updated = res?.task;
    if (updated && typeof updated === "object") {
      rawRows.value = rawRows.value.map((r) => (r.id === row.id ? { ...r, ...updated } : r));
    } else {
      await loadTasks();
    }
  } catch (e) {
    msgError(e?.message || "停止失败");
  } finally {
    stopLoadingMap.value = { ...stopLoadingMap.value, [row.id]: false };
  }
}

function goNew() {
  router.push({ name: "perf-task-new" });
}
function goEdit(row) {
  router.push({ name: "perf-task-edit", params: { id: String(row.id) } });
}
function goReport(row) {
  router.push({ name: "perf-report", params: { id: String(row.id) } });
}
function goConsole(row) {
  router.push({ name: "perf-console", params: { id: String(row.id) } });
}

async function rerun(row) {
  if (row.status === "running") {
    return;
  }
  const canStart = ["draft", "completed", "finished", "failed", "stopped"].includes(row.status);
  if (!canStart) {
    msgWarning("当前状态不可启动压测");
    return;
  }
  startLoadingMap.value = { ...startLoadingMap.value, [row.id]: true };
  try {
    const res = await startPerformanceTest(row.id);
    msgSuccess("压测已启动");
    if (res?.hint) {
      msgWarning(res.hint);
    }
    loadTasks();
    // 带 _run 便于控制台识别「刚启动」并等待状态变为 running；同路径仅 query 变化时也会触发控制台重新拉数
    router.push({
      name: "perf-console",
      params: { id: String(row.id) },
      query: { _run: String(Date.now()) }
    });
  } catch (e) {
    msgError(e?.message || "启动失败");
  } finally {
    startLoadingMap.value = { ...startLoadingMap.value, [row.id]: false };
  }
}

async function confirmDelete(row) {
  try {
    await confirmWarning("确定删除该任务？删除后不可恢复。");
  } catch {
    return;
  }
  await deleteTask(row);
}

async function deleteTask(row) {
  try {
    await deletePerformanceTask(row.id);
    msgSuccess("已删除");
    loadTasks();
  } catch (e) {
    msgError(e?.message || "删除失败");
  }
}

onMounted(() => {
  loadProjects();
  loadTasks();
});
</script>

<style scoped>
.perf-list-page {
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
.page-header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.page-subtitle { font-size: var(--el-font-size-base); color: #909399; }
.page-header-right { display: flex; gap: 8px; align-items: center; }

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

.filter-label {
  font-size: 16px;
  color: #6c757d;
  margin: 0;
  width: 72px;
  flex-shrink: 0;
  text-align: right;
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

.filter-control.filter-control--wide {
  width: 200px;
}

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

.filter-hint {
  line-height: 1.5;
}

.table-wrap {
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}
.perf-task-table :deep(.el-table__cell) {
  padding-left: 8px;
  padding-right: 8px;
}
.action-btns {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 4px;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  margin-top: 16px;
}
.page-filter-note {
  font-size: 13px;
  color: #909399;
  margin-left: 8px;
}
</style>

