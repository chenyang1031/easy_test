<template>
  <div class="project-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">项目管理</h2>
        <span class="page-subtitle" v-if="store.total > 0">共 {{ store.total }} 个项目</span>
      </div>
      <div class="page-header-right">
        <el-button @click="loadData" :icon="Refresh">刷新</el-button>
        <el-button type="primary" @click="goCreate" :icon="Plus">新增项目</el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 搜索栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          placeholder="搜索项目名称..."
          clearable
          style="width:260px"
          @keyup.enter="doSearch"
          @clear="doSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="doSearch" :icon="Search">查询</el-button>
      </div>

      <!-- 加载状态 -->
      <div v-if="store.loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="store.list.length === 0" description="暂无项目">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><FolderOpened /></el-icon>
        </template>
        <el-button type="primary" @click="goCreate" :icon="Plus">新增项目</el-button>
      </el-empty>

      <!-- 数据表格 -->
      <template v-else>
        <el-table :data="store.list" stripe border class="data-table">
          <el-table-column label="名称" min-width="180">
            <template #default="{ row }">
              <router-link :to="`/projects/${row.id}`" class="name-link" @click.stop>
                {{ row.name }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column label="描述" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="desc-text">{{ row.description || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="创建人" width="140">
            <template #default="{ row }">
              <div class="creator-cell">
                <span class="creator-avatar">{{ getInitial(row.created_by_name) }}</span>
                <span>{{ row.created_by_name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="170" align="right">
            <template #default="{ row }">
              <span class="time-cell">{{ formatTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right" align="center">
            <template #default="{ row }">
              <div class="table-actions" @click.stop>
                <el-button size="small" text @click="$router.push(`/projects/${row.id}`)">
                  <el-icon><View /></el-icon> 查看
                </el-button>
                <el-button size="small" text type="primary" @click="$router.push(`/projects/${row.id}/edit`)">
                  <el-icon><Edit /></el-icon> 编辑
                </el-button>
                <el-popconfirm title="确定删除此项目？" @confirm="deleteProject(row.id)">
                  <template #reference>
                    <el-button size="small" text type="danger">
                      <el-icon><Delete /></el-icon> 删除
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div v-if="store.total > store.pageSize" class="pagination-wrap">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { View, Edit, Delete, Plus, Refresh, Search, Loading, FolderOpened } from '@element-plus/icons-vue'
import { useProjectManageStore } from '../../../projects/stores/projectStore.js'
import { projectApi } from '../../../projects/api/index.js'

const router = useRouter()
const store = useProjectManageStore()

const searchText = ref('')

function getInitial(name) { return (name || '?').charAt(0).toUpperCase() }

function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadData() {
  const params = {}
  if (searchText.value) params.search = searchText.value
  await store.loadList(params)
}

function doSearch() { store.page = 1; loadData() }

function goCreate() {
  router.push('/projects/create').catch((err) => {
    console.error('导航失败:', err)
    ElMessage.error('页面跳转失败，请刷新页面后重试')
  })
}

async function deleteProject(id) {
  try {
    await store.remove(id)
    ElMessage.success('项目已删除')
  } catch (e) {
    ElMessage.error('删除失败: ' + (e.message || '未知错误'))
  }
}

onMounted(() => { loadData() })
</script>

<style scoped>
.project-list-page { padding: 0; background: var(--bg-body); min-height: 100%; }

/* ---- 页面标题 ---- */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px; margin-bottom: 20px;
}
.page-header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.page-subtitle { font-size: 14px; color: #909399; }
.page-header-right { display: flex; gap: 8px; align-items: center; }

/* ---- 卡片 ---- */
.panel-card {
  background: #fff; border-radius: 10px; padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
}

/* ---- 筛选栏 ---- */
.filter-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }

/* ---- 加载状态 ---- */
.loading-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 60px 0; color: #909399; font-size: 14px;
}

/* ---- 表格 ---- */
.data-table { width: 100%; }
.data-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
.name-link { color: #409eff; text-decoration: none; font-weight: 500; }
.name-link:hover { text-decoration: underline; }
.desc-text { color: #606266; font-size: 13px; }
.time-cell { font-size: 13px; color: #909399; }
.creator-cell { display: flex; align-items: center; gap: 8px; }
.creator-avatar {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
  background: #409eff; color: #fff;
  font-size: 12px; font-weight: 600; flex-shrink: 0;
}
.table-actions { display: flex; gap: 8px; justify-content: center; flex-wrap: nowrap; white-space: nowrap; }

/* ---- 分页 ---- */
.pagination-wrap { display: flex; justify-content: flex-end; padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px; }
</style>
