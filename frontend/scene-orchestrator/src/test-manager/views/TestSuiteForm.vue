<template>
  <div class="ts-form">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="$router.back()" class="back-btn"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h3 class="page-title">{{ isEdit ? '编辑测试套件' : '新建测试套件' }}</h3>
      </div>
    </div>

    <el-form ref="formRef" :model="form" label-width="80px" class="main-form">
      <el-card shadow="never" class="form-card">
        <template #header><span class="card-title"><el-icon><InfoFilled /></el-icon> 基础信息</span></template>

        <el-row :gutter="24">
          <el-col :xs="24" :md="12">
            <el-form-item label="名称" required>
              <el-input v-model="form.name" placeholder="套件名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="项目">
              <el-select v-model="form.project" disabled style="width:100%">
                <el-option v-for="p in projectStore.projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :xs="24" :md="12">
            <el-form-item label="分组">
              <el-select v-model="form.group" clearable placeholder="选择分组" style="width:100%">
                <el-option v-for="g in groupStore.flatList" :key="g.id" :label="g.name" :value="g.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12" />
        </el-row>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="套件描述..." />
        </el-form-item>
      </el-card>

      <el-alert type="info" :closable="false" class="info-alert" show-icon>
        <template #title>创建套件后，可在套件详情中添加测试用例</template>
      </el-alert>

      <div class="form-footer">
        <el-button size="large" @click="$router.back()">取消</el-button>
        <el-button size="large" type="primary" :loading="submitting" @click="submit">保存</el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useProjectStore } from '../stores/project.js'
import { useTestSuiteStore } from '../stores/testSuite.js'
import { useTestSuiteGroupStore } from '../stores/testSuiteGroup.js'
import { testSuiteApi } from '../api/index.js'

const props = defineProps({ id: [String, Number] })
const router = useRouter()
const projectStore = useProjectStore()
const store = useTestSuiteStore()
const groupStore = useTestSuiteGroupStore()

const submitting = ref(false)
const form = reactive({ name:'', project:null, group:null, description:'' })
const isEdit = computed(() => !!props.id)

onMounted(async () => {
  form.project = projectStore.currentProjectId
  if (form.project) groupStore.loadList(form.project)
  if (isEdit.value) {
    try {
      const data = await testSuiteApi.get(props.id)
      form.name = data.name; form.project = data.project
      form.group = data.group; form.description = data.description || ''
    } catch (e) { ElMessage.error('加载失败') }
  }
})

async function submit() {
  if (!form.name) { ElMessage.warning('请输入名称'); return }
  submitting.value = true
  try {
    const payload = { ...form, group: form.group || null }
    if (isEdit.value) { await store.update(props.id, payload); ElMessage.success('更新成功') }
    else { await store.create(payload); ElMessage.success('创建成功') }
    router.back()
  } catch (e) { ElMessage.error(e.message) }
  finally { submitting.value = false }
}
</script>

<style scoped>
.ts-form { max-width:720px; margin:0 auto; }

/* ---- 页面标题 ---- */
.page-header {
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:20px;
}
.page-header-left { display:flex; align-items:center; gap:8px; }
.back-btn { font-size:14px; color:#606266; }
.page-title { font-size:22px; font-weight:600; color:#303133; margin:0; line-height:1.3; }

/* ---- 表单卡片 ---- */
.form-card { border:1px solid #ebeef5; border-radius:8px; margin-bottom:16px; }
.form-card :deep(.el-card__header) {
  padding:12px 16px; border-bottom:1px solid #f0f0f0; background:#fafafa;
}
.card-title { font-size:16px; font-weight:600; color:#303133; display:flex; align-items:center; gap:6px; }

.main-form :deep(.el-form-item) { margin-bottom:18px; }
.main-form :deep(.el-form-item:last-child) { margin-bottom:0; }
.main-form :deep(.el-input-number) { width:100%; }

.info-alert { margin-bottom:20px; }

/* ---- 提交按钮 ---- */
.form-footer {
  display:flex; justify-content:flex-end; gap:12px; padding:8px 0 32px;
}
</style>
