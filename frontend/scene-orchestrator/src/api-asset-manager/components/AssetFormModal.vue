<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑接口' : '新增接口'"
    width="640px"
    :close-on-click-modal="false"
    @open="resetForm"
  >
    <el-form :model="form" label-position="top">
      <el-row :gutter="16">
        <el-col :span="16">
          <el-form-item label="接口名称" required>
            <el-input v-model="form.name" placeholder="请输入接口名称" maxlength="200" ref="nameRef" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="Method" required>
            <el-select v-model="form.method" style="width:100%">
              <el-option label="GET" value="GET" />
              <el-option label="POST" value="POST" />
              <el-option label="PUT" value="PUT" />
              <el-option label="DELETE" value="DELETE" />
              <el-option label="PATCH" value="PATCH" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="URL" required>
        <el-input v-model="form.url" placeholder="如 /api/users" maxlength="500" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="所属分组">
            <el-select v-model="form.group" placeholder="根目录" clearable style="width:100%">
              <el-option v-for="g in store.flatGroupsForSelect" :key="g.id ?? 'root'" :label="g.displayName" :value="g.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width:100%">
              <el-option label="草稿" value="draft" />
              <el-option label="可用" value="active" />
              <el-option label="已废弃" value="deprecated" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="请求头 (JSON)">
        <el-input v-model="form.headersText" type="textarea" :rows="3" placeholder='{"Content-Type":"application/json"}' />
        <span class="form-hint" v-if="headersError">{{ headersError }}</span>
      </el-form-item>
      <el-form-item label="请求体 (JSON)">
        <el-input v-model="form.bodyText" type="textarea" :rows="4" placeholder='{"key":"value"}' />
        <span class="form-hint" v-if="bodyError">{{ bodyError }}</span>
      </el-form-item>
    </el-form>

    <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useApiAssetStore } from '../stores/apiAsset.js'
import { apiAssetApi } from '../api/index.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  asset: { type: Object, default: null }
})
const emit = defineEmits(['update:modelValue', 'saved'])

const store = useApiAssetStore()
const nameRef = ref(null)
const submitting = ref(false)
const errorMsg = ref('')
const headersError = ref('')
const bodyError = ref('')
const form = ref({ name: '', method: 'GET', url: '', group: null, status: 'draft', headersText: '', bodyText: '' })

const visible = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })
const isEdit = computed(() => !!props.asset)

function resetForm() {
  if (props.asset) {
    form.value = {
      name: props.asset.name || '',
      method: props.asset.method || 'GET',
      url: props.asset.url || '',
      group: props.asset.group || null,
      status: props.asset.status || 'draft',
      headersText: (props.asset.request_headers || props.asset.headers) ? JSON.stringify(props.asset.request_headers || props.asset.headers, null, 2) : '',
      bodyText: props.asset.body ? JSON.stringify(props.asset.body, null, 2) : '',
    }
  } else {
    form.value = { name: '', method: 'GET', url: '', group: store.currentGroupId, status: 'draft', headersText: '', bodyText: '' }
  }
  errorMsg.value = ''; headersError.value = ''; bodyError.value = ''
  nextTick(() => nameRef.value?.focus())
}

async function handleSubmit() {
  const f = form.value
  if (!f.name.trim()) { errorMsg.value = '请输入接口名称'; return }
  if (!f.url.trim()) { errorMsg.value = '请输入URL'; return }

  // 解析JSON
  let headers = null, body = null
  if (f.headersText.trim()) {
    try { headers = JSON.parse(f.headersText); headersError.value = '' }
    catch { headersError.value = '请求头JSON格式错误'; return }
  }
  if (f.bodyText.trim()) {
    try { body = JSON.parse(f.bodyText); bodyError.value = '' }
    catch { bodyError.value = '请求体JSON格式错误'; return }
  }

  const payload = {
    name: f.name.trim(),
    method: f.method,
    url: f.url.trim(),
    group: f.group || null,
    status: f.status,
    headers, body,
  }
  if (isEdit.value) {
    payload.project = store.currentProjectId
  } else {
    payload.project = store.currentProjectId
  }

  submitting.value = true; errorMsg.value = ''
  try {
    if (isEdit.value) {
      await apiAssetApi.update(props.asset.id, payload)
    } else {
      await apiAssetApi.create(payload)
    }
    visible.value = false
    emit('saved')
    store.fetchAssets()
    store.fetchProjectStats()
  } catch (e) {
    const msg = typeof e?.data === 'object' ? (e.data.detail || Object.values(e.data)[0]?.[0] || '操作失败') : (e?.message || '操作失败')
    errorMsg.value = String(msg)
  } finally { submitting.value = false }
}
</script>

<style scoped>
.error-msg { color: #f56c6c; font-size: 13px; margin-top: -8px; }
.form-hint { color: #f56c6c; font-size: 12px; }
</style>
