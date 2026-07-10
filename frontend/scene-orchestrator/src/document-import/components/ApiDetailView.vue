<template>
  <el-drawer
    v-model="visible"
    :title="detailRecord ? detailRecord.task_name : 'API详情'"
    size="70%"
    append-to-body
    @open="onOpen"
  >
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="28"><Loading /></el-icon><span>加载中...</span>
    </div>

    <template v-else-if="detailRecord">
      <!-- 基本信息 -->
      <div class="detail-header">
        <div class="header-item">
          <el-text size="small" type="info">原始文件</el-text>
          <el-text>{{ detailRecord.original_filename }}</el-text>
        </div>
        <div class="header-item">
          <el-text size="small" type="info">创建时间</el-text>
          <el-text>{{ formatTime(detailRecord.created_at) }}</el-text>
        </div>
        <div class="header-item">
          <el-text size="small" type="info">状态</el-text>
          <el-tag :type="statusTagType" size="small" effect="light" round>{{ statusTagLabel }}</el-tag>
        </div>
        <div class="header-item">
          <el-text size="small" type="info">AI模型</el-text>
          <el-text>{{ detailRecord.model_name || '-' }}</el-text>
        </div>
        <div class="header-item">
          <el-text size="small" type="info">提示词模板</el-text>
          <el-text>{{ detailRecord.template_name || '-' }}</el-text>
        </div>
        <div class="header-item">
          <el-text size="small" type="info">API数量</el-text>
          <el-text>{{ apis.length }}</el-text>
        </div>
      </div>

      <el-divider />

      <!-- Markdown 内容折叠 -->
      <el-collapse class="md-collapse">
        <el-collapse-item title="原始 Markdown 文档内容" name="md">
          <pre class="md-content">{{ detailRecord.md_content || '无内容' }}</pre>
        </el-collapse-item>
      </el-collapse>

      <el-divider />

      <!-- API 列表 -->
      <div class="api-list-section">
        <div class="section-title">
          <span>提取的 API 列表</span>
          <el-button size="small" type="primary" @click="handleBatchImport" :disabled="apis.length === 0">
            导入全部
          </el-button>
        </div>

        <div v-if="apis.length === 0" class="empty-section">
          <el-empty description="暂无API数据" :image-size="80" />
        </div>

        <el-table v-else :data="apis" stripe border class="api-table" @row-click="toggleExpand">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="api-detail">
                <el-descriptions :column="2" border size="small">
                  <el-descriptions-item label="接口名称" :span="2">{{ row.name || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="请求方法">{{ row.method || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="请求URL" :span="2">
                    <code>{{ row.url || '-' }}</code>
                  </el-descriptions-item>
                  <el-descriptions-item label="接口描述" :span="2">{{ row.interface_desc || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="请求体格式">{{ row.request_body_format || 'json' }}</el-descriptions-item>
                  <el-descriptions-item label="鉴权配置" v-if="row.auth_config && Object.keys(row.auth_config).length">
                    <pre class="inline-json">{{ JSON.stringify(row.auth_config, null, 2) }}</pre>
                  </el-descriptions-item>
                </el-descriptions>

                <div v-if="row.request_headers && Object.keys(row.request_headers).length" class="detail-section">
                  <h4 class="detail-section-title">请求头</h4>
                  <pre class="json-block">{{ JSON.stringify(row.request_headers, null, 2) }}</pre>
                </div>

                <div v-if="row.request_params && row.request_params.length" class="detail-section">
                  <h4 class="detail-section-title">请求参数</h4>
                  <el-table :data="row.request_params" size="small" border>
                    <el-table-column prop="key" label="参数名" min-width="120" />
                    <el-table-column prop="type" label="类型" width="80" />
                    <el-table-column prop="required" label="必填" width="60">
                      <template #default="{ row: p }">{{ p.required ? '是' : '否' }}</template>
                    </el-table-column>
                    <el-table-column prop="desc" label="说明" min-width="120" />
                  </el-table>
                </div>

                <div v-if="row.request_body && Object.keys(row.request_body).length" class="detail-section">
                  <h4 class="detail-section-title">请求体</h4>
                  <pre class="json-block">{{ JSON.stringify(row.request_body, null, 2) }}</pre>
                </div>

                <div v-if="row.response_schema && Object.keys(row.response_schema).length" class="detail-section">
                  <h4 class="detail-section-title">响应结构</h4>
                  <pre class="json-block">{{ JSON.stringify(row.response_schema, null, 2) }}</pre>
                </div>

                <div v-if="row.error_code && row.error_code.length" class="detail-section">
                  <h4 class="detail-section-title">错误码</h4>
                  <pre class="json-block">{{ JSON.stringify(row.error_code, null, 2) }}</pre>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="名称" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">{{ row.name || '-' }}</template>
          </el-table-column>
          <el-table-column label="方法" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="methodTagType(row.method)" size="small" effect="plain">{{ row.method }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="URL" min-width="240" show-overflow-tooltip prop="url" />
          <el-table-column label="描述" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">{{ row.interface_desc || '-' }}</template>
          </el-table-column>
          <el-table-column label="导入状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag v-if="row._imported" type="success" size="small" effect="light" round>已导入</el-tag>
              <el-tag v-else type="info" size="small" effect="plain" round>待导入</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <el-empty v-else description="无法加载记录详情" />
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { useDocumentImportStore } from '../stores/documentImport.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  recordId: { type: [Number, String], default: null },
})
const emit = defineEmits(['update:modelValue'])

const store = useDocumentImportStore()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const detailRecord = computed(() => store.detailRecord)
const apis = computed(() => store.detailApis)
const loading = computed(() => store.detailLoading)

const statusTagType = computed(() => {
  const map = { uploading: 'info', converting: 'warning', generating: 'primary', success: 'success', failed: 'danger' }
  return map[detailRecord.value?.status] || 'info'
})
const statusTagLabel = computed(() => {
  const map = { uploading: '上传中', converting: '转换中', generating: 'AI生成中', success: '生成成功', failed: '生成失败' }
  return map[detailRecord.value?.status] || detailRecord.value?.status || '未知'
})

function methodTagType(m) {
  const map = { GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return map[m] || 'info'
}

function formatTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '-'
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function toggleExpand(row) {
  // 点击行时触发展开/折叠
}

function handleBatchImport() {
  // 打开导入弹窗（复用 DocumentGenList 中的逻辑）
  if (detailRecord.value) {
    store.openImportDialog(detailRecord.value)
  }
}

async function onOpen() {
  if (props.recordId) {
    await store.loadDetail(props.recordId)
  }
}
</script>

<style scoped>
.loading-state { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 60px 0; color: #909399; font-size: 14px; }
.detail-header { display: flex; gap: 24px; flex-wrap: wrap; }
.header-item { display: flex; flex-direction: column; gap: 4px; min-width: 120px; }
.md-collapse { margin-bottom: 8px; }
.md-content { white-space: pre-wrap; word-break: break-word; font-size: 13px; background: #f5f7fa; padding: 12px; border-radius: 6px; max-height: 400px; overflow: auto; font-family: 'Consolas', monospace; }
.api-list-section { margin-top: 8px; }
.section-title { display: flex; align-items: center; justify-content: space-between; font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.empty-section { padding: 20px 0; }
.api-table { width: 100%; }
.api-table :deep(th.el-table__cell) { background: #f6f8fa !important; color: #303133; font-weight: 600; }

.api-detail { padding: 8px 12px; }
.detail-section { margin-top: 16px; }
.detail-section-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.json-block { background: #f5f7fa; padding: 12px; border-radius: 6px; font-size: 13px; overflow-x: auto; white-space: pre-wrap; word-break: break-word; max-height: 300px; overflow-y: auto; font-family: 'Consolas', monospace; }
.inline-json { margin: 0; font-size: 12px; background: #f5f7fa; padding: 4px 8px; border-radius: 4px; }
</style>
