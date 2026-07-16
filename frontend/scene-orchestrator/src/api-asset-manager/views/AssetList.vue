<template>
  <div class="api-asset-manager">
    <!-- ====== 页面标题 ====== -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">API资产管理</h2>
        <span class="page-subtitle">管理接口资产，支持分组导航、导入导出和AI批量生成</span>
      </div>
      <div class="page-header-right">
        <ApiProjectSelector />
        <template v-if="store.currentProjectId">
          <el-button @click="showImportModal = true" size="default">
            <el-icon><Upload /></el-icon> 导入
          </el-button>
          <el-button @click="handleExportOpenApi" size="default">
            <el-icon><Download /></el-icon> 导出OpenAPI
          </el-button>
          <el-button id="ai-batch-generate-btn" type="primary" @click="handleAiBatchGenerate" size="default">
            <el-icon><MagicStick /></el-icon> AI批量生成
          </el-button>
        </template>
      </div>
    </div>

    <!-- 主体三栏布局 -->
    <div class="manager-body" v-if="store.currentProjectId">
      <!-- 左侧：分组导航 -->
      <div class="panel-left">
        <div class="panel-card">
          <div class="panel-header">
            <span>分组导航</span>
            <div class="panel-header-actions">
              <el-button size="small" type="primary" @click="showGroupCreateModal = true">
                <el-icon><Plus /></el-icon>
              </el-button>
              <el-button size="small" type="danger" @click="handleDeleteGroup" :disabled="!store.currentGroupId">
                <el-icon><Delete /></el-icon>
              </el-button>
              <el-button size="small" @click="handleRefreshGroups">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="panel-body">
            <div class="group-search">
              <el-input v-model="groupSearchInput" placeholder="搜索分组名称" size="small" clearable @keyup.enter="store.groupSearchKeyword = groupSearchInput" @clear="groupSearchInput = ''; store.groupSearchKeyword = ''" />
              <el-button size="small" type="primary" @click="store.groupSearchKeyword = groupSearchInput">搜索</el-button>
            </div>
            <ApiProjectStats />
            <div class="group-tree-scroll">
              <GroupTree />
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：接口列表 -->
      <div class="panel-right">
        <div class="panel-card">
          <!-- 搜索筛选栏 -->
          <div class="asset-toolbar">
            <el-input v-model="store.searchKeyword" placeholder="搜索接口名称、URL或关键字" size="default" clearable style="flex:1; max-width:400px" @keyup.enter="handleSearch">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-button type="primary" size="default" @click="handleSearch">搜索</el-button>
            <el-select v-model="store.filterMethod" placeholder="全部 Method" clearable size="default" style="width:140px" @change="store.fetchAssets()">
              <el-option label="GET" value="GET" />
              <el-option label="POST" value="POST" />
              <el-option label="PUT" value="PUT" />
              <el-option label="DELETE" value="DELETE" />
              <el-option label="PATCH" value="PATCH" />
            </el-select>
            <el-select v-model="store.filterStatus" placeholder="全部状态" clearable size="default" style="width:140px" @change="store.fetchAssets()">
              <el-option label="草稿" value="draft" />
              <el-option label="可用" value="active" />
              <el-option label="已废弃" value="deprecated" />
            </el-select>
            <el-button type="primary" size="default" @click="$router.push('/api-assets/create')">
              <el-icon><Plus /></el-icon> 新增接口
            </el-button>
          </div>

          <!-- 批量操作栏 -->
          <BatchToolbar />

          <!-- 接口表格 -->
          <ApiAssetTable @edit="handleAssetEdit" @delete="handleAssetDelete" />

          <!-- 分页 -->
          <div class="asset-pagination">
            <el-pagination
              v-model:current-page="store.currentPage"
              v-model:page-size="store.pageSize"
              :total="store.totalCount"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @current-change="store.fetchAssets()"
              @size-change="store.fetchAssets()"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 未选择项目提示 -->
    <div class="no-project-hint" v-else>
      <el-empty description="请先在项目菜单创建项目，然后在上方下拉框中选择一个项目" />
    </div>

    <!-- 新建分组弹窗 -->
    <GroupCreateModal v-model="showGroupCreateModal" />
    <!-- 导入弹窗 -->
    <ImportModal v-model="showImportModal" />
    <!-- AI批量生成弹窗 -->
    <AIGenerateModal v-model="showAiGenerateModal" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Upload, Download, MagicStick, Search, Plus, Refresh, Delete } from '@element-plus/icons-vue'
