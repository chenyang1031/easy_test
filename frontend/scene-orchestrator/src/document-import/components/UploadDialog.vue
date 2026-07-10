<template>
  <el-dialog
    v-model="visible"
    title="上传文档"
    width="600px"
    :close-on-click-modal="false"
    @open="onOpen"
    @closed="onClosed"
  >
    <el-form ref="formRef" :model="form" label-width="100px" label-position="top">
      <el-form-item label="任务名称" required>
        <el-input v-model="form.task_name" placeholder="请输入自定义任务名称" maxlength="200" show-word-limit />
      </el-form-item>

      <el-form-item label="选择项目" required>
        <el-select v-model="form.project_id" placeholder="选择API项目" style="width:100%" @change="onProjectChange">
          <el-option v-for="p in store.apiProjects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>

      <el-form-item label="上传文件" required>
        <el-upload
          ref="uploadRef"
          drag
          :auto-upload="false"
          :limit="1"
          accept=".docx,.md"
          :on-change="onFileChange"
          :on-exceed="() => $message.warning('只能上传一个文件')"
        >
          <el-icon :size="40" color="#409eff"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽文件到此处，或<em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">仅支持 .docx 和 .md 文件，最大 50MB</div>
          </template>
        </el-upload>
      </el-form-item>

      <el-form-item label="AI模型">
        <el-select v-model="form.model_provider_id" placeholder="选择AI模型（可选）" style="width:100%" clearable>
          <el-option v-for="p in store.aiModelProviders" :key="p.id" :label="p.name" :value="p.id">
            <span>{{ p.name }}</span>
            <el-tag v-if="p.is_default" size="small" type="warning" style="margin-left:4px">默认</el-tag>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="提示词模板">
        <el-select v-model="form.prompt_template_id" placeholder="使用默认模板" style="width:100%" clearable>
          <el-option v-for="t in store.promptTemplates" :key="t.id" :label="t.name" :value="t.id">
            <span>{{ t.name }}</span>
            <el-tag v-if="t.is_default" size="small" type="success" style="margin-left:6px">默认</el-tag>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 进度 -->
      <div v-if="uploading" class="progress-section">
        <el-progress :percentage="progressPercent" :stroke-width="10" />
        <el-text size="small" type="info">{{ progressText }}</el-text>
      </div>
      <div v-if="resultMsg" class="result-section">
        <el-alert :title="resultMsg" :type="resultType" show-icon :closable="false" />
      </div>
    </el-form>

    <template #footer>
      <el-button @click="visible = false" :disabled="uploading">取消</el-button>
      <el-button type="primary" :loading="uploading" @click="startUpload" :disabled="!canUpload">
        <el-icon><Upload /></el-icon> 开始生成
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, UploadFilled } from '@element-plus/icons-vue'
import { useDocumentImportStore } from '../stores/documentImport.js'
import { documentImportApi } from '../api/index.js'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue', 'saved'])
const store = useDocumentImportStore()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const form = ref({
  task_name: '',
  project_id: null,
  model_provider_id: null,
  prompt_template_id: null,
})
const uploadedFile = ref(null)
const uploading = ref(false)
const progressPercent = ref(0)
const progressText = ref('')
const resultMsg = ref('')
const resultType = ref('success')
const uploadRef = ref(null)
const formRef = ref(null)

const canUpload = computed(() => {
  return form.value.task_name.trim() && form.value.project_id && uploadedFile.value
})

function onOpen() {
  form.value = { task_name: '', project_id: null, model_provider_id: null, prompt_template_id: null }
  uploadedFile.value = null
  resultMsg.value = ''
  resultType.value = 'success'
  progressPercent.value = 0
  progressText.value = ''
  // 自动选中默认模板
  const defaultTpl = store.promptTemplates.find(t => t.is_default)
  if (defaultTpl) {
    form.value.prompt_template_id = defaultTpl.id
  }
}

function onClosed() {
  if (uploadRef.value) uploadRef.value.clearFiles()
}

function onFileChange(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['docx', 'md'].includes(ext)) {
    ElMessage.warning('仅支持 .docx 和 .md 文件')
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 50MB')
    return false
  }
  uploadedFile.value = file.raw
  return true
}

function onProjectChange() {
  // 项目变更时可重新加载相关选项
}

async function startUpload() {
  if (!canUpload.value) {
    ElMessage.warning('请填写必填项')
    return
  }

  uploading.value = true
  resultMsg.value = ''

  try {
    progressText.value = '正在上传文档…'
    progressPercent.value = 20

    const fd = new FormData()
    fd.append('task_name', form.value.task_name.trim())
    fd.append('project_id', String(form.value.project_id))
    fd.append('file', uploadedFile.value)
    if (form.value.model_provider_id) fd.append('model_provider_id', String(form.value.model_provider_id))
    if (form.value.prompt_template_id) fd.append('prompt_template_id', String(form.value.prompt_template_id))

    progressText.value = '正在转换格式…'
    progressPercent.value = 50

    await documentImportApi.upload(fd)

    progressPercent.value = 100
    progressText.value = '完成'

    resultType.value = 'success'
    resultMsg.value = '上传完成，AI 提取任务已加入队列，请稍后在列表中查看结果'
    emit('saved')
    setTimeout(() => { visible.value = false }, 2000)
  } catch (err) {
    resultType.value = 'error'
    resultMsg.value = '处理失败：' + (err.message || '未知错误')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.progress-section { margin-top: 16px; padding: 12px; background: #f5f7fa; border-radius: 6px; display: flex; flex-direction: column; gap: 8px; }
.result-section { margin-top: 12px; }
</style>
