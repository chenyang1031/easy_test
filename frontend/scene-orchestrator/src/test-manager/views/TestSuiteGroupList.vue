<template>
  <div class="group-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">测试套件分组</h2>
        <span class="page-subtitle">管理测试套件的分层结构</span>
      </div>
      <div class="page-header-right">
        <el-button :disabled="!filterProjectId" @click="toggleExpandAll">
          <el-icon><component :is="allExpanded ? 'Fold' : 'Expand'" /></el-icon>
          {{ allExpanded ? '全部折叠' : '全部展开' }}
        </el-button>
        <el-button type="primary" :disabled="!filterProjectId" @click="openForm(null)">
          <el-icon><Plus /></el-icon> 新建分组
        </el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="12" class="filter-row">
          <el-col :xs="24" :sm="8" :md="6">
            <el-select v-model="filterProjectId" placeholder="选择项目进行过滤" clearable class="filter-item" @change="onProjectChange">
              <el-option v-for="p in projectStore.projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="16" :md="8">
            <div class="filter-item search-with-btn">
              <el-input v-model="searchQuery" placeholder="搜索分组名称..." clearable @keyup.enter="onSearchInput">
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <el-button type="primary" @click="onSearchInput">搜索</el-button>
            </div>
          </el-col>
          <el-col :xs="24" :sm="24" :md="10">
            <span class="filter-hint" v-if="!filterProjectId">
              <el-icon><InfoFilled /></el-icon> 当前显示全部项目的分组，请选择项目以管理分组
            </span>
          </el-col>
        </el-row>
      </div>

      <!-- 加载中 -->
      <div v-if="store.loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 加载出错 -->
      <div v-else-if="store.error" class="error-state">
        <el-alert type="error" :title="store.error" show-icon :closable="false" />
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="displayTreeData.length === 0" :description="filterProjectId ? '暂无分组数据' : '请先选择一个项目'">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><FolderOpened /></el-icon>
        </template>
        <el-button v-if="filterProjectId" type="primary" @click="openForm(null)">创建第一个分组</el-button>
      </el-empty>

      <!-- 分组树 -->
      <el-tree
        v-else-if="displayTreeData.length"
        ref="treeRef"
        :data="displayTreeData"
        :props="{ children: 'children', label: 'name' }"
        node-key="id"
        :default-expand-all="true"
        :highlight-current="false"
        :filter-node-method="filterNode"
        class="group-tree"
      >
        <template #default="{ data }">
          <div class="tree-node" :style="{ borderLeftColor: getLevelColor(data._depth || 0) }">
            <div class="tree-node-main">
              <el-icon :color="getLevelColor(data._depth || 0)" :size="18">
                <component :is="data.children && data.children.length ? 'FolderOpened' : 'Folder'" />
              </el-icon>
              <span class="tree-name">{{ data.name }}</span>
            </div>
            <div class="tree-node-meta">
              <el-tag size="small" effect="plain" round>{{ data.test_suite_count || 0 }} 套件</el-tag>
              <el-tag v-if="data.sub_group_count" size="small" type="warning" effect="plain" round>{{ data.sub_group_count }} 子分组</el-tag>
            </div>
            <div class="tree-node-actions">
              <el-tooltip content="查看套件列表" placement="top">
                <el-button link type="primary" size="small" @click.stop="$router.push(`/test-suites?group=${data.id}`)">
                  <el-icon><View /></el-icon> 查看套件
                </el-button>
              </el-tooltip>
              <el-divider direction="vertical" />
              <el-tooltip content="编辑分组" placement="top">
                <el-button link type="primary" size="small" @click.stop="openForm(data)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-popconfirm title="确定删除此分组？其子分组也将一并删除。" @confirm="delGroup(data.id)">
                <template #reference>
                  <el-tooltip content="删除分组" placement="top">
                    <el-button link type="danger" size="small"><el-icon><Delete /></el-icon></el-button>
                  </el-tooltip>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </template>
      </el-tree>
    </div>

    <GroupFormDialog v-model="dialogVisible" :editing="editingGroup" :project-id="filterProjectId" :groups="store.flatList" type="testSuite" @saved="onSaved" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { useProjectStore } from '../stores/project.js'
import { useTestSuiteGroupStore } from '../stores/testSuiteGroup.js'
import GroupFormDialog from '../components/group/GroupFormDialog.vue'

const projectStore = useProjectStore()
const store = useTestSuiteGroupStore()

const filterProjectId = ref(null)
const dialogVisible = ref(false)
const editingGroup = ref(null)
const searchQuery = ref('')
const treeRef = ref(null)
const allExpanded = ref(true)