import { useApiAssetStore } from '../stores/apiAsset.js'
import { apiAssetApi } from '../api/index.js'
import { ElMessageBox, ElMessage } from 'element-plus'
import ApiProjectSelector from '../components/ApiProjectSelector.vue'
import ApiProjectStats from '../components/ApiProjectStats.vue'
import GroupTree from '../components/GroupTree.vue'
import GroupCreateModal from '../components/GroupCreateModal.vue'
import ApiAssetTable from '../components/ApiAssetTable.vue'
import BatchToolbar from '../components/BatchToolbar.vue'
import ImportModal from '../components/ImportModal.vue'
import AIGenerateModal from '../components/AIGenerateModal.vue'

const router = useRouter()
const store = useApiAssetStore()

const showImportModal = ref(false)
const showGroupCreateModal = ref(false)
const showAiGenerateModal = ref(false)

function handleSearch() {
  store.currentPage = 1
  store.fetchAssets()
}

function handleExportOpenApi() {
  store.exportOpenApi().then(() => ElMessage.success('导出成功')).catch(e => ElMessage.error(e?.message || '导出失败'))
}

function handleAiBatchGenerate() {
  if (store.selectedAssetIds.size === 0) {
    if (store.assets.length === 0) { ElMessage.warning('当前无接口可生成'); return }
    store.setAISelectedAssets(store.assets)
  } else {
    store.setAISelectedAssets(store.assets.filter(a => store.selectedAssetIds.has(a.id)))
  }
  showAiGenerateModal.value = true
}

function handleAssetEdit(row) {
  router.push(`/api-assets/edit/${row.id}`)
}

function handleAssetDelete(row) {
  ElMessageBox.confirm('确定删除该接口吗？', '确认删除', {
    confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
  }).then(async () => {
    try { await apiAssetApi.remove(row.id); ElMessage.success('已删除'); store.fetchAssets(); store.fetchProjectStats() }
    catch (e) { ElMessage.error(e?.message || '删除失败') }
  }).catch(() => {})
}

function handleDeleteGroup() {
  if (!store.currentGroupId) return
  ElMessageBox.confirm('确定删除该分组吗？如果该分组下有子分组，子分组将变为根分组。', '确认删除',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try { await store.deleteGroup(store.currentGroupId); ElMessage.success('分组已删除') }
    catch (e) { ElMessage.error(e?.message || '删除失败') }
  }).catch(() => {})
}

function handleRefreshGroups() { store.fetchGroups() }
</script>

<style scoped>
.api-asset-manager { display: flex; flex-direction: column; flex: 1; min-height: 0; gap: 16px; }
.page-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; flex-shrink: 0; }
.page-header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.page-subtitle { font-size: var(--el-font-size-base); color: #909399; }
.page-header-right { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.manager-body { display: flex; flex: 1; gap: 16px; min-height: 0; overflow: hidden; }
.panel-left { width: 300px; flex-shrink: 0; }
.panel-card { background: #fff; border-radius: 10px; display: flex; flex-direction: column; height: 100%; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04); }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px 12px; border-bottom: 1px solid #ebeef5; font-weight: 600; font-size: 14px; }
.panel-header-actions { display: flex; gap: 4px; }
.panel-body { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.group-search { padding: 10px 14px; display: flex; gap: 8px; align-items: center; }
.group-search .el-input { flex: 1; }
.group-tree-scroll { flex: 1; overflow-y: auto; padding: 0 14px 12px; }
.panel-right { flex: 1; min-width: 0; }
.panel-right .panel-card { padding: 20px; overflow: visible; }
.asset-toolbar { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.asset-pagination { display: flex; justify-content: flex-end; align-items: center; padding-top: 16px; border-top: 1px solid #ebeef5; margin-top: 16px; }
.no-project-hint { flex: 1; display: flex; align-items: center; justify-content: center; }
</style>
