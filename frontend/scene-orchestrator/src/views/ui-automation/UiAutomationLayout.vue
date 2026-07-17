<template>
  <div class="ui-automation-page">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">UI 自动化</h2>
        <span class="page-subtitle">页面元素管理、用例编排、自动化执行与 AI 驱动测试</span>
      </div>
      <div class="page-header-right">
        <el-select v-model="selectedProject" placeholder="选择项目" size="small" style="width: 200px" @change="onProjectChange">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_modules }}</div>
        <div class="stat-label">模块</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_pages }}</div>
        <div class="stat-label">页面</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_elements }}</div>
        <div class="stat-label">元素</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_test_cases }}</div>
        <div class="stat-label">测试用例</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_executions }}</div>
        <div class="stat-label">执行次数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.pass_rate }}%</div>
        <div class="stat-label">通过率</div>
      </div>
    </div>

    <!-- 主内容区：左侧模块树 + 右侧内容 -->
    <div class="ui-main-layout">
      <div class="ui-tree-panel">
        <div class="tree-header">
          <span>模块树</span>
          <el-button type="primary" size="small" text @click="showAddModule = true">+ 新增</el-button>
        </div>
        <el-tree
          :data="moduleTree"
          node-key="id"
          :props="{ label: 'name', children: 'children' }"
          highlight-current
          default-expand-all
          @node-click="onModuleClick"
          draggable
          @node-drop="onNodeDrop"
        >
          <template #default="{ node, data }">
            <span class="tree-node-label">
              <span>{{ data.name }}</span>
              <span class="tree-node-count">{{ data.element_count || 0 }}</span>
            </span>
          </template>
        </el-tree>
      </div>

      <div class="ui-content-panel">
        <!-- 子路由内容 -->
        <router-view :project-id="selectedProject" :module-id="selectedModuleId" @refresh="loadStats" />
      </div>
    </div>

    <!-- 新增模块对话框 -->
    <el-dialog v-model="showAddModule" title="新增模块" width="400px">
      <el-form :model="newModule" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="newModule.name" placeholder="模块名称" />
        </el-form-item>
        <el-form-item label="父模块">
          <el-tree-select v-model="newModule.parent" :data="moduleTreeOptions" :props="{ label: 'name', value: 'id', children: 'children' }" check-strictly placeholder="无（顶级模块）" clearable style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newModule.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddModule = false">取消</el-button>
        <el-button type="primary" @click="createModule" :loading="creating">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { uiModuleApi, uiDashboardApi } from '../../api/uiAutomation'
import { http } from '../../api/http'

const router = useRouter()
const projects = ref([])
const selectedProject = ref(null)
const moduleTree = ref([])
const stats = ref(null)
const selectedModuleId = ref(null)
const showAddModule = ref(false)
const creating = ref(false)
const newModule = ref({ name: '', parent: null, description: '' })

const moduleTreeOptions = computed(() => [{ id: null, name: '顶级模块', children: moduleTree.value }])

async function loadProjects() {
  try {
    const data = await http.get('/api/v1/projects/')
    projects.value = data.results || data || []
    if (projects.value.length > 0 && !selectedProject.value) {
      selectedProject.value = projects.value[0].id
    }
  } catch (e) {
    console.error('加载项目失败', e)
  }
}

async function loadModuleTree() {
  if (!selectedProject.value) return
  try {
    const data = await uiModuleApi.tree(selectedProject.value)
    moduleTree.value = data || []
  } catch (e) {
    console.error('加载模块树失败', e)
  }
}

async function loadStats() {
  if (!selectedProject.value) return
  try {
    stats.value = await uiDashboardApi.stats(selectedProject.value)
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

function onProjectChange() {
  loadModuleTree()
  loadStats()
}

function onModuleClick(data) {
  selectedModuleId.value = data.id
}

async function onNodeDrop(draggingNode, dropNode, dropType) {
  const moduleId = draggingNode.data.id
  const targetId = dropNode.data.id
  const dropPosition = dropType === 'inner' ? 'inside' : dropType === 'after' ? 'after' : 'before'
  try {
    await uiModuleApi.move(moduleId, { target_id: targetId, drop_position: dropPosition })
    loadModuleTree()
  } catch (e) {
    console.error('移动模块失败', e)
  }
}

async function createModule() {
  if (!newModule.value.name) return
  creating.value = true
  try {
    await uiModuleApi.create({
      project: selectedProject.value,
      name: newModule.value.name,
      parent: newModule.value.parent || null,
      description: newModule.value.description,
      level: newModule.value.parent ? 2 : 1,
    })
    showAddModule.value = false
    newModule.value = { name: '', parent: null, description: '' }
    loadModuleTree()
  } catch (e) {
    console.error('创建模块失败', e)
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.ui-automation-page {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary-color);
}
.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.ui-main-layout {
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
}
.ui-tree-panel {
  width: 280px;
  flex-shrink: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  overflow-y: auto;
}
.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 600;
  color: var(--text-primary);
}
.tree-node-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.tree-node-count {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-body);
  padding: 1px 6px;
  border-radius: 10px;
}
.ui-content-panel {
  flex: 1;
  min-width: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow-y: auto;
}
</style>
