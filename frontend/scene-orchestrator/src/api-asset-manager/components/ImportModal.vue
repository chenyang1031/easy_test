<template>
  <el-dialog v-model="visible" title="导入API资产" width="800px" :close-on-click-modal="false" append-to-body @open="resetForm">
    <el-tabs v-model="activeTab">
      <!-- 本地文件导入 -->
      <el-tab-pane label="本地文件导入" name="local">
        <el-row :gutter="12" style="margin-bottom:14px">
          <el-col :span="6">
            <el-select v-model="fileType" placeholder="文件类型" style="width:100%">
              <el-option label="Postman v2.1" value="postman" />
              <el-option label="Apifox JSON" value="apifox" />
              <el-option label="OpenAPI/Swagger" value="openapi" />
            </el-select>
          </el-col>
          <el-col :span="7">
            <el-upload :auto-upload="false" :limit="1" :on-change="handleFileChange" :file-list="fileList" accept=".json,.yaml,.yml">
              <el-button>选择文件</el-button>
            </el-upload>
          </el-col>
          <el-col :span="5">
            <el-select v-model="targetProject" placeholder="目标项目" style="width:100%">
              <el-option v-for="p in store.platformProjects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select v-model="targetGroup" placeholder="目标分组" clearable style="width:100%">
              <el-option v-for="g in store.flatGroupsForSelect" :key="g.id ?? 'root'" :label="g.displayName" :value="g.id" />
            </el-select>
          </el-col>
        </el-row>
        <el-button :loading="previewLoading" @click="previewImport">预览</el-button>
      </el-tab-pane>

      <!-- 在线导入 -->
      <el-tab-pane label="在线导入" name="online">
        <el-row :gutter="12" style="margin-bottom:14px">
          <el-col :span="14">
            <el-input v-model="onlineUrl" placeholder="https://example.com/openapi.json" />
          </el-col>
          <el-col :span="5">
            <el-select v-model="targetProject" placeholder="目标项目" style="width:100%">
              <el-option v-for="p in store.platformProjects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-col>
          <el-col :span="5">
            <el-button :loading="previewLoading" @click="previewUrlImport">解析链接</el-button>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>

    <!-- 预览结果 -->
    <div v-if="previewItems.length > 0" style="margin-top:16px">
      <el-alert :title="`预览完成，共 ${previewItems.length} 条，其中 ${conflictCount} 条冲突`" type="info" show-icon :closable="false" style="margin-bottom:12px" />
      <el-select v-model="conflictStrategy" placeholder="冲突处理策略" style="width:200px;margin-bottom:12px">
        <el-option label="覆盖已有" value="overwrite" />
        <el-option label="跳过冲突" value="skip" />
        <el-option label="创建副本" value="duplicate" />
      </el-select>
      <el-table :data="previewItems" max-height="300" stripe size="small">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="method" label="Method" width="80" />
        <el-table-column prop="url" label="URL" min-width="200" />
        <el-table-column label="冲突" width="70">
          <template #default="{ row }">
            <el-tag v-if="row._conflict" type="warning" size="small">冲突</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:12px">
        <el-button type="primary" :loading="importLoading" @click="confirmImport">确认导入</el-button>
      </div>
    </div>

    <div v-if="errorMsg" class="error-msg" style="margin-top:12px">{{ errorMsg }}</div>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useApiAssetStore } from '../stores/apiAsset.js'
import { apiAssetApi, apiProjectApi } from '../api/index.js'
import { ElMessage } from 'element-plus'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue'])
const store = useApiAssetStore()

const visible = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const activeTab = ref('local')
const fileType = ref('postman')
const fileList = ref([])
const selectedFile = ref(null)
const targetProject = ref(store.platformProjectId)
const targetGroup = ref(null)
const onlineUrl = ref('')
const previewLoading = ref(false)
const importLoading = ref(false)
const previewItems = ref([])
const conflictCount = ref(0)
const conflictStrategy = ref('overwrite')
const errorMsg = ref('')

function handleFileChange(file) {
  selectedFile.value = file.raw
}

function resetForm() {
  targetProject.value = store.platformProjectId
  targetGroup.value = null
  errorMsg.value = ''
  previewItems.value = []
  conflictCount.value = 0
}

async function previewImport() {
  if (!selectedFile.value) { errorMsg.value = '请选择文件'; return }
  previewLoading.value = true; errorMsg.value = ''
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('file_type', fileType.value)
    if (targetProject.value) {
      const { api_project_id } = await apiProjectApi.resolve(targetProject.value)
      formData.append('project_id', api_project_id)
    }
    const data = await apiAssetApi.previewImport(formData)
    previewItems.value = data.items || []
    conflictCount.value = data.conflict_count || 0
  } catch (e) { errorMsg.value = e?.message || '预览失败' }
  finally { previewLoading.value = false }
}

async function previewUrlImport() {
  if (!onlineUrl.value) { errorMsg.value = '请输入在线链接'; return }
  previewLoading.value = true; errorMsg.value = ''
  try {
    let projectId = null
    if (targetProject.value) {
      const { api_project_id } = await apiProjectApi.resolve(targetProject.value)
      projectId = api_project_id
    }
    const data = await apiAssetApi.previewImportUrl(onlineUrl.value, projectId)
    previewItems.value = data.items || []
    conflictCount.value = data.conflict_count || 0
  } catch (e) { errorMsg.value = e?.message || '解析失败' }
  finally { previewLoading.value = false }
}

async function confirmImport() {
  importLoading.value = true; errorMsg.value = ''
  try {
    let projectId = null
    if (targetProject.value) {
      const { api_project_id } = await apiProjectApi.resolve(targetProject.value)
      projectId = api_project_id
    }
    const items = previewItems.value.map(it => ({
      ...it,
      _conflict_strategy: it._conflict ? conflictStrategy.value : null,
    }))
    await apiAssetApi.confirmImport({
      project_id: projectId,
      group_id: targetGroup.value || null,
      items,
      default_conflict_strategy: conflictStrategy.value,
    })
    visible.value = false
    ElMessage.success('导入成功')
    store.fetchAssets()
    store.fetchGroups()
    store.fetchProjectStats()
  } catch (e) { errorMsg.value = e?.message || '导入失败' }
  finally { importLoading.value = false }
}
</script>
