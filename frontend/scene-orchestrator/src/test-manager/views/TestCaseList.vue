<template>
  <div class="tc-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">测试用例</h2>
        <span class="page-subtitle" v-if="store.total !== null">共 {{ store.total }} 个用例</span>
      </div>
      <div class="page-header-right">
        <el-button @click="openGroupForm(null)"><el-icon><FolderAdd /></el-icon> 新建分组</el-button>
        <el-button @click="importExportDialogVisible = true"><el-icon><Download /></el-icon> 导入/导出</el-button>
        <el-button type="primary" @click="$router.push('/test-cases/create')"><el-icon><Plus /></el-icon> 新增用例</el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="12" class="filter-row">
          <el-col :xs="24" :sm="8" :md="6">
            <el-select v-model="filterProjectId" placeholder="选择项目" clearable class="filter-item" @change="onFilterProjectChange">
              <el-option v-for="p in projectStore.projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <el-input v-model="search" placeholder="搜索名称/描述/URL..." clearable class="filter-item" @keyup.enter="doSearch" @clear="doSearch">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </el-col>
          <el-col :xs="24" :sm="4" :md="4">
            <el-button type="primary" @click="doSearch" class="filter-item"><el-icon><Search /></el-icon> 查询</el-button>
          </el-col>
          <el-col :xs="24" :sm="24" :md="6">
            <el-button type="danger" :disabled="selectedIds.size === 0" @click="confirmBatchDelete" class="filter-item">
              <el-icon><Delete /></el-icon> 批量删除 ({{ selectedIds.size }})
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 分组卡片 -->
      <div v-if="filterProjectId && childGroups.length" class="group-section">
        <div class="section-header">
          <el-icon color="#e6a23c"><FolderOpened /></el-icon>
          <span class="section-title">子分组</span>
        </div>
        <el-row :gutter="16">
          <el-col v-for="g in childGroups" :key="g.id" :xl="6" :lg="8" :md="12" :sm="24">
            <el-card shadow="hover" class="group-card" @click="currentGroupId=g.id">
              <div class="group-card-inner">
                <div class="group-card-icon"><el-icon :size="24" color="#e6a23c"><Folder /></el-icon></div>
                <div class="group-card-body">
                  <div class="group-card-name">{{ g.name }}</div>
                  <div class="group-card-meta">
                    <el-tag size="small" type="info" round>{{ g.test_case_count || 0 }} 用例</el-tag>
                    <el-tag v-if="g.sub_group_count" size="small" type="info" round>{{ g.sub_group_count }} 子分组</el-tag>
                  </div>
                </div>
                <div class="group-card-actions" @click.stop>
                  <el-button size="small" text @click="openGroupForm(g)" title="编辑分组"><el-icon><Edit /></el-icon></el-button>
                  <el-popconfirm title="确定删除此分组？" @confirm="deleteGroup(g.id)">
                    <template #reference>
                      <el-button size="small" text type="danger" title="删除分组"><el-icon><Delete /></el-icon></el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 加载状态 -->
      <div v-if="store.loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="store.list.length===0" description="暂无测试用例">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><Document /></el-icon>
        </template>
        <el-button type="primary" @click="$router.push('/test-cases/create')">新建用例</el-button>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table :data="store.list" stripe border class="data-table" @row-click="(row) => $router.push(`/test-cases/${row.id}`)" @selection-change="onSelectionChange">
          <el-table-column type="selection" width="42" />
          <el-table-column label="名称" min-width="200" show-overflow-tooltip>
            <template #default="{row}">
              <router-link :to="`/test-cases/${row.id}`" class="name-link" @click.stop>{{ row.name }}</router-link>
            </template>
          </el-table-column>
          <el-table-column label="项目" width="110" show-overflow-tooltip prop="project_name" />
          <el-table-column label="分组" width="110" show-overflow-tooltip prop="group_name" />
          <el-table-column label="方法" width="80" align="center">
            <template #default="{row}"><RequestMethodBadge :method="row.request_method" /></template>
          </el-table-column>
          <el-table-column label="URL" min-width="220" show-overflow-tooltip>
            <template #default="{row}"><code class="url-code">{{ row.request_url }}</code></template>
          </el-table-column>
          <el-table-column label="状态码" width="80" align="center">
            <template #default="{row}"><el-tag size="small" type="info" effect="plain">{{ row.expected_status_code }}</el-tag></template>
          </el-table-column>
          <el-table-column label="更新时间" width="160" align="right">
            <template #default="{row}">{{ formatDateTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{row}">
              <div class="table-actions" @click.stop>
                <el-button size="small" text @click="$router.push(`/test-cases/${row.id}`)">查看</el-button>
                <el-button size="small" text type="primary" @click="$router.push(`/test-cases/${row.id}/edit`)">编辑</el-button>
                <el-button size="small" text type="success" @click="$router.push(`/test-cases/${row.id}/run`)">运行</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrap" v-if="store.total > store.pageSize">
          <el-pagination
            v-model:current-page="store.page"
            v-model:page-size="store.pageSize"
            :total="store.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="loadData"
            @size-change="(s) => { store.pageSize = s; loadData() }"
          />
        </div>
      </template>
    </div>

    <GroupFormDialog v-model="groupDialogVisible" :editing="editingGroup" :project-id="filterProjectId" :groups="groupStore.flatList" type="testCase" @saved="onGroupSaved" />
    <TestCaseImportExportDialog v-model="importExportDialogVisible" :project-id="filterProjectId" :selected-case-ids="Array.from(selectedIds)" @success="onImportSuccess" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { useProjectStore } from '../stores/project.js'
