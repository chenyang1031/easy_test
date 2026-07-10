<template>
  <div class="report-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">测试报告</h2>
        <span class="page-subtitle" v-if="total > 0">共 {{ total }} 条</span>
      </div>
      <div class="page-header-right">
        <el-button size="default" type="primary" :disabled="!projects.length" @click="goCreate">
          <el-icon><Plus /></el-icon> 新建报告
        </el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="12" class="filter-row">
          <el-col :xs="24" :sm="12" :md="6">
            <el-select
              v-model="filterProject"
              placeholder="全部项目"
              clearable
              class="filter-item"
              popper-class="scene-select-popper"
              @change="loadReports"
            >
              <el-option label="全部项目" value="" />
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="String(p.id)" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="6" :md="4">
            <el-select
              v-model="filterReportType"
              placeholder="全部类型"
              clearable
              class="filter-item"
              popper-class="scene-select-popper"
              @change="loadReports"
            >
              <el-option label="全部类型" value="" />
              <el-option label="测试运行" value="test_run" />
              <el-option label="测试套件" value="test_suite_run" />
              <el-option label="场景执行" value="scene_execution" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="6" :md="4">
            <el-input
              v-model="searchQuery"
              placeholder="名称/描述搜索"
              size="default"
              clearable
              class="filter-item"
              @keyup.enter="loadReports"
              @clear="loadReports"
            />
          </el-col>
          <el-col :xs="24" :sm="12" :md="2">
            <div class="filter-actions">
              <el-button type="primary" size="default" @click="loadReports">查询</el-button>
              <el-button size="default" @click="resetFilters">重置</el-button>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 加载中 -->
      <div v-if="listLoading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="!reports.length" description="暂无测试报告">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><Document /></el-icon>
        </template>
        <el-text type="info">通过生成报告或手动创建来添加测试报告</el-text>
        <el-button type="primary" @click="goCreate" style="margin-top:12px">新建报告</el-button>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table :data="reports" stripe border class="data-table" size="small" @row-click="(row) => goDetail(row)">
          <el-table-column label="名称" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <el-button link type="primary" @click.stop="goDetail(row)" class="name-link">
                {{ row.name }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column label="描述" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="text-muted">{{ row.description || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="项目" min-width="100" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.project_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="报告类型" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="reportTypeTag(row.report_type)" size="small" effect="light" round>
                {{ row.report_type_display }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="格式" width="70" align="center">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.report_format_display }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="关联场景" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="text-muted">{{ row.scene_name || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="生成时间" width="170" align="center">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click.stop="goDetail(row)">查看</el-button>
              <el-popconfirm title="确定删除此报告？" @confirm.stop="confirmDelete(row)">
                <template #reference>
                  <el-button link type="danger" size="small" @click.stop>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrap" v-if="total > 0">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="total"
            layout="total, sizes, prev, pager, next"
            @size-change="loadReports"
            @current-change="loadReports"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { Plus, Loading, Document } from "@element-plus/icons-vue";
import { fetchReports, deleteReport } from "../../api/report";
import { fetchProjects } from "../../api/scene";
import { confirmWarning, msgSuccess, msgError } from "../../utils/uiMessage.js";

const router = useRouter();

const listLoading = ref(false);
const projects = ref([]);
const reports = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

const filterProject = ref("");
const filterReportType = ref("");
const searchQuery = ref("");

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

async function loadProjects() {
  try {
    const res = await fetchProjects();
    projects.value = res.results || res.data || res || [];
    if (Array.isArray(res)) projects.value = res;
  } catch (e) {
    msgError(e?.message || "加载项目失败");
  }
}

async function loadReports() {
  listLoading.value = true;
  try {
    const params = { page: page.value, page_size: pageSize.value };
    if (filterProject.value) params.project = filterProject.value;
    if (filterReportType.value) params.report_type = filterReportType.value;
    if (searchQuery.value) params.q = searchQuery.value;
    const res = await fetchReports(params);
    reports.value = res.results || [];
    total.value = res.count ?? reports.value.length;
  } catch (e) {
    msgError(e?.message || "加载报告列表失败");
  } finally {
    listLoading.value = false;
  }
}

function resetFilters() {
  filterProject.value = "";
  filterReportType.value = "";
  searchQuery.value = "";
  page.value = 1;
  loadReports();
}

function goCreate() {
  router.push({ name: "reportCreate" });
}

function goDetail(row) {
  router.push({ name: "reportDetail", params: { id: String(row.id) } });
}

async function confirmDelete(row) {
  try {
    await confirmWarning(`确定删除测试报告「${row.name}」吗？此操作不可撤销。`);
  } catch {
    return;
  }
  try {
    await deleteReport(row.id);
    msgSuccess("已删除");
    loadReports();
  } catch (e) {
    msgError(e?.message || "删除失败");
  }
}

onMounted(() => {
  loadProjects();
  loadReports();
});
</script>

<style scoped>
.report-list-page {
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
.page-title { font-size: 20px; font-weight: 600; color: #303133; margin: 0; }
.page-subtitle { font-size: 14px; color: #909399; }
.page-header-right { display: flex; gap: 8px; align-items: center; }

/* ---- 统一卡片 ---- */
.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* ---- 筛选栏 ---- */
.filter-bar { margin-bottom: 16px; }
.filter-row { align-items: end; }
.filter-item { width: 100%; }
.filter-actions { display: flex; gap: 8px; }

/* ---- 加载/空状态 ---- */
.loading-state {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  padding: 60px 0; color: #909399; font-size: 14px;
}

/* ---- 表格 ---- */
.data-table { width: 100%; cursor: pointer; }
.data-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
.data-table :deep(.el-table__cell) { padding-left: 8px; padding-right: 8px; }
.name-link { font-weight: 500; }
.text-muted { color: #909399; font-size: 13px; }

/* ---- 分页 ---- */
.pagination-wrap {
  display: flex; justify-content: flex-end; align-items: center;
  padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px;
}
</style>
