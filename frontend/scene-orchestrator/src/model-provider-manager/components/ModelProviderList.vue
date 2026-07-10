<template>
  <div class="model-provider-manager">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">AI大模型管理</h2>
        <span class="page-subtitle">配置AI大模型供应商，驱动测试用例智能生成</span>
      </div>
      <div class="page-header-right">
        <el-button type="success" :icon="Plus" @click="store.openCreate()">新增供应商</el-button>
      </div>
    </div>

    <div class="panel-card">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-row :gutter="10" class="filter-row">
          <el-col :xs="12" :sm="6" :md="4">
            <el-select v-model="typeModel" placeholder="全部类型" clearable class="filter-item">
              <el-option label="OpenAI 兼容" value="openai" />
              <el-option label="智谱 AI" value="zhipu" />
              <el-option label="DeepSeek" value="deepseek" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-col>
          <el-col :xs="12" :sm="5" :md="3">
            <el-select v-model="enabledModel" placeholder="全部状态" clearable class="filter-item">
              <el-option label="已启用" value="true" />
              <el-option label="已禁用" value="false" />
            </el-select>
          </el-col>
          <el-col :xs="16" :sm="8" :md="6">
            <el-input v-model="keywordModel" placeholder="搜索供应商名称..." :prefix-icon="Search" clearable class="filter-item" @keyup.enter="store.loadProviders(1)" />
          </el-col>
          <el-col :xs="8" :sm="4" :md="3">
            <div class="filter-actions">
              <el-button type="primary" :icon="Search" @click="store.loadProviders(1)">筛选</el-button>
              <el-button :icon="Refresh" @click="store.loadProviders(store.currentPage)">刷新</el-button>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 加载 -->
      <div v-if="store.loading" class="loading-state">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon><span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="store.providers.length === 0" description="暂未配置AI大模型供应商">
        <template #image><el-icon :size="64" color="#c0c4cc"><Cpu /></el-icon></template>
        <el-button type="primary" @click="store.openCreate()">新增供应商</el-button>
      </el-empty>

      <!-- 表格 -->
      <template v-else>
        <el-table :data="store.providers" stripe border class="data-table">
          <el-table-column prop="name" label="供应商" min-width="160">
            <template #default="{ row }">
              <div class="cell-name">
                <span class="cell-name-text">{{ row.name }}</span>
                <el-tag v-if="row.is_default" type="success" size="small" effect="dark" round>默认</el-tag>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="类型" width="120" align="center">
            <template #default="{ row }">
              <el-tag type="info" effect="light" size="small" round>{{ store.typeLabel(row.provider_type) }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column label="模型" width="160">
            <template #default="{ row }">
              <code class="cell-code">{{ row.model_name }}</code>
            </template>
          </el-table-column>

          <el-table-column label="API 地址" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="cell-url">{{ row.base_url }}{{ row.api_path }}</span>
            </template>
          </el-table-column>

          <el-table-column label="温度" width="70" align="center">
            <template #default="{ row }"><span>{{ row.temperature }}</span></template>
          </el-table-column>

          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small" effect="light" round>
                {{ row.is_enabled ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="200" align="center" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button link type="primary" :icon="Edit" size="small" @click="store.openEdit(row.id)">编辑</el-button>
                <el-button v-if="!row.is_default" link type="success" :icon="Star" size="small" @click="store.setDefault(row.id)">默认</el-button>
                <el-popconfirm title="确定要删除此供应商吗？" confirm-button-text="删除" cancel-button-text="取消" @confirm="store.remove(row.id, row.name)">
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
            @current-change="store.loadProviders"
            @size-change="() => store.loadProviders(1)"
          />
        </div>
      </template>
    </div>

    <ModelProviderModal />
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { Search, Refresh, Plus, Edit, Star, Delete, Loading } from '@element-plus/icons-vue'
import { useModelProviderStore } from '../stores/modelProvider.js'
import ModelProviderModal from './ModelProviderModal.vue'

const store = useModelProviderStore()

const keywordModel = computed({ get: () => store.keyword, set: (v) => store.keyword = v })
const typeModel = computed({
  get: () => store.filterType,
  set: (v) => { store.filterType = v || ''; store.loadProviders(1) }
})
const enabledModel = computed({
  get: () => store.filterEnabled,
  set: (v) => { store.filterEnabled = v || ''; store.loadProviders(1) }
})

onMounted(() => { store.loadProviders(1) })
</script>

<style scoped>
.model-provider-manager { display:flex; flex-direction:column; gap:16px; flex:1; min-height:0; }

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
.filter-actions { display:flex; gap:8px; }

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
.cell-code { font-size:14px; color:#303133; background:#f5f7fa; padding:2px 8px; border-radius:4px; }
.cell-url { font-size:13px; color:#909399; word-break:break-all; }
.table-actions { display:flex; gap:2px; align-items:center; justify-content:center; }

/* ---- 分页 ---- */
.table-footer {
  display:flex; justify-content:flex-end; align-items:center;
  padding-top:16px; border-top:1px solid #ebeef5; margin-top:16px;
}
</style>