// 给树数据附加深度信息
const displayTreeData = computed(() => {
  const addDepth = (nodes, depth = 0) => {
    return nodes.map(n => ({
      ...n,
      _depth: depth,
      children: n.children ? addDepth(n.children, depth + 1) : undefined,
    }))
  }
  return addDepth(store.treeData)
})

// 层级颜色
const levelColors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb']
function getLevelColor(depth) {
  return levelColors[depth % levelColors.length]
}

function onProjectChange(val) {
  filterProjectId.value = val
  projectStore.setProject(val)
  store.loadTree(val)
}

function openForm(g) {
  editingGroup.value = g || null
  dialogVisible.value = true
}

async function onSaved(data) {
  try {
    const projectId = filterProjectId.value
    if (!projectId) { ElMessage.warning('请先选择一个项目'); return }
    if (data.id) await store.update(data.id, { name: data.name, parent: data.parent, project: projectId })
    else await store.create({ name: data.name, parent: data.parent, project: projectId })
    await store.loadTree(projectId)
    ElMessage.success('已保存')
  } catch (e) { ElMessage.error(e.message) }
}

async function delGroup(id) {
  try {
    await store.remove(id, filterProjectId.value)
    await store.loadTree(filterProjectId.value)
    ElMessage.success('已删除')
  } catch (e) { ElMessage.error(e.message) }
}

// 树搜索
function onSearchInput() {
  nextTick(() => {
    treeRef.value?.filter(searchQuery.value)
  })
}

function filterNode(value, data) {
  if (!value) return true
  return data.name.toLowerCase().includes(value.toLowerCase())
}

// 展开/折叠
function toggleExpandAll() {
  allExpanded.value = !allExpanded.value
  const nodes = treeRef.value?.store?.nodes
  if (!nodes) return
  Object.values(nodes).forEach(node => {
    if (node.childNodes?.length) {
      node.expanded = allExpanded.value
    }
  })
}

onMounted(() => {
  store.loadTree()
})
</script>

<style scoped>
/* ---- 页面基础 ---- */
.group-list { padding: 0; }

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
  min-height: 200px;
}

/* ---- 筛选栏 ---- */
.filter-bar { margin-bottom: 16px; }
.filter-row { align-items: center; }
.filter-item { width: 100%; }
.search-with-btn { display: flex; gap: 8px; align-items: center; }
.search-with-btn .el-input { flex: 1; }
.filter-hint {
  font-size: 13px; color: #909399; display: flex; align-items: center; gap: 6px;
  padding: 4px 0;
}

/* ---- 状态 ---- */
.loading-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 60px 0; color: #909399; font-size: 14px;
}
.error-state { margin-bottom: 12px; }

/* ---- 分组树 ---- */
.group-tree { font-size: 14px; }
.group-tree :deep(.el-tree-node__content) {
  height: auto; padding: 4px 0;
  border-radius: 6px;
  transition: background-color .15s;
}
.group-tree :deep(.el-tree-node__content:hover) {
  background-color: #f5f7fa;
}

.tree-node {
  display: flex; align-items: center; gap: 10px;
  flex: 1; padding: 8px 12px; width: 100%; flex-wrap: wrap;
  border-left: 3px solid transparent;
  border-radius: 0 4px 4px 0;
  transition: background-color .15s;
}
.tree-node:hover {
  background-color: #fafafa;
}
.tree-node-main {
  display: flex; align-items: center; gap: 6px; flex-shrink: 0;
}
.tree-name {
  font-weight: 600; font-size: 14px; color: #303133;
}
.tree-node-meta { display: flex; gap: 4px; align-items: center; }
.tree-node-meta :deep(.el-tag) {
  font-size: 12px; padding: 0 6px; height: 22px; line-height: 22px;
}

.tree-node-actions {
  display: flex; gap: 2px; align-items: center;
  margin-left: auto; flex-shrink: 0;
  opacity: .5; transition: opacity .2s;
}
.tree-node:hover .tree-node-actions { opacity: 1; }
.tree-node-actions :deep(.el-button) { font-size: 13px; }
.tree-node-actions :deep(.el-divider--vertical) {
  height: 14px; margin: 0 4px;
}

/* ---- 响应式 ---- */
@media (max-width: 768px) {
  .page-title { font-size: 20px; }
  .tree-node { padding: 6px 8px; }
  .tree-name { font-size: 13px; }
  .tree-node-actions { opacity: .8; }
}
</style>