import { useTestCaseStore } from '../stores/testCase.js'
import { useTestCaseGroupStore } from '../stores/testCaseGroup.js'
import { formatDateTime } from '../composables/useFormat.js'
import RequestMethodBadge from '../components/common/RequestMethodBadge.vue'
import GroupFormDialog from '../components/group/GroupFormDialog.vue'
import TestCaseImportExportDialog from '../components/testCase/TestCaseImportExportDialog.vue'

const projectStore = useProjectStore()
const store = useTestCaseStore()
const groupStore = useTestCaseGroupStore()

const search = ref('')
const filterProjectId = ref(null)
const currentGroupId = ref(null)
const selectedIds = ref(new Set())

const childGroups = computed(() => {
  if (!filterProjectId.value) return []
  const all = groupStore.flatList
  return currentGroupId.value ? all.filter(g => g.parent === currentGroupId.value) : all.filter(g => !g.parent)
})

function onFilterProjectChange(val) { filterProjectId.value = val; projectStore.setProject(val) }

const groupDialogVisible = ref(false)
const editingGroup = ref(null)
const importExportDialogVisible = ref(false)
function openGroupForm(g) { editingGroup.value = g || null; groupDialogVisible.value = true }

async function onGroupSaved(data) {
  try {
    if (data.id) await groupStore.update(data.id, { name:data.name, parent:data.parent, project:filterProjectId.value })
    else await groupStore.create({ name:data.name, parent:data.parent, project:filterProjectId.value })
    ElMessage.success('已保存')
  } catch (e) { ElMessage.error(e.message) }
}
async function deleteGroup(id) {
  try { await groupStore.remove(id, filterProjectId.value); ElMessage.success('已删除') }
  catch (e) { ElMessage.error(e.message) }
}

function onSelectionChange(rows) {
  selectedIds.value = new Set(rows.map(r => r.id))
}

