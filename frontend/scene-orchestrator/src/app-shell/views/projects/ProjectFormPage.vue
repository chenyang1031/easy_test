<template>
  <div class="project-form-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="goBack" :icon="ArrowLeft" class="back-btn" />
        <h2 class="page-title">{{ isEdit ? '编辑项目' : '新建项目' }}</h2>
      </div>
    </div>

    <!-- 加载骨架 -->
    <div v-if="loading" class="skeleton-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 表单 -->
    <template v-else>
      <div class="panel-card">
        <div class="card-header-row">
          <span class="card-section-title">
            <el-icon><FolderOpened /></el-icon> 基本信息
          </span>
        </div>
        <div class="form-body">
          <el-form label-position="top" class="project-form">
            <el-form-item
              label="项目名称"
              :error="formErrors.name"
            >
              <el-input
                v-model="form.name"
                placeholder="输入项目名称..."
                maxlength="100"
                size="large"
                show-word-limit
                clearable
              />
              <div class="form-help">给你的项目起一个简短的名称（例如：OA 系统、电商平台）</div>
            </el-form-item>

            <el-form-item
              label="描述"
              :error="formErrors.description"
            >
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="5"
                placeholder="描述项目的用途和范围..."
                maxlength="500"
                show-word-limit
              />
              <div class="form-help">详细描述项目，便于团队成员理解项目背景</div>
            </el-form-item>
          </el-form>
        </div>

        <div class="form-footer">
          <div>
            <el-button @click="goBack">取消</el-button>
          </div>
          <div class="form-footer-right">
            <el-button type="primary" :loading="saving" @click="handleSubmit">
              <el-icon><Check /></el-icon> {{ isEdit ? '保存修改' : '创建项目' }}
            </el-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check, FolderOpened } from '@element-plus/icons-vue'
import { projectApi } from '../../../projects/api/index.js'

const router = useRouter()
const route = useRoute()

const isEdit = computed(() => !!route.params.id)
const loading = ref(false)
const saving = ref(false)
const form = ref({ name: '', description: '' })
const formErrors = reactive({ name: '', description: '' })

function clearErrors() {
  formErrors.name = ''
  formErrors.description = ''
}

function goBack() {
  if (isEdit.value) {
    router.push(`/projects/${route.params.id}`)
  } else {
    router.push('/projects')
  }
}

function validate() {
  clearErrors()
  let valid = true
  if (!form.value.name.trim()) {
    formErrors.name = '项目名称不能为空'
    valid = false
  } else if (form.value.name.trim().length < 2) {
    formErrors.name = '项目名称至少需要 2 个字符'
    valid = false
  }
  return valid
}

async function handleSubmit() {
  if (!validate()) return

  saving.value = true
  try {
    const payload = { name: form.value.name.trim(), description: form.value.description.trim() || '' }

    if (isEdit.value) {
      await projectApi.update(route.params.id, payload)
      ElMessage.success('项目已更新')
      router.push(`/projects/${route.params.id}`)
    } else {
      const result = await projectApi.create(payload)
      ElMessage.success('项目已创建')
      router.push(`/projects/${result.id}`)
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

async function loadDetail() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const data = await projectApi.get(route.params.id)
    form.value = { name: data.name || '', description: data.description || '' }
  } catch (e) {
    ElMessage.error('加载项目信息失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadDetail() })
</script>

<style scoped>
.project-form-page { padding: 0; min-height: 100%; }

/* ---- 页面标题 ---- */
.page-header { display: flex; align-items: center; margin-bottom: 20px; }
.page-header-left { display: flex; align-items: center; gap: 8px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.back-btn { font-size: 20px; padding: 4px; }

/* ---- 骨架屏 ---- */
.skeleton-wrap { background: #fff; border-radius: 10px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }

/* ---- 卡片 ---- */
.panel-card {
  background: #fff; border-radius: 10px; padding: 24px; max-width: 720px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  margin: 0 auto;
}
.card-header-row {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #f2f3f5;
}
.card-section-title { font-size: 16px; font-weight: 600; color: #303133; display: flex; align-items: center; gap: 6px; }

/* ---- 表单 ---- */
.form-body { min-height: 100px; }
.project-form :deep(.el-form-item) { margin-bottom: 24px; }
.project-form :deep(.el-form-item__label) { font-weight: 500; color: #303133; }
.form-help { font-size: 12px; color: #909399; margin-top: 4px; line-height: 1.4; }

/* ---- 底部按钮 ---- */
.form-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 32px; padding-top: 20px; border-top: 1px solid #ebeef5;
}
</style>
