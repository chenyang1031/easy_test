<template>
  <div class="ts-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">测试套件</h2>
        <span class="page-subtitle" v-if="store.total !== null">共 {{ store.total }} 个套件</span>
      </div>
      <div class="page-header-right">
        <el-button @click="openGroupForm(null)"><el-icon><FolderAdd /></el-icon> 新建分组</el-button>
        <el-button type="primary" @click="$router.push('/test-suites/create')"><el-icon><Plus /></el-icon> 新增套件</el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="12" class="filter-row">
          <el-col :xs="24" :sm="8" :md="5">
            <el-select v-model="filterProjectId" placeholder="选择项目" clearable class="filter-item" @change="onFilterProjectChange">
              <el-option v-for="p in projectStore.projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="10" :md="7">
            <el-input v-model="search" placeholder="搜索套件名称/描述..." clearable class="filter-item" @keyup.enter="doSearch" @clear="doSearch">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </el-col>
          <el-col :xs="24" :sm="6" :md="4">
            <el-button type="primary" @click="doSearch" class="filter-item" style="width:100%"><el-icon><Search /></el-icon> 查询</el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 分组卡片区域 -->
      <div v-if="filterProjectId && childGroups.length" class="group-section">
        <div class="section-header">
          <el-icon color="#e6a23c" :size="18"><FolderOpened /></el-icon>
          <span class="section-title">子分组</span>
          <span class="section-count">{{ childGroups.length }} 个分组</span>
        </div>
        <el-row :gutter="16">
          <el-col v-for="g in childGroups" :key="g.id" :xl="6" :lg="8" :md="12" :sm="24">
            <el-card shadow="never" class="group-card" @click="currentGroupId=g.id">
              <div class="group-card-inner">
                <div class="group-card-icon">
                  <el-icon :size="28" color="#e6a23c"><Folder /></el-icon>
                </div>
                <div class="group-card-body">
                  <div class="group-card-name">
                    {{ g.name }}
                    <el-tag v-if="g.sub_group_count" size="small" round class="sub-tag">{{ g.sub_group_count }} 子分组</el-tag>
                  </div>
                  <div class="group-card-meta">
                    <span class="meta-item">
                      <el-icon><Document /></el-icon>
                      {{ g.test_suite_count || 0 }} 套件
                    </span>
                  </div>
                </div>
                <div class="group-card-actions" @click.stop>
                  <el-tooltip content="编辑分组" placement="top">
                    <el-button size="small" text @click="openGroupForm(g)"><el-icon><Edit /></el-icon></el-button>
                  </el-tooltip>
                  <el-popconfirm title="确定删除此分组？" @confirm="deleteGroup(g.id)">
                    <template #reference>
                      <el-tooltip content="删除分组" placement="top">
                        <el-button size="small" text type="danger"><el-icon><Delete /></el-icon></el-button>
                      </el-tooltip>
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
      <el-empty v-else-if="store.list.length === 0" description="暂无测试套件">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><FolderOpened /></el-icon>
        </template>
        <el-button type="primary" @click="$router.push('/test-suites/create')">新建套件</el-button>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table :data="store.list" stripe class="data-table" @row-click="(row) => $router.push(`/test-suites/${row.id}`)">
          <el-table-column label="名称" min-width="200" show-overflow-tooltip>
            <template #default="{row}">
              <div class="name-cell">
                <router-link :to="`/test-suites/${row.id}`" class="name-link" @click.stop>{{ row.name }}</router-link>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="项目" width="120" show-overflow-tooltip prop="project_name" />
          <el-table-column label="分组" width="120" show-overflow-tooltip>
            <template #default="{row}">
              <span v-if="row.group_name" class="group-cell">
                <el-icon :size="14" color="#e6a23c"><Folder /></el-icon>
                {{ row.group_name }}
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="用例数" width="80" align="center">
            <template #default="{row}">
              <el-tag size="small" effect="plain" round>{{ row.test_case_count || 0 }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建人" width="130">
            <template #default="{row}">
              <AvatarName :username="row.created_by_name" />
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="160" align="right">
            <template #default="{row}">
              <span class="time-cell">{{ formatDateTime(row.updated_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{row}">
              <div class="table-actions" @click.stop>
                <el-tooltip content="运行套件" placement="top">
                  <el-button size="small" text type="success" @click="$router.push(`/test-suites/${row.id}/run`)">
                    <el-icon><VideoPlay /></el-icon> 运行
                  </el-button>
                </el-tooltip>
                <el-divider direction="vertical" />
                <el-tooltip content="查看详情" placement="top">
                  <el-button size="small" text @click="$router.push(`/test-suites/${row.id}`)">查看</el-button>
                </el-tooltip>
                <el-tooltip content="编辑套件" placement="top">
                  <el-button size="small" text type="primary" @click="$router.push(`/test-suites/${row.id}/edit`)">编辑</el-button>
                </el-tooltip>
                <el-popconfirm title="确定删除此套件？" @confirm="deleteSuite(row.id)">
                  <template #reference>
                    <el-tooltip content="删除套件" placement="top">
                      <el-button size="small" text type="danger"><el-icon><Delete /></el-icon></el-button>
                    </el-tooltip>
                  </template>
                </el-popconfirm>
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

    <GroupFormDialog v-model="groupDialogVisible" :editing="editingGroup" :project-id="filterProjectId" :groups="groupStore.flatList" type="testSuite" @saved="onGroupSaved" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useProjectStore } from '../stores/project.js'
import { useTestSuiteStore } from '../stores/testSuite.js'
import { useTestSuiteGroupStore } from '../stores/testSuiteGroup.js'
import { formatDateTime } from '../composables/useFormat.js'
import AvatarName from '../components/common/AvatarName.vue'
import GroupFormDialog from '../components/group/GroupFormDialog.vue'

const projectStore = useProjectStore()
const store = useTestSuiteStore()
const groupStore = useTestSuiteGroupStore()

const search = ref('')
const filterProjectId = ref(null)
const currentGroupId = ref(null)

const childGroups = computed(() => {
  if (!filterProjectId.value) return []
  const all = groupStore.flatList
  return currentGroupId.value ? all.filter(g => g.parent === currentGroupId.value) : all.filter(g => !g.parent)
})

function onFilterProjectChange(val) {
  filterProjectId.value = val
  projectStore.setProject(val)
}

const groupDialogVisible = ref(false)
const editingGroup = ref(null)

function openGroupForm(g) { editingGroup.value = g || null; groupDialogVisible.value = true }

async function onGroupSaved(data) {
  try {
    if (data.id) await groupStore.update(data.id, { name: data.name, parent: data.parent, project: filterProjectId.value })
    else await groupStore.create({ name: data.name, parent: data.parent, project: filterProjectId.value })
    ElMessage.success('已保存')
  } catch (e) { ElMessage.error(e.message) }
}
async function deleteGroup(id) { try { await groupStore.remove(id, filterProjectId.value); ElMessage.success('已删除') } catch (e) { ElMessage.error(e.message) } }
async function deleteSuite(id) { try { await store.remove(id); ElMessage.success('已删除'); loadData() } catch (e) { ElMessage.error(e.message) } }

async function loadData() {
  const params = {}
  if (filterProjectId.value) params.project = filterProjectId.value
  if (currentGroupId.value) params.group = currentGroupId.value
  if (search.value) params.search = search.value
  await store.loadList(params)
}
function doSearch() { store.page = 1; loadData() }

onMounted(() => {
  filterProjectId.value = projectStore.currentProjectId
  if (filterProjectId.value) groupStore.loadList(filterProjectId.value)
  loadData()
})
watch(() => projectStore.currentProjectId, (id) => {
  filterProjectId.value = id
  store.page = 1
  currentGroupId.value = null
  if (id) groupStore.loadList(id)
  loadData()
})
watch(currentGroupId, () => { store.page = 1; loadData() })
</script>

<style scoped>
/* ---- 页面基础 ---- */
.ts-list { padding: 0; }

/* ---- 页面标题 ---- */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px; flex-wrap: wrap; gap: 12px;
}
.page-header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.page-subtitle { font-size: 14px; color: #909399; }
.page-header-right { display: flex; gap: 8px; }

/* ---- 内容卡片 ---- */
.panel-card {
  background: #fff; border-radius: 10px; padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
}

/* ---- 筛选栏 ---- */
.filter-bar { margin-bottom: 16px; }
.filter-item { width: 100%; }
.filter-row { align-items: center; }
.filter-row .el-col { min-height: 0; }

/* ---- 分组区域 ---- */
.group-section { margin-bottom: 18px; padding-bottom: 16px; border-bottom: 1px solid #f0f0f0; }
.section-header { display: flex; align-items: center; gap: 6px; margin-bottom: 12px; }
.section-title { font-size: 14px; font-weight: 600; color: #606266; }
.section-count { font-size: 12px; color: #909399; margin-left: auto; }

.group-card {
  cursor: pointer; transition: transform .15s, box-shadow .15s;
  border: 1px solid #ebeef5; border-radius: 8px;
}
.group-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0,0,0,.1);
  border-color: #d9d9d9;
}
.group-card :deep(.el-card__body) { padding: 14px; }
.group-card-inner { display: flex; align-items: flex-start; gap: 12px; }
.group-card-icon { flex-shrink: 0; padding-top: 2px; }
.group-card-body { flex: 1; min-width: 0; }
.group-card-name {
  font-size: 14px; font-weight: 600; color: #303133;
  margin-bottom: 6px; display: flex; align-items: center; gap: 6px;
}
.group-card-name .sub-tag { font-size: 11px; padding: 0 6px; height: 20px; line-height: 20px; }
.group-card-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-item { font-size: 12px; color: #909399; display: flex; align-items: center; gap: 3px; }
.group-card-actions {
  display: flex; gap: 2px; flex-shrink: 0;
  opacity: 0; transition: opacity .2s;
}
.group-card:hover .group-card-actions { opacity: 1; }

/* ---- 加载状态 ---- */
.loading-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 60px 0; color: #909399; font-size: 14px;
}

/* ---- 数据表格 ---- */
.data-table { width: 100%; }
.data-table :deep(th.el-table__cell) {
  background: #f6f8fa !important; color: #303133; font-weight: 600;
  padding: 10px 8px;
}
.data-table :deep(.el-table__row) { cursor: pointer; transition: background .15s; }
.data-table :deep(.el-table__row:hover) { background: #f0f7ff !important; }
.data-table :deep(.cell) { padding-left: 8px; padding-right: 8px; }

.name-cell { display: flex; align-items: center; gap: 6px; }
.name-link { color: #409eff; text-decoration: none; font-weight: 500; font-size: 14px; }
.name-link:hover { text-decoration: underline; color: #66b1ff; }

.group-cell { display: flex; align-items: center; gap: 4px; color: #606266; font-size: 13px; }
.text-muted { color: #c0c4cc; }
.time-cell { font-size: 13px; color: #909399; }

.table-actions {
  display: flex; gap: 2px; flex-wrap: nowrap; white-space: nowrap; align-items: center;
}
.table-actions :deep(.el-button) { font-size: 13px; }
.table-actions :deep(.el-divider--vertical) { height: 14px; margin: 0 4px; }

/* ---- 分页 ---- */
.pagination-wrap { display: flex; justify-content: flex-end; align-items: center; padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px; }

/* ---- 响应式 ---- */
@media (max-width: 768px) {
  .page-title { font-size: 20px; }
  .table-actions { flex-wrap: wrap; }
}
</style>
