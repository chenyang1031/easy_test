<template>
  <div class="draft-box-manager">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">AI草稿箱</h2>
        <span class="page-subtitle">AI生成的测试用例草稿，可批量导入到项目中</span>
      </div>
      <div class="page-header-right">
        <el-button :icon="Refresh" @click="store.loadGroups()">刷新</el-button>
      </div>
    </div>

    <!-- 项目筛选 -->
    <div class="filter-bar">
      <el-select
        v-model="store.filterProjectId"
        placeholder="全部项目"
        clearable
        style="width:200px"
        @change="store.setFilterProject($event)"
      >
        <el-option v-for="p in store.projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-text type="info" size="small" v-if="store.filterProjectId">
        <el-icon><FolderOpened /></el-icon> 共 {{ store.groupsTotal }} 个草稿组
      </el-text>
    </div>

    <!-- 主体：左右分栏 -->
    <div class="split-panel">
      <!-- 左侧：草稿组列表 -->
      <div class="left-panel">
        <div class="panel-header">
          <span><el-icon color="#e6a23c"><Folder /></el-icon> 草稿组</span>
          <el-tag v-if="store.groups.length" size="small" type="primary" effect="plain" round>{{ store.groups.length }}</el-tag>
        </div>
        <div v-loading="store.groupsLoading" class="left-list">
          <el-empty v-if="!store.groupsLoading && store.groups.length === 0" description="暂无草稿组" :image-size="60" />
          <div
            v-for="g in store.groups" :key="g.id"
            class="group-item"
            :class="{ active: store.activeGroupId === g.id }"
            @click="store.loadDrafts(g.id, 1)"
          >
            <div class="group-item-top">
              <div class="group-name">{{ g.name }}</div>
              <el-tag :type="store.statusTag(g.status).type" size="small" effect="light" round>{{ store.statusTag(g.status).text }}</el-tag>
            </div>
            <div class="group-meta">
              <span class="group-count">{{ g.draft_count }} 条草稿</span>
              <span class="group-project">{{ g.project_name || '项目'+g.id }}</span>
            </div>
            <div class="group-time">{{ store.formatTime(g.created_at) }}</div>
          </div>
        </div>
        <div class="left-pagination" v-if="store.groupsTotal > 0">
          <el-pagination
            v-model:current-page="store.groupsPage"
            v-model:page-size="store.groupsPageSize"
            :total="store.groupsTotal"
            :page-sizes="[10, 20, 30, 50]"
            layout="prev, pager, next"
            @current-change="store.handleGroupsPageChange"
            @size-change="store.handleGroupsSizeChange"
          />
        </div>
      </div>

      <!-- 右侧：草稿列表 -->
      <div class="right-panel">
        <template v-if="!store.activeGroup">
          <div class="empty-right">
            <el-empty description="选择左侧草稿组查看详情" :image-size="80" />
          </div>
        </template>
        <template v-else>
          <div class="panel-header">
            <div class="panel-header-left">
              <el-icon color="#e6a23c"><FolderOpened /></el-icon>
              <span>{{ store.activeGroup.name }}</span>
            </div>
            <div class="header-actions">
              <el-button
                type="primary" size="small" :icon="Upload"
                :loading="store.importing" :disabled="store.selectedDraftIds.size === 0"
                @click="store.openImportDialog()"
              >导入选中 ({{ store.selectedDraftIds.size }})</el-button>
              <el-button
                type="danger" size="small" :icon="Delete"
                :loading="store.deleting" :disabled="store.selectedDraftIds.size === 0"
                @click="store.deleteSelectedDrafts()"
              >删除选中</el-button>
              <el-popconfirm title="确定删除整个草稿组？" @confirm="store.deleteGroup()">
                <template #reference>
                  <el-button type="danger" size="small" :icon="Delete" :loading="store.deleting" plain>删除组</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>

          <div class="right-content">
            <el-table
              v-loading="store.draftsLoading"
              :data="store.drafts"
              stripe
              border
              class="data-table"
              @selection-change="(rows) => store.selectedDraftIds = new Set(rows.filter(r => r.can_select).map(r => r.id))"
              ref="draftTable"
            >
              <el-table-column type="selection" width="42" :selectable="(row) => row.can_select" />
              <el-table-column prop="case_name" label="用例名称" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <span :style="{ color: row.can_select ? '#303133' : '#c0c4cc', fontWeight: 500 }">{{ row.case_name || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="方法" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="methodTag(row.request_method).type" size="small" effect="plain">{{ row.request_method }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="request_url" label="URL" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <code class="url-text">{{ row.request_url }}</code>
                </template>
              </el-table-column>
              <el-table-column label="导入状态" width="100" align="center">
                <template #default="{ row }">
                  <el-tag :type="store.importStatusTag(row.import_status).type" size="small" effect="light" round>
                    {{ store.importStatusTag(row.import_status).text }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="详情" width="80" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" :icon="View" size="small" @click="showDetail(row)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="right-pagination" v-if="store.draftsTotal > 0">
            <el-pagination
              v-model:current-page="store.draftsPage"
              v-model:page-size="store.draftsPageSize"
              :total="store.draftsTotal"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @current-change="store.handleDraftsPageChange"
              @size-change="store.handleDraftsSizeChange"
            />
          </div>
        </template>
      </div>
    </div>

    <!-- 导入弹窗 -->
    <el-dialog v-model="store.importDialogVisible" title="导入草稿到测试套件" width="600px" destroy-on-close @open="onImportDialogOpen" class="dialog-wrap">
      <div class="import-dialog-body">
        <el-alert type="info" :closable="false" show-icon class="import-alert">
          将选中的 <strong>{{ store.selectedDraftIds.size }}</strong> 条草稿导入为测试用例。
          <span v-if="importProjectName">目标项目：<strong>{{ importProjectName }}</strong></span>
        </el-alert>

        <el-radio-group v-model="store.importTargetType" class="import-radio-group">
          <el-radio value="none" size="large">不关联套件（仅创建测试用例）</el-radio>
          <el-radio value="existing" size="large">关联已有测试套件</el-radio>
          <el-radio value="new" size="large">创建新的测试套件</el-radio>
        </el-radio-group>

        <div class="import-option-panel">
          <template v-if="store.importTargetType === 'existing'">
            <el-select
              v-model="store.importExistingSuiteId"
              placeholder="请选择测试套件"
              style="width:100%"
              :loading="store.suitesLoading"
              size="large"
            >
              <el-option v-for="s in store.suites" :key="s.id" :label="s.name" :value="s.id">
                <span>{{ s.name }}</span>
                <span style="float:right;color:#909399;font-size: var(--el-font-size-extra-small)">项目: {{ s.project_name || '项目'+s.project_id }}</span>
              </el-option>
            </el-select>
          </template>
          <template v-if="store.importTargetType === 'new'">
            <el-input
              v-model="store.importNewSuiteName"
              placeholder="输入新套件名称，如：智能工牌-鉴权接口测试"
              size="large"
              maxlength="100"
            />
          </template>
        </div>
      </div>

      <template #footer>
        <el-button @click="store.importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="store.importing" @click="store.doImport()">确认导入</el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="用例详情" width="700px" destroy-on-close class="dialog-wrap">
      <template v-if="detailDraft">
        <el-descriptions :column="2" border size="small" class="detail-desc">
          <el-descriptions-item label="用例名称" :span="2" label-class-name="desc-label">{{ detailDraft.case_name }}</el-descriptions-item>
          <el-descriptions-item label="用例描述" :span="2" label-class-name="desc-label">
            <span class="desc-text">{{ detailDraft.description || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="请求方法" label-class-name="desc-label">
            <el-tag :type="methodTag(detailDraft.request_method).type" size="small">{{ detailDraft.request_method }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="导入状态" label-class-name="desc-label">
            <el-tag :type="store.importStatusTag(detailDraft.import_status).type" size="small">{{ store.importStatusTag(detailDraft.import_status).text }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="请求URL" :span="2" label-class-name="desc-label">
            <code class="detail-url">{{ detailDraft.request_url }}</code>
          </el-descriptions-item>
        </el-descriptions>
        <div class="detail-section">
          <div class="detail-section-title"><el-icon><List /></el-icon> 请求头</div>
          <pre class="detail-json">{{ formatHeaders(detailDraft.request_headers) }}</pre>
        </div>
        <div class="detail-section" v-if="hasParams(detailDraft.request_params)">
          <div class="detail-section-title"><el-icon><Switch /></el-icon> 请求参数</div>
          <pre class="detail-json">{{ formatParams(detailDraft.request_params) }}</pre>
        </div>
        <div class="detail-section">
          <div class="detail-section-title"><el-icon><Document /></el-icon> 请求体</div>
          <pre class="detail-json">{{ formatBody(detailDraft.request_body) }}</pre>
        </div>
        <div class="detail-section">
          <div class="detail-section-title"><el-icon><Select /></el-icon> 校验规则</div>
          <pre class="detail-json">{{ formatRules(detailDraft.validation_rules) }}</pre>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Refresh, FolderOpened, Folder, Upload, Delete, View, List, Document, Select, Switch } from '@element-plus/icons-vue'
import { useDraftBoxStore } from '../stores/draftBox.js'

const store = useDraftBoxStore()
const draftTable = ref(null)

const detailVisible = ref(false)
const detailDraft = ref(null)

const importProjectName = computed(() => store.activeGroup?.project_name || '')

function showDetail(row) { detailDraft.value = row; detailVisible.value = true }
function methodTag(m) {
  const map = { GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return { type: map[m] || 'info' }
}
function formatHeaders(h) {
  try { const d = typeof h === 'string' ? JSON.parse(h) : h; return JSON.stringify(d || {}, null, 2) } catch { return String(h || '-') }
}
function formatBody(b) {
  try { const d = typeof b === 'string' ? JSON.parse(b) : b; return JSON.stringify(d || {}, null, 2) } catch { return String(b || '-') }
}
function formatRules(r) {
  try { const d = typeof r === 'string' ? JSON.parse(r) : r; return JSON.stringify(d || [], null, 2) } catch { return String(r || '-') }
}
function hasParams(p) {
  return p && typeof p === 'object' && Object.keys(p).length > 0
}
function formatParams(p) {
  try { return JSON.stringify(p || {}, null, 2) } catch { return String(p || '-') }
}

function onImportDialogOpen() {
  const projectId = store.activeGroup?.project_id
  if (projectId) store.loadSuites(projectId)
}

onMounted(() => { store.loadProjects(); store.loadGroups() })
</script>

<style scoped>
.draft-box-manager { display:flex; flex-direction:column; gap:16px; flex:1; min-height:0; }

/* ---- 页面标题 ---- */
.page-header {
  display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;
}
.page-header-left { display:flex; align-items:baseline; gap:12px; }
.page-title { font-size:24px; font-weight:600; color:#303133; margin:0; line-height:1.3; }
.page-subtitle { font-size: var(--el-font-size-base); color:#909399; }
.page-header-right { display:flex; gap:8px; }

/* ---- 项目筛选 ---- */
.filter-bar { display:flex; align-items:center; gap:12px; flex-shrink:0; }

/* ---- 左右分栏面板 ---- */
.split-panel {
  display:flex; flex:1; min-height:0; overflow:hidden;
  background:#fff; border-radius:10px;
  box-shadow:0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  border:1px solid #ebeef5;
}

/* ---- 左面板 ---- */
.left-panel {
  width:300px; min-width:240px; border-right:1px solid #ebeef5;
  display:flex; flex-direction:column; overflow:hidden;
}
.panel-header {
  display:flex; align-items:center; justify-content:space-between;
  padding:14px 16px; font-weight:600; font-size: var(--fs-card-title); color:#303133;
  border-bottom:1px solid #ebeef5; flex-shrink:0; gap:8px;
}
.panel-header-left { display:flex; align-items:center; gap:6px; }
.header-actions { display:flex; gap:6px; flex-wrap:wrap; }
.left-list { flex:1; overflow-y:auto; padding:6px 0; }

.group-item {
  padding:12px 16px; cursor:pointer; transition:all .15s;
  border-left:3px solid transparent;
}
.group-item:hover { background:#f5f7fa; }
.group-item.active { background:#ecf5ff; border-left-color:#409eff; }
.group-item-top { display:flex; align-items:flex-start; justify-content:space-between; gap:8px; margin-bottom:6px; }
.group-name { font-weight:600; font-size: var(--fs-card-title); color:#303133; line-height:1.3; word-break:break-word; }
.group-meta { display:flex; align-items:center; gap:8px; font-size: var(--el-font-size-small); margin-bottom:4px; }
.group-count { color:#909399; }
.group-project { color:#606266; }
.group-time { font-size: var(--el-font-size-extra-small); color:#c0c4cc; }

/* ---- 右面板 ---- */
.right-panel { flex:1; display:flex; flex-direction:column; overflow:hidden; min-width:0; }
.right-panel > .panel-header { padding:14px 20px; }
.empty-right { display:flex; align-items:center; justify-content:center; flex:1; }
.right-content { flex:1; overflow:auto; padding:0; }

/* ---- 分页 ---- */
.left-pagination {
  padding:8px 12px; border-top:1px solid #ebeef5;
  display:flex; justify-content:center; flex-shrink:0;
  overflow:hidden; max-width:100%;
}
.left-pagination :deep(.el-pagination) {
  --el-pagination-button-size:26px;
  flex-wrap:nowrap; white-space:nowrap;
}
.left-pagination :deep(.el-pagination .el-pagination__total) { margin-right:4px; }
.left-pagination :deep(.el-pagination button, .el-pagination .el-pager li) { min-width:26px; }
.right-pagination {
  padding:16px 20px 0; border-top:1px solid #ebeef5; margin-top:16px;
  display:flex; justify-content:flex-end; flex-shrink:0;
}

/* ---- 表格 ---- */
.data-table { width:100%; }
.data-table :deep(th.el-table__cell) { background:#f6f8fa !important; color:#303133; font-weight:600; }
.url-text {
  font-size: var(--el-font-size-small); color:#606266; background:#f5f7fa;
  padding:2px 6px; border-radius:4px;
  display:inline-block; max-width:100%;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}

/* ---- 导入弹窗 ---- */
.import-alert { margin-bottom:20px; }
.import-radio-group { display:flex; flex-direction:column; gap:12px; margin-bottom:16px; }
.import-option-panel { padding-left:28px; min-height:40px; }

/* ---- 详情弹窗 ---- */
.detail-section { margin-top:16px; }
.detail-section-title { font-weight:600; font-size: var(--el-font-size-base); color:#606266; margin-bottom:6px; display:flex; align-items:center; gap:6px; }
.detail-desc :deep(.desc-label) { width:90px; color:#606266; font-weight:500; background:#fafafa; }
.detail-url {
  font-size: var(--el-font-size-small); color:#409eff; background:#ecf5ff;
  padding:2px 6px; border-radius:4px; word-break:break-all;
}
.desc-text {
  font-size: var(--el-font-size-small); color:#606266; line-height:1.6;
  white-space:pre-wrap; word-break:break-all;
}
.detail-json {
  background:#f6f8fa; border-radius:6px; padding:10px 14px;
  font-family:'Cascadia Code','Fira Code','Consolas',monospace;
  font-size: var(--el-font-size-small); line-height:1.6; white-space:pre-wrap; word-break:break-all;
  max-height:240px; overflow-y:auto; margin:0; border:1px solid #f0f0f0;
}

/* ---- 弹窗通用 ---- */
.dialog-wrap :deep(.el-dialog__body) { padding:20px; }
</style>
