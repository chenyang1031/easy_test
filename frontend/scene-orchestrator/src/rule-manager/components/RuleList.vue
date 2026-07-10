<template>
  <div class="rule-manager">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">AI规则管理</h2>
        <span class="page-subtitle">管理AI生成测试用例的规则配置</span>
      </div>
      <div class="page-header-right">
        <el-button :icon="Download" @click="store.exportJson()">导出JSON</el-button>
        <el-button :icon="Upload" @click="store.openImportModal()">导入JSON</el-button>
        <el-button type="success" :icon="Plus" @click="store.openCreateModal()">新建规则</el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="10" class="filter-row">
          <el-col :xs="12" :sm="6" :md="4">
            <el-select v-model="categoryModel" placeholder="全部分类" clearable class="filter-item">
              <el-option v-for="(label, value) in CATEGORY_OPTIONS" :key="value" :label="label" :value="value" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="5" :md="3">
            <el-select v-model="priorityModel" placeholder="全部优先级" clearable class="filter-item">
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="5" :md="3">
            <el-select v-model="enabledModel" placeholder="全部状态" clearable class="filter-item">
              <el-option label="已启用" value="true" />
              <el-option label="已禁用" value="false" />
            </el-select>
          </el-col>
          <el-col :xs="16" :sm="8" :md="7">
            <el-input v-model="keywordModel" placeholder="搜索规则名称/描述..." :prefix-icon="Search" clearable class="filter-item" @keyup.enter="store.applyFilter()" />
          </el-col>
          <el-col :xs="8" :sm="4" :md="3">
            <div class="filter-actions">
              <el-button type="primary" :icon="Search" @click="store.applyFilter()">筛选</el-button>
              <el-button :icon="Refresh" @click="store.loadRules(store.currentPage)">刷新</el-button>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 批量操作栏 -->
      <transition name="fade">
        <div v-if="store.selectedIds.size > 0" class="batch-bar">
          <span class="batch-info">已选 <strong>{{ store.selectedIds.size }}</strong> 条</span>
          <el-divider direction="vertical" />
          <el-button size="small" type="success" plain @click="store.batchToggleEnabled(true)">批量启用</el-button>
          <el-button size="small" type="warning" plain @click="store.batchToggleEnabled(false)">批量禁用</el-button>
          <el-button size="small" type="danger" plain @click="store.batchDelete()">批量删除</el-button>
          <el-button size="small" text @click="store.clearSelection()">取消选择</el-button>
        </div>
      </transition>

      <!-- 加载 -->
      <div v-if="store.loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon><span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="store.rules.length === 0" description="暂无规则">
        <template #image><el-icon :size="64" color="#c0c4cc"><Document /></el-icon></template>
        <el-button type="primary" @click="store.openCreateModal()">新建规则</el-button>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table
          :data="store.rules"
          stripe border
          class="data-table"
          @selection-change="onSelectionChange"
          ref="tableRef"
        >
          <el-table-column type="selection" width="42" />

          <el-table-column prop="name" label="规则名称" min-width="200">
            <template #default="{ row }">
              <div class="cell-name">
                <span class="cell-name-text">{{ row.name }}</span>
              </div>
              <div v-if="row.description" class="cell-desc-short">
                {{ row.description.length > 60 ? row.description.slice(0, 60) + '...' : row.description }}
              </div>
            </template>
          </el-table-column>

          <el-table-column label="分类" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="categoryTagType(row.category)" effect="light" size="small" round>
                {{ store.categoryLabel(row.category) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="优先级" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="priorityTagType(row.priority)" effect="dark" size="small" round>
                {{ store.priorityLabel(row.priority) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="规则条数" width="100" align="center">
            <template #default="{ row }">
              <el-popover v-if="row.rule_lines?.length" placement="bottom" :width="380" trigger="click">
                <template #reference>
                  <el-link type="primary" :underline="false">{{ row.rule_lines.length }} 条</el-link>
                </template>
                <div class="rule-popover-list">
                  <div v-for="(line, idx) in row.rule_lines" :key="idx" class="rule-line-item">
                    <span class="rule-index">{{ idx + 1 }}.</span>
                    <span>{{ line }}</span>
                  </div>
                </div>
              </el-popover>
              <span v-else class="cell-zero">0</span>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small" effect="light" round>
                {{ row.is_enabled ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="更新时间" width="160" align="right">
            <template #default="{ row }">
              <span class="cell-time">{{ formatTime(row.updated_at) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="140" align="center" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button link type="primary" :icon="Edit" size="small" @click="store.openEditModal(row.id)">编辑</el-button>
                <el-popconfirm title="确定要删除此规则吗？" confirm-button-text="删除" cancel-button-text="取消" @confirm="store.deleteRule(row.id, row.name)">
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
            @current-change="store.loadRules"
            @size-change="() => store.loadRules(1)"
          />
        </div>
      </template>
    </div>

    <RuleModal />
    <ImportJsonModal />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Search, Refresh, Plus, Upload, Download, Edit, Delete, Loading
} from '@element-plus/icons-vue'
import { useRuleStore } from '../stores/rule.js'
import RuleModal from './RuleModal.vue'
import ImportJsonModal from './ImportJsonModal.vue'

const store = useRuleStore()
const tableRef = ref(null)

const CATEGORY_OPTIONS = {
  param_validate: '参数校验',
  biz_logic: '业务逻辑',
  error_handle: '异常处理',
  boundary: '边界值',
  security: '安全',
  performance: '性能',
  other: '其他'
}

const keywordModel = computed({
  get: () => store.keyword,
  set: (v) => store.keyword = v
})
const categoryModel = computed({
  get: () => store.filterCategory,
  set: (v) => { store.filterCategory = v || ''; store.applyFilter() }
})
const priorityModel = computed({
  get: () => store.filterPriority,
  set: (v) => { store.filterPriority = v || ''; store.applyFilter() }
})
const enabledModel = computed({
  get: () => store.filterEnabled,
  set: (v) => { store.filterEnabled = v || ''; store.applyFilter() }
})

function categoryTagType(cat) {
  const map = { param_validate: '', biz_logic: 'info', error_handle: 'warning', boundary: 'info', security: 'danger', performance: '', other: 'info' }
  return map[cat] || ''
}
function priorityTagType(pri) {
  const map = { high: 'danger', medium: 'warning', low: 'success' }
  return map[pri] || ''
}

function onSelectionChange(vals) {
  store.selectedIds = new Set(vals.map(r => r.id))
}

function formatTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '-'
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => { store.loadRules(1) })
</script>

<style scoped>
.rule-manager { display:flex; flex-direction:column; gap:16px; flex:1; min-height:0; }

/* ---- 页面标题 ---- */
.page-header {
  display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;
}
.page-header-left { display:flex; align-items:baseline; gap:12px; }
.page-title { font-size:24px; font-weight:600; color:#303133; margin:0; line-height:1.3; }
.page-subtitle { font-size: var(--el-font-size-base); color:#909399; }
.page-header-right { display:flex; gap:8px; }

/* ---- 主体卡片 ---- */
.panel-card {
  background:#fff; border-radius:10px; padding:20px;
  box-shadow:0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  flex:1; min-height:0; overflow:auto;
}

/* ---- 筛选栏 ---- */
.filter-bar { margin-bottom:16px; }
.filter-row { display:flex; align-items:center; }
.filter-item { width:100%; }
.filter-actions { display:flex; gap:8px; }

/* ---- 批量操作栏 ---- */
.batch-bar {
  display:flex; align-items:center; gap:8px;
  padding:8px 14px; margin-bottom:14px;
  background:#f0f5ff; border-radius:8px;
  border:1px solid #d6e4ff;
}
.batch-info { font-size: var(--el-font-size-base); color:#409eff; font-weight:500; margin-right:4px; }
.batch-info strong { font-size: var(--el-font-size-medium); }
.fade-enter-active, .fade-leave-active { transition:all .2s; }
.fade-enter-from, .fade-leave-to { opacity:0; transform:translateY(-4px); }

/* ---- 加载 ---- */
.loading-state {
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  gap:12px; padding:80px 0; color:#909399; font-size: var(--el-font-size-base);
}

/* ---- 表格 ---- */
.data-table { width:100%; }
.data-table :deep(th.el-table__cell) { background:#f6f8fa !important; color:#303133; font-weight:600; }
.cell-name { display:flex; align-items:center; gap:6px; }
.cell-name-text { font-weight:600; }
.cell-desc-short { font-size: var(--el-font-size-small); color:#909399; margin-top:3px; line-height:1.4; }
.cell-time { font-size: var(--el-font-size-base); color:#909399; }
.cell-zero { color:#c0c4cc; }
.table-actions { display:flex; gap:2px; align-items:center; justify-content:center; }

.rule-popover-list { max-height:300px; overflow-y:auto; }
.rule-line-item { display:flex; gap:6px; padding:4px 0; font-size: var(--el-font-size-base); line-height:1.5; border-bottom:1px solid #f5f5f5; }
.rule-line-item:last-child { border-bottom:none; }
.rule-index { color:#909399; min-width:22px; text-align:right; flex-shrink:0; }

/* ---- 分页 ---- */
.table-footer {
  display:flex; justify-content:flex-end; align-items:center;
  padding-top:16px; border-top:1px solid #ebeef5; margin-top:16px;
}
</style>
