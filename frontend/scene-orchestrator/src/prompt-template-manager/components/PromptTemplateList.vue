<template>
  <div class="prompt-template-manager">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">AI提示词管理</h2>
        <span class="page-subtitle">管理AI生成测试用例的提示词模板</span>
      </div>
      <div class="page-header-right">
        <el-button :icon="Download" @click="store.exportJson()">导出JSON</el-button>
        <el-button :icon="Upload" @click="store.openImportModal()">导入JSON</el-button>
        <el-button type="success" :icon="Plus" @click="store.openCreateModal()">新建模板</el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="10" class="filter-row">
          <el-col :xs="24" :sm="8" :md="6">
            <el-input v-model="keywordModel" placeholder="搜索模板名称/描述..." :prefix-icon="Search" clearable class="filter-item" @keyup.enter="store.applyFilter()" />
          </el-col>
          <el-col :xs="12" :sm="5" :md="3">
            <el-select v-model="categoryModel" placeholder="全部分类" clearable class="filter-item">
              <el-option label="API生成" value="api_gen" />
              <el-option label="用例生成" value="test_case_gen" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="5" :md="3">
            <el-select v-model="isEnabledModel" placeholder="全部状态" clearable class="filter-item">
              <el-option label="已启用" value="true" />
              <el-option label="已禁用" value="false" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="4" :md="3">
            <el-button type="primary" :icon="Search" @click="store.applyFilter()">筛选</el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 加载中 -->
      <div v-if="store.loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon><span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="store.templates.length === 0" description="暂无AI提示词模板">
        <template #image><el-icon :size="64" color="#c0c4cc"><Document /></el-icon></template>
        <el-button type="primary" @click="store.openCreateModal()">新建模板</el-button>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table :data="store.templates" stripe border class="data-table">
          <el-table-column prop="name" label="模板名称" min-width="200">
            <template #default="{ row }">
              <div class="cell-name">
                <span class="cell-name-text">{{ row.name }}</span>
                <el-tag v-if="row.is_default" type="success" size="small" effect="dark" round>默认</el-tag>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="description" label="描述" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="cell-desc">{{ row.description || '-' }}</span>
            </template>
          </el-table-column>

          <el-table-column label="分类" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.category === 'api_gen' ? 'warning' : 'primary'" size="small" effect="light" round>
                {{ row.category === 'api_gen' ? 'API生成' : '用例生成' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="变量" width="90" align="center">
            <template #default="{ row }">
              <el-popover v-if="row.template_variables?.length" placement="bottom" :width="240" trigger="click" :show-arrow="false">
                <template #reference>
                  <el-link type="primary" :underline="false">{{ row.template_variables.length }}</el-link>
                </template>
                <div class="var-popover-list">
                  <el-tag v-for="v in row.template_variables" :key="v" size="small" effect="plain" round>
                    {{ '{' + v + '}' }}
                  </el-tag>
                </div>
              </el-popover>
              <span v-else class="cell-zero">0</span>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small" effect="light" round>
                {{ row.is_enabled ? '已启用' : '已禁用' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="更新时间" width="160" align="right">
            <template #default="{ row }"><span class="cell-time">{{ formatTime(row.updated_at) }}</span></template>
          </el-table-column>

          <el-table-column label="操作" width="180" align="center" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button link type="primary" :icon="Edit" size="small" @click="store.openEditModal(row.id)">编辑</el-button>
                <el-button v-if="!row.is_default" link type="success" :icon="Star" size="small" @click="store.setDefault(row.id)">默认</el-button>
                <el-popconfirm title="确定要删除此模板吗？" confirm-button-text="删除" cancel-button-text="取消" @confirm="store.deleteTemplate(row.id, row.name)">
                  <template #reference><el-button link type="danger" :icon="Delete" size="small">删除</el-button></template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="table-footer">
          <el-pagination
            v-model:current-page="store.currentPage"
            v-model:page-size="store.pageSize"
            :total="store.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="store.loadTemplates"
            @size-change="() => store.loadTemplates(1)"
          />
        </div>
      </template>
    </div>

    <PromptTemplateModal />
    <ImportJsonModal />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Search, Refresh, Plus, Upload, Download, Edit, Star, Delete, Loading } from '@element-plus/icons-vue'
import { usePromptTemplateStore } from '../stores/promptTemplate.js'
import PromptTemplateModal from './PromptTemplateModal.vue'
import ImportJsonModal from './ImportJsonModal.vue'

const store = usePromptTemplateStore()

const keywordModel = computed({
  get: () => store.keyword,
  set: (v) => store.keyword = v
})
const categoryModel = computed({
  get: () => store.categoryFilter,
  set: (v) => { store.categoryFilter = v || ''; store.applyFilter() }
})
const isEnabledModel = computed({
  get: () => store.isEnabled,
  set: (v) => { store.isEnabled = v || ''; store.applyFilter() }
})

function formatTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '-'
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => { store.loadTemplates(1) })
</script>

<style scoped>
.prompt-template-manager { display:flex; flex-direction:column; gap:16px; flex:1; min-height:0; }

/* ---- 页面标题 ---- */
.page-header {
  display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;
}
.page-header-left { display:flex; align-items:baseline; gap:12px; }
.page-title { font-size:24px; font-weight:600; color:#303133; margin:0; line-height:1.3; }
.page-subtitle { font-size:14px; color:#909399; }
.page-header-right { display:flex; gap:8px; }

/* ---- 主体卡片 ---- */
.panel-card {
  background:#fff; border-radius:10px; padding:20px;
  box-shadow:0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  flex:1; min-height:0; overflow:auto;
}

/* ---- 筛选栏 ---- */
.filter-bar { margin-bottom:16px; }
.filter-item { width:100%; }

/* ---- 加载 ---- */
.loading-state {
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  gap:12px; padding:80px 0; color:#909399; font-size:14px;
}

/* ---- 表格 ---- */
.data-table { width:100%; }
.data-table :deep(th.el-table__cell) { background:#f6f8fa !important; color:#303133; font-weight:600; }
.cell-name { display:flex; align-items:center; gap:6px; }
.cell-name-text { font-weight:600; }
.cell-desc { color:#909399; }
.cell-time { font-size:14px; color:#909399; }
.cell-zero { color:#c0c4cc; }
.table-actions { display:flex; gap:2px; align-items:center; justify-content:center; }

.var-popover-list { display:flex; flex-wrap:wrap; gap:6px; }

/* ---- 分页 ---- */
.table-footer {
  display:flex; justify-content:flex-end; align-items:center;
  padding-top:16px; border-top:1px solid #ebeef5; margin-top:16px;
}
</style>