async function confirmBatchDelete() {
  const ids = Array.from(selectedIds.value)
  if (ids.length === 0) { ElMessage.warning('请先选择测试用例'); return }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 个测试用例？`, '批量删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
  } catch { return }
  try {
    const data = await store.batchDelete(ids)
    ElMessage.success(`已删除 ${data.deleted_count} 个测试用例`)
    selectedIds.value = new Set()
  } catch (e) { ElMessage.error('批量删除失败: ' + (e.message || '未知错误')) }
}

async function loadData() {
  const params = {}
  if (filterProjectId.value) params.project = filterProjectId.value
  if (currentGroupId.value) params.group = currentGroupId.value
  if (search.value) params.search = search.value
  await store.loadList(params)
}
function doSearch() { store.page = 1; loadData() }
function onImportSuccess() { importExportDialogVisible.value = false; loadData() }

onMounted(() => {
  if (!projectStore.projects.length) projectStore.loadProjects()
  filterProjectId.value = projectStore.currentProjectId
  if (filterProjectId.value) groupStore.loadList(filterProjectId.value)
  loadData()
})
watch(() => projectStore.currentProjectId, (id) => { filterProjectId.value = id; store.page=1; currentGroupId.value=null; if(id) groupStore.loadList(id); loadData() })
watch(currentGroupId, () => { store.page=1; loadData() })
</script>

<style scoped>
/* ---- 页面基础 ---- */
.tc-list { padding:0; }

/* ---- 页面标题 ---- */
.page-header {
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:20px; flex-wrap:wrap; gap:12px;
}
.page-header-left { display:flex; align-items:baseline; gap:12px; }
.page-title { font-size:24px; font-weight:600; color:#303133; margin:0; line-height:1.3; }
.page-subtitle { font-size:14px; color:#909399; }
.page-header-right { display:flex; gap:8px; }

/* ---- 内容卡片 ---- */
.panel-card {
  background:#fff; border-radius:10px; padding:20px;
  box-shadow:0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  transition:box-shadow .2s;
}

/* ---- 筛选栏 ---- */
.filter-bar { margin-bottom:16px; }
.filter-row { display:flex; align-items:center; }
.filter-row :deep(.el-col) { min-height:0; }
.filter-item { width:100%; }

/* ---- 筛选条件标签 ---- */
/* ---- 分组区域 ---- */
.group-section { margin-bottom:18px; padding-bottom:16px; border-bottom:1px solid #f0f0f0; }
.section-header { display:flex; align-items:center; gap:6px; margin-bottom:12px; }
.section-title { font-size:14px; font-weight:600; color:#606266; }

.group-card { cursor:pointer; transition:transform .15s, box-shadow .15s; border:1px solid #ebeef5; }
.group-card:hover { transform:translateY(-1px); box-shadow:0 4px 12px rgba(0,0,0,.08); }
.group-card :deep(.el-card__body) { padding:14px; }
.group-card-inner { display:flex; align-items:flex-start; gap:12px; }
.group-card-icon { flex-shrink:0; padding-top:2px; }
.group-card-body { flex:1; min-width:0; }
.group-card-name { font-size:14px; font-weight:600; color:#303133; margin-bottom:6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.group-card-meta { display:flex; gap:4px; flex-wrap:wrap; }
.group-card-actions { display:flex; gap:2px; flex-shrink:0; opacity:0; transition:opacity .15s; }
.group-card:hover .group-card-actions { opacity:1; }

/* ---- 加载状态 ---- */
.loading-state {
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  gap:12px; padding:60px 0; color:#909399; font-size:14px;
}

/* ---- 数据表格 ---- */
.data-table { width:100%; }
.data-table :deep(th.el-table__cell) { background:#f6f8fa !important; color:#303133; font-weight:600; }
.data-table :deep(.el-table__row) { cursor:pointer; transition:background .15s; }
.data-table :deep(.el-table__row:hover) { background:#f0f7ff !important; }
.name-link { color:#409eff; text-decoration:none; font-weight:500; }
.name-link:hover { text-decoration:underline; }
.url-code {
  font-size:13px; color:#606266; background:#f5f7fa;
  padding:2px 8px; border-radius:4px;
  display:inline-block; max-width:100%;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.table-actions { display:flex; gap:4px; flex-wrap:nowrap; white-space:nowrap; }

/* ---- 分页 ---- */
.pagination-wrap { display:flex; justify-content:flex-end; align-items:center; padding-top:16px; border-top:1px solid #ebeef5; margin-top:16px; }
</style>
