<template>
  <el-dialog
    v-model="visible"
    title="导入API资产"
    width="800px"
    :close-on-click-modal="false"
    @open="onOpen"
  >
    <!-- API 列表 -->
    <div v-if="apis.length === 0" style="text-align:center;padding:40px 0">
      <el-text type="info">暂无API数据</el-text>
    </div>

    <template v-else>
      <!-- 目标项目/分组 -->
      <div class="target-section">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="目标项目">
              <el-select v-model="selectedProjectId" placeholder="选择项目" style="width:100%" @change="onProjectChange">
                <el-option v-for="p in store.apiProjects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标分组">
              <el-select v-model="selectedGroupId" placeholder="选择分组（不选则自动创建）" style="width:100%" clearable :loading="groupsLoading">
                <el-option v-for="g in apiGroups" :key="g.id" :label="g.name" :value="g.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <div class="selection-info">
        <el-text size="small" type="info">已选 {{ checkedIndices.length }} / {{ apis.length }} 个API</el-text>
      </div>

      <el-table :data="apis" stripe border class="api-table" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="42" />
        <el-table-column label="名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="方法" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="methodType(row.method)" size="small" effect="plain">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="URL" min-width="200" show-overflow-tooltip prop="url" />
        <el-table-column label="描述" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.interface_desc || '-' }}</template>
        </el-table-column>
      </el-table>

      <!-- 冲突检测结果 -->
      <div v-if="previewResult" class="preview-section">
        <el-divider />
        <div class="preview-header">
          <el-text size="small" :type="previewResult.conflict_count > 0 ? 'warning' : 'success'">
            检测到 {{ previewResult.conflict_count }} 个冲突，{{ previewResult.no_conflict_count }} 个无冲突
          </el-text>
        </div>

        <div v-if="previewResult.conflicts.length" class="conflict-list">
          <el-text size="small" type="danger">以下API与已有资产冲突：</el-text>
          <div v-for="c in previewResult.conflicts" :key="c.index" class="conflict-item">
            <el-tag size="small" type="danger" effect="plain">{{ c.method }}</el-tag>
            <code>{{ c.url }}</code>
            <el-text size="small" type="info">→ 已有: {{ c.existing_asset_name }}</el-text>
          </div>
        </div>

        <div v-if="previewResult.conflict_count > 0" style="margin-top:12px">
          <el-text size="small">冲突策略：</el-text>
          <el-radio-group v-model="conflictStrategy" style="margin-left:8px">
            <el-radio value="skip">跳过</el-radio>
            <el-radio value="overwrite">覆盖</el-radio>
            <el-radio value="keep_both">保留两者</el-radio>
          </el-radio-group>
        </div>
      </div>

      <!-- 导入结果 -->
      <div v-if="importResult" class="result-section">
        <el-alert
          :title="`导入完成：创建 ${importResult.created_count} 条，更新 ${importResult.updated_count} 条，跳过 ${importResult.skipped_count} 条`"
          type="success"
          show-icon
          :closable="false"
        />
      </div>
    </template>

    <template #footer>
      <el-button @click="visible = false" :disabled="importing">关闭</el-button>
      <el-button
        v-if="!importResult && checkedIndices.length > 0"
        :loading="previewing"
        @click="handlePreview"
      >
        检测冲突
      </el-button>
      <el-button
        v-if="previewResult && !importResult"
        type="primary"
        :loading="importing"
        @click="handleImport"
      >
        确认导入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useDocumentImportStore } from '../stores/documentImport.js'
import { documentImportApi } from '../api/index.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  record: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'imported'])
const store = useDocumentImportStore()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const apis = ref([])
const selectedRows = ref([])

const selectedProjectId = ref(null)
const selectedGroupId = ref(null)
const apiGroups = ref([])
const groupsLoading = ref(false)

const previewing = ref(false)
const importing = ref(false)
const previewResult = ref(null)
const importResult = ref(null)
const conflictStrategy = ref('skip')

const checkedIndices = computed(() => {
  const indices = []
  selectedRows.value.forEach(row => {
    const idx = apis.value.indexOf(row)
    if (idx !== -1) indices.push(idx)
  })
  return indices
})

function methodType(m) {
  const map = { GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return map[m] || 'info'
}

async function onOpen() {
  apis.value = []
  selectedRows.value = []
  previewResult.value = null
  importResult.value = null
  conflictStrategy.value = 'skip'
  selectedGroupId.value = null
  apiGroups.value = []

  // 优先使用记录关联的项目
  if (props.record?.project) {
    selectedProjectId.value = props.record.project
    await loadGroups(props.record.project)
  } else {
    selectedProjectId.value = null
  }

  if (props.record && props.record.id) {
    try {
      const [data, projectsData] = await Promise.all([
        documentImportApi.getApis(props.record.id),
        store.apiProjects.length === 0 ? documentImportApi.getApiProjects() : null,
      ])
      apis.value = data.apis || []
      if (projectsData) store.apiProjects = projectsData.results || projectsData || []
    } catch (err) {
      ElMessage.error('加载API列表失败：' + err.message)
    }
  }
}

function onSelectionChange(rows) {
  selectedRows.value = rows
}

function onProjectChange(projectId) {
  selectedGroupId.value = null
  apiGroups.value = []
  if (projectId) loadGroups(projectId)
}

async function loadGroups(projectId) {
  groupsLoading.value = true
  try {
    const data = await documentImportApi.getApiGroups(projectId)
    apiGroups.value = data.results || data || []
  } catch (err) {
    console.warn('加载分组列表失败：', err)
    apiGroups.value = []
  } finally {
    groupsLoading.value = false
  }
}

async function handlePreview() {
  if (checkedIndices.value.length === 0) {
    ElMessage.warning('请选择至少一个API')
    return
  }
  previewing.value = true
  previewResult.value = null
  try {
    previewResult.value = await documentImportApi.previewImport(
      props.record.id, checkedIndices.value, selectedGroupId.value
    )
  } catch (err) {
    ElMessage.error('检测冲突失败：' + err.message)
  } finally {
    previewing.value = false
  }
}

async function handleImport() {
  importing.value = true
  try {
    importResult.value = await documentImportApi.confirmImport(
      props.record.id, checkedIndices.value, conflictStrategy.value, selectedGroupId.value
    )
    ElMessage.success('导入成功')
    emit('imported')
  } catch (err) {
    ElMessage.error('导入失败：' + err.message)
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.target-section { margin-bottom: 14px; padding: 12px; background: #f9fafb; border-radius: 6px; }
.target-section :deep(.el-form-item) { margin-bottom: 0; }
.selection-info { margin-bottom: 10px; }
.api-table { width: 100%; }
.api-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }
.preview-section { margin-top: 8px; }
.preview-header { margin-bottom: 8px; }
.conflict-list { margin: 8px 0; }
.conflict-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
.conflict-item code { font-size: 13px; color: #606266; background: #f5f7fa; padding: 2px 6px; border-radius: 4px; }
.result-section { margin-top: 12px; }
</style>
